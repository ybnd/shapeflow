from dataclasses import dataclass, field
from enum import IntEnum, Enum

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

from pydantic import Field, FilePath, DirectoryPath

from isimple import settings, get_logger, get_cache
from isimple.endpoints import BackendRegistry

from isimple.core import RootException, SetupError, RootInstance
from isimple.maths.colors import HsvColor
from isimple.util.meta import describe_function
from isimple.util import Timer, Timing, hash_file, timed
from isimple.core.config import Factory, untag, BaseConfig, Instance, Configurable
from isimple.core.streaming import stream, streams, EventStreamer

from isimple.core.interface import InterfaceFactory


log = get_logger(__name__)
backend = BackendRegistry()


class BackendSetupError(SetupError):
    msg = 'Error while setting up backend'


class BackendError(RootException):
    msg = 'Error in backend'


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


_BLOCKED = 'BLOCKED'


class CachingInstance(Instance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]

    _is_caching: bool
    _background: threading.Thread
    _cancel_caching: threading.Event

    def __init__(self, config: BaseConfig = None):
        super(CachingInstance, self).__init__(config)

        self._cache = None
        self._cancel_caching = threading.Event()

    @backend.expose(backend.is_caching)
    def is_caching(self) -> bool:
        return self._is_caching

    @backend.expose(backend.cancel_caching)
    def cancel_caching(self) -> None:
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
                if key in self._cache:
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
                while self._is_blocked(key) and time.time() < t0 + settings.cache.block_timeout:
                    # Some other thread is currently reading the same frame
                    # Wait a bit and try to get from cache again
                    log.debug(f'{self.__class__}: waiting for {key} to be released...', 5)
                    time.sleep(0.01)

                value = self._from_cache(key)
                if isinstance(value, str) and value == _BLOCKED:
                    log.warning(f'{self.__class__}: timed out waiting for {key}.')
                else:
                    log.debug(f"{self.__class__}: read cached {key}.")
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

    def __enter__(self, override: bool = False):
        if settings.cache.do_cache or override:
            if self._cache is None:
                log.debug(f'{self.__class__.__qualname__}: opening cache @ {settings.cache.dir}')
                self._cache = diskcache.Cache(
                    directory=settings.cache.dir,
                    size_limit=settings.cache.size_limit_gb * 1e9,
                )

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._cache is not None:
            log.debug(f'{self.__class__.__qualname__}: closing cache @ {settings.cache.dir}')
            self._cache.close()
            self._cache = None

        if exc_type != None:  # `is not` doesn't work here
            raise(exc_type, exc_value, tb)
        else:
            return True

    @contextmanager
    def caching(self, override: bool = False):
        try:
            self.__enter__(override)
            yield self
        finally:
            self.__exit__(*sys.exc_info())


class Handler(abc.ABC):
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


class FeatureConfig(BaseConfig, abc.ABC):
    pass


class Feature(abc.ABC):  # todo: should probably use Config for parameters after all :)
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[HsvColor]
    _state: Optional[np.ndarray]

    _label: str = ''  # todo: keep these in the config instead?
    _unit: str = ''
    _description: str = ''
    _elements: Tuple[Instance, ...] = ()

    _config: Optional[FeatureConfig]
    _global_config: FeatureConfig
    _config_class: Type[FeatureConfig] = FeatureConfig

    def __init__(self, elements: Tuple[Instance, ...], global_config: FeatureConfig, config: Optional[FeatureConfig] = None):
        self._skip = False
        self._ready = False

        self._elements = elements
        self._global_config = global_config
        self._config = config
        self._color = HsvColor(h=0,s=200,v=255)  # start out as red

    def calculate(self, frame: np.ndarray, state: np.ndarray = None) \
            -> Tuple[Any, Optional[np.ndarray]]:
        """Calculate Feature for given frame
            and update state image (optional)
        """
        if state is not None:
            state = self.state(frame, state)
        return self.value(frame), state

    @classmethod
    def label(cls) -> str:
        return cls._label

    @classmethod
    def unit(cls) -> str:
        return cls._unit

    @property
    def skip(self) -> bool:
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        raise NotImplementedError

    def set_color(self, color: HsvColor):
        self._color = color

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
    def _guideline_color(self) -> HsvColor:
        """Returns the 'guideline color' of a Feature instance
            Used by FeatureSet to determine the actual _color
        """
        raise NotImplementedError

    @abc.abstractmethod  # todo: we're dealing with frames explicitly, so maybe this should be an isimple.video thing...
    def state(self, frame: np.ndarray, state: np.ndarray) -> np.ndarray:
        """Return the Feature instance's state image for a given frame
        """
        raise NotImplementedError

    @abc.abstractmethod
    def value(self, frame: np.ndarray) -> Any:
        """Compute the value of the Feature instance for a given frame
        """
        raise NotImplementedError

    @classmethod
    def description(cls) -> str:
        return cls._description

    @property
    def config(self):
        if self._config is not None:
            return self._config
        else:
            return self._global_config


class FeatureSet(object):
    _feature: Tuple[Feature, ...]
    _colors: Tuple[HsvColor, ...]

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features

    def resolve_colors(self) -> Tuple[HsvColor, ...]:
        guideline_colors = [f._guideline_color() for f in self._features]

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
                    if abs(float(color.h) - np.mean([guideline_colors[i].h for i in bin])) < tolerance:
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
    def colors(self) -> Tuple[HsvColor, ...]:
        return self._colors

    @property
    def features(self) -> Tuple[Feature, ...]:
        return self._features


class FeatureType(Factory):  # todo: nest in Feature?
    _type = Feature
    _mapping: Dict[str, Type[Feature]] = {}

    def get(self) -> Type[Feature]:
        feature = super().get()

        if issubclass(feature, Feature):
            return feature
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{feature}'. "
                f"This is very weird and shouldn't happen, really."
            )


class BaseAnalyzerConfig(BaseConfig):
    video_path: Optional[str] = Field(default=None)
    design_path: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)


class AnalyzerEvent(Enum):
    STATUS = 'status'
    CONFIG = 'config'
    RESULT = 'result'
    RMETAD = 'result_metadata'


class AnalyzerState(IntEnum):
    UNKNOWN = 0
    INCOMPLETE = 1
    CAN_LAUNCH = 2
    LAUNCHED = 3
    CACHING = 4
    CAN_ANALYZE = 5
    ANALYZING = 6
    DONE = 7
    CANCELED = 8
    ERROR = 9

    @classmethod
    def can_launch(cls, state: int) -> bool:
        return state in [
            cls.CAN_LAUNCH,
            cls.LAUNCHED,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.CANCELED,
        ]

    @classmethod
    def is_launched(cls, state: int) -> bool:
        return state in [
            cls.LAUNCHED,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.ANALYZING,
            cls.CANCELED,
        ]


class BaseVideoAnalyzer(Instance, RootInstance):
    _endpoints: BackendRegistry = backend
    _instances: List[Instance]
    _instance_class = Instance
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

    _model: Optional[object]
    _eventstreamer: Optional[EventStreamer]

    def __init__(self, config: BaseAnalyzerConfig = None, eventstreamer: EventStreamer = None):
        self.set_eventstreamer(eventstreamer)

        super().__init__(config)

        self._description = ''
        self._timer = Timer(self)
        self._launched = False

        self._hash_video = None
        self._hash_design = None

        self._state: AnalyzerState = AnalyzerState.INCOMPLETE
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

    @property
    def eventstreamer(self):
        return self._eventstreamer

    def set_eventstreamer(self, eventstreamer: EventStreamer = None):
        self._eventstreamer = eventstreamer

    def event(self, category: AnalyzerEvent, data: dict):
        """Push an event

        :param category: event category
        :param data: event data
        :return:
        """

        if self.eventstreamer is not None:
            self.eventstreamer.event(category.value, self.id, data)

    @backend.expose(backend.commit)
    def commit(self) -> bool:
        """Save video analysis configuration to history database
        """
        if self._model is not None:
            log.debug(f"committing {self.id}")
            self._model.store()  # type: ignore
            # todo: solve circular dependency
            return True
        else:
            return False

    @abc.abstractmethod
    @backend.expose(backend.can_launch)
    def can_launch(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    @backend.expose(backend.can_analyze)
    def can_analyze(self) -> bool:
        raise NotImplementedError

    @property
    def launched(self):
        return AnalyzerState.is_launched(self.state)

    def set_state(self, state: int, push: bool = True):
        self._state = state

        if push:
            self.push_status()

    @property
    def state(self) -> AnalyzerState:
        assert isinstance(self._state, AnalyzerState)  # todo: fix int / AnalyzerState typing
        return self._state

    @property
    def done(self) -> bool:
        return self.state == AnalyzerState.DONE

    @backend.expose(backend.state_transition)
    def state_transition(self, push: bool = True) -> int:
        """Handle state transitions
        """

        if self.state == AnalyzerState.INCOMPLETE and self.can_launch():
            self.set_state(AnalyzerState.CAN_LAUNCH, push)
        elif self.state == AnalyzerState.LAUNCHED:
            if self.can_analyze:
                self.set_state(AnalyzerState.CAN_ANALYZE, push)
        elif self.state == AnalyzerState.DONE or self.state == AnalyzerState.CANCELED:
            self.set_progress(0.0, push=False)
            if self.can_analyze:
                self.set_state(AnalyzerState.CAN_ANALYZE, push)
            elif self.launched:
                self.set_state(AnalyzerState.LAUNCHED, push)
            elif self.can_launch:
                self.set_state(AnalyzerState.CAN_LAUNCH, push)

        return int(self.state)

    def set_busy(self, busy: bool, push: bool = True):
        self._busy = busy

        if push:
            self.push_status()

    @property
    def busy(self) -> bool:
        return self._busy

    @contextmanager
    def busy_context(self, busy_state: AnalyzerState = None, done_state: AnalyzerState = None):
        if done_state is None:
            done_state = self.state
        try:
            if busy_state is not None:
                self.set_state(busy_state)
            self.set_busy(True)
            yield
        finally:
            self.set_busy(False)
            self.set_state(done_state)

    @backend.expose(backend.cancel)
    def cancel(self) -> None:
        super().cancel()
        self.set_state(AnalyzerState.CANCELED)

    def set_progress(self, progress: float, push: bool = True):
        self._progress = progress
        if push:
            self.push_status()

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
    @abc.abstractmethod
    def position(self) -> float:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def cached(self) -> bool:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def has_results(self) -> bool:
        raise NotImplementedError

    @backend.expose(backend.status)
    def status(self) -> dict:
        status = {
            'state': self.state,
            'busy': self.busy,
            'cached': self.cached,
            'results': self.has_results,
            'position': self.position,
            'progress': self.progress,
        }

        return status

    def push_status(self):
        self.event(AnalyzerEvent.STATUS, self.status())

    @backend.expose(backend.get_config)
    def get_config(self, do_tag=False) -> dict:
        self._gather_config()
        config = self.config.to_dict(do_tag)
        return config

    @abc.abstractmethod
    def _gather_config(self):
        raise NotImplementedError

    @backend.expose(backend.launch)
    def launch(self) -> bool:
        with self.lock():
            if self.can_launch():
                self._launch()
                self._gather_instances()

                # Commit to history
                self.commit()

                # Push events
                self.set_state(AnalyzerState.LAUNCHED)
                self.event(AnalyzerEvent.CONFIG, self.get_config())

                # State transition (may change from LAUNCHED ~ config)
                self.state_transition()

                return self.launched
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
            isinstance(e, CachingInstance)
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
            isinstance(e, CachingInstance)
        ]
        log.debug(f'{self.__class__.__name__}: propagate caching context '
                  f'to {[i.__class__.__name__ for i in caching_instances]}')
        for element in caching_instances:
            element.__enter__()

    def cache_close(self):
        caching_instances = [
            e for e in self._instances if
            isinstance(e, CachingInstance)
        ]
        log.debug(f'close cache')
        for element in caching_instances:
            element.__exit__(*sys.exc_info())

    @contextmanager
    def time(self, message: str = '', logger = log):
        try:
            self._timer.set_logger(logger)
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
    _mapping: Dict[str, Type[BaseVideoAnalyzer]] = {}

    def get(self) -> Type[BaseVideoAnalyzer]:
        t = super().get()
        assert issubclass(t, self._type)
        return t
