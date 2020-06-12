import numpy as np
import cv2

from isimple import get_logger, settings
from isimple.config import extend, ConfigType, Field

from isimple.core.interface import FilterConfig, FilterInterface, FilterType

from isimple.maths.colors import HsvColor

log = get_logger(__name__)


@extend(ConfigType)
class HsvRangeFilterConfig(FilterConfig):
    """HSV range filter"""
    range: HsvColor = Field(default=HsvColor(h=10, s=75, v=75))
    color: HsvColor = Field(default=HsvColor())

    @property
    def ready(self) -> bool:
        return self.color != HsvColor()

    @property
    def c0(self) -> HsvColor:
        return self.color - self.range

    @property
    def c1(self) -> HsvColor:
        return self.color + self.range


@extend(FilterType)
class HsvRangeFilter(FilterInterface):
    """Filters by a range of hues ~ HSV representation
    """
    _config_class = HsvRangeFilterConfig

    def set_filter(self, filter: HsvRangeFilterConfig, color: HsvColor) -> HsvRangeFilterConfig:
        log.debug(f'Setting filter {filter} ~ color {color}')
        filter(color=color)
        return filter

    def mean_color(self, filter: HsvRangeFilterConfig) -> HsvColor:
        # todo: S and V are arbitrary for now
        return HsvColor(h=filter.color.h, s=255, v=200)

    def filter(self, filter: HsvRangeFilterConfig, img: np.ndarray) -> np.ndarray:
        c0 = np.float32(filter.c0.list)
        c1 = np.float32(filter.c1.list)  # todo: doesn't work after pydantic colors :(
        return cv2.inRange(
            img, c0, c1, img
        )
