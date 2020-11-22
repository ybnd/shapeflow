from typing import Optional, Tuple, Dict, Any, Type, Union
import json

from pydantic import Field, validator

from shapeflow import __version__, settings

from shapeflow.core.config import extend, ConfigType, \
    log, VERSION, CLASS, untag, BaseConfig
from shapeflow.core.backend import BaseAnalyzerConfig, \
    FeatureType, FeatureConfig, AnalyzerState, QueueState
from shapeflow.core import EnforcedStr
from shapeflow.core.interface import FilterType, TransformType, TransformConfig, \
    FilterConfig, HandlerConfig
from shapeflow.maths.coordinates import Roi
from shapeflow.maths.colors import HsvColor

from shapeflow.util import before_version


class ColorSpace(EnforcedStr):  # todo: this is never used outside of tests
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):
    _options = ['Nf', 'dt']
    _descriptions = {
        'Nf': '# of equally spaced frames',
        'dt': 'frame interval (s)',
    }


@extend(ConfigType)
class VideoFileHandlerConfig(BaseConfig):
    pass


class FlipConfig(BaseConfig):
    vertical: bool = Field(default=False)
    horizontal: bool = Field(default=False)


@extend(ConfigType)
class TransformHandlerConfig(HandlerConfig):
    """Transform handler configuration
    """
    type: TransformType = Field(default_factory=TransformType)
    data: TransformConfig = Field(default_factory=TransformConfig)

    roi: Optional[Roi] = Field(default=None)
    """The region of interest (ROI).
    
    This is the position of the chip in the video in relative coordinates with
    respect to its resolution.
    """
    flip: FlipConfig = Field(default_factory=FlipConfig)
    """Flip the selected ROI horizontally/vertically 
    before estimating the transform
    """
    turn: int = Field(default=0)
    """Turn the ROI a number of clockwise 90° turns
    before estimating the transform
    """


@extend(ConfigType)
class FilterHandlerConfig(HandlerConfig):
    """Filter handler configuration
    """
    type: FilterType = Field(default_factory=FilterType)
    data: FilterConfig = Field(default_factory=FilterConfig)

    @property
    def ready(self) -> bool:
        return self.data.ready


@extend(ConfigType)
class MaskConfig(BaseConfig):
    """Mask configuration
    """
    name: str = Field(default=None)
    """The name of this mask.
    
    Taken from the name of its layer in the design file.
    """
    skip: bool = Field(default=False)
    """Whether to skip this mask when analyzing
    """
    filter: FilterHandlerConfig = Field(default_factory=FilterHandlerConfig)
    """Filter configuration for this mask.
    """

    parameters: Tuple[Optional[dict],...] = Field(default=())
    """Feature parameter overrides for this mask.
    
    If ``None``, the global feature parameters are used 
    when computing the feature value.
    """

    @property
    def ready(self):
        """Whether this mask is ready to be analyzed
        """
        return self.filter.ready

    @validator('parameters')
    def _validate_parameters(cls, value, values):
        return value


@extend(ConfigType)
class DesignFileHandlerConfig(BaseConfig):
    """Design file handler configuration
    """
    dpi: int = Field(default=400, ge=50, le=1200)
    """The details per inch (DPI) at which to render the design
    """

    overlay_alpha: float = Field(default=0.1, ge=0.0, le=1.0)  # todo: more of a application setting maybe?
    """Transparency of the overlay
    """
    smoothing: int = Field(default=7, ge=0, le=50)
    """The smoothing kernel size used when generating masks from renders
    """

    _resolve_smoothing = validator('smoothing', allow_reuse=True)(BaseConfig._odd_add)
    _limit_smoothing = validator('smoothing', allow_reuse=True, pre=True)(BaseConfig._int_limits)
    _limit_dpi = validator('dpi', allow_reuse=True, pre=True)(BaseConfig._int_limits)
    _limit_alpha = validator('overlay_alpha', allow_reuse=True, pre=True)(BaseConfig._float_limits)


@extend(ConfigType)
class VideoAnalyzerConfig(BaseAnalyzerConfig):
    """Video analyzer configuration
    """
    frame_interval_setting: FrameIntervalSetting = Field(default_factory=FrameIntervalSetting)
    """Determines which parameter to use when requesting a set of frames 
    to analyze.
    
    * ``Nf``: request :attr:`shapeflow.video.VideoAnalyzerConfig.Nf` frames in total
    
    * ``dt``: request a frame every seconds :attr:`shapeflow.video.VideoAnalyzerConfig.dt` seconds
    """
    dt: Optional[float] = Field(default=5.0)
    """Frame interval in seconds
    """
    Nf: Optional[int] = Field(default=100, description="Nf")
    """Total number of frames
    """

    video: VideoFileHandlerConfig = Field(default_factory=VideoFileHandlerConfig)
    """Video file handler configuration
    """
    design: DesignFileHandlerConfig = Field(default_factory=DesignFileHandlerConfig)
    """Design file handler configuration
    """
    transform: TransformHandlerConfig = Field(default_factory=TransformHandlerConfig)
    """Transform handler configuration
    """

    features: Tuple[FeatureType, ...] = Field(default=())
    """The features to extract
    """
    feature_parameters: Tuple[FeatureConfig, ...] = Field(default=())
    """The feature parameters to use
    """

    masks: Tuple[MaskConfig, ...] = Field(default_factory=tuple)
    """Mask configuration
    """

    @classmethod
    def schema(cls, by_alias: bool = True, ref_template: str = '') -> Dict[str, Any]:
        schema = super().schema(by_alias)

        schema.update({
            'implementations': {  # add implementation schemas to schema
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
            },
            'shapeflow_version': __version__,  # add version to schema
        })

        # definitions in schema['implementations'] to top-level
        for category in schema['implementations'].values():
            for implementation in category.values():
                if 'definitions' in implementation:
                    schema['definitions'].update(implementation.pop('definitions'))

        return schema


    @validator('masks')
    def _validate_masks(cls, value, values):
        for mask in value:
            # Resolve class
            if isinstance(mask, dict):
                mask = MaskConfig(**mask)
            elif isinstance(mask, MaskConfig):
                pass
            else:
                raise TypeError

            # Resolve parameters
            parameters = []

            if 'features' in values and 'feature_parameters' in values:
                for index, feature in enumerate(values['features']):
                    if index >= len(mask.parameters) or mask.parameters[index] is None:
                        parameters.append(None)
                    else:
                        parameters.append(mask.parameters[index])

            mask.parameters = tuple(parameters)
        return tuple(value)

    @validator('features')
    def _validate_features(cls, value):
        return tuple([
            FeatureType(feature)
            if not isinstance(feature, FeatureType) else feature
            for feature in value
        ])

    @validator('feature_parameters', pre=True)
    def _validate_parameters(cls, value, values):
        if 'features' in values:
            features = values['features']
        else:
            features = []

        parameters = []
        for index, feature in enumerate(features):
            if index < len(value):
                if value[index] and isinstance(value[index], dict):
                    # Resolve non-empty dict to FeatureConfig
                    parameters.append(
                        feature.get()._config_class(**value[index])
                    )
                elif not value[index]:
                    # Resolve *empty* to default FeatureConfig silently
                    parameters.append(feature.get()._config_class())
                else:
                    # Resolve anything else to default FeatureConfig and complain
                    parameters.append(feature.get()._config_class())
                    log.error(
                        f"{feature}: parameters should be specified as "
                        f"a list of dict / array of object instead of "
                        f"{value[index]} -- set to default")
            else:
                # Resolve not provided to default FeatureConfig silently
                parameters.append(feature.get()._config_class())

        return tuple(parameters)

    _validate_fis = validator('frame_interval_setting')(BaseConfig._resolve_enforcedstr)


def schemas() -> Dict[str, dict]:
    """Get the JSON schemas of

    * :class:`shapeflow.video.VideoAnalyzerConfig`

    * :class:`shapeflow.Settings`

    * :class:`shapeflow.core.backend.AnalyzerState`

    * :class:`shapeflow.core.backend.QueueState`
    """
    return {
        'config': VideoAnalyzerConfig.schema(),
        'settings': settings.schema(),
        'analyzer_state': dict(AnalyzerState.__members__),
        'queue_state': dict(QueueState.__members__),
    }

def loads(config: str) -> BaseConfig:
    """Load a configuration object from a JSON string.

    Parameters
    ----------
    config: str
        JSON string configuration

    Returns
    -------
    BaseConfig
        A configuration object
    """
    d = json.loads(config)

    try:
        config_cls = ConfigType(d[CLASS]).get()
    except KeyError:
        log.error('')  # todo: not very transparent...
        config_cls = VideoAnalyzerConfig

    try:
        d = normalize_config(d)
    except NotImplementedError:
        log.warning(f"can't normalize '{config_cls.__name__}'")

    return config_cls(**d)


def normalize_config(d: dict) -> dict:
    """Normalize a configuration dictionary to match the current
    :data:`~shapeflow.__version__`

    Parameters
    ----------
    d: dict
        A configuration ``dict``

    Returns
    -------
    dict
        A normalized configuration ``dict``
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
    #       more complex.  todo: actually, no.
    #                            Just add some nested functions for the
    #                            internal fields, switch ~ class.
    #                            Some classes can use multiple functions;
    #                            go over the fields and pick out functions.
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
                    m['filter']['data']['c0'] = HsvColor(*make_tuple(m['filter']['data']['c0']))
                if 'c1' in m['filter']['data']:
                    m['filter']['data']['c1'] = HsvColor(*make_tuple(m['filter']['data']['c1']))
                if 'radius' in m['filter']['data']:
                    m['filter']['data']['radius'] = HsvColor(*make_tuple(m['filter']['data']['radius']))
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
                        m['ready'] = m['filter']['data']['c0'] != HsvColor()
                    except KeyError:
                        m['ready'] = False
        if before_version(d[VERSION], '0.3.7'):
            normalizing_to('0.3.7')
            # remove DesignFileHandlerConfig.keep_renders & VideoFileHandlerConfig.do_resolve_frame_number
            if 'video' in d:
                if 'do_resolve_frame_number' in d['video']:
                    d['video'].pop('do_resolve_frame_number')
            if 'design' in d:
                if 'keep_renders' in d['design']:
                    d['design'].pop('keep_renders')
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
        if before_version(d[VERSION], '0.3.15'):
            normalizing_to('0.3.15')
            # rename parameters -> feature_parameters
            if 'parameters' in d:
                d['feature_parameters'] = d.pop('parameters')

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
