import warnings
from typing import Callable, Dict, List
import numpy as np


class Endpoint(object):
    _name: str
    _signature: type

    def __init__(self, name: str, signature: type):
        self._name = name
        self._signature = signature


class RegistryEntry(object):
    _mapping: Dict[Endpoint, Callable]

    def __init__(self):
        self._mapping = {}

    def expose(self, endpoint: Endpoint):  # todo: check if method matches endpoint call signature
        def wrapper(method):
            if endpoint in self._mapping:
                warnings.warn(
                    f"Exposing {method} has overridden previously "
                    f"exposed method {self._mapping[endpoint]}")
            self._mapping.update(
                {endpoint: method}
            )
            return method
        return wrapper

    def exposes(self, endpoint: Endpoint):
        return endpoint in self._mapping

    def endpoints(self):
        return list(self._mapping.keys())


class Registry(object):
    pass


class backend(Registry):
    VideoFileHandler = RegistryEntry()
    IdentityTransform = RegistryEntry()
    PerspectiveTransform = RegistryEntry()
    Mask = RegistryEntry()
    HsvRangeFilter = RegistryEntry()
    VideoAnalyzer = RegistryEntry()


class endpoint(object):
    get_raw_frame = Endpoint('get_raw_frame', Callable[[int], np.ndarray])
    estimate_transform = Endpoint('estimate_transform', Callable[[List], None])
    set_filter_from_color = Endpoint('set_filter', Callable[[List], None])
    get_transformed_frame = Endpoint('get_transformed_frame', Callable[[int], np.ndarray])
    get_transformed_overlaid_frame = Endpoint('get_transformed_overlaid_frame', Callable[[int], np.ndarray])
