import abc
import re
from typing import Tuple, Any, Optional, List, Type, Generator
import os

import numpy as np
import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import frame_number_iterator
from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum
from isimple.core.backend import backend, BackendManager
from isimple.core.endpoints import beep, geep
from isimple.core.features import FeatureSet
from isimple.core.gui import *
from isimple.core.meta import *
from isimple.video import VideoFileHandler, DesignFileHandler, Transform, \
    VideoFeatureType, VideoHandlerType, DesignHandlerType, TransformType


class VideoAnalyzer(BackendManager):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    _gui: guiManager

    video: VideoFileHandler
    design: DesignFileHandler
    transform: Transform

    featuresets: List[FeatureSet]

    frame_interval_setting: FrameIntervalSetting  # use dt or Nf
    dt: float                                     # interval in seconds
    Nf: int                                       # number of evenly spaced frames
    video_type: Type[VideoFileHandler]
    design_type: Type[DesignFileHandler]
    transform_type: Type[Transform]

    __default__ = {
        'frame_interval_setting':   FrameIntervalSetting(),
        'dt':                       5.0,
        'Nf':                       100,
        'features':                 [VideoFeatureType('pixel_sum')],
        'video_type':               VideoHandlerType(),
        'design_type':              DesignHandlerType(),
        'transform_type':           TransformType(),
    }

    def __init__(self, video_path: str = None, design_path: str = None, config: dict = None):  # todo: add optional feature list to override self._config.features
        super(VideoAnalyzer, self).__init__(config)

        if video_path is None or design_path is None:
            video_path = ''  # todo: initialize gui & ask; freak out if there was no gui provided
            design_path = ''

        self.video = self.video_type(video_path, config)
        self.design = self.design_type(design_path, config)
        self.transform = self.transform_type(self.video.shape, config)
        self.masks = self.design.masks
        self.filters = [mask.filter for mask in self.masks]

        self._gather_instances()  # todo: annoying that we have to call this one explicilty, but doing it at super.__init__ makes it less dynamic

        self.featuresets = [
            FeatureSet(
                    tuple(feature.get()(mask) for mask in self.design.masks)
                ) for feature in self.features
        ]

    def frame_numbers(self) -> Generator[int, None, None]:
        if self.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count, Nf = self.Nf)
        elif self.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count, dt = self.dt, fps = self.video.fps)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self.frame_interval_setting}")

    @backend.expose(beep.get_transformed_frame)
    def get_transformed_frame(self, frame_number: int) -> np.ndarray:
        return self.transform(self.video.read_frame(frame_number))# todo: depending on self.frame is dangerous in case we want to run this in a different thread

    @backend.expose(beep.get_transformed_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
        return self.design.overlay(self.get_transformed_frame(frame_number))

    def calculate(self, frame_number: int):
        """Return a state image for each FeatureSet
        """
        frame = self.get_transformed_frame(frame_number)

        V = []
        S = []
        for fs in self.featuresets:
            values = []
            state = np.zeros(frame.shape, dtype=np.uint8) # todo: can't just set it to self.frame.dtype?
            # todo: may be faster / more memory-efficient to keep state[i] and set it to 0

            for feature in fs._features:  # todo: make featureset iterable maybe
                value, state = feature.calculate(
                    frame.copy(),  # don't overwrite self.frame ~ cv2 dst parameter  # todo: better to let OpenCV handle copying, or not?
                    state               # additive; each feature adds to state
                )
                values.append(value)

            # Add overlay on top of state
            state = self.design.overlay(state)

            V.append(values)   # todo: value values value ugh
            S.append(state)

        # todo: launch callbacks here

    def analyze(self):
        for fn in self.frame_numbers():
            self.calculate(fn)


class VideoAnalyzerGui(guiManager):
    _backend: BackendManager  # todo: good idea to have these two in "direct contact"?

    def __init__(self, backend: BackendManager):
        self._backend = backend