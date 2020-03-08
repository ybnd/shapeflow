import abc
import sys
from typing import Optional, Tuple, Generator
import time

import queue
import threading

import numpy as np
import cv2


# cheated off of https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/


class FrameStreamer(abc.ABC):
    _queue: queue.Queue
    _stop: threading.Event

    _empty_queue_timeout: float = 0.01

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
        while not self._stop.is_set():
            if not self._queue.empty():
                (success, encoded_frame) = self._encode(self._queue.get())
                if not success:
                    continue
                else:
                    yield self._decorate(encoded_frame)
            else:
                time.sleep(self._empty_queue_timeout)

    @abc.abstractmethod
    def _encode(self, frame: np.ndarray) -> Tuple[bool, bytes]:
        raise NotImplementedError

    @abc.abstractmethod
    def _decorate(self, encoded_frame: bytes) -> bytes:
        raise NotImplementedError


class JpegStreamer(FrameStreamer):
    def _encode(self, frame: np.ndarray) -> Tuple[bool, bytes]:
        return cv2.imdecode(".jpg", frame)

    def _decorate(self, encoded_frame: bytes) -> bytes:
        return (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                bytearray(encoded_frame) + b"\r\n")
