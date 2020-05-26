import abc
from typing import Type, Tuple, Optional
from dataclasses import dataclass, field

import numpy as np

from isimple.core.config import Config, Factory
from isimple.maths.colors import HsvColor
from isimple.maths.coordinates import Coo


class Interface(object):
    _config_class: Type[Config]

    @classmethod
    def config_class(cls):
        return cls._config_class


class InterfaceFactory(Factory):
    def get(self) -> Type[Interface]:
        interface = super().get()
        if issubclass(interface, Interface):
            return interface
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{interface}'. "
                f"This is very weird and shouldn't happen, really."
            )


class HandlerConfig(Config, abc.ABC):
    type: InterfaceFactory
    data: Config

    def _get_field_type(self, attr):
        if attr == 'data':
            return self.type.get().config_class()
        else:
            return super()._get_field_type(attr)


@dataclass
class TransformConfig(Config):
    matrix: Optional[np.ndarray] = field(default=None)
    inverse: Optional[np.ndarray] = field(default=None)


class TransformInterface(Interface, abc.ABC):
    _config_class: Type[TransformConfig]

    @abc.abstractmethod
    def validate(self, matrix: Optional[np.ndarray]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def from_coordinates(self, roi: dict) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def to_coordinates(self, shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, roi: dict, shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, transform, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def inverse(self, transform, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        raise NotImplementedError

    def coordinate(self, transform, coordinate: Coo, shape: Tuple[int, int]) -> Coo:
        raise NotImplementedError


class FilterConfig(Config):
    @property
    def ready(self):
        """Return true if filter can be applied ~ this configuration.
            Override for specific filter implementations
        """
        return False


class FilterInterface(Interface, abc.ABC):
    """Handles pixel filtering operations
    """
    _config_class: Type[FilterConfig]

    @abc.abstractmethod
    def set_filter(self, filter, color: HsvColor):
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> HsvColor:
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, filter, image: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class FilterType(InterfaceFactory):
    _type = FilterInterface

    def get(self) -> Type[FilterInterface]:
        filter = super().get()
        if issubclass(filter, FilterInterface):
            return filter
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{filter}'. "
                f"This is very weird and shouldn't happen, really."
            )


class TransformType(Factory):
    _type = TransformInterface
