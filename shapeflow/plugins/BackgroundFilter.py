import numpy as np
import cv2

from pydantic import Field, validator

from shapeflow import get_logger
from shapeflow.config import extend, ConfigType, BaseConfig

from shapeflow.core.interface import FilterConfig, FilterInterface, FilterType
from shapeflow.maths.images import ckernel
from shapeflow.maths.colors import Color, HsvColor, convert, WRAP

log = get_logger(__name__)
COLOR = HsvColor(h=0, s=0, v=0)


@extend(ConfigType, True)
class _Config(FilterConfig):
    """Configuration for :class:`shapeflow.plugins.BackgroundFilter.BackgroundFilter`
    """
    color: HsvColor = Field(default=HsvColor())
    """See :attr:`shapeflow.plugins.HsvRangeFilter._Config.color`
    """
    range: HsvColor = Field(default=HsvColor(h=10, s=75, v=75))
    """See :attr:`shapeflow.plugins.HsvRangeFilter._Config.range`
    """
    close: int = Field(default=0, ge=0, le=200)
    """:attr:`shapeflow.plugins.HsvRangeFilter._Config.close`
    """
    open: int = Field(default=0, ge=0, le=200)
    """:attr:`shapeflow.plugins.HsvRangeFilter._Config.open`
    """

    @property
    def ready(self) -> bool:
        return self.color != HsvColor()

    @property
    def c0(self) -> HsvColor:
        """See :func:`shapeflow.plugins.HsvRangeFilter._Config.c0`
        """
        return self.color - self.range

    @property
    def c1(self) -> HsvColor:
        """See :func:`shapeflow.plugins.HsvRangeFilter._Config.c1`
        """
        return self.color + self.range

    _resolve_close = validator('close', allow_reuse=True)(BaseConfig._odd_add)
    _resolve_open = validator('open', allow_reuse=True)(BaseConfig._odd_add)
    _close_limits = validator('close', pre=True, allow_reuse=True)(BaseConfig._int_limits)
    _open_limits = validator('open', pre=True, allow_reuse=True)(BaseConfig._int_limits)


@extend(FilterType, True)
class BackgroundFilter(FilterInterface):
    """Filters out colors outside of a :class:`~shapeflow.maths.colors.HsvColor`
    radius around a center color and inverts the resulting image.
    """
    _config_class = _Config

    def set_filter(self, filter: _Config, color: Color) -> _Config:
        color = convert(color, HsvColor)

        log.debug(f'Setting filter {filter} ~ color {color}')
        filter(color=color)
        return filter

    def mean_color(self, filter: _Config) -> Color:
        return COLOR

    def filter(self, filter: _Config, img: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        if mask is None:
            raise ValueError('No mask provided to BackgroundFilter')

        if filter.c0.h > filter.c1.h:
            # handle hue wrapping situation with two ranges
            c0_a = np.array(filter.c0.list, dtype=np.float32)
            c1_a = np.array([WRAP-1] + filter.c1.list[1:], dtype=np.float32)
            c0_b = np.array([0] + filter.c0.list[1:], dtype=np.float32)
            c1_b = np.array(filter.c1.list, dtype=np.float32)

            inverse = cv2.inRange(img, c0_a, c1_a, img) \
                   + cv2.inRange(img, c0_b, c1_b, img)
        else:
            c0 = np.array(filter.c0.list, dtype=np.float32)
            c1 = np.array(filter.c1.list, dtype=np.float32)

            inverse = cv2.inRange(img, c0, c1, img)

        if filter.close:
            inverse = cv2.morphologyEx(inverse, cv2.MORPH_CLOSE, ckernel(filter.close))
        if filter.open:
            inverse = cv2.morphologyEx(inverse, cv2.MORPH_OPEN, ckernel(filter.open))

        binary = cv2.bitwise_not(inverse)

        if mask is not None:
            # Mask off again
            binary = cv2.bitwise_and(binary, mask)

        return binary

