import unittest
from copy import deepcopy

import os
import time
import copy
import numpy as np
import cv2
from threading import Thread
import shutil

from OnionSVG import OnionSVG

from isimple.config import VideoFileHandlerConfig, TransformHandlerConfig, \
    DesignFileHandlerConfig, VideoAnalyzerConfig, TransformType, PerspectiveTransformConfig
from isimple.video import VideoFileHandler, VideoFileTypeError, \
    CachingInstance, VideoAnalyzer
from isimple import settings
from isimple.core.config import *

# Get validation frames from test video ~ "raw" OpenCV
__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'
__DPI__ = 400

# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/isimple':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__

OnionSVG(__DESIGN__, dpi=__DPI__).peel('all', to = '.render')
overlay = cv2.imread('.render/overlay.png')
shutil.rmtree('.render')

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

    dsize = (overlay.shape[1], overlay.shape[0])
    TEST_TRANSFORMED_FRAME_BGR[frame_number] = cv2.warpPerspective(frame, TRANSFORM, dsize, borderValue=(255,255,255))
    TEST_TRANSFORMED_FRAME_HSV[frame_number] = cv2.warpPerspective(frame_hsv, TRANSFORM, dsize, borderValue=(255,255,255))

# Clear cache
vi = VideoFileHandler(__VIDEO__)
with vi.caching():
    assert vi._cache is not None
    vi._cache.clear()


class FrameTest(unittest.TestCase):
    def assertEqualArray(self, frame1, frame2):
        self.assertTrue(np.equal(frame1, frame2).all())

    def assertFrameInCache(self, vi, frame_number):
        assert isinstance(vi, CachingInstance) and vi._cache is not None
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
                self.assertEqualArray(
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
                self.assertEqualArray(
                        frame, vi.read_frame(frame_number)
                )

    def test_get_cached_frame_threaded(self):
        __INTERVAL__ = 0.1

        def read_frames_and_cache():
            with VideoFileHandler(__VIDEO__) as vi_source:
                for frame_number in TEST_FRAME_HSV.keys():
                    time.sleep(__INTERVAL__)
                    vi_source.read_frame(frame_number)

        # Start timing main thread executin time
        t0 = time.time()

        with VideoFileHandler(
                __VIDEO__, None
        ) as vi_sink:
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
            self.assertEqualArray(frame1, TEST_FRAME_HSV[fn])


class VAConfigTest(FrameTest):
    def test_config_propagation(self):
        d = DesignFileHandlerConfig(smoothing = 37)
        va = VideoAnalyzerConfig(design=d)

        self.assertEqualArray(d.smoothing, va.design.smoothing)


class VideoAnalyzerTest(FrameTest):
    config = VideoAnalyzerConfig(
        video_path=__VIDEO__,
        design_path=__DESIGN__,
        transform=TransformHandlerConfig(type=TransformType('PerspectiveTransform')),
        video=VideoFileHandlerConfig(do_cache=False),
        design=DesignFileHandlerConfig(),
    )

    def test_loading(self):
        config = deepcopy(self.config)

        og_keep = deepcopy(settings.render.keep)
        settings.render.keep=True  # keep renders
        config.design(do_cache=False) # don't use cached design renders

        va = VideoAnalyzer(config)
        va.launch()
        # self.assertEqual(self.config, config)  # todo: replace with a less problematic assertion

        self.assertListEqual(
            sorted(list(os.listdir(settings.render.dir))),
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

        settings.render.keep=og_keep  # set keep renders back to original setting

    def test_loading_after_init(self):
        config = deepcopy(self.config)

        og_cache = deepcopy(settings.cache)
        og_render = deepcopy(settings.render)
        settings.cache.do_cache=False # force render
        settings.render.keep=True # keep renders

        va = VideoAnalyzer()

        self.assertFalse(hasattr(va, 'video'))
        self.assertFalse(hasattr(va, 'design'))
        self.assertFalse(hasattr(va, 'transform'))

        va.set_config(config.to_dict())
        va.launch()
        # self.assertEqual(self.config, config)  # todo: replace with a less problematic assertion

        self.assertListEqual(
            sorted(list(os.listdir(settings.render.dir))),
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

        settings.cache = og_cache
        settings.render = og_render

    def test_frame_number_generator(self):  # todo: don't need the design to load here
        # Don't overwrite self.config
        config = deepcopy(self.config)

        config.frame_interval_setting = 'Nf'
        config.Nf = 1000
        va = VideoAnalyzer(config)
        va.launch()
        frames = [f for f in va.frame_numbers()]

        self.assertEqual(67, len(frames))

        config.frame_interval_setting = 'dt'
        config.dt = 60
        va = VideoAnalyzer(config)
        va.launch()
        frames = [f for f in va.frame_numbers()]

        self.assertEqual(12, len(frames))

    @unittest.skip("Unreliable, needs a deep dive")
    def test_context(self):  # todo: don't need the design to load here
        # Don't overwrite self.config
        config = deepcopy(self.config)
        og_cache = deepcopy(settings.cache)

        # Caching is disabled
        settings.cache.do_cache = False
        settings.cache.do_background = False
        va = VideoAnalyzer(config)
        va.launch()

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertEqual(None, va.video._cache)
        self.assertEqual(None, va.video._cache)

        # Caching is enabled
        settings.cache.do_cache = True
        settings.cache.do_background = False
        va = VideoAnalyzer(config)
        va.launch()

        # self.assertEqual(None, va.video._cache)  todo: cache stays open ~ isimple.main -- not sure why
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
        self.assertEqual(None, va.video._cache)

        # Background caching is enabled
        settings.cache.do_cache = True
        settings.cache.do_background = True
        va = VideoAnalyzer(config)
        va.launch()

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
        self.assertEqual(None, va.video._cache)

        # By default, main-thread caching is enabled
        va = VideoAnalyzer(VideoAnalyzerConfig(__VIDEO__, __DESIGN__))
        va.launch()

        self.assertEqual(None, va.video._cache)
        with va.caching():
            self.assertNotEqual(None, va.video._cache)
        self.assertEqual(None, va.video._cache)

        settings.cache = og_cache

    def test_get_frame(self):
        config = deepcopy(self.config)
        va = VideoAnalyzer(config)
        va.launch()
        va.transform._matrix = TRANSFORM

        with va.caching():
            for fn in va.frame_numbers():
                if fn in FRAMES:  # todo: !!!!!! if this test checks out, transform is not applied (:
                    frame = va.get_transformed_frame(fn)
                    self.assertEqualArray(TEST_TRANSFORMED_FRAME_HSV[fn], frame)


if __name__ == '__main__':
    unittest.main()
