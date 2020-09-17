import abc
from typing import Type, Tuple, Optional, Dict, Mapping

import numpy as np

from isimple import get_logger
from isimple.core import Described
from isimple.core.config import BaseConfig, Configurable, Factory
from isimple.maths.colors import Color
from isimple.maths.coordinates import ShapeCoo, Roi

from pydantic import validator

log = get_logger(__name__)


class InterfaceFactory(Factory):
    _type: Type[Configurable]
    _mapping: Mapping[str, Type[Configurable]] = {}
    _config_type: Type[BaseConfig] = BaseConfig

    def get(self) -> Type[Configurable]:
        interface = super().get()
        assert issubclass(interface, Configurable)
        return interface

    def config_schema(self) -> dict:
        return self.get().config_schema()

    @classmethod
    def __modify_schema__(cls, field_schema):
        super().__modify_schema__(field_schema)
        field_schema.update(interface=cls._config_type.__name__)


class Handler(abc.ABC):  # todo: move to isimple.core.interface?
    _implementation: Configurable
    _implementation_factory: Type[InterfaceFactory]
    _implementation_class: Type[Configurable]

    def set_implementation(self, implementation: str) -> str:
        impl_type: type = self._implementation_factory(implementation).get()
        assert issubclass(impl_type, self._implementation_class)

        self._implementation = impl_type()
        return self._implementation_factory.get_str(  # todo: this is not necessary when using @extend(<Factory>)
            self._implementation.__class__
        )

    def get_implementation(self) -> str:
        return self._implementation.__class__.__qualname__

    def implementation_config(self) -> BaseConfig:
        pass


class HandlerConfig(BaseConfig, abc.ABC):
    """Abstract handler configuration"""

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
    """Transform configuration"""
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
    def estimate(self, roi: Roi, from_shape: tuple, to_shape: tuple) -> Optional[np.ndarray]:
        raise NotImplementedError

    def invert(self, matrix: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if matrix is not None:
            return np.linalg.inv(matrix)
        else:
            return None

    @abc.abstractmethod
    def transform(self, transform: np.ndarray, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def coordinate(self, transform: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
        raise NotImplementedError


class FilterConfig(BaseConfig):
    """Filter configuration"""

    @property
    def ready(self):
        """Return true if filter can be applied ~ this configuration.
            Override for specific filter implementations
        """
        raise NotImplementedError


class FilterInterface(Configurable, abc.ABC):
    """Handles pixel filtering operations"""

    @abc.abstractmethod
    def set_filter(self, filter, color: Color):
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> Color:
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, filter, image: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        raise NotImplementedError


class FilterType(InterfaceFactory):
    _type = FilterInterface
    _mapping: Mapping[str, Type[FilterInterface]] = {}
    _config_type = FilterConfig

    def get(self) -> Type[FilterInterface]:
        interface = super().get()
        assert issubclass(interface, FilterInterface)
        return interface


class TransformType(InterfaceFactory):
    _type = TransformInterface
    _mapping: Mapping[str, Type[TransformInterface]] = {}
    _config_type = TransformConfig

    def get(self) -> Type[TransformInterface]:
        interface = super().get()
        assert issubclass(interface, TransformInterface)
        return interface
