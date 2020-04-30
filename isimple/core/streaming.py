import abc
import sys
import json
from typing import Optional, Tuple, Generator, Callable, Dict, Type, Any, Union, List
import time
from functools import wraps

from isimple import get_logger
import queue
import threading
import time

import numpy as np
import cv2

from isimple.util import timed, sizeof_fmt


# cheated off of https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/

log = get_logger(__name__)


class BaseStreamer(abc.ABC):
    _queue: queue.Queue
    _stop: threading.Event

    _empty_queue_timeout: float = 0.02
    _stop_timeout: float = 60

    _boundary: bytes
    _content_type: bytes

    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()

    def push(self, value: Any):
        if self._validate(value):
            self._queue.put(value)
        else:
            log.warning(f"{self.__class__.__name__}: skipping invalid value")

    def stream(self) -> Generator[Any, None, None]:
        self._stop.clear()

        while not self._stop.is_set():
            if not self._queue.empty():
                value = self._queue.get()
                output = self._decorate(self._encode(value))

                if output is not None:
                    yield output
                    yield output   # todo: doesn't work properly if not yielded twice
                else:
                    log.warning(f"{self.__class__.__name__}: encoding failed")
                    continue
            else:
                time.sleep(self._empty_queue_timeout)

    def stop(self):
        self._stop.set()
        with self._queue.mutex:
            self._queue.queue.clear()

    @classmethod
    def mime_type(cls):
        return f"multipart/x-mixed-replace; boundary={cls._boundary.decode('utf-8')}"

    @classmethod
    def content_type(cls):
        return cls._content_type

    @abc.abstractmethod
    def _validate(self, value: Any) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def _encode(self, value: Any) -> Optional[bytes]:
        raise NotImplementedError

    def _decorate(self, data: Optional[bytes]) -> Optional[bytes]:
        if data is not None:
            try:
                return (
                    b"--frame\r\nContent-Type: "
                    + self.content_type()
                    + b"\r\n\r\n" +
                    bytearray(data)
                    + b"\r\n"
                )
            except Exception as e:
                log.error(e)
                return None
        else:
            return None


class JsonStreamer(BaseStreamer):
    _boundary = b"data"
    _content_type = b"application/json"

    def _validate(self, value: Any) -> bool:
        return isinstance(value, dict)

    def _encode(self, value: dict) -> Optional[bytes]:
        try:
            return json.dumps(value).encode('utf-8')
        except Exception:  # todo: make more specific
            return None


class FrameStreamer(BaseStreamer):  # todo: should be child of Streamer, along with JsonStreamer
    _boundary = b"frame"

    _empty_queue_timeout: float = 0.02
    _stop_timeout: float = 60

    def _validate(self, value: Any) -> bool:
        return isinstance(value, np.ndarray)


class JpegStreamer(FrameStreamer):
    _content_type = b"image/jpeg"

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        # Assuming HSV input frame, cv2.imencode works with BGR
        (success, encoded_frame) = cv2.imencode(
            ".jpg", cv2.cvtColor(frame, cv2.COLOR_HSV2BGR),
            params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        )

        if success:
            return encoded_frame
        else:
            return None


class PngStreamer(FrameStreamer):
    _content_type = b"image/png"

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        # Assume HSV input frame, cv2.imencode works with BGR
        (success, encoded_frame) = cv2.imencode(
            ".png", cv2.cvtColor(frame, cv2.COLOR_HSV2BGR),
            params = [cv2.IMWRITE_PNG_COMPRESSION, 10]
        )

        if success:
            return encoded_frame
        else:
            return None


class StreamHandler(object):  # todo: is a singleton
    """A singleton object to handle streaming frames from methods
    """
    _streams: Dict[tuple, FrameStreamer]
    _lock: threading.Lock

    def __init__(self):
        self._streams = {}
        self._lock = threading.Lock()

    def register(self, instance: object, method, stream_type: Type[FrameStreamer] = JpegStreamer) -> FrameStreamer:
        """Register `method`, start a streamer.
            If `method` has been registered already, return its streamer.
        """
        with self.lock:
            k = self.key(instance, method)
            if k in self._streams:
                log.debug(f'cleaning up {self._streams[k]}')
                self._streams[k].stop()
                del self._streams[k]

            stream = stream_type()
            self._streams[k] = stream

            log.debug(f'registering {k} as {stream}')

            return stream

    def is_registered(self, instance: object, method) -> bool:
        return self.key(instance, method) in self._streams

    @property
    def lock(self):
        return self._lock

    def key(self, instance, method):
        return (instance, method)

    def push(self, instance: object, method, frame: np.ndarray):
        """If `method` is registered, push `frame` to its streamer.
        """
        with self.lock:
            if isinstance(method, list):
                for m in method:
                    k = self.key(instance, m)
                    if k in self._streams:
                        log.debug(f"pushing {m.__qualname__} to stream")
                        self._streams[k].push(frame)
            else:
                k = self.key(instance, method)
                if k in self._streams:
                    log.debug(f"pushing {method.__qualname__} to stream")
                    self._streams[k].push(frame)

    def unregister(self, instance: object, method):
        """Unregister `method`: stop its streamer & delete
        """  # todo: should unregister explicitly e.g. when closing a page
        with self.lock:
            k = self.key(instance, method)
            if k in self._streams:
                self._streams[k].stop()
                del self._streams[k]

    def update(self):
        try:
            for instance, method in self._streams.keys():
                self.push(instance, method, method())
        except RuntimeError:
            log.debug(f"new stream opened while updating")
            # Repeat the update. This doesn't happen too often,
            # so don't worry about the performance hit.
            self.update()
            # Recursion could be problematic if too many streams are opened
            # within a short time span, but this shouldn't be an issue.

    def stop(self):
        for instance, method in self._streams:
            self.unregister(instance, method)


# Global StreamHandler instance
streams = StreamHandler()


def stream(method):  # todo: check method._endpoint._streaming & select Streamer implementation
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
