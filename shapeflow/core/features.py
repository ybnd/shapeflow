import abc
from typing import Optional, Tuple, Type, Any, List, Mapping

import numpy as np

from shapeflow.core.config import BaseConfig, Configurable, Instance
from shapeflow.core.interface import InterfaceType
from shapeflow.maths.colors import Color, HsvColor, as_hsv


class FeatureConfig(BaseConfig, abc.ABC):
    """Abstract :class:`~shapeflow.core.backend.Feature` parameters"""
    pass


class Feature(abc.ABC, Configurable):  # todo: should probably use Config for parameters after all :)
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[Color]
    _state: Optional[np.ndarray]

    _label: str = ''  # todo: keep these in the config instead?
    """Label string, to be used in exported data and the user interface
    """
    _unit: str = ''
    """Unit string, to be used in exported data and the user interface
    """
    _elements: Tuple[Instance, ...] = ()

    _config: Optional[FeatureConfig]
    _global_config: FeatureConfig
    _config_class: Type[FeatureConfig] = FeatureConfig

    def __init__(self, elements: Tuple[Instance, ...], global_config: FeatureConfig, config: Optional[dict] = None):
        self._skip = False
        self._ready = False

        self._elements = elements
        self._global_config = global_config

        if config is not None:
            self._config = global_config.__class__(**config)
        else:
            self._config = None

        self._color = HsvColor(h=0,s=200,v=255)  # start out as red

    def calculate(self, frame: np.ndarray, state: np.ndarray = None) \
            -> Tuple[Any, Optional[np.ndarray]]:
        """Calculate the feature for the given frame

        Parameters
        ----------
        frame : np.ndarray
            A video frame
        state : Optional[np.ndarray]
            An ``np.ndarray`` for the state image. Should have the same
            dimensions as the ``frame``

        Returns
        -------
        Any
            The calculated feature value
        Optional[np.ndarray]
            If a state image was provided, return this state frame with the
            feature's state frame added onto it. If not, return ``None``.
        """
        """Calculate the feature for given frame
        """
        if state is not None:
            state = self.state(frame, state)
        return self.value(frame), state

    @classmethod
    def label(cls) -> str:
        """The label of this feature. Used in the user interface and results.
        """
        return cls._label

    @classmethod
    def unit(cls) -> str:
        """The unit of this feature. Used in the user interface and results.
        """
        return cls._unit

    @property
    def skip(self) -> bool:
        """Whether this feature should be skipped
        """
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        """Whether this feature is ready to be calculated
        """
        raise NotImplementedError

    def set_color(self, color: Color):
        self._color = color

    @property
    def color(self) -> Color:
        """Color of the feature in figures.

        A feature's color is handled by its :class:`~shapeflow.core.backend.FeatureSet`
        as not to overlap with any other features in that set.
        """
        if self._color is not None:
            return self._color
        else:
            raise ValueError

    @abc.abstractmethod
    def _guideline_color(self) -> Color:
        """Returns the 'guideline color' of a feature, which is used to resolve
        to the final color within a feature set.
        """
        raise NotImplementedError

    @abc.abstractmethod  # todo: we're dealing with frames explicitly, so maybe this should be an shapeflow.video thing...
    def state(self, frame: np.ndarray, state: np.ndarray) -> np.ndarray:
        """Return the feature's state image for a given frame
        """
        raise NotImplementedError

    @abc.abstractmethod
    def value(self, frame: np.ndarray) -> Any:
        """Compute the value of the feature for a given frame
        """
        raise NotImplementedError

    @property
    def config(self):
        """The configuration of the feature.
        Default to the global configuration if no specific one is provided.
        """
        if self._config is not None:
            return self._config
        else:
            return self._global_config


class FeatureSet(Configurable):
    """A set of :class:`~shapeflow.core.backend.Feature` instances
    """
    _feature: Tuple[Feature, ...]
    _colors: Tuple[Color, ...]
    _config_class = FeatureConfig

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features

    def resolve_colors(self) -> Tuple[Color, ...]:
        """Resolve the colors of all features in this set so that none of them
        overlap.
        """
        guideline_colors = [
            as_hsv(f._guideline_color()) for f in self._features
        ]

        min_v = 20.0
        max_v = 255.0
        tolerance = 15

        bins: list = []
        # todo: clean up binning
        for index, color in enumerate(guideline_colors):
            if not bins:
                bins.append([index])
            else:
                in_bin = False
                for bin in bins:
                    if abs(
                            float(color.h) -
                            np.mean([guideline_colors[i].h for i in bin])
                    ) < tolerance:
                        bin.append(index)
                        in_bin = True
                        break
                if not in_bin:
                    bins.append([index])

        for bin in bins:
            if len(bin) < 4:
                increment = 60.0
            else:
                increment = (max_v - min_v) / len(bin)

            for repetition, index in enumerate(bin):
                self._features[index].set_color(
                    HsvColor(
                        h=guideline_colors[index].h,
                        s=220,
                        v=int(max_v - repetition * increment)
                    )
                )

        self._colors = tuple([feature.color for feature in self._features])
        return self.colors

    @property
    def colors(self) -> Tuple[Color, ...]:
        """The resolved colors in this feature set
        """
        return self._colors

    @property
    def features(self) -> Tuple[Feature, ...]:
        """The features in this feature set
        """
        return self._features

    def calculate(self, frame: np.ndarray, state: Optional[np.ndarray]) -> Tuple[List[Any], Optional[np.ndarray]]:
        """Calculate all features in this set for a given frame

        Parameters
        ----------
        frame : np.ndarray
            An image
        state : Optional[np.ndarray]
            An empty ``np.ndarray`` for the state image. Should have the same
            dimensions as the ``frame``

        Returns
        -------
        List[Any]
            The calculated feature values
        Optional[np.ndarray]
            If a state image was provided, return the composite state image of
            this feature set. If not, return ``None``.
        """
        values = []

        for feature in self.features:
            value, state = feature.calculate(frame=frame, state=state)
            values.append(value)

        return values, state


class FeatureType(InterfaceType):
    """:class:`~shapeflow.core.backend.Feature` factory
    """
    _type = Feature
    _mapping: Mapping[str, Type[Feature]] = {}
    _config_type = FeatureConfig

    def get(self) -> Type[Feature]:
        """Get the :class:`~shapeflow.core.backend.Feature` for this feature type
        """
        feature = super().get()
        assert issubclass(feature, Feature)
        return feature

    def config_schema(self) -> dict:
        """The ``pydantic`` configuration schema for
        this type of :class:`~shapeflow.core.backend.Feature`
        """
        return self.get().config_schema()

    @classmethod
    def __modify_schema__(cls, field_schema):
        """Modify ``pydantic`` schema to include units and labels.
        """
        super().__modify_schema__(field_schema)
        field_schema.update(
            units={ k:v._unit for k,v in cls._mapping.items() },
            labels={ k:v._label for k,v in cls._mapping.items() }
        )