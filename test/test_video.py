import unittest

import os
import numpy as np
from isimple.___restructure_flat import VideoInterface, VideoFileTypeError
import cv2
from threading import Thread
import time


# Get validation frames from test video ~ OpenCV
__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'
__FRAMES__ = [1, 20, 50]
__TRANSFORM__ = np.random.rand(3,3)

__TEST_FRAME__ = {}
__TEST_FRAME_HSV__ = {}
__TEST_TRANSFORMED_FRAME__ = {}

if os.path.isfile(__VIDEO__):
    capture = cv2.VideoCapture(__VIDEO__)
else:
    raise FileNotFoundError

for frame_number in __FRAMES__:
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = capture.read()
    __TEST_FRAME__[frame_number] = frame

    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    __TEST_FRAME_HSV__[frame_number] = frame_hsv

    transformed_frame = cv2.transform(frame_hsv, __TRANSFORM__)
    __TEST_TRANSFORMED_FRAME__[frame_number] = transformed_frame


class VideoInterfaceTest(unittest.TestCase):
    def assertEqualFrames(self, frame1, frame2):
        self.assertTrue(np.equal(frame1, frame2).all())

    def assertInCache(self, vi, frame_number, to_hsv):
        self.assertTrue(
            vi._get_key(frame_number, to_hsv) in vi._cache
        )

    def test_path_problems(self):
        self.assertRaises(
            FileNotFoundError, VideoInterface, 'non-existent'
        )
        self.assertRaises(
            VideoFileTypeError, VideoInterface, __DESIGN__
        )

    def test_get_frame_hsv(self):
        with VideoInterface(__VIDEO__) as vi:
            for frame_number, frame in __TEST_FRAME_HSV__.items():
                self.assertEqualFrames(
                    frame, vi.get_frame(frame_number, True)
                )
                self.assertInCache(vi, frame_number, True)

    def test_get_frame(self):
        with VideoInterface(__VIDEO__) as vi:
            for frame_number, frame in __TEST_FRAME__.items():
                self.assertTrue(
                    np.equal(
                        frame, vi.get_frame(frame_number, False)
                    ).all()
                )
                self.assertInCache(vi, frame_number, False)

    def test_get_cached_frame(self):
        with VideoInterface(__VIDEO__) as vi:
            for frame_number in __TEST_FRAME_HSV__.keys():
                # Read frames, which are cached
                vi.get_frame(frame_number, to_hsv=True)
                self.assertInCache(vi, frame_number, True)

            # Disconnect VideoInterface from OpenCV capture
            #  to ensure frames are read from cache
            vi._capture = None

            # Read frames
            for frame_number, frame in __TEST_FRAME_HSV__.items():
                self.assertInCache(vi, frame_number, True)
                self.assertEqualFrames(
                        frame, vi.get_frame(frame_number, True)
                )

    def test_get_cached_frame_threaded(self):
        __INTERVAL__ = 0.1

        def read_frames():
            with VideoInterface(__VIDEO__) as vi_source:
                for frame_number in __TEST_FRAME__.keys():
                    time.sleep(__INTERVAL__)
                    vi_source.get_frame(frame_number, to_hsv=True)

        # Start timing main thread executin time
        t0 = time.time()

        with VideoInterface(__VIDEO__) as vi_sink:
            # Disconnect VideoInterface from OpenCV capture
            #  to ensure frames are read from cache
            vi_sink._capture = None

            subthread = Thread(target = read_frames)
            subthread.start()

            subthread_frames = []
            for frame_number in __TEST_FRAME_HSV__.keys():
                frame = None
                key = vi_sink._get_key(frame_number, True)
                while frame is None:
                    # Can't get frame while not in cache
                    if key in vi_sink._cache:
                        frame = vi_sink.get_frame(
                            frame_number, True, from_cache=True
                        )
                subthread_frames.append(frame)

            subthread.join()

        # Main thread should have waited at least as long as subthread
        self.assertGreaterEqual(
            time.time() - t0,
            len(__FRAMES__) * __INTERVAL__
        )

        for frame1, fn in zip(subthread_frames, __TEST_FRAME_HSV__.keys()):
            self.assertEqualFrames(frame1, __TEST_FRAME_HSV__[fn])


if __name__ == '__main__':
    unittest.main()
