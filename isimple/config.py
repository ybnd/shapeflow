from typing import Optional, Tuple, Dict, Any, Type

import yaml
import json

from pydantic import Field, validator

from isimple.core.config import extend, ConfigType, \
    log, VERSION, CLASS, untag, BaseConfig
from isimple.core.backend import BaseAnalyzerConfig, \
    FeatureType, FeatureConfig
from isimple.core import EnforcedStr
from isimple.core.interface import FilterType, TransformType, TransformConfig, \
    FilterConfig, HandlerConfig
from isimple.maths.coordinates import Roi
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


class FlipConfig(BaseConfig):
    """Flip"""
    vertical: bool = Field(default=False)
    horizontal: bool = Field(default=False)


@extend(ConfigType)
class TransformHandlerConfig(HandlerConfig):
    """Transform"""
    type: TransformType = Field(default_factory=TransformType)
    data: TransformConfig = Field(default_factory=TransformConfig)

    roi: Optional[Roi] = Field(default=None)  # todo: maybe make this a config?
    flip: FlipConfig = Field(default_factory=FlipConfig)
    turn: int = Field(default=0) # number of 90° turns (CW)


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
    name: str = Field(default=None)
    skip: bool = Field(default=False)
    filter: FilterHandlerConfig = Field(default_factory=FilterHandlerConfig)

    parameters: Tuple[Optional[FeatureConfig],...] = Field(default=())

    @property
    def ready(self):
        return self.filter.ready

    @validator('parameters', pre=True)
    def _validate_parameters(cls, value, values):
        return value


@extend(ConfigType)
class DesignFileHandlerConfig(BaseConfig):
    """Design file"""
    dpi: int = Field(default=400)

    overlay_alpha: float = Field(default=0.1)  # todo: more of a application setting; has no direct effect on the output
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

    features: Tuple[FeatureType, ...] = Field(default=())
    parameters: Tuple[FeatureConfig, ...] = Field(default=())

    @classmethod
    def schema(cls, by_alias: bool = True) -> Dict[str, Any]:
        schema = super().schema(by_alias)

        # add implementation schemas to schema
        schema.update({'implementations': {
            'FeatureConfig': {
                feature: FeatureType(feature).config_schema()
                for feature in FeatureType().options
            },
            'TransformConfig': {
                transform: TransformType(transform).config_schema()
                for transform in TransformType().options
            },
            'FilterConfig': {
                filter: FilterType(filter).config_schema()
                for filter in FilterType().options
            },
        }})

        # definitions in schema['implementations'] to top-level
        for category in schema['implementations'].values():
            for implementation in category.values():
                if 'definitions' in implementation:
                    schema['definitions'].update(implementation.pop('definitions'))

        return schema


    @validator('masks', pre=True)
    def _validate_masks(cls, value, values):  # todo: actually validate
        for mask in value:
            # Resolve class
            if isinstance(mask, dict):
                mask = MaskConfig(**mask)
            elif isinstance(mask, MaskConfig):
                pass
            else:
                raise TypeError

            # Resolve parameters
            parameters = list(mask.parameters)

            if 'features' in values and 'parameters' in values:
                for index, (feature, config) in enumerate(zip(values['features'], values['parameters'])):
                    if index >= len(mask.parameters):
                        parameters.append(None)
                    elif parameters[index] is None:
                        pass
                    elif not parameters[index]:
                        parameters[index] = None
                    else:
                        if isinstance(parameters[index], dict):
                            parameters[index] = feature.config_class()(
                                **parameters[index]
                            )
                        else:
                            raise ValueError(
                                f"can not resolve parameters {parameters[index]}"
                            )

            mask.parameters = tuple(parameters)
        return tuple(value)

    @validator('features', pre=True)
    def _validate_features(cls, value):
        return tuple([
            FeatureType(feature)
            if not isinstance(feature, FeatureType) else feature
            for feature in value
        ])

    @validator('parameters', pre=True)
    def _validate_parameters(cls, value, values):  # todo: actually validate
        # todo: can we know for certain that values['features'] has already been validated?
        parameters = []
        for index, feature in enumerate(values['features']):
            if index < len(value):
                if isinstance(value[index], dict):
                    # Resolve dict to FeatureConfig
                    parameters.append(feature.get()._config_class(**value[index]))
                elif not value[index]:
                    # Resolve *empty* to default FeatureConfig silently
                    parameters.append(feature.get()._config_class())
                else:
                    # Resolve anything else to default FeatureConfig and complain
                    parameters.append(feature.get()._config_class())
                    log.warning(f"{feature}: parameters should be specified as "
                                f"a list of dict / array of object instead of "
                                f"{value[index]} -- set to default")
            else:
                # Resolve not provided to default FeatureConfig silently
                parameters.append(feature.get()._config_class())

        return tuple(parameters)

    _validate_fis = validator('frame_interval_setting')(BaseConfig._resolve_enforcedstr)


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
        if before_version(d[VERSION], '0.3.12'):
            normalizing_to('0.3.12')
            # flip (bool, bool) to pydantic
            if 'transform' in d:
                if 'flip' in d['transform']:
                    d['transform']['flip'] = {
                        'vertical': d['transform']['flip'][0],
                        'horizontal': d['transform']['flip'][1]
                    }
        if before_version(d[VERSION], '0.3.13'):
            normalizing_to('0.3.13')
            # HsvRangeFilter: radius/c0/c1 -> range/color
            if 'masks' in d:
                for mask in d['masks']:
                    if 'filter' in mask and mask['filter']['type'] == 'HsvRangeFilter':
                        if 'radius' in mask['filter']['data']:
                            mask['filter']['data']['range'] = mask['filter']['data'].pop('radius')
                        if 'c0' in mask['filter']['data']:
                            c0 = mask['filter']['data'].pop('c0')
                        if 'c1' in mask['filter']['data']:
                            mask['filter']['data'].pop('c1')

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
