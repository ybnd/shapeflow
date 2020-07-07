import abc
from typing import Type, Tuple, Optional, Dict

import numpy as np

from isimple import get_logger
from isimple.core import Described
from isimple.core.config import BaseConfig, Configurable, Factory
from isimple.maths.colors import HsvColor
from isimple.maths.coordinates import ShapeCoo, Roi

from pydantic import validator

log = get_logger(__name__)


class InterfaceFactory(Factory):
    _type = Configurable
    _mapping: Dict[str, Type[Described]] = {}

    def get(self) -> Type[Configurable]:
        interface = super().get()
        assert issubclass(interface, Configurable)
        return interface

    def config_schema(self) -> dict:
        return self.get().config_schema()


class HandlerConfig(BaseConfig, abc.ABC):
    type: InterfaceFactory
    data: BaseConfig

    @validator('type', pre=True)
    def _validate_type(cls, value, values: dict):
        if isinstance(value, cls.__fields__['type'].type_):
            return value
        else:
            return cls.__fields__['type'].type_(value)

    @validator('data', pre=True)
    def _validate_data(cls, value, values: dict):
        if isinstance(value, values['type'].get().config_class()):
            return value
        elif isinstance(value, dict):
            return values['type'].get().config_class()(**value)
        else:
            raise NotImplementedError


class TransformConfig(BaseConfig):
    """Undefined transform"""
    pass


class TransformInterface(Configurable, abc.ABC):
    @abc.abstractmethod
    def validate(self, matrix: Optional[np.ndarray]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def from_coordinates(self, roi: Roi, from_shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def to_coordinates(self, to_shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, roi: Roi, from_shape: tuple, to_shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, transform: np.ndarray, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def coordinate(self, transform: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
        raise NotImplementedError


class FilterConfig(BaseConfig):
    """Undefined filter"""

    @property
    def ready(self):
        """Return true if filter can be applied ~ this configuration.
            Override for specific filter implementations
        """
        raise NotImplementedError


class FilterInterface(Configurable, abc.ABC):
    """Handles pixel filtering operations
    """

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
    _mapping: Dict[str, Type[Described]] = {}

    def get(self) -> Type[FilterInterface]:
        interface = super().get()
        assert issubclass(interface, FilterInterface)
        return interface


class TransformType(InterfaceFactory):
    _type = TransformInterface
    _mapping: Dict[str, Type[Described]] = {}

    def get(self) -> Type[TransformInterface]:
        interface = super().get()
        assert issubclass(interface, TransformInterface)
        return interface
