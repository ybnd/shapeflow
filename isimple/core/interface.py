import abc
from typing import Type

import numpy as np

from isimple.core.config import Config, Factory
from isimple.maths.colors import HsvColor


class TransformInterface(abc.ABC):
    default = np.eye(3)

    @abc.abstractmethod
    def validate(self, transform: np.ndarray) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, roi: dict, shape: tuple) -> np.ndarray:  # todo: explain what and why shape is
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        raise NotImplementedError


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