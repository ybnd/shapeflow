"""Some basic tools for working with colors.

For now, only 8-bit integer colors are handled.
"""
import re
from collections import namedtuple
from typing import Dict, Type, List

from shapeflow.core.config import BaseConfig, Field, validator

import cv2
import numpy as np

# colorspaces
_HSV = 'hsv'
_BGR = 'bgr'
_RGB = 'rgb'

WRAP = 180

class Color(BaseConfig):
    """An abstract color.

    A ``pydantic`` data class; subclasses implementing specific colors should
    include their channels as three separate ``pydantic.Field`` attributes.
    """
    _colorspace: str = ''
    """The name of this colorspace.
    """
    _conversion_map: Dict[str, int] = {}
    """Conversion map from this color to other colors. Maps ``_colorspace``
    strings to ``OpenCV`` conversion method identifiers.
    """

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
        """This color as a 3D ``numpy`` array. Used with ``OpenCV``
        conversions and when multiplying with binary images to 'color' them.
        """
        return np.uint8([[list(self.__dict__.values())]])

    @property
    def list(self) -> List[int]:
        """This color as a list.
        """
        return list(np.uint8(list(self.__dict__.values())))

    def convert(self, colorspace: str) -> tuple:
        """Convert this color to another colorspace.

        Parameters
        ----------
        colorspace: str
            The name of the colorspace to convert to.
            Will raise ``NotImplementedError`` if not in
            :attr:`~shapeflow.maths.colors.Color._conversion_map`.

        Returns
        -------
        tuple
            The converted color as a tuple.
        """
        if colorspace not in self._conversion_map:
            raise NotImplementedError
        converted = cv2.cvtColor(self.np3d, self._conversion_map[colorspace])
        return tuple(converted.flatten())

    @classmethod
    def from_str(cls, color: str) -> 'Color':
        """Deserialize from a formatted string.

        Parameters
        ----------
        color: str
            A color string formatted as ``"SomeColor(a=1,b=2,c=3)"``

        Returns
        -------
        Color
            A new :class:`~shapeflow.maths.colors.Color` object
        """
        return cls(
            **{k:int(float(v.strip("'"))) for k,v,_
               in re.findall('([A-Za-z0-9]*)=([0-9]+)([,)]?)', color)}
        )

    def __add__(self, other):
        assert isinstance(other, type(self))
        return type(self)(
            **{
                channel:(getattr(self, channel) + getattr(other, channel))
                for channel in self.__fields__.keys()
               }
        )

    def __sub__(self, other):
        assert isinstance(other, type(self))
        return type(self)(
            **{channel:(getattr(self, channel) - getattr(other, channel))
               for channel in self.__fields__.keys()}
        )

    @validator('*', pre=True)
    def normalize_channel(cls, v: int) -> int:
        """Enforce 8-bit values [0-255] for a color channel.
        This is the default ``pydantic.validator`` for all channels of a color.

        Parameters
        ----------
        v: int
            The original value of the channel

        Returns
        -------
        int
            The value of the channel clamped to [0-255]
        """
        if v < 0:
            return 0
        if v > 255:
            return 255
        else:
            return v


class HsvColor(Color):
    """Hue-Saturation-Value color.
    """
    h: int = Field(default=0, ge=0, le=WRAP - 1)
    s: int = Field(default=0, ge=0, le=255)
    v: int = Field(default=0, ge=0, le=255)

    _colorspace: str = _HSV
    _conversion_map = {
        _RGB: cv2.COLOR_HSV2RGB,
        _BGR: cv2.COLOR_HSV2BGR,
    }

    @validator('h', pre=True)
    def hue_wraps(cls, h: int) -> int:
        """Make sure the hue channel wraps at ``h=180``.

        Parameters
        ----------
        v: int
            The original value of the hue channel
        Returns
        -------
        int
            The value of the hue channel wrapped around at ``h=180``
        """
        while h < 0:
            h += WRAP
        while h > WRAP:
            h -= WRAP
        return h


class RgbColor(Color):
    """Red-Green-Blue color.
    """
    r: int = Field(default=0)
    g: int = Field(default=0)
    b: int = Field(default=0)

    _colorspace: str = _RGB
    _conversion_map = {
        _HSV: cv2.COLOR_RGB2HSV,
        _BGR: cv2.COLOR_RGB2BGR,
    }


class BgrColor(Color):
    """Blue-Green-Red color.
    This is the ``OpenCV`` default.
    """
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
    """Convert a :class:`~shapeflow.maths.colors.Color` object to another
    :class:`~shapeflow.maths.colors.Color` type.

    Parameters
    ----------
    color: Color
        The original :class:`~shapeflow.maths.colors.Color` object
    to: Type[Color]
        The :class:`~shapeflow.maths.colors.Color` type to convert it to

    Returns
    -------
    Color
        The original :class:`~shapeflow.maths.colors.Color` object converted to
        the new :class:`~shapeflow.maths.colors.Color` type.
    """
    if not isinstance(color, Color):
        raise ValueError(f"'{color}' is not a valid color.")

    if type(color) == to:
        return color
    else:
        return to(*color.convert(to._colorspace))


def as_hsv(color: Color) -> HsvColor:
    """Convert a color to HSV.

    Parameters
    ----------
    color: Color
        Any :class:`~shapeflow.maths.colors.Color` object.

    Returns
    -------
    HsvColor
        The original :class:`~shapeflow.maths.colors.Color` object as a
        :class:`~shapeflow.maths.colors.HsvColor` object.
    """
    out = convert(color, HsvColor)
    assert isinstance(out, HsvColor)
    return out


def as_bgr(color: Color) -> BgrColor:
    """Convert a color to BGR.

    Parameters
    ----------
    color: Color
        Any :class:`~shapeflow.maths.colors.Color` object.

    Returns
    -------
    BgrColor
        The original :class:`~shapeflow.maths.colors.Color` object as a
        :class:`~shapeflow.maths.colors.BgrColor` object.
    """
    out = convert(color, BgrColor)
    assert isinstance(out, BgrColor)
    return out


def as_rgb(color: Color) -> RgbColor:
    """Convert a color to RGB.

    Parameters
    ----------
    color: Color
        Any :class:`~shapeflow.maths.colors.Color` object.

    Returns
    -------
    RgbColor
        The original :class:`~shapeflow.maths.colors.Color` object as a
        :class:`~shapeflow.maths.colors.RgbColor` object.
    """
    out = convert(color, RgbColor)
    assert isinstance(out, RgbColor)
    return out


def complementary(color: Color) -> Color:
    """Get the complementary of a color. Takes a shortcut through HSV.

    Parameters
    ----------
    color: Color
        Any :class:`~shapeflow.maths.colors.Color` object.

    Returns
    -------
    Color
        The complementary color in the same colorspace as the original one.
    """
    hsv0 = as_hsv(color)
    hsv1 = HsvColor(int(round((hsv0.h + WRAP / 2) % WRAP)), hsv0.s, hsv0.v)
    return convert(hsv1, type(color))


def css_hex(color: Color) -> str:
    """Get the color as a CSS-compatible hex RGB string::
       >>> css_hex(RgbColor(r=170,g=187,b=204))
           "#aabbcc"

    Parameters
    ----------
    color: Color
        Any :class:`~shapeflow.maths.colors.Color` object.

    Returns
    -------
    str
        A hex RGB string
    """
    rgb = as_rgb(color)

    def _hex(num: int) -> str:
        return "{0:0{1}x}".format(num,2)

    return f"#{_hex(rgb.r)}{_hex(rgb.g)}{_hex(rgb.b)}"
