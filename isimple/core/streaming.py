import abc
import json
from typing import Optional, Tuple, Generator, Callable, Dict, Type, Any, Union, List
from functools import wraps

from isimple import get_logger
from isimple.core import _Streaming, Lockable

from isimple.util import Singleton
from isimple.util.meta import unbind
import queue

import threading
import time

import numpy as np
import cv2


# cheated off of https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/

log = get_logger(__name__)


class BaseStreamer(abc.ABC):
    _queue: queue.Queue
    _stop: threading.Event
    _paused: bool

    _empty_queue_timeout: float = 0.02
    _stop_timeout: float = 60

    _boundary: Optional[bytes] = None
    _content_type: Optional[bytes] = None
    _mime_type: Optional[str] = None

    _double_yield: bool = False

    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._paused = False

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
                    log.vdebug(f"{self}: yielding...")
                    yield output
                    if self._double_yield:
                        yield output   # todo: image streaming doesn't work properly if not yielded twice for some reason
                else:
                    log.warning(f"{self.__class__.__name__}: encoding failed for {value}")
                    continue
            else:
                time.sleep(self._empty_queue_timeout)

    def stop(self):
        self._stop.set()
        with self._queue.mutex:
            self._queue.queue.clear()

    @classmethod
    def mime_type(cls) -> str:
        if cls._mime_type is None:
            assert cls._boundary is not None
            return f"multipart/x-mixed-replace; boundary={cls._boundary.decode('utf-8')}"
        else:
            return cls._mime_type

    @classmethod
    def content_type(cls):
        return cls._content_type

    @abc.abstractmethod
    def _validate(self, value: Any) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def _encode(self, value: Any) -> Optional[bytes]:
        raise NotImplementedError

    @abc.abstractmethod
    def _decorate(self, value: Optional[bytes]) -> Optional[bytes]:
        raise NotImplementedError


class JsonStreamer(BaseStreamer):
    _boundary = b"data"
    _mime_type = "text/event-stream"

    def _validate(self, value: Any) -> bool:
        return isinstance(value, dict)

    def _encode(self, value: dict) -> Optional[bytes]:
        try:
            return json.dumps(value).encode('utf-8')
        except Exception:  # todo: make more specific
            return None

    def _decorate(self, value: Optional[bytes]) -> Optional[bytes]:
        if value is not None:
            return b"data:   " + value + b"\n\n"
        else:
            return None


class EventStreamer(JsonStreamer):
    def event(self, category: str, id: str, data: Any):
        """Push a JSON event

        :param category: event category
        :param id: UUID of event source
        :param data: event data
        :return:
        """
        log.debug(f"pushing event - id:{id} category:{category} data:{data}")
        self.push({'category': category, 'id': id, 'data': data})

    def stop(self):
        self.push({'categroy': 'close', 'data': ''})
        super().stop()


class FrameStreamer(BaseStreamer):
    _boundary = b"frame"

    _empty_queue_timeout: float = 0.02
    _stop_timeout: float = 60

    _double_yield = True

    def _validate(self, value: Any) -> bool:
        return isinstance(value, np.ndarray)

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


class JpegStreamer(FrameStreamer):  # todo: configure quality in settings
    _content_type = b"image/jpeg"

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        # Assuming HSV input frame, cv2.imencode works with BGR
        (success, encoded_frame) = cv2.imencode(
            ".jpg", cv2.cvtColor(frame, cv2.COLOR_HSV2BGR),
            params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        if success:
            return encoded_frame
        else:
            return None


_stream_mapping: dict = {
    _Streaming('json'): JsonStreamer,
    _Streaming('image'): JpegStreamer,
}

class StreamHandler(Lockable):
    """A singleton object to handle streaming frames from methods
    """
    __metaclass__ = Singleton

    _streams: Dict[object, Dict[Callable, BaseStreamer]]

    def __init__(self):
        super().__init__()
        self._streams = {}

    def register(self, instance: object, method, stream_type: Type[BaseStreamer] = None) -> BaseStreamer:
        """Register `method`, start a streamer.
            If `method` has been registered already, return its streamer.
        """
        with self.lock():
            method = unbind(method)

            if self.is_registered(instance, method):
                stream = self._streams[instance][method]
            else:
                if hasattr(method, '_endpoint'):
                    stream_type = _stream_mapping[method._endpoint.streaming]

                if stream_type is not None:
                    stream = stream_type()

                    if instance not in self._streams:
                        self._streams[instance] = {}

                    self._streams[instance][method] = stream
                    log.debug(f'registering {instance}, {method} as {stream}')

                    self.push(instance, method, method(instance))
                else:
                    raise ValueError('cannot resolve stream type')
            return stream

    def is_registered(self, instance: object, method = None) -> bool:
        if instance in self._streams:
            if method is not None:
                return method in self._streams[instance]
            else:
                return True
        else:
            return False

    def push(self, instance: object, method, data):
        """If `method` is registered, push `data` to its streamer.
        """
        method = unbind(method)

        if isinstance(method, list):
            for m in method:
                if self.is_registered(instance, m):
                    log.debug(f"pushing {m.__qualname__} to {self._streams[instance][m]}")
                    self._streams[instance][m].push(data)
        else:
            if self.is_registered(instance, method):
                log.debug(f"pushing {method.__qualname__} to {self._streams[instance][method]}")
                self._streams[instance][method].push(data)

    def unregister(self, instance: object, method = None):
        """Unregister `method`: stop its streamer & delete
        """  # todo: should unregister explicitly e.g. when closing a page
        def _unregister(method):
            method = unbind(method)
            if self.is_registered(instance, method):
                log.debug(f'unregistering {instance}, {method}')
                self._streams[instance][method].stop()
                del self._streams[instance][method]

        with self.lock():
            if method is not None:
                _unregister(method)
            else:
                for method in self._streams[instance].values():
                    _unregister(method)

    def update(self):
        try:
            for instance in self._streams.keys():
                for method in self._streams[instance].keys():
                    try:
                        log.debug(f'updating {instance}, {method}')
                        self.push(instance, method, method(instance))
                    except Exception as e:
                        log.error(f"{e} occured @ {instance}, {method}")
        except RuntimeError:
            log.debug(f"new stream opened while updating")
            # Repeat the update. This doesn't happen too often,
            # so don't worry about the performance hit.
            self.update()
            # Recursion could be problematic if too many streams are opened
            # within a short time span, but this shouldn't be an issue.
        except Exception as e:
            log.error(f"{e} occurred")

    def stop(self):
        for instance in list(self._streams):
            self.unregister(instance)


# Global StreamHandler instance
streams = StreamHandler()


def stream(method):
    """Decorator for streaming methods.
        To stream frames, the wrapped method should be registered
         in the global StreamHandler `streams`.
    """

    @wraps(method)
    def wrapped_method(*args, **kwargs):
        data = method(*args, **kwargs)

        # Push data to streamer
        streams.push(
            instance = args[0],
            method = unbind(method),
            data = data
        )
        return data

    # Pass on attributes from `method` to `wrapped_method` todo: this is *very* wonky!
    for (attr, value) in method.__dict__.items():
        setattr(wrapped_method, attr, value)

    return wrapped_method
