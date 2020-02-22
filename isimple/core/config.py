import yaml
from yaml.representer import SafeRepresenter
import json
from ast import literal_eval as make_tuple
import os
import time
import pandas as pd
import numpy as np
import warnings
from typing import List, Optional, NamedTuple, Dict, Tuple, Union
from dataclasses import dataclass
from collections.abc import Iterable

from isimple.maths.images import ckernel
from isimple.core.util import timing

# https://stackoverflow.com/questions/16782112
yaml.add_representer(
    dict, lambda self,
    data: yaml.representer.SafeRepresenter.represent_dict(self, data.items())
)


# Extension
__ext__ = '.meta'

# Excel sheet name
__meta_sheet__ = 'metadata'


class EnforcedStr(object):
    _options: List[str] = ['']
    _str: str

    def __init__(self, string: str = None):
        if string is not None:
            if string not in self.options:
                warnings.warn(f"Illegal {self.__class__.__name__} '{string}', "
                              f"should be one of {self.options}. "
                              f"Defaulting to '{self.default}'.")
                self._str = self.default
            else:
                self._str = str(string)
        else:
            self._str = self.default

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self._str}'>"

    def __str__(self):
        return self._str

    def __eq__(self, other):
        if hasattr(other, '_str'):
            return self._str == other._str
        elif isinstance(other, str):
            return self._str == other
        else:
            return False

    @property
    def options(self):
        return self._options

    @property
    def default(self):
        return self._options[0]


class Factory(EnforcedStr):
    _mapping: dict = {'': None}
    _default: Optional[str] = None

    def get(self) -> type:
        if self._str in self._mapping:
            return self._mapping[self._str]
        else:
            raise ValueError(f"Factory {self.__class__.__name__} doesn't map"
                             f"{self._str} to a class.")

    @classmethod
    def get_str(cls, mapped_value):
        str = cls.default
        for k,v in cls._mapping.items():
            if mapped_value == v:
                str = k

        return str

    @property
    def options(self):
        return list(self._mapping.keys())

    @property
    def default(self):
        if self._default is not None:
            return self._default
        else:
            if len(self._mapping):
                return list(self._mapping.keys())[0]
            else:
                return None

    @classmethod
    def extend(cls, mapping: dict):
        # todo: sanity check this
        cls._mapping.update(mapping)


class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):  # todo: this is a horrible name
    _options = ['dt', 'Nf']


class TransformType(Factory):
    _mapping: dict = {}


class FilterType(Factory):
    _mapping: dict = {}


class VideoFeatureType(Factory):
    _mapping: dict = {}


@dataclass
class Config(object):
    def __init__(self, **kwargs):
        for kw, arg in kwargs.items():
            if hasattr(self, kw):
                setattr(self, kw, arg)
        self.__post_init__()

    def __post_init__(self):
        pass

    def to_dict(self) -> dict:
        output: dict = {}
        def _represent(obj, default) -> Union[dict, str]:
            if isinstance(obj, Config):
                return obj.to_dict()
            if isinstance(obj, EnforcedStr):
                if obj != default:
                    return str(obj)
                else:
                    raise ValueError('Value is default')
            if isinstance(obj, tuple):
                if obj != default:
                    return Config.__tuple2str__(obj)
                else:
                    raise ValueError('Value is default')
            if isinstance(obj, np.ndarray):
                if np.any(obj != default):
                    return Config.__ndarray2json__(obj)
                else:
                    raise ValueError('Value is default')
            else:
                if obj != default:
                    return obj
                raise ValueError('Value is default')

        defaults = self.__class__()
        for attr, val in self.__dict__.items():
            try:
                default = getattr(defaults, attr)
                if isinstance(val, list) or isinstance(val, tuple):
                    output[attr] = []
                    for v in val:
                        try:
                            output[attr].append(_represent(v,default))
                        except ValueError:
                            pass
                else:
                    output[attr] = _represent(val, default)
            except ValueError:
                pass
        return output

    @staticmethod
    def resolve(val, type, iter=False):
        def _resolve(val, type):
            if isinstance(val, str):
                if issubclass(type, EnforcedStr):
                    val = type(val)
                elif type == tuple:
                    val = Config.__str2tuple__(val)
                elif type == np.ndarray:
                    val = Config.__str2ndarray__(val)
            if isinstance(val, list):
                if type == np.ndarray:
                    val = np.array(val)
                else:
                    val = type(val)
            elif isinstance(val, dict) and issubclass(type, Config):
                val = type(**val)
            return val

        if not isinstance(val, type):
            if iter and isinstance(val, Iterable):
                val = [_resolve(v, type) for v in val]
            else:
                val = _resolve(val, type)
        return val

    @staticmethod
    def __ndarray2json__(array: np.ndarray) -> str:
        return json.dumps(array.tolist())

    @staticmethod
    def __str2ndarray__(string: str) -> np.ndarray:
        return np.array(json.loads(str(string)))

    @staticmethod
    def __tuple2str__(t: tuple) -> str:
        return str(t)

    @staticmethod
    def __str2tuple__(t: str) -> tuple:
        t = make_tuple(t)
        assert isinstance(t, tuple)
        return t


class BackendInstanceConfig(Config):
    pass


@dataclass
class CachingBackendInstanceConfig(BackendInstanceConfig):
    do_cache: bool = True
    do_background: bool = True

    cache_dir: str = '.cache'
    cache_size_limit: int = 2**32

    block_timeout: float = 1
    cache_consumer: bool = False


@dataclass
class VideoFileHandlerConfig(CachingBackendInstanceConfig):
    do_resolve_frame_number: bool = True


@dataclass
class TransformHandlerConfig(BackendInstanceConfig):
    type: Union[TransformType,str] = ''
    matrix: Union[np.ndarray,str] = np.eye(3)

    def __post_init__(self):
        self.type = self.resolve(self.type, TransformType)
        self.matrix = self.resolve(self.matrix, np.ndarray)


class FilterConfig(Config):
    pass


@dataclass
class HsvRangeFilterConfig(FilterConfig):
    hue_radius: float = 10
    sat_radius: float = 75
    val_radius: float = 75

    c0: Union[tuple, str] = (0,0,0)
    c1: Union[tuple, str] = (0,0,0)

    def __post_init__(self):
        self.c0 = self.resolve(self.c0, tuple)
        self.c1 = self.resolve(self.c1, tuple)


@dataclass
class FilterHandlerConfig(BackendInstanceConfig):
    type: Union[FilterType,str] = ''
    filter: Union[FilterConfig, dict,None] = None

    def __post_init__(self):
        self.type = self.resolve(self.type, FilterType)
        self.filter = self.resolve(self.filter, self.type._default.__class__)


@dataclass
class MaskConfig(BackendInstanceConfig):
    height: Optional[float] = None
    filter: Union[FilterHandlerConfig,dict,None] = None

    def __post_init__(self):
        self.filter = self.resolve(self.filter, FilterHandlerConfig)


@dataclass
class DesignFileHandlerConfig(CachingBackendInstanceConfig):
    render_dir: str = '.render'
    keep_renders: bool = False
    dpi: int = 400

    overlay_alpha: float = 0.1
    smoothing_kernel: Union[np.ndarray,str] = ckernel(7)

    def __post_init__(self):
        self.smoothing_kernel = self.resolve(self.smoothing_kernel, np.ndarray)


@dataclass
class BackendManagerConfig(BackendInstanceConfig):
    pass


@dataclass
class VideoAnalyzerConfig(BackendManagerConfig):
    video_path: Optional[str] = None
    design_path: Optional[str] = None

    frame_interval_setting: Union[FrameIntervalSetting,str] = ''
    dt: Optional[float] = 5.0
    Nf: Optional[int] = 100

    height: float = 0.153e-3

    video: Union[VideoFileHandlerConfig,dict,None] = None
    design: Union[DesignFileHandlerConfig,dict,None] = None
    transform: Union[TransformHandlerConfig,dict,None] = None
    masks: Tuple[Union[MaskConfig,dict,None], ...] = (None,)
    features: Tuple[Union[VideoFeatureType,str], ...] = ('',)

    def __post_init__(self):
        self.frame_interval_setting = self.resolve(self.frame_interval_setting, FrameIntervalSetting)
        self.video = self.resolve(self.video, VideoFileHandlerConfig)
        self.design = self.resolve(self.design, DesignFileHandlerConfig)
        self.transform = self.resolve(self.transform, TransformHandlerConfig)
        self.masks = tuple(self.resolve(self.masks, MaskConfig, iter=True))
        self.features = tuple(self.resolve(self.features, VideoFeatureType, iter=True))


def load(path: str) -> VideoAnalyzerConfig:  # todo: internals should be replaced with more sensible methods for setting; reuse those in UI etc.
    with open(path, 'r') as f:  # todo: assuming it is yaml, sanity check?
        d = yaml.safe_load(f)

    return VideoAnalyzerConfig(**d)


def dump(config: VideoAnalyzerConfig, path:str):
    with open(path, 'w+') as f:
        yaml.safe_dump(config.to_dict(), f)
