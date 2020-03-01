import os
import sys

from typing import Tuple, List, Union, Dict

import tkinter
import tkinter.ttk as ttk

from isimple.core.config import (
    EnforcedStr,
    VideoAnalyzerConfig,
    TransformHandlerConfig,
    VideoFileHandlerConfig,
    DesignFileHandlerConfig,
    MaskConfig,
    FilterHandlerConfig,
)
from isimple.core.gui import TreeDict
from isimple.video import HsvRangeFilterConfig  # to make sure the factories are populated


class OptionsHandler(object):
    _options: VideoAnalyzerConfig
    def __init__(self, options: VideoAnalyzerConfig):
        self._options = options

    def update(self, options: dict) -> dict:
        self._options = VideoAnalyzerConfig(**options)
        return self._options.to_dict()

    @property
    def options(self):
        return self._options


ttk.Style().theme_use('alt')

oh = OptionsHandler(
    VideoAnalyzerConfig(
        video_path='some path',
        design_path='some_path',
        video=VideoFileHandlerConfig(),
        design=DesignFileHandlerConfig(),
        transform=TransformHandlerConfig(),
        masks=(
            MaskConfig(name='mask1', filter=FilterHandlerConfig(data=HsvRangeFilterConfig())),
            MaskConfig(name='mask2', filter=FilterHandlerConfig(data=HsvRangeFilterConfig())),
            MaskConfig(name='mask3', filter=FilterHandlerConfig(data=HsvRangeFilterConfig())),
        )
    )
)

root = tkinter.Tk()
canvas = tkinter.Canvas(root)

t = TreeDict(root, oh.options.to_dict(), oh.update)
root.mainloop()
