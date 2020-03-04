import abc
import datetime
from dataclasses import dataclass
from typing import Union, Optional, Tuple, Type

import numpy as np
import yaml

from isimple.core.backend import BackendInstanceConfig, \
    CachingBackendInstanceConfig, AnalyzerConfig
from isimple.core.config import Config, extend, ConfigType, \
    log, VERSION, CLASS, __version__, EnforcedStr, Factory, untag
from isimple.core.features import FeatureType
from isimple.maths.colors import HsvColor
from isimple.util import before_version


class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):
    _options = ['dt', 'Nf']


@extend(ConfigType)
@dataclass
class VideoFileHandlerConfig(CachingBackendInstanceConfig):
    do_resolve_frame_number: bool = True


class TransformInterface(abc.ABC):
    default = np.eye(3)

    @abc.abstractmethod
    def validate(self, transform: np.ndarray) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, coordinates: list, shape: tuple) -> np.ndarray:  # todo: explain what and why shape is
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        raise NotImplementedError


class TransformType(Factory):
    _type = TransformInterface


@extend(ConfigType)
@dataclass
class TransformHandlerConfig(BackendInstanceConfig):
    type: Union[TransformType, str] = ''
    matrix: Union[np.ndarray,str] = np.eye(3)
    coordinates: Union[list, str] = ''

    def __post_init__(self):
        self.type = self.resolve(self.type, TransformType)
        self.matrix = self.resolve(self.matrix, np.ndarray)
        if len(self.coordinates) > 0:
            self.coordinates = self.resolve(self.coordinates, np.ndarray).tolist()


class FilterConfig(Config):
    pass


class FilterInterface(abc.ABC):
    """Handles pixel filtering operations
    """
    _config_class: Type[FilterConfig]

    @abc.abstractmethod
    def set_filter(self, filter, color: HsvColor):
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> HsvColor:  # todo: add custom np.ndarray type 'hsvcolor'
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, image: np.ndarray, filter) -> np.ndarray:  # todo: add custom np.ndarray type 'image'
        raise NotImplementedError


class FilterType(Factory):
    _type = FilterInterface


@extend(ConfigType)
@dataclass
class HsvRangeFilterConfig(FilterConfig):
    radius: Union[HsvColor, str] = HsvColor(10, 75, 75)

    c0: Union[HsvColor, str] = HsvColor(0, 0, 0)
    c1: Union[HsvColor, str] = HsvColor(0, 0, 0)

    def __post_init__(self):
        self.radius = self.resolve(self.radius, HsvColor)
        self.c0 = self.resolve(self.c0, HsvColor)
        self.c1 = self.resolve(self.c1, HsvColor)


@extend(ConfigType)
@dataclass
class FilterHandlerConfig(BackendInstanceConfig):
    type: Union[FilterType, str] = ''
    data: Union[FilterConfig, dict, None] = None

    def __post_init__(self):
        self.type = self.resolve(self.type, FilterType)
        self.data = self.resolve(self.data, self.type.get()._config_class)  # todo: something something typing in Factory


@extend(ConfigType)
@dataclass
class MaskConfig(BackendInstanceConfig):
    name: Optional[str] = None
    height: Optional[float] = None
    filter: Union[FilterHandlerConfig,dict,None] = None

    def __post_init__(self):
        self.filter = self.resolve(self.filter, FilterHandlerConfig)


@extend(ConfigType)
@dataclass
class DesignFileHandlerConfig(CachingBackendInstanceConfig):
    render_dir: str = '.render'
    keep_renders: bool = False
    dpi: int = 400

    overlay_alpha: float = 0.1
    smoothing: int = 7


@extend(ConfigType)
@dataclass
class VideoAnalyzerConfig(AnalyzerConfig):
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
    features: Tuple[Union[FeatureType, str], ...] = ('',)

    def __post_init__(self):
        self.frame_interval_setting = self.resolve(self.frame_interval_setting, FrameIntervalSetting)
        self.video = self.resolve(self.video, VideoFileHandlerConfig)
        self.design = self.resolve(self.design, DesignFileHandlerConfig)
        self.transform = self.resolve(self.transform, TransformHandlerConfig)
        self.masks = tuple(self.resolve(self.masks, MaskConfig, iter=True))
        self.features = tuple(self.resolve(self.features, FeatureType, iter=True))


def load(path: str) -> VideoAnalyzerConfig:  # todo: internals should be replaced with more sensible methods for setting; reuse those in UI etc.
    log.debug(f'Loading VideoAnalyzerConfig from {path}')
    with open(path, 'r') as f:  # todo: assuming it is yaml, sanity check?
        d = yaml.safe_load(f)   # todo: if using sqlite, no reason to store YAML

    d = normalize_config(d)

    return VideoAnalyzerConfig(**d)


def normalize_config(d: dict) -> dict:
    """Normalize a configuration dictionary to match the current version of `isimple.core.config`
    :param d: configuration dictionary
    :return:
    """
    # Deal with legacy formatting
    if VERSION not in d or CLASS not in d:
        if 'version' in d:
            # Support pre-0.3 config metadata field
            d[VERSION] = d.pop('version')
            d[CLASS] = VideoAnalyzerConfig.__name__

    if d[CLASS] == VideoAnalyzerConfig.__name__:
        if before_version(d[VERSION], '0.2.1'):
            log.info(f"Normalizing configuration (from v{d[VERSION]} to v0.2.1)")
            # Rename mask[i].filter.filter to mask[i].filter.data
            for m in d['masks']:
                m['filter']['data'] = m['filter'].pop('filter')
        if before_version(d[VERSION], '0.2.2'):
            log.info(f"Normalizing configuration (from v{d[VERSION]} to v0.2.2)")
            # Convert tuple string color '(0,0,0)' to HsvColor string 'HsvColor(h=0, s=0, v=0)'
            from ast import literal_eval as make_tuple  # todo: this is unsafe!
            for m in d['masks']:
                if 'c0' in m['filter']['data']:
                    m['filter']['data']['c0'] = str(
                        HsvColor(*make_tuple(m['filter']['data']['c0'])))
                if 'c1' in m['filter']['data']:
                    m['filter']['data']['c1'] = str(
                        HsvColor(*make_tuple(m['filter']['data']['c1'])))
                if 'radius' in m['filter']['data']:
                    m['filter']['data']['radius'] = str(
                        HsvColor(*make_tuple(m['filter']['data']['radius'])))

    # Deal with non-standard fields
    config_type = ConfigType(d[CLASS]).get()
    for k in list(d.keys()):
        if k not in (VERSION, CLASS):
            if not hasattr(config_type, k):
                log.warning(f"Removed unexpected attribute '{k}':{d.pop(k)} from {d[CLASS]}")

    # Remove timestamp & version info
    d.pop('timestamp', None)
    d.pop('version', None)

    untag(d)

    return d


def dump(config: VideoAnalyzerConfig, path:str):
    with open(path, 'w+') as f:
        yaml.safe_dump(config.to_dict(),f, width=999)


def dumps(config: VideoAnalyzerConfig) -> str:
    return yaml.safe_dump(config.to_dict(do_tag=True), width=999)
