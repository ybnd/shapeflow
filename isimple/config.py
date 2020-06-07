from dataclasses import dataclass, field
from typing import Union, Optional, Tuple, Dict, Any

import datetime

import numpy as np
import yaml
import json

from pydantic import Field, FilePath, DirectoryPath
from pydantic.dataclasses import dataclass

from isimple import __version__
from isimple.core.backend import BaseAnalyzerConfig, \
    FeatureType
from isimple.core.config import extend, ConfigType, \
    log, VERSION, CLASS, untag, BaseConfig
from isimple.core import EnforcedStr
from isimple.core.interface import FilterConfig, \
    FilterType, TransformType, TransformConfig, FilterConfig, HandlerConfig
from isimple.maths.colors import HsvColor
from isimple.util import before_version


class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):
    _options = ['Nf', 'dt']
    _descriptions = {
        'Nf': '# of equally spaced frames',
        'dt': 'frame interval (s)',
    }


@extend(ConfigType)
class VideoFileHandlerConfig(BaseConfig):
    """Video file"""
    pass


@extend(ConfigType)
class PerspectiveTransformConfig(TransformConfig):
    """Perspective transform"""
    pass


@extend(ConfigType)
class TransformHandlerConfig(HandlerConfig):
    """Transform"""
    type: TransformType = Field(default_factory=TransformType)
    data: TransformConfig = Field(default_factory=TransformConfig)

    roi: Optional[dict] = Field(default=None)  # todo: maybe make this a config?
    flip: Tuple[bool, bool] = Field(default=(False, False))  # (vertical, horizontal)
    turn: int = Field(default=0) # number of 90° turns (CW)


@extend(ConfigType)
class HsvRangeFilterConfig(FilterConfig):
    """HSV range filter"""
    radius: HsvColor = Field(default=HsvColor(10, 75, 75))

    c0: HsvColor = Field(default=HsvColor(0, 0, 0))
    c1: HsvColor = Field(default=HsvColor(0, 0, 0))

    @property
    def ready(self) -> bool:
        return self.c0 != self.c1


@extend(ConfigType)
class FilterHandlerConfig(HandlerConfig):
    """Filter"""
    type: FilterType = Field(default_factory=FilterType)
    data: FilterConfig = Field(default_factory=FilterConfig)

    @property
    def ready(self) -> bool:
        return self.data.ready


@extend(ConfigType)
class MaskConfig(BaseConfig):
    """Mask"""
    name: Optional[str] = Field(default=None)
    skip: bool = Field(default=False)
    filter: FilterHandlerConfig = Field(default_factory=FilterHandlerConfig)

    parameters: Dict[FeatureType, Dict[str, Tuple[bool, Any]]] = Field(default_factory=dict)

    @property
    def ready(self):
        return self.filter.ready


@extend(ConfigType)
class DesignFileHandlerConfig(BaseConfig):
    """Design file"""
    dpi: int = Field(default=400)

    overlay_alpha: float = Field(default=0.1)  # todo: more of a application setting
    smoothing: int = Field(default=7)


@extend(ConfigType)
class VideoAnalyzerConfig(BaseAnalyzerConfig):
    """Video analyzer"""
    frame_interval_setting: FrameIntervalSetting = Field(default_factory=FrameIntervalSetting)
    dt: Optional[float] = Field(default=5.0)
    Nf: Optional[int] = Field(default=100)

    video: VideoFileHandlerConfig = Field(default_factory=VideoFileHandlerConfig)
    design: DesignFileHandlerConfig = Field(default_factory=DesignFileHandlerConfig)
    transform: TransformHandlerConfig = Field(default_factory=TransformHandlerConfig)
    masks: Tuple[MaskConfig, ...] = Field(default_factory=tuple)

    features: Tuple[FeatureType, ...] = Field(default=())  # todo: should be a tuple of (FeatureType, <config of feature>)
    parameters: Dict[FeatureType, Dict[str, Any]] = Field(default_factory=dict)

    def resolve(self):
        super(VideoAnalyzerConfig, self).resolve()  # todo: doesn't seem to resolve correctly ~ pydantic

        # Remove unused parameters
        for feature in list(self.parameters.keys()):
            if feature not in self.features:
                self.parameters.pop(feature)

        # Propagate global parameters to masks
        #   this overwrites any values that were overridden by the masks!
        for mask in self.masks:
            if isinstance(mask, dict):
                mask = MaskConfig(**mask)  # todo: this should have happened in super().resolve(), but it didn't!
            mask(parameters=self.parameters)


def load(path: str) -> VideoAnalyzerConfig:
    log.debug(f'Loading VideoAnalyzerConfig from {path}')
    with open(path, 'r') as f:  # todo: assuming it is yaml, sanity check?
        d = yaml.safe_load(f)
    d = normalize_config(d)

    return VideoAnalyzerConfig(**d)


def loads(config: str) -> BaseConfig:
    d = json.loads(config)

    try:
        config_cls = ConfigType(d[CLASS]).get()
    except KeyError:
        config_cls = VideoAnalyzerConfig

    d = normalize_config(d)
    return config_cls(**d)


def normalize_config(d: dict) -> dict:
    """Normalize a configuration dictionary to match the current version of `isimple.core.config`
    :param d: configuration dictionary
    :return:
    """

    # If empty dict, return empty dict
    if len(d) == 0:
        return d

    # Deal with legacy formatting
    if VERSION not in d or CLASS not in d:
        if 'version' in d:
            # Support pre-0.3 config metadata field
            d[VERSION] = d.pop('version')
            d[CLASS] = VideoAnalyzerConfig.__name__
        else:
            raise ValueError(f"No version or class info in config")

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
        if before_version(d[VERSION], '0.3.4'):
            normalizing_to('0.3.4')
            # Set frame_interval_setting to dt, the previous default
            if 'dt' in d:
                d['frame_initerval_setting'] = FrameIntervalSetting('dt')
        if before_version(d[VERSION], '0.3.5'):
            normalizing_to('0.3.5')
            # Convert roi from list to dict
            if 'transform' in d:
                if 'roi' in d['transform']:
                    d['transform']['roi'] = {
                        corner: {'x': coordinate[0], 'y': coordinate[1]}
                        for coordinate, corner in zip(
                            json.loads(d['transform']['roi']),
                            ['BL', 'TL', 'TR', 'BR']
                        )
                    }
        if before_version(d[VERSION], '0.3.6'):
            normalizing_to('0.3.6')
            # add ready & skip tags to mask
            if 'masks' in d:
                for m in d['masks']:
                    m['skip'] = False
                    try:
                        m['ready'] = not (m['filter']['data']['c0'] == 'HsvColor(h=0, s=0, v=0')
                    except KeyError:
                        m['ready'] = False
        if before_version(d[VERSION], '0.3.7'):
            normalizing_to('0.3.7')
            # remove DesignFileHandlerConfig.keep_renders & VideoFileHandlerConfig.do_resolve_frame_number
            if 'video' in d:
                if 'do_resolve_frame_number' in d['video']:
                    d.pop('do_resolve_frame_number')
            if 'design' in d:
                if 'keep_renders' in d['design']:
                    d.pop('keep_renders')
        if before_version(d[VERSION], '0.3.8'):
            normalizing_to('0.3.8')
            # remove CachingInstance.cache_consumer
            if 'video' in d:
                if 'cache_consumer' in d['video']:
                    d['video'].pop('cache_consumer')
            if 'design' in d:
                if 'cache_consumer' in d['design']:
                    d['design'].pop('cache_consumer')
        if before_version(d[VERSION], '0.3.9'):
            normalizing_to('0.3.9')
            # remove mask.ready attribute
            if 'masks' in d:
                for mask in d['masks']:
                    if 'ready' in mask:
                        mask.pop('ready')
        if before_version(d[VERSION], '0.3.10'):
            normalizing_to('0.3.10')
            # move TransformConfig fields into TransformConfig.data
            if 'transform' in d:
                if not 'data' in d['transform']:
                    d['transform']['data'] = {}
                d['transform']['data']['matrix'] = d['transform'].pop('matrix')
        if before_version(d[VERSION], '0.3.11'):
            normalizing_to('0.3.11')
            # remove matrix & inverse fields from TransformConfig.data
            if 'transform' in d:
                if 'data' in d['transform']:
                    if 'matrix' in d['transform']['data']:
                        d['transform']['data'].pop('matrix')
                    if 'inverse' in d['transform']['data']:
                        d['transform']['data'].pop('inverse')


    else:
        raise NotImplementedError

    # Remove non-standard fields
    config_type = ConfigType(d[CLASS]).get()
    for k in list(d.keys()):
        if k not in (VERSION, CLASS):
            if not k in config_type.__fields__:
                log.warning(f"Removed unexpected attribute "
                            f"'{k}':{d.pop(k)} from {d[CLASS]}")

    # Remove timestamp & version info
    d.pop('timestamp', None)
    d.pop('version', None)

    untag(d)

    return d


def dump(config: VideoAnalyzerConfig, path:str):
    with open(path, 'w+') as f:
        yaml.safe_dump(config.to_dict(do_tag=True),f, width=999)


def dumps(config: VideoAnalyzerConfig) -> str:
    return yaml.safe_dump(config.to_dict(do_tag=True), width=999)
