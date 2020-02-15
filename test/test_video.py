import unittest

import os
import numpy as np
from isimple.video import \
    VideoFileHandler, VideoAnalyzer, VideoFileTypeError, PixelSum, CachingBackendElement
from isimple.meta import *
from isimple.util import timing
import cv2
from threading import Thread
import time


# Get validation frames from test video ~ "raw" OpenCV
__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'

# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/isimple':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__

FRAMES = [1, 20, 50]
TRANSFORM = np.random.rand(3, 3)

TEST_FRAME_BGR = {}
TEST_FRAME_HSV = {}
TEST_TRANSFORMED_FRAME_BGR = {}
TEST_TRANSFORMED_FRAME_HSV = {}

if os.path.isfile(__VIDEO__):
    capture = cv2.VideoCapture(__VIDEO__)
else:
    raise FileNotFoundError(f'No file at {os.getcwd()}/{__VIDEO__}')

for frame_number in FRAMES:
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = capture.read()
    TEST_FRAME_BGR[frame_number] = frame

    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    TEST_FRAME_HSV[frame_number] = frame_hsv

    dsize = (frame.shape[1], frame.shape[0])
    TEST_TRANSFORMED_FRAME_BGR[frame_number] = cv2.warpPerspective(frame, TRANSFORM, dsize)
    TEST_TRANSFORMED_FRAME_HSV[frame_number] = cv2.warpPerspective(frame_hsv, TRANSFORM, dsize)

# Clear cache
vi = VideoFileHandler(__VIDEO__)
with vi.caching():
    assert vi._cache is not None
    vi._cache.clear()


class FrameTest(unittest.TestCase):
    def assertEqualFrames(self, frame1, frame2):
        self.assertTrue(np.equal(frame1, frame2).all())

    def assertFrameInCache(self, vi, frame_number):
        assert isinstance(vi, CachingBackendElement) and vi._cache is not None
        self.assertTrue(
            vi._get_key(vi._read_frame, vi.path, frame_number) in vi._cache
        )


class VideoInterfaceTest(FrameTest):
    def test_path_problems(self):
        self.assertRaises(
            FileNotFoundError, VideoFileHandler, 'non-existent'
        )
        self.assertRaises(
            VideoFileTypeError, VideoFileHandler, __DESIGN__
        )

    def test_get_frame(self):
        with VideoFileHandler(__VIDEO__) as vi:
            for frame_number, frame in TEST_FRAME_HSV.items():
                self.assertTrue(
                    np.equal(
                        frame, vi.read_frame(frame_number)
                    ).all()
                )
                self.assertFrameInCache(vi, frame_number)

    def test_get_cached_frame(self):
        with VideoFileHandler(__VIDEO__) as vi:
            for frame_number in TEST_FRAME_HSV.keys():
                # Read frames, which are cached
                self.assertEqualFrames(
                    TEST_FRAME_HSV[frame_number],
                    vi.read_frame(frame_number)
                )
                self.assertFrameInCache(vi, frame_number)


            # Disconnect VideoInterface from OpenCV capture
            #  to ensure frames are read from cache
            vi._capture = None

            # Read frames
            for frame_number, frame in TEST_FRAME_HSV.items():
                self.assertFrameInCache(vi, frame_number)
                self.assertEqualFrames(
                        frame, vi.read_frame(frame_number)
                )

    def test_get_cached_frame_threaded(self):
        __INTERVAL__ = 0.1

        @timing
        def read_frames_and_cache():
            with VideoFileHandler(__VIDEO__) as vi_source:
                for frame_number in TEST_FRAME_HSV.keys():
                    time.sleep(__INTERVAL__)
                    vi_source.read_frame(frame_number)

        # Start timing main thread executin time
        t0 = time.time()

        with VideoFileHandler(__VIDEO__) as vi_sink:
            vi_sink._config['consumer'] = True

            subthread = Thread(target = read_frames_and_cache)
            subthread.start()

            subthread_frames = []
            for frame_number in TEST_FRAME_HSV.keys():
                frame = vi_sink.read_frame(frame_number)
                subthread_frames.append(frame)

            subthread.join()

        # Main thread should have waited
        #  at least as long as the subthread has
        self.assertGreaterEqual(
            time.time() - t0,
            len(FRAMES) * __INTERVAL__
        )

        for frame1, fn in zip(subthread_frames, TEST_FRAME_HSV.keys()):
            self.assertEqualFrames(frame1, TEST_FRAME_HSV[fn])


class VideoAnalyzerTest(FrameTest):
    config = {
        'keep_renders': True,
        'transform_matrix': TRANSFORM,
    }

    def test_aloading(self):
        config = {k: v for k, v in self.config.items()}
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)
        self.assertEqual(self.config, config)

        self.assertListEqual(
            sorted(list(os.listdir(va.design.render_dir))),
            sorted([
                '1 - WLC_SIMPLE.png',
                '2 - PM_SIMPLE.png',
                '3 - push1.png',
                '4 - push2.png',
                '5 - WLC_iSIMPLE.png',
                '6 - PM_iSIMPLE.png',
                '7 - block.png',
                '8 - PM_block.png',
                '9 - SLC.png',
                'overlay.png'
            ])
        )
        va.design._clear_renders()

        self.assertTrue(hasattr(va.design, '_masks'))
        self.assertEqual(len(va.design._masks), 9)
        self.assertTrue(
            np.all(np.equal(TRANSFORM, va.transform.transform_matrix))
        )

    def test_loading_path_problems(self):
        self.assertRaises(
            FileNotFoundError, VideoAnalyzer, __VIDEO__, 'non-existent', [PixelSum]
        )

        # Not testing cache, don't need with statement
        va1 = VideoAnalyzer(__VIDEO__, __VIDEO__, self.config)
        va2 = VideoAnalyzer(__VIDEO__, __DESIGN__)
        self.assertTrue(np.equal(va1.design._overlay, va2.design._overlay).all())
        self.assertEqual(len(va1.design._masks), len(va2.design._masks))

        va1.design._clear_renders()

    def test_frame_number_generator(self):  # todo: don't need the design to load here
        # Don't overwrite self.config
        config = {k:v for k,v in self.config.items()}

        config.update(
            {
                'frame_interval_setting': 'Nf',
                'Nf': 1000, # test video has only 68 frames
            }
        )

        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)
        frames = [f for f in va.frame_numbers()]

        self.assertEqual(68, len(frames))

        config.update(
            {
                'frame_interval_setting': 'dt',
                'dt': 60,  # The test video is at ~ 0.1 fps
            }
        )

        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)
        frames = [f for f in va.frame_numbers()]

        self.assertEqual(12, len(frames))

    def test_context(self):  # todo: don't need the design to load here
        # Don't overwrite self.config
        config = {k: v for k, v in self.config.items()}

        # Caching is disabled
        config.update(
            {'do_cache': False, 'do_background': False}
        )
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertEqual(None, va.video._cache)
            self.assertEqual(None, va.video._background)
        self.assertEqual(None, va.video._cache)

        # Caching is disabled, but background caching is enabled (ignored)
        config.update(
            {'do_cache': False, 'do_background': True}
        )
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertEqual(None, va.video._cache)
            self.assertEqual(None, va.video._background)
        self.assertEqual(None, va.video._cache)

        # Caching is enabled
        config.update(
            {'do_cache': True, 'do_background': False}
        )
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
            self.assertEqual(None, va.video._background)
        self.assertEqual(None, va.video._cache)

        # Background caching is enabled
        config.update(
            {'do_cache': True, 'do_background': True}
        )
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, config)

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
            #self.assertNotEqual(None, va.video._background)  # todo: implement backgrond caching
        self.assertEqual(None, va.video._cache)

        # By default, main-thread caching is enabled
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, self.config)

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
            self.assertEqual(None, va.video._background)
        self.assertEqual(None, va.video._cache)

    def test_get_frame(self):
        va = VideoAnalyzer(__VIDEO__, __DESIGN__, self.config)

        with va.caching():
            for fn in va.frame_numbers():
                frame = va.get_transformed_frame(fn)
                if fn in FRAMES:  # todo: !!!!!! if this test checks out, transform is not applied (:
                    self.assertEqualFrames(TEST_TRANSFORMED_FRAME_HSV[fn], frame)


if __name__ == '__main__':
    unittest.main()
