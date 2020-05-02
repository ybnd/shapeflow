from dataclasses import dataclass, field
from enum import IntEnum

import diskcache
import sys
import abc
import copy
import time
import threading
from contextlib import contextmanager
from typing import Any, Callable, List, Optional, Union, Tuple, Dict, Type

import numpy as np
import pandas as pd

from isimple import settings, get_logger
from isimple.endpoints import BackendRegistry

from isimple.core import RootException, SetupError, RootInstance
from isimple.maths.colors import HsvColor
from isimple.util.meta import describe_function
from isimple.util import Timer, Timing, hash_file
from isimple.core.config import Factory, untag, Config
from isimple.core.streaming import stream, streams


log = get_logger(__name__)
backend = BackendRegistry()


class BackendSetupError(SetupError):
    msg = 'Error while setting up backend'


class BackendError(RootException):
    msg = 'Error in backend'


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


class BackendInstance(object):
    _config: Config

    def __init__(self, config: Optional[Config]):
        self._configure(config)
        self._lock = threading.Lock()
        super(BackendInstance, self).__init__()

        log.debug(f'Initialized {self.__class__.__qualname__} with {self._config}')

    def _configure(self, config: Config = None):   # todo: adapt to dataclass implementation
        _type = self.__annotations__['_config']

        if config is not None:
            if isinstance(config, _type):
                # Each instance should have a *copy* of the config, not references to the actual values
                self._config = copy.deepcopy(config)
            elif isinstance(config, dict):
                log.warning(f"Initializing '{self.__class__.__name__}' from a dict, "
                            f"please initialize from '{_type}' instead.")
                self._config = _type(**untag(config))
            else:
                raise TypeError(f"Tried to initialize '{self.__class__.__name__}' with {type(config).__name__} '{config}'.")
        else:
            self._config = _type()

    @property
    def config(self) -> Config:
        return self._config


_BLOCKED = 'BLOCKED'


@dataclass
class CachingBackendInstanceConfig(Config):
    do_cache: bool = field(default=True)
    do_background: bool = field(default=True)

    block_timeout: float = field(default=0.1)


class CachingBackendInstance(BackendInstance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]

    _is_caching: bool
    _background: threading.Thread
    _cancel_caching: threading.Event

    _config: CachingBackendInstanceConfig
    _class = CachingBackendInstanceConfig()

    def __init__(self, config: CachingBackendInstanceConfig = None):
        super(CachingBackendInstance, self).__init__(config)

        self._cache = None
        self._cancel_caching = threading.Event()

    @backend.expose(backend.is_caching)
    def is_caching(self) -> bool:
        return self._is_caching

    @backend.expose(backend.cancel_caching)
    def cancel_caching(self):
        if self._cancel_caching is not None:
            self._cancel_caching.set()

    def _get_key(self, method, *args) -> str:
        # Key should be instance-independent to handle multithreading
        #  and caching between application runs.
        # Hashing the string is a significant performance hit.
        return f"{describe_function(method)}{args}"

    def _to_cache(self, key: str, value: Any):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, value)

    def _from_cache(self, key: str) -> Optional[Any]:
        assert self._cache is not None, CacheAccessError
        return self._cache.get(key)

    def _block(self, key: str):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, _BLOCKED)

    def _is_blocked(self, key: str) -> bool:
        assert self._cache is not None, CacheAccessError
        return key in self._cache \
               and isinstance(self._cache[key], str) \
               and self._from_cache(key) == _BLOCKED

    def _touch_keys(self, keys: List[str]):
        if self._cache is not None:
            for key in keys:
                self._cache.touch(key)
        else:
            with self.caching():
                self._touch_keys(keys)

    def _drop(self, key: str):
        assert self._cache is not None, CacheAccessError
        del self._cache[key]

    def _is_cached(self, method, *args):
        return self._get_key(method, *args) in self._cache

    def _cached_call(self, method, *args, **kwargs):  # todo: kwargs necessary?
        """Wrapper for a method, handles caching 'at both ends'
        """
        key = self._get_key(method, *args)
        if self._cache is not None:
            # Check if the file's already cached
            if key in self._cache:
                t0 = time.time()
                while self._is_blocked(key) and time.time() < t0 + self._config.block_timeout:
                    # Some other thread is currently reading the same frame
                    # Wait a bit and try to get from cache again
                    log.debug(f'{self.__class__}: waiting for {key} to be released...', 5)
                    time.sleep(0.01)

                value = self._from_cache(key)
                if isinstance(value, str) and value == _BLOCKED:
                    log.warning(f'{self.__class__}: timed out waiting for {key}.')
                else:
                    log.debug(f"{self.__class__}: read {key}.")
                    return value

            # Cache a temporary string to 'block' the key
            log.debug(f"{self.__class__}: caching {key}")
            log.vdebug(f"{self.__class__}: block {key}.")
            self._block(key)
            log.vdebug(f"{self.__class__}: execute {key}.")
            value = method(*args, **kwargs)
            log.vdebug(f"{self.__class__}: write {key}.")
            self._to_cache(key, value)
            return value


        log.vdebug(f"Execute {key}.")
        return method(*args, **kwargs)

    def __enter__(self):
        if self._config.do_cache:
            if self._cache is None:
                log.debug(f'{self.__class__.__qualname__}: opening cache.')
                self._cache = diskcache.Cache(
                    directory=settings.cache.dir,
                    size_limit=settings.cache.size_limit_gb * 1e9,
                )

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._config.do_cache:
            if self._cache is not None:
                log.debug(f'{self.__class__.__qualname__}: closing cache.')
                self._cache.close()
                self._cache = None

            if exc_type != None:  # `is not` doesn't work here
                raise(exc_type, exc_value, tb)
            else:
                return True

    @contextmanager
    def caching(self):
        try:
            self.__enter__()
            yield self
        finally:
            self.__exit__(*sys.exc_info())


class Handler(object):
    """
    """

    _implementation: object
    _implementation_factory = Factory
    _implementation_class = object  # actually, it's type, but that doesn't fly with MyPy for some reason

    def set_implementation(self, implementation: str) -> str:
        impl_type: type = self._implementation_factory(implementation).get()
        assert issubclass(impl_type, self._implementation_class)

        self._implementation = impl_type()
        return self._implementation_factory.get_str(  # todo: this is not necessary when using @extend(<Factory>)
            self._implementation.__class__
        )

    def get_implementation(self) -> str:
        return self._implementation.__class__.__qualname__


class Feature(abc.ABC):  # todo: should probably use Config for parameters after all :)
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[HsvColor]
    _state: Optional[np.ndarray]
    _skip: bool
    _ready: bool

    _description: str = ''
    _elements: Tuple[BackendInstance, ...] = ()

    _parameters: Tuple[str,...] = ()
    _parameter_defaults: Dict[str, Any] = {}
    _parameter_descriptions: Dict[str, str] = {}

    def __init__(self, elements: Tuple[BackendInstance, ...]):
        self._skip = False
        self._ready = False

        self._elements = elements
        self._color = HsvColor(255,255,255)  # start out as white

    def calculate(self, frame: np.ndarray, state: np.ndarray = None) \
            -> Tuple[Any, np.ndarray]:
        """Calculate Feature for given frame
            and update state image (optional)
        """
        if state is not None:
            state = self.state(frame, state)
        return self.value(frame), state

    @property
    def skip(self) -> bool:
        return self._skip

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def color(self) -> HsvColor:
        """Color of the Feature in figures.

            A Feature's color must be set as not to overlap with
            other Features in the same FeatureSet.
            Therefore, <Feature>._color must be determined by FeatureSet!
        """
        if self._color is not None:
            return self._color
        else:
            raise ValueError

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

    @abc.abstractmethod
    def name(self) -> str:
        """Return the name of the feature
        """
        raise NotImplementedError

    @classmethod
    def parameters(cls) -> Tuple[str,...]:
        return cls._parameters

    @classmethod
    def parameter_defaults(cls) -> Dict[str, Any]:
        return cls._parameter_defaults

    @classmethod
    def parameter_descriptions(cls) -> Dict[str, str]:
        return cls._parameter_descriptions

    @classmethod
    def description(cls) -> str:
        return cls._description


class FeatureSet(object):
    _features: Tuple[Feature, ...]
    _colors: Tuple[HsvColor, ...]

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features

    def get_colors(self) -> Tuple[HsvColor, ...]:  # todo: should be called each time a color is set
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

            color = HsvColor(
                float(color[0]),
                float(220),
                float(255 - repetition * increment)
            )

            feature._color = color
            colors.append(color)

        self._colors = tuple(HsvColor(*c) for c in colors)
        return self.colors

    @property
    def colors(self) -> Tuple[HsvColor, ...]:
        return self._colors

    @property
    def features(self) -> Tuple[Feature, ...]:
        return self._features


class FeatureType(Factory):  # todo: nest in Feature?
    _type = Feature

    def get(self) -> Type[Feature]:
        feature = super().get()
        if issubclass(feature, Feature):
            return feature
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{feature}'. "
                f"This is very weird and shouldn't happen, really."
            )


@dataclass
class BaseAnalyzerConfig(Config):
    video_path: Optional[str] = field(default=None)
    design_path: Optional[str] = field(default=None)
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)


class AnalyzerState(IntEnum):  # todo: would be cool to compare this and analyzer_state in api.js on load
    UNKNOWN = 0
    INCOMPLETE = 1
    CAN_LAUNCH = 2
    LAUNCHED = 3
    CAN_RUN = 4
    RUNNING = 5
    DONE = 6
    CANCELED = 7
    ERROR = 8

    @classmethod
    def do_launch(cls, state: int) -> bool:
        return state in [
            cls.CAN_LAUNCH,
            cls.LAUNCHED,
            cls.CAN_RUN,
            cls.RUNNING,
            cls.DONE,
            cls.CANCELED
        ]


class BaseVideoAnalyzer(BackendInstance, RootInstance):
    _instances: List[BackendInstance]
    _instance_class = BackendInstance
    _config: BaseAnalyzerConfig

    _state: int
    _busy: bool
    _progress: float

    _cancel: threading.Event

    results: Dict[str, pd.DataFrame]

    _description: str

    _timer: Timer

    _video_hash: Optional[str]
    _design_hash: Optional[str]

    _launched: bool
    _ok_to_run: bool

    _model: Optional[object]

    def __init__(self, config: BaseAnalyzerConfig = None):
        super().__init__(config)

        self._description = ''
        self._timer = Timer(self)
        self._launched = False
        self._ok_to_run = False

        self._hash_video = None
        self._hash_design = None

        self._state = AnalyzerState.INCOMPLETE
        self._busy = False
        self._progress = 0.0
        self._model = None


    def set_model(self, model):
        self._model = model
        if self.config.name is None:
            self.config(name=f"#{self.model['id']}")

    @property
    def model(self):
        return self._model

    @backend.expose(backend.commit)
    def commit(self) -> bool:
        """Save video analysis configuration to history database
        """
        log.debug("committing")
        self._model.store()  # todo: solve circular dependency
        return True

    @abc.abstractmethod
    @backend.expose(backend.can_launch)
    def can_launch(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    @backend.expose(backend.can_run)
    def can_run(self) -> bool:
        raise NotImplementedError

    @backend.expose(backend.confirm_run)
    def override(self) -> None:
        self._do_run = True

    @property
    def ok_to_run(self):
        return self._ok_to_run

    @property
    def launched(self):
        return self._launched

    def set_state(self, state: int):
        self._state = state

    @property
    def state(self) -> int:
        return self._state

    def set_busy(self, busy: bool):
        self._busy = busy

    @property
    def busy(self) -> bool:
        return self._busy

    def set_progress(self, progress: float):
        self._progress = progress

    @property
    def progress(self) -> float:
        return self._progress

    @abc.abstractmethod
    def _launch(self):
         raise NotImplementedError

    @property
    def config(self) -> BaseAnalyzerConfig:
        return self._config

    @abc.abstractmethod
    def _new_results(self):
        raise NotImplementedError

    @abc.abstractmethod
    @backend.expose(backend.analyze)
    def analyze(self) -> bool:
        raise NotImplementedError

    @property
    def position(self) -> float:
        return -1.0

    @stream
    @backend.expose(backend.status)
    def status(self) -> dict:
        return {
            'state': self.state,
            'busy': self.busy,
            'position': self.position,
            'progress': self.progress,
        }

    @backend.expose(backend.launch)
    def launch(self) -> bool:
        with self.lock():
            if self.can_launch():
                self._launch()
                self._gather_instances()
                self.set_state(AnalyzerState.LAUNCHED)
                streams.update()
                return True
            else:
                log.warning(f"{self.__class__.__qualname__} can not be launched.")  # todo: try to be more verbose
                return False

    @contextmanager
    def caching(self):
        """Caching context: propagated context to
            every object in _instances that implements caching
        """
        caching_instances = [
            e for e in self._instances if
            isinstance(e, CachingBackendInstance)
        ]
        log.debug(f'{self.__class__.__name__}: propagate caching context '
                  f'to {[i.__class__.__name__ for i in caching_instances]}')
        try:
            for element in caching_instances:
                element.__enter__()
            yield self
        finally:
            for element in caching_instances:
                element.__exit__(*sys.exc_info())

    def cache_open(self):
        caching_instances = [
            e for e in self._instances if
            isinstance(e, CachingBackendInstance)
        ]
        log.debug(f'{self.__class__.__name__}: propagate caching context '
                  f'to {[i.__class__.__name__ for i in caching_instances]}')
        for element in caching_instances:
            element.__enter__()

    def cache_close(self):
        caching_instances = [
            e for e in self._instances if
            isinstance(e, CachingBackendInstance)
        ]
        log.debug(f'close cache')
        for element in caching_instances:
            element.__exit__(*sys.exc_info())

    @contextmanager
    def time(self, message: str = ''):
        try:
            self._timer.__enter__(message)
            yield self
        finally:
            self._timer.__exit__()

    @property
    def timing(self) -> Optional[Timing]:
        if self._timer.timing is not None:
            return Timing(*self._timer.timing)
        else:
            return None

    def export(self):
        raise NotImplementedError

    def describe(self, description: str):
        self._description = description

    @property
    def description(self):
        return self._description


class AnalyzerType(Factory):
    _type = BaseVideoAnalyzer

    def get(self) -> Type[BaseVideoAnalyzer]:
        t = super().get()
        assert issubclass(t, self._type)
        return t
