import warnings
from typing import Callable, Dict, List
import numpy as np


class Registry(object):
    _mapping: Dict[str, Callable]

    def __init__(self):
        self._mapping = {}

    def expose(self, signature):
        def wrapper(method):
            if signature in self._mapping:
                warnings.warn(
                    f"Exposing {method} has overridden previously "
                    f"exposed method {self._mapping[signature]}")
            self._mapping.update(
                {signature: method}
            )
            return method
        return wrapper

    def exposes(self, signature):
        return signature in self._mapping

    def signatures(self):
        return list(self._mapping.keys())


class Endpoint(object):
    _name: str
    _signature: type

    def __init__(self, name: str, signature: type):
        self._name = name
        self._signature = signature



class registry():  # todo: there are probably better ways to do this, eg. namedtuple?
    VideoFileHandler = Registry()
    IdentityTransform = Registry()
    PerspectiveTransform = Registry()
    Mask = Registry()
    HsvRangeFilter = Registry()
    VideoAnalyzer = Registry()


class endpoint():
    get_raw_frame = Endpoint('get_raw_frame', Callable[[int], np.ndarray])
    estimate_transform = Endpoint('estimate_transform', Callable[[List], None])
    set_filter_from_color = Endpoint('set_filter', Callable[[List], None])
    get_transformed_frame = Endpoint('get_transformed_frame', Callable[[int], np.ndarray])
    get_transformed_overlaid_frame = Endpoint('get_transformed_overlaid_frame', Callable[[int], np.ndarray])
