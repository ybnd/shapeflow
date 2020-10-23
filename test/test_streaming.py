import unittest

from typing import Generator, Type, Callable
from threading import Thread
import time

import cv2
import numpy as np

from shapeflow.core import Endpoint, Dispatcher, stream_image
from shapeflow.core.config import Instance, BaseConfig
from shapeflow.core.streaming import BaseStreamer, JpegStreamer, JsonStreamer, streams, stream


class StreamerThread(Thread):
    stream: Generator
    data: list

    def __init__(self, stream: Generator):
        super().__init__(daemon=True)
        self.stream = stream
        self.data = []

    def run(self):
        try:
            while True:
                self.data.append(next(self.stream))
        except StopIteration:
            pass


class BaseStreamerTest(unittest.TestCase):
    streamer_type: Type[BaseStreamer]

    valid_data: list
    invalid_data: list

    _timeout: float = 0.1

    def test_push_valid_data(self):
        streamer = self.streamer_type()

        thread = StreamerThread(streamer.stream())
        thread.start()

        for data in self.valid_data:
            streamer.push(data)

        time.sleep(self._timeout)
        streamer.stop()

        thread.join()

        # Valid data should 'arrive' at the generator
        if streamer._double_yield:
            self.assertEqual(
                2 * len(self.valid_data), len(thread.data)
            )
        else:
            self.assertEqual(
                len(self.valid_data), len(thread.data)
            )

    def test_push_invalid_data(self):
        streamer = self.streamer_type()

        thread = StreamerThread(streamer.stream())
        thread.start()

        for data in self.invalid_data:
            streamer.push(data)

        time.sleep(self._timeout)
        streamer.stop()

        thread.join()

        # Invalid data is dropped (with a warning)
        self.assertEqual(
            0, len(thread.data)
        )


class JpegStreamerTest(BaseStreamerTest):
    streamer_type = JpegStreamer

    valid_data: list = [
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8),
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8),
    ]
    invalid_data: list = [
        'not an image',
        None,
        {'oops': 'json', 'wrong': 'streamer'},
    ]


class JsonStreamerTest(BaseStreamerTest):
    streamer_type = JsonStreamer

    valid_data: list = [
        {'something': 'or other'},
        {'something': 'else'},
    ]
    invalid_data: list = [
        'not a dict',
        None,
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8),
    ]


class StreamHandlerTest(unittest.TestCase):
    def test_normal_operation(self):
        class TestDispatcher(Dispatcher):
            method1 = Endpoint(Callable[[], np.ndarray], stream_image)
            method2 = Endpoint(Callable[[], np.ndarray], stream_image)

        class StreamableClass(object):
            @stream
            @TestDispatcher.method1.expose()
            def method1(self) -> np.ndarray:
                return np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

            @stream
            @TestDispatcher.method2.expose()
            def method2(self) -> np.ndarray:
                return np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

        streamable = StreamableClass()
        dispatcher = TestDispatcher(streamable)

        thread1 = StreamerThread(
            streams.register(
                streamable, dispatcher.method1.method
            ).stream()
        )
        thread1.start()
        thread2 = StreamerThread(
            streams.register(
                streamable, dispatcher.method2.method
            ).stream()
        )
        thread2.start()

        streams.update()
        time.sleep(0.1)

        # Unregiter specific method
        streams.unregister(streamable, streamable.method1)
        # Unregister all methods & stop
        streams.stop()

        # FrameStreamer -> double yield
        # each streamer pushes once when registered and once on streams.update()
        self.assertEqual(
            4, len(thread1.data)
        )
        self.assertEqual(
            4, len(thread2.data)
        )


del BaseStreamerTest
