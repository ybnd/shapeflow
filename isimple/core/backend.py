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
class CachingBackendInstanceConfig(abc.ABC, Config):
    do_cache: bool = field(default=True)
    do_background: bool = field(default=False)

    block_timeout: float = field(default=0.1)
    cache_consumer: bool = field(default=False)


class CachingBackendInstance(BackendInstance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]
    _background: Optional[threading.Thread]
    _background_task: Callable

    _config: CachingBackendInstanceConfig
    _class = CachingBackendInstanceConfig()

    def __init__(self, config: CachingBackendInstanceConfig = None):
        super(CachingBackendInstance, self).__init__(config)

        self._cache = None
        self._background = None

    def _get_key(self, method, *args) -> str:
        # Key should be instance-independent to handle multithreading
        #  and caching between application runs.
        # Hashing the string is a significant performance hit.
        return f"{describe_function(method)}:{args}"

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

    def _drop(self, key: str):
        assert self._cache is not None, CacheAccessError
        del self._cache[key]

    def _cached_call(self, method, *args, **kwargs):
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
                    log.vdebug(f"Cache: read {key}.")
                    return value
            if not self._config.cache_consumer:
                # Cache a temporary string to 'block' the key
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
            log.debug(f'{self.__class__.__qualname__}: opening cache.')
            self._cache = diskcache.Cache(
                directory=settings.cache.dir,
                size_limit=settings.cache.size_limit_gb * 1e9,
            )
            if self._config.do_background:
                log.debug(f'{self.__class__.__qualname__}: starting background thread.')
                pass  # todo: can start caching frames in background thread here

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._config.do_cache:
            if self._cache is not None:
                log.debug(f'{self.__class__.__qualname__}: closing cache.')
                self._cache.close()
                self._cache = None

            if self._background is not None and self._background.is_alive():
                log.debug(f'{self.__class__.__qualname__}: stopping background thread.')
                pass  # todo: can stop background thread here (gracefully)
                #        ...also: self._background.is_alive() doesn't recognize self...

            if exc_type is not None:
                return False
            else:
                return True

    @contextmanager
    def caching(self):
        try:
            self.__enter__()
            yield self
        finally:
            self.__exit__(*sys.exc_info())


class Handler(object):  # todo: implementations of CachingBackendInstance in `_implementation` will not be found by `_gather_instances`
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


class Feature(abc.ABC):
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[HsvColor]
    _state: Optional[np.ndarray]
    _skip: bool
    _ready: bool

    _elements: Tuple[BackendInstance, ...]

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


class FeatureType(Factory):
    _type = Feature


@dataclass
class BaseAnalyzerConfig(abc.ABC, Config):
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


class BaseVideoAnalyzer(abc.ABC, BackendInstance, RootInstance):
    _instances: List[BackendInstance]
    _instance_class = BackendInstance
    _config: BaseAnalyzerConfig
    _state: int
    _progress: float

    _lock: threading.Lock

    results: Dict[str, pd.DataFrame]

    _description: str

    _timer: Timer

    _video_hash: Optional[str]
    _design_hash: Optional[str]

    _launched: bool
    _ok_to_run: bool

    _model: Optional[object]

    _stream_methods: list

    def __init__(self, config: BaseAnalyzerConfig = None):
        self.get_id()
        self._stream_methods = []

        super().__init__(config)
        self._description = ''
        self._lock = threading.Lock()
        self._timer = Timer(self)
        self._launched = False
        self._ok_to_run = False

        self._hash_video = None
        self._hash_design = None

        self._state = AnalyzerState.INCOMPLETE
        self._progress = 0.0
        self._model = None

    @property
    def id(self):
        return self._id

    @property
    def stream_methods(self):
        return self._stream_methods

    def set_model(self, model):
        self._model = model
        if self.config.name is None:
            self.config(name=f"#{self.model['id']}")

    @property
    def model(self):
        return self._model

    @abc.abstractmethod
    @backend.expose(backend.can_launch)
    def can_launch(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    @backend.expose(backend.can_run)
    def can_run(self) -> bool:
        raise NotImplementedError

    @backend.expose(backend.confirm_run)
    def override(self):
        self._do_run = True

    @property
    def ok_to_run(self):
        return self._ok_to_run

    @property
    def launched(self):
        return self._launched

    @property
    def state(self):
        return self._state

    @property
    def progress(self):
        return self._progress

    @abc.abstractmethod
    def _launch(self):
         raise NotImplementedError

    @property
    def config(self) -> BaseAnalyzerConfig:
        return self._config

    @abc.abstractmethod
    @backend.expose(backend.analyze)
    def analyze(self) -> bool:
        raise NotImplementedError

    @backend.expose(backend.launch)
    def launch(self) -> bool:
        with self.lock():
            if self.can_launch():
                self._launch()
                self._gather_instances()
                self._state = AnalyzerState.LAUNCHED
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
    def lock(self):
        lock = self._lock.acquire()
        try:
            log.debug(f"Locking {self}")
            yield lock
        finally:
            log.debug(f"Unlocking {self}")
            self._lock.release()

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
