import numpy as np
import cv2

from shapeflow import get_logger, settings
from shapeflow.config import extend, ConfigType, Field

from shapeflow.core.interface import FilterConfig, FilterInterface, FilterType

from shapeflow.maths.colors import Color, HsvColor, convert, WRAP

log = get_logger(__name__)


COLOR = HsvColor(h=0, s=0, v=0)


@extend(ConfigType)
class BackgroundFilterConfig(FilterConfig):
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
class BackgroundFilter(FilterInterface):
    """Filters by a range of hues ~ HSV representation
    """
    _config_class = BackgroundFilterConfig

    def set_filter(self, filter: BackgroundFilterConfig, color: Color) -> BackgroundFilterConfig:
        color = convert(color, HsvColor)

        log.debug(f'Setting filter {filter} ~ color {color}')
        filter(color=color)
        return filter

    def mean_color(self, filter: BackgroundFilterConfig) -> Color:
        return COLOR

    def filter(self, filter: BackgroundFilterConfig, img: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        if mask is None:
            raise ValueError('No mask provided to BackgroundFilter')

        if filter.c0.h > filter.c1.h:
            # handle hue wrapping situation with two ranges
            c0_a = np.float32(filter.c0.list)
            c1_a = np.float32([WRAP-1] + filter.c1.list[1:])
            c0_b = np.float32([0] + filter.c0.list[1:])
            c1_b = np.float32(filter.c1.list)

            inv = cv2.bitwise_not(
                    cv2.inRange(img, c0_a, c1_a, img)
                    + cv2.inRange(img, c0_b, c1_b, img)
                )

            return cv2.bitwise_and(inv, mask)
        else:
            c0 = np.float32(filter.c0.list)
            c1 = np.float32(filter.c1.list)

            inv = cv2.bitwise_not(cv2.inRange(img, c0, c1, img))
            return cv2.bitwise_and(inv, mask)
