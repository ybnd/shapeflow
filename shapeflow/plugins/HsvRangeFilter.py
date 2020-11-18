import numpy as np
import cv2

from shapeflow import get_logger
from shapeflow.config import extend, ConfigType, Field, validator, BaseConfig

from shapeflow.core.interface import FilterConfig, FilterInterface, FilterType
from shapeflow.maths.images import ckernel
from shapeflow.maths.colors import Color, HsvColor, convert, WRAP

log = get_logger(__name__)


@extend(ConfigType, __name__.split('.')[-1])
class _Config(FilterConfig):
    """Configuration for :class:`shapeflow.plugins.HsvRangeFilter._Filter`
    """
    color: HsvColor = Field(default=HsvColor())
    """The center color.
    """
    range: HsvColor = Field(default=HsvColor(h=10, s=75, v=75))
    """The range around the center color.
    
    The default setting of ``HsvColor(h=10,s=75,v=75)`` works well 
    for most cases, but if you notice false positive or false negative regions
    you can try adjusting the range. 
    
    Mixing or separating colors can be handled by increasing the ``h`` value 
    (allowing more hues through) and uneven lighting/shadows can be compensated 
    for by increasing the ``v`` value (lightness of the color).
    """
    close: int = Field(default=0, ge=0, le=200)
    """Kernel size (circular) of a morphological `closing`_ operation.
    
    If ``close`` is set to 0 (the default), no closing will be performed.
    This attribute will be coerced to an odd integer below 200 in order to
    keep performance somewhat reasonable.
    
    You may want to configure a higher ``close`` if you notice that the state 
    image of the corresponding frame includes noise (small objects or colored 
    pixels) *outside* of its main area.
    
    .. _closing: https://en.wikipedia.org/wiki/Closing_(morphology)
    """
    open: int = Field(default=0, ge=0, le=200)
    """Kernel size (circular) of a morphological `opening`_ operation.
    
    If ``open`` is set to 0 (the default), no opening will be performed.
    This attribute will be coerced to an odd integer below 200 in order to
    keep performance somewhat reasonable.
    
    You may want to configure a higher ``open`` if you notice that the state 
    image of the corresponding frame includes noise (small ‘holes’ or 
    non-colored pixels) *inside* of its main area.
    
    .. _opening: https://en.wikipedia.org/wiki/Opening_(morphology)
    """

    @property
    def ready(self) -> bool:
        return self.color != HsvColor()

    @property
    def c0(self) -> HsvColor:
        """The center color minus the range.
        """
        return self.color - self.range

    @property
    def c1(self) -> HsvColor:
        """The center color plus the range.
        """
        return self.color + self.range

    _resolve_close = validator('close', allow_reuse=True)(BaseConfig._odd_add)
    _resolve_open = validator('open', allow_reuse=True)(BaseConfig._odd_add)
    _close_limits = validator('close', pre=True, allow_reuse=True)(BaseConfig._int_limits)
    _open_limits = validator('open', pre=True, allow_reuse=True)(BaseConfig._int_limits)


@extend(FilterType, __name__.split('.')[-1])
class _Filter(FilterInterface):
    """Filters out colors outside of a :class:`~shapeflow.maths.colors.HsvColor`
    radius around a center color.
    """
    _config_class = _Config

    def set_filter(self, filter: _Config, color: Color) -> _Config:
        color = convert(color, HsvColor)

        log.debug(f'Setting filter {filter} ~ color {color}')
        filter(color=color)
        return filter

    def mean_color(self, filter: _Config) -> Color:
        # S and V are arbitrary but work relatively well
        # for both overlay & plot colors
        return HsvColor(h=filter.color.h, s=255, v=200)

    def filter(self, filter: _Config, img: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
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
