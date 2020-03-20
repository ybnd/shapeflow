from dataclasses import dataclass, field
from typing import Union, Optional, Tuple

import numpy as np
import yaml

from isimple import settings
from isimple.core.backend import AnalyzerConfig, CachingBackendInstanceConfig, \
    FeatureType
from isimple.core.config import extend, ConfigType, \
    log, VERSION, CLASS, EnforcedStr, untag, Config
from isimple.core.interface import FilterConfig, \
    FilterType, TransformType
from isimple.maths.colors import HsvColor
from isimple.util import before_version


class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):
    _options = ['dt', 'Nf']


@extend(ConfigType)
@dataclass
class VideoFileHandlerConfig(CachingBackendInstanceConfig):
    do_resolve_frame_number: bool = field(default=True)


@extend(ConfigType)
@dataclass
class TransformHandlerConfig(Config):
    type: Union[TransformType, str] = field(default='')
    matrix: Union[np.ndarray,str] = field(default=np.eye(3))
    roi: Union[np.ndarray, str] = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        self.type = self.resolve(self.type, TransformType)
        self.matrix = self.resolve(self.matrix, np.ndarray)
        if len(self.roi) > 0:
            self.roi = self.resolve(self.roi, np.ndarray).tolist()


@extend(ConfigType)
@dataclass
class HsvRangeFilterConfig(FilterConfig):
    radius: Union[HsvColor, str] = field(default=HsvColor(10, 75, 75))

    c0: Union[HsvColor, str] = field(default=HsvColor(0, 0, 0))
    c1: Union[HsvColor, str] = field(default=HsvColor(0, 0, 0))

    def __post_init__(self):
        self.radius = self.resolve(self.radius, HsvColor)
        self.c0 = self.resolve(self.c0, HsvColor)
        self.c1 = self.resolve(self.c1, HsvColor)


@extend(ConfigType)
@dataclass
class FilterHandlerConfig(Config):
    type: Union[FilterType, str] = field(default='')
    data: Union[FilterConfig, dict, None] = field(default=None)

    def __post_init__(self):
        self.type = self.resolve(self.type, FilterType)
        self.data = self.resolve(self.data, self.type.get()._config_class)  # todo: something something typing in Factory


@extend(ConfigType)
@dataclass
class MaskConfig(Config):
    name: Optional[str] = field(default=None)
    height: Optional[float] = field(default=None)
    filter: Union[FilterHandlerConfig,dict,None] = field(default=None)

    def __post_init__(self):
        self.filter = self.resolve(self.filter, FilterHandlerConfig)


@extend(ConfigType)
@dataclass
class DesignFileHandlerConfig(CachingBackendInstanceConfig):
    keep_renders: bool = field(default=False)
    dpi: int = field(default=400)

    overlay_alpha: float = field(default=0.1)
    smoothing: int = field(default=7)


@extend(ConfigType)
@dataclass
class VideoAnalyzerConfig(AnalyzerConfig):
    video_path: Optional[str] = field(default=None)
    design_path: Optional[str] = field(default=None)

    frame_interval_setting: Union[FrameIntervalSetting,str] = field(default=FrameIntervalSetting())
    dt: Optional[float] = field(default=5.0)
    Nf: Optional[int] = field(default=100)

    height: float = field(default=0.153e-3)

    video: Union[VideoFileHandlerConfig,dict,None] = field(default=None)
    design: Union[DesignFileHandlerConfig,dict,None] = field(default=None)
    transform: Union[TransformHandlerConfig,dict,None] = field(default=None)
    masks: Tuple[Union[MaskConfig,dict,None], ...] = field(default=(None,))  # todo: would be better as Dict[str, MaskConfig]?
    features: Tuple[Union[FeatureType, str], ...] = field(default=('',))

    def __post_init__(self):
        self.frame_interval_setting = self.resolve(self.frame_interval_setting, FrameIntervalSetting)
        self.video = self.resolve(self.video, VideoFileHandlerConfig)
        self.design = self.resolve(self.design, DesignFileHandlerConfig)
        self.transform = self.resolve(self.transform, TransformHandlerConfig)
        self.masks = tuple(self.resolve(self.masks, MaskConfig, iter=True))
        self.features = tuple(self.resolve(self.features, FeatureType, iter=True))


def load(path: str) -> VideoAnalyzerConfig:
    log.debug(f'Loading VideoAnalyzerConfig from {path}')
    with open(path, 'r') as f:  # todo: assuming it is yaml, sanity check?
        d = yaml.safe_load(f)
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

    def normalizing_to(version):
        log.debug(f"Normalizing configuration (from v{d[VERSION]} to v{version})")

    # VideoAnalyzerConfig is the only class that should be deserialized!
    #    -> other classes are contained within it or should only be used
    #       internally. Otherwise, this function would have to be a lot
    #       more complex.
    if d[CLASS] == VideoAnalyzerConfig.__name__:
        if before_version(d[VERSION], '0.2.1'):
            normalizing_to('0.2.1')
            # Rename mask[i].filter.filter to mask[i].filter.data
            for m in d['masks']:
                m['filter']['data'] = m['filter'].pop('filter')
        if before_version(d[VERSION], '0.2.2'):
            normalizing_to('0.2.2')
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
        if before_version(d[VERSION], '0.3.1'):
            normalizing_to('0.3.1')
            # Rename TransformHandlerConfig 'coordinates' to 'roi'
            if 'transform' in d:
                if 'coordinates' in d['transform']:
                    d['transform']['roi'] = d['transform'].pop('coordinates')
        if before_version(d[VERSION], '0.3.2'):
            normalizing_to('0.3.2')
            # Remove some fields that should be in the global settings
            to_remove = ('cache_dir', 'cache_size_limit', 'render_dir')
            if 'video' in d:
                for k in to_remove:
                    d['video'].pop(k, None)
            if 'design' in d:
                for k in to_remove:
                    d['design'].pop(k, None)
    else:
        raise NotImplementedError

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
