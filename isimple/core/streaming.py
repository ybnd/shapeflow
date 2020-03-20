import abc
import sys
from typing import Optional, Tuple, Generator, Callable, Dict, Type, Any
import time

import queue
import threading
import time

import numpy as np
import cv2


# cheated off of https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/


class FrameStreamer(abc.ABC):
    _queue: queue.Queue
    _stop: threading.Event

    _empty_queue_timeout: float = 0.01
    _stop_timeout: float = 60

    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()

    def push(self, frame: np.ndarray):
        self._queue.put(frame)

    def stop(self):
        self._stop.set()
        with self._queue.mutex:
            self._queue.queue.clear()

    def stream(self) -> Generator[bytes, None, None]:
        self._stop.clear()
        last_yield = time.time()
        while not self._stop.is_set():
            if not self._queue.empty():
                (success, encoded_frame) = self._encode(self._queue.get())
                if not success:
                    continue
                else:
                    last_yield = time.time()
                    yield self._decorate(encoded_frame)
            else:
                if time.time() - last_yield > self._stop_timeout:
                    # If the stream is inactive for more than 10 seconds,
                    # stop it.
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
        return cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_HSV2BGR))

    def _decorate(self, encoded_frame: bytes) -> bytes:
        return (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                bytearray(encoded_frame) + b"\r\n")


class StreamHandler(object):  # todo: is a singleton
    """A singleton object to handle streaming frames from methods
    """
    _streams: Dict[Callable[[Any], np.ndarray], FrameStreamer]

    def __init__(self):
        self._streams = {}

    def register(self, method: Callable[[Any], np.ndarray], stream_type: Type[FrameStreamer] = JpegStreamer) -> FrameStreamer:
        """Register `method`, start a streamer.
            If `method` has been registered already, return its streamer.
        """
        if method not in self._streams:
            stream = stream_type()
            self._streams[method] = stream
        else:
            stream = self._streams[method]
        return stream

    def is_registered(self, method: Callable[[Any], np.ndarray]) -> bool:
        return method in self._streams

    def push(self, method: Callable[[Any], np.ndarray], frame: np.ndarray):
        """If `method` is registered, push `frame` to its streamer.
        """
        if method in self._streams:
            self._streams[method].push(frame)

    def unregister(self, method):
        """Unregister `method`: stop its streamer & delete
        """
        if method in self._streams:
            self._streams[method].stop()
            del self._streams[method]

    def stop(self):
        for method in self._streams:
            self.unregister(method)


# Global StreamHandler instance
streams = StreamHandler()


def stream(method):
    """Decorator for streaming methods.
        To stream frames, the wrapped method should be registered
         in the global StreamHandler `streams`.
    """
    def wrapped_method(*args, **kwargs):
        frame = method(*args, **kwargs)
        # Push frame to streamer
        streams.push(method, frame)
        return frame

    # Pass on attributes from `method` to `wrapped_method` todo: this is *very* wonky!
    for (attr, value) in method.__dict__.items():
        setattr(wrapped_method, attr, value)

    return wrapped_method
