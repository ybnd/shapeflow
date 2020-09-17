import numpy as np
import cv2

from isimple import get_logger, settings
from isimple.config import extend, ConfigType, Field, validator, BaseConfig

from isimple.core.interface import FilterConfig, FilterInterface, FilterType
from isimple.maths.images import ckernel
from isimple.maths.colors import Color, HsvColor, convert, WRAP

log = get_logger(__name__)


@extend(ConfigType)
class HsvRangeFilterConfig(FilterConfig):
    """HSV range filter"""
    range: HsvColor = Field(default=HsvColor(h=10, s=75, v=75))
    color: HsvColor = Field(default=HsvColor())
    close: int = Field(default=0, ge=0, le=200)
    open: int = Field(default=0, ge=0, le=200)

    @property
    def ready(self) -> bool:
        return self.color != HsvColor()

    @property
    def c0(self) -> HsvColor:
        return self.color - self.range

    @property
    def c1(self) -> HsvColor:
        return self.color + self.range

    _resolve_close = validator('close', allow_reuse=True)(BaseConfig._odd_add)
    _resolve_open = validator('open', allow_reuse=True)(BaseConfig._odd_add)
    _close_limits = validator('close', pre=True, allow_reuse=True)(BaseConfig._int_limits)
    _open_limits = validator('open', pre=True, allow_reuse=True)(BaseConfig._int_limits)


@extend(FilterType)
class HsvRangeFilter(FilterInterface):
    """Filters by a range of hues ~ HSV representation
    """
    _config_class = HsvRangeFilterConfig

    def set_filter(self, filter: HsvRangeFilterConfig, color: Color) -> HsvRangeFilterConfig:
        color = convert(color, HsvColor)

        log.debug(f'Setting filter {filter} ~ color {color}')
        filter(color=color)
        return filter

    def mean_color(self, filter: HsvRangeFilterConfig) -> Color:
        # S and V are arbitrary but work relatively well
        # for both overlay & plot colors
        return HsvColor(h=filter.color.h, s=255, v=200)

    def filter(self, filter: HsvRangeFilterConfig, img: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        if filter.c0.h > filter.c1.h:
            # handle hue wrapping situation with two ranges
            c0_a = np.float32(filter.c0.list)
            c1_a = np.float32([WRAP-1] + filter.c1.list[1:])
            c0_b = np.float32([0] + filter.c0.list[1:])
            c1_b = np.float32(filter.c1.list)

            binary = cv2.inRange(img, c0_a, c1_a, img) \
                   + cv2.inRange(img, c0_b, c1_b, img)
        else:
            c0 = np.float32(filter.c0.list)
            c1 = np.float32(filter.c1.list)

            binary = cv2.inRange(img, c0, c1, img)

        if filter.close:
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, ckernel(filter.close))
        if filter.open:
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, ckernel(filter.open))
        if mask is not None:
            # Mask off again
            binary = cv2.bitwise_and(binary, mask)

        return binary
