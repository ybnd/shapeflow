import numpy as np
import abc
from typing import Tuple, Any, Optional

from isimple.core.backend import BackendInstance


class Feature(abc.ABC):
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[np.ndarray]
    _state: Optional[np.ndarray]

    _elements: Tuple[BackendInstance, ...]

    def __init__(self, elements: Tuple[BackendInstance, ...]):
        self._elements = elements

    def calculate(self, frame: np.ndarray, state: np.ndarray = None) \
            -> Tuple[Any, np.ndarray]:
        """Calculate Feature for given frame
            and update state image (optional)
        """
        if state is not None:
            state = self.state(frame, state)
        return self.value(frame), state

    @property
    def color(self) -> np.ndarray:
        """Color of the Feature in figures.

            A Feature's color must be set as not to overlap with
            other Features in the same FeatureSet.
            Therefore, <Feature>._color must be determined by FeatureSet!
        """
        return self._color

    @abc.abstractmethod
    def _guideline_color(self) -> np.ndarray:
        """Returns the 'guideline color' of a Feature instance
            Used by FeatureSet to determine the actual _color
        """
        raise NotImplementedError

    @abc.abstractmethod  # todo: we're dealing with frames explicitly, so maybe this should be an isimple.video thing...
    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        """Return the Feature instance's state image for a given frame
        """
        raise NotImplementedError

    @abc.abstractmethod
    def value(self, frame: np.ndarray) -> Any:
        """Compute the value of the Feature instance for a given frame
        """
        raise NotImplementedError


class FeatureSet(object):
    _features: Tuple[Feature, ...]
    _colors: Tuple[tuple, ...]

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features

    def get_colors(self) -> Tuple[tuple, ...]:
        if not hasattr(self, '_colors'):
            guideline_colors = [f._guideline_color() for f in self._features]
            colors: list = []

            # For all features in the FeatureSet
            for feature, color in zip(self._features, guideline_colors):
                # Dodge the other colors by hue
                tolerance = 15
                increment = 60  # todo: should be set *after* the number of repititions is determined
                repetition = 0
                for registered_color in colors:
                    if abs(float(color[0]) - float(registered_color[0])) < tolerance:
                        repetition += 1

                color = (color[0], 220, 255 - repetition * increment)

                feature._color = color
                colors.append(color)

            self._colors = tuple(colors)
        return self.colors

    @property
    def colors(self) -> Tuple[tuple, ...]:
        return self._colors