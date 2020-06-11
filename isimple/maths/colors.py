import re
from collections import namedtuple
from typing import Dict, Type, List

from pydantic import BaseModel, Field

from isimple.core.config import BaseConfig

import cv2
import numpy as np

# colorspaces
_HSV = 'hsv'
_BGR = 'bgr'
_RGB = 'rgb'


class Color(BaseConfig):
    _colorspace: str = ''
    _conversion_map: Dict = {}

    def __init__(self, *args, **kwargs):
        if not args:
            super().__init__(**kwargs)
        else:
            # Make sure no numpy ints get through by accident (not serializable)
            super().__init__(**{kw:int(arg) for kw, arg in zip(self.__fields__.keys(), args)})

    def __call__(self, **kwargs):
        # Make sure no numpy ints get through by accident
        super().__call__(**{kw:int(arg) for kw, arg in kwargs.items()})

    def __eq__(self, other: object) -> bool:
        return self.__dict__ == other.__dict__ and type(self) == type(other)

    @property
    def np3d(self) -> np.ndarray:
        return np.uint8([[list(self.__dict__.values())]])

    @property
    def list(self) -> List[int]:
        return list(np.uint8(list(self.__dict__.values())))

    def _convert(self, colorspace: str) -> tuple:
        if colorspace not in self._conversion_map:
            raise NotImplementedError
        converted = cv2.cvtColor(self.np3d, self._conversion_map[colorspace])
        return tuple(converted.flatten())

    @classmethod
    def from_str(cls, color: str) -> 'Color':
        return cls(
            **{k:int(float(v.strip("'"))) for k,v,_
               in re.findall('([A-Za-z0-9]*)=(.*?)([,)])', color)}
        )

    def inverse(self) -> 'Color':
        raise NotImplementedError

    def __add__(self, other):
        assert isinstance(other, type(self))
        return type(self)(
            **{channel:(getattr(self, channel) + getattr(other, channel))
               for channel in self.__fields__.keys()}
        )

    def __sub__(self, other):
        assert isinstance(other, type(self))
        return type(self)(
            **{channel:(getattr(self, channel) - getattr(other, channel))
               for channel in self.__fields__.keys()}
        )



class HsvColor(Color):
    h: int = Field(default=0)
    s: int = Field(default=0)
    v: int = Field(default=0)

    _colorspace: str = _HSV
    _conversion_map = {
        _RGB: cv2.COLOR_HSV2RGB,
        _BGR: cv2.COLOR_HSV2BGR,
    }



class RgbColor(Color):
    r: int = Field(default=0)
    g: int = Field(default=0)
    b: int = Field(default=0)

    _colorspace: str = _RGB
    _conversion_map = {
        _HSV: cv2.COLOR_RGB2HSV,
        _BGR: cv2.COLOR_RGB2BGR,
    }


class BgrColor(Color):
    b: int = Field(default=0)
    g: int = Field(default=0)
    r: int = Field(default=0)

    _colorspace: str = _BGR
    _conversion_map = {
        _HSV: cv2.COLOR_BGR2HSV,
        _RGB: cv2.COLOR_BGR2RGB,
    }


# noinspection PyArgumentList
def convert(color: Color, to: Type[Color]) -> Color:
    if type(color) == to:
        return color
    else:
        return to(*color._convert(to._colorspace))


# noinspection Mypy
def complementary(color: Color) -> Color:
    hsv0 = convert(color, HsvColor)
    hsv1 = HsvColor(int(round((hsv0.h + 90) % 180)), hsv0.s, hsv0.v)  # type: ignore
    return convert(hsv1, type(color))

def css_hex(color: Color) -> str:
    rgb = convert(color, RgbColor)
    assert isinstance(rgb, RgbColor)

    def _hex(num: int) -> str:
        return "{0:0{1}x}".format(num,2)

    return f"#{_hex(rgb.r)}{_hex(rgb.g)}{_hex(rgb.b)}"
