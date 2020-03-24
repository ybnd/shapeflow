import abc
import sys
from typing import Optional, Tuple, Generator, Callable, Dict, Type, Any, Union, List
import time
from functools import wraps

from isimple import get_logger
import queue
import threading
import time

import numpy as np
import cv2


# cheated off of https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/

log = get_logger(__name__)

class FrameStreamer(abc.ABC):
    _queue: queue.Queue
    _stop: threading.Event

    _empty_queue_timeout: float = 0.01
    _stop_timeout: float = 60

    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()
    def push(self, frame: np.ndarray):
        log.debug(f'{self} - pushing a frame')
        self._queue.put(frame)

    def stop(self):
        log.debug(f'{self} - stopping stream')
        self._stop.set()
        with self._queue.mutex:
            self._queue.queue.clear()

    def join(self):
        self._queue.join()

    def stream(self) -> Generator[bytes, None, None]:
        log.debug('Streaming')
        self._stop.clear()
        last_yield = time.time()

        while not self._stop.is_set():
            if not self._queue.empty():
                log.debug(f'{self} - getting frame from queue')
                frame = self._queue.get()

                (success, encoded_frame) = self._encode(frame)
                if not success:
                    continue
                else:
                    last_yield = time.time()
                    log.debug(f'{self} - yielding a frame')
                    yield self._decorate(encoded_frame)
            else:
                if time.time() - last_yield > self._stop_timeout:
                    self.stop()
                else:
                    time.sleep(self._empty_queue_timeout)  # todo: is this a good idea ~ performance?

    @abc.abstractmethod
    def _encode(self, frame: np.ndarray) -> Tuple[bool, bytes]:
        raise NotImplementedError

    @abc.abstractmethod
    def _decorate(self, encoded_frame: bytes) -> bytes:
        raise NotImplementedError


class JpegStreamer(FrameStreamer):
    def _encode(self, frame: np.ndarray) -> Tuple[bool, bytes]:
        # Assume HSV input frame, cv2.imencode works with BGR
        log.debug(f'{self} - encoding frame')
        return cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_HSV2BGR))

    def _decorate(self, encoded_frame: bytes) -> bytes:
        log.debug(f'{self} - decorating frame')
        return (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                bytearray(encoded_frame) + b"\r\n")


class StreamHandler(object):  # todo: is a singleton
    """A singleton object to handle streaming frames from methods
    """
    _streams: Dict[Tuple[object, str], FrameStreamer]
    _lock: threading.Lock

    def __init__(self):
        self._streams = {}
        self._lock = threading.Lock()

    def register(self, instance: object, method: Callable[[Any], np.ndarray], stream_type: Type[FrameStreamer] = JpegStreamer) -> FrameStreamer:
        """Register `method`, start a streamer.
            If `method` has been registered already, return its streamer.
        """
        with self.lock:
            log.debug(f'trying to register {instance}, {method}')
            k = self.key(instance, method)
            if k in self._streams:
                log.debug(f'Cleaning up {self._streams[k]}')
                self._streams[k].stop()
                self._streams[k].join()
                del self._streams[k]

            stream = stream_type()
            self._streams[k] = stream

            log.debug(f'registering {k} as {stream}')

            return stream


    def is_registered(self, instance: object, method: Callable[[Any], np.ndarray]) -> bool:
        return self.key(instance, method) in self._streams

    @property
    def lock(self):
        return self._lock

    def key(self, instance, method):
        return (instance, method.__qualname__)

    def push(self, instance: object, method: Union[Callable[[Any], np.ndarray], List[Callable[[Any], np.ndarray]]], frame: np.ndarray):
        """If `method` is registered, push `frame` to its streamer.
        """
        log.debug('Pushing to streamers')
        with self.lock:
            if isinstance(method, list):
                for m in method:
                    k = self.key(instance, m)
                    if k in self._streams:
                        self._streams[k].push(frame)
                    else:
                        log.debug(f'Skipping {k}')
            else:
                k = self.key(instance, method)
                if k in self._streams:
                    self._streams[k].push(frame)
                else:
                    log.debug(f'Skipping {k}')
        log.debug('Done pushing to streamers')

    def unregister(self, k):
        """Unregister `method`: stop its streamer & delete
        """
        if k in self._streams:
            self._streams[k].stop()
            del self._streams[k]

    def stop(self):
        for k in self._streams:
            self.unregister(k)


# Global StreamHandler instance
streams = StreamHandler()


def stream(method):
    """Decorator for streaming methods.
        To stream frames, the wrapped method should be registered
         in the global StreamHandler `streams`.
    """
    @wraps(method)
    def wrapped_method(*args, **kwargs):
        frame = method(*args, **kwargs)
        # Push frame to streamer
        streams.push(instance = args[0], method = method, frame = frame)
        return frame

    # Pass on attributes from `method` to `wrapped_method` todo: this is *very* wonky!
    for (attr, value) in method.__dict__.items():
        setattr(wrapped_method, attr, value)

    return wrapped_method
