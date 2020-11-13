from enum import IntEnum, Enum

import diskcache
import sys
import abc
import time
import threading
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple, Dict, Type, Mapping

import numpy as np
import pandas as pd

from pydantic import Field

from shapeflow import settings, get_logger, get_cache
from shapeflow.api import api

from shapeflow.core import RootException, SetupError, RootInstance, Described
from shapeflow.maths.colors import Color, HsvColor, as_hsv
from shapeflow.util.meta import describe_function
from shapeflow.util import Timer, Timing
from shapeflow.core.db import BaseAnalysisModel
from shapeflow.core.config import Factory, BaseConfig, Instance, Configurable
from shapeflow.core.streaming import EventStreamer

from shapeflow.core.interface import InterfaceFactory


log = get_logger(__name__)


class BackendSetupError(SetupError):
    msg = 'Error while setting up backend'


class BackendError(RootException):
    msg = 'Error in backend'


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


_BLOCKED = 'BLOCKED'


class PushEvent(Enum):
    STATUS = 'status'
    CONFIG = 'config'
    NOTICE = 'notice'


class AnalyzerState(IntEnum):
    """The state of an analyzer"""

    UNKNOWN = 0
    INCOMPLETE = 1
    CAN_LAUNCH = 2
    LAUNCHED = 3
    CAN_FILTER = 4
    CAN_ANALYZE = 5
    ANALYZING = 6
    DONE = 7
    CANCELED = 8
    ERROR = 9

    @classmethod
    def can_launch(cls, state: int) -> bool:
        """Returns ``True`` if an analyzer can launch from this state"""
        return state in [
            cls.CAN_LAUNCH,
            cls.LAUNCHED,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.CANCELED,
        ]

    @classmethod
    def is_launched(cls, state: int) -> bool:
        """Returns ``True`` if an analyzer is launched in this state"""
        return state in [
            cls.LAUNCHED,
            cls.CAN_FILTER,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.ANALYZING,
            cls.CANCELED,
        ]


class QueueState(IntEnum):
    """The state of the analysis queue"""
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class CachingInstance(Instance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]

    def __init__(self, config: BaseConfig = None):
        super(CachingInstance, self).__init__(config)
        self._open_cache()

    def __del__(self):
        self._close_cache()

    def _get_key(self, method, *args) -> str:
        # Key should be instance-independent to handle multithreading
        #  and caching between application runs.
        # Hashing the string is a significant performance hit.
        return f"{describe_function(method)}{args}"

    def _to_cache(self, key: str, value: Any):
        if self._cache is None:
            raise CacheAccessError
        self._cache.set(key, value)

    def _from_cache(self, key: str) -> Optional[Any]:
        if self._cache is None:
            raise CacheAccessError
        return self._cache.get(key)

    def _block(self, key: str):
        if self._cache is None:
            raise CacheAccessError
        self._cache.set(key, _BLOCKED)

    def _is_blocked(self, key: str) -> bool:
        if self._cache is None:
            raise CacheAccessError
        return key in self._cache \
               and isinstance(self._cache[key], str) \
               and self._from_cache(key) == _BLOCKED

    def _touch_keys(self, keys: List[str]):
        if self._cache is None:
            raise CacheAccessError
        for key in keys:
            if key in self._cache:
                self._cache.touch(key)

    def _drop(self, key: str):
        if self._cache is None:
            raise CacheAccessError
        del self._cache[key]

    def _is_cached(self, method, *args):
        if self._cache is None:
            raise CacheAccessError
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
                    log.debug(f'{self.__class__.__qualname__}: '
                              f'waiting for {key} to be released...', 5)
                    time.sleep(0.01)

                value = self._from_cache(key)
                if isinstance(value, str) and value == _BLOCKED:
                    log.warning(f'{self.__class__.__qualname__}: '
                                f'timed out waiting for {key}.')
                else:
                    log.debug(f"{self.__class__.__qualname__}: "
                              f"read cached {key}.")
                    return value

            # Cache a temporary string to 'block' the key
            log.debug(f"{self.__class__.__qualname__}: caching {key}")
            log.vdebug(f"{self.__class__.__qualname__}: block {key}.")
            self._block(key)
            log.vdebug(f"{self.__class__.__qualname__}: execute {key}.")
            value = method(*args, **kwargs)
            log.vdebug(f"{self.__class__.__qualname__}: write {key}.")
            self._to_cache(key, value)
            return value
        else:
            log.vdebug(f"Execute {key}.")
            return method(*args, **kwargs)

    def _open_cache(self, override: bool = False):
        if settings.cache.do_cache or override:
            log.debug(f"{self.__class__.__qualname__}: "
                      f"opening cache @ {settings.cache.dir}")
            self._cache = get_cache(settings)
        else:
            self._cache = None

    def _close_cache(self):
        if self._cache is not None:
            log.debug(f"{self.__class__.__qualname__}: "
                      f"closing cache @ {settings.cache.dir}")
            self._cache.close()
            self._cache = None

class FeatureConfig(BaseConfig, abc.ABC):
    """Abstract :class:`~shapeflow.core.backend.Feature` parameters"""
    pass


class Feature(abc.ABC, Configurable):  # todo: should probably use Config for parameters after all :)
    """A feature implements interactions between BackendElements to
        produce a certain value
    """
    _color: Optional[Color]
    _state: Optional[np.ndarray]

    _label: str = ''  # todo: keep these in the config instead?
    _unit: str = ''
    _elements: Tuple[Instance, ...] = ()

    _config: Optional[FeatureConfig]
    _global_config: FeatureConfig
    _config_class: Type[FeatureConfig] = FeatureConfig

    def __init__(self, elements: Tuple[Instance, ...], global_config: FeatureConfig, config: Optional[dict] = None):
        self._skip = False
        self._ready = False

        self._elements = elements
        self._global_config = global_config

        if config is not None:
            self._config = global_config.__class__(**config)
        else:
            self._config = None

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

    def set_color(self, color: Color):
        self._color = color

    @property
    def color(self) -> Color:
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
    def _guideline_color(self) -> Color:
        """Returns the 'guideline color' of a Feature instance
            Used by FeatureSet to determine the actual _color
        """
        raise NotImplementedError

    @abc.abstractmethod  # todo: we're dealing with frames explicitly, so maybe this should be an shapeflow.video thing...
    def state(self, frame: np.ndarray, state: np.ndarray) -> np.ndarray:
        """Return the Feature instance's state image for a given frame
        """
        raise NotImplementedError

    @abc.abstractmethod
    def value(self, frame: np.ndarray) -> Any:
        """Compute the value of the Feature instance for a given frame
        """
        raise NotImplementedError

    @property
    def config(self):
        if self._config is not None:
            return self._config
        else:
            return self._global_config


class FeatureSet(Configurable):
    """A set of :class:`~shapeflow.core.backend.Feature` instances"""

    _feature: Tuple[Feature, ...]
    _colors: Tuple[Color, ...]
    _config_class = FeatureConfig

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features

    def resolve_colors(self) -> Tuple[Color, ...]:
        guideline_colors = [as_hsv(f._guideline_color()) for f in self._features]

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
    def colors(self) -> Tuple[Color, ...]:
        return self._colors

    @property
    def features(self) -> Tuple[Feature, ...]:
        return self._features

    def calculate(self, frame: np.ndarray, state: Optional[np.ndarray]) -> Tuple[List[Any], Optional[np.ndarray]]:
        values = []

        for feature in self.features:
            value, state = feature.calculate(frame=frame, state=state)
            values.append(value)

        return values, state


class FeatureType(InterfaceFactory):
    """:class:`~shapeflow.core.backend.Feature` factory"""

    _type = Feature
    _mapping: Mapping[str, Type[Feature]] = {}
    _config_type = FeatureConfig

    def get(self) -> Type[Feature]:
        feature = super().get()
        assert issubclass(feature, Feature)
        return feature

    def config_schema(self) -> dict:
        return self.get().config_schema()

    @classmethod
    def __modify_schema__(cls, field_schema):
        super().__modify_schema__(field_schema)
        field_schema.update(
            units={ k:v._unit for k,v in cls._mapping.items() },
            labels={ k:v._label for k,v in cls._mapping.items() }
        )


class BaseAnalyzerConfig(BaseConfig):
    """Abstract analyzer configuration"""
    video_path: Optional[str] = Field(default=None)
    design_path: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)


class BaseAnalyzer(Instance, RootInstance):
    """Abstract analyzer"""

    _config: BaseAnalyzerConfig

    _state: int
    _busy: bool
    _progress: float

    _cancel: threading.Event
    _error: threading.Event

    results: Dict[str, pd.DataFrame]

    _timer: Timer

    _video_hash: Optional[str]
    _design_hash: Optional[str]

    _model: Optional[BaseAnalysisModel]
    _eventstreamer: Optional[EventStreamer]

    _runs: int

    def __init__(self, config: BaseAnalyzerConfig = None, eventstreamer: EventStreamer = None):
        self.set_eventstreamer(eventstreamer)

        super().__init__(config)

        self._timer = Timer(self, log)
        self._launched = False

        self._hash_video = None
        self._hash_design = None

        self._state: AnalyzerState = AnalyzerState.INCOMPLETE
        self._busy = False
        self._progress = 0.0
        self._model = None

        self._cancel = threading.Event()
        self._error = threading.Event()

    def set_model(self, model: BaseAnalysisModel):
        self._model = model
        if self.config.name is None:
            self.config(name=self.get_name())

        self._runs = self.model.get_runs()

    @property
    def model(self):
        return self._model

    @property
    def runs(self):
        return self._runs

    def _new_run(self):
        self._runs += 1

    @property
    def eventstreamer(self):
        return self._eventstreamer

    def set_eventstreamer(self, eventstreamer: EventStreamer = None):
        self._eventstreamer = eventstreamer

    def event(self, category: PushEvent, data: dict):
        """Push an event

        :param category: event category
        :param data: event data
        :return:
        """

        if self.eventstreamer is not None:
            self.eventstreamer.event(category.value, self.id, data)

    def notice(self, message: str, persist: bool = False):
        self.event(
            PushEvent.NOTICE,
            data={'message': message, 'persist': persist}
        )
        log.warning(f"'{self.id}': {message}")

    # @backend.expose(backend.commit)
    @api.va.__id__.commit.expose()
    def commit(self) -> bool:
        """Save video analysis configuration to history database
        """
        if self._model is not None:
            log.debug(f"committing '{self.id}'")
            self._model.store()
            return True
        else:
            return False

    # @backend.expose(backend.can_launch)
    @abc.abstractmethod
    def can_launch(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def can_filter(self) -> bool:
        raise NotImplementedError

    # @backend.expose(backend.can_analyze)
    @abc.abstractmethod
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

    # @backend.expose(backend.state_transition)
    @api.va.__id__.state_transition.expose()
    def state_transition(self, push: bool = True) -> int:
        """| Handle state transitions
           | :attr:`shapeflow.api._VideoAnalyzerDispatcher.state_transition`
        """

        if self.state == AnalyzerState.INCOMPLETE and self.can_launch():
            self.set_state(AnalyzerState.CAN_LAUNCH, push)
        elif self.state == AnalyzerState.LAUNCHED or self.state == AnalyzerState.CAN_FILTER:
            if self.can_analyze():
                self.set_state(AnalyzerState.CAN_ANALYZE, push)
            elif self.can_filter():
                self.set_state(AnalyzerState.CAN_FILTER, push)
            else:
                self.set_state(AnalyzerState.LAUNCHED, push)
        elif self.state == AnalyzerState.DONE or self.state == AnalyzerState.CANCELED:
            self.set_progress(0.0, push=False)
            if self.can_analyze():
                self.set_state(AnalyzerState.CAN_ANALYZE, push)
            elif self.can_filter():
                self.set_state(AnalyzerState.CAN_FILTER, push)
            elif self.launched:
                self.set_state(AnalyzerState.LAUNCHED, push)
        else:
            if self.can_analyze():
                self.set_state(AnalyzerState.CAN_ANALYZE, push)
            elif self.can_filter():
                self.set_state(AnalyzerState.CAN_FILTER, push)
            elif self.launched:
                self.set_state(AnalyzerState.LAUNCHED, push)
            elif self.can_launch():
                self.set_state(AnalyzerState.CAN_LAUNCH, push)
            else:
                self.set_state(AnalyzerState.ERROR)

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

    # @backend.expose(backend.cancel)
    @api.va.__id__.cancel.expose()
    def cancel(self) -> None:
        super().cancel()
        self.set_state(AnalyzerState.CANCELED)

    def error(self) -> None:
        super().error()
        self.set_state(AnalyzerState.ERROR)

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

    # @backend.expose(backend.analyze)
    @abc.abstractmethod
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

    # @backend.expose(backend.status)
    @api.va.__id__.status.expose()
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
        self.event(PushEvent.STATUS, self.status())

    # @backend.expose(backend.get_config)
    @api.va.__id__.get_config.expose()
    def get_config(self, do_tag=False) -> dict:
        self._gather_config()
        config = self.config.to_dict(do_tag)
        return config

    # @backend.expose(backend.set_config)
    @abc.abstractmethod
    def set_config(self, config: dict, silent: bool = False) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def _gather_config(self):
        raise NotImplementedError

    # @backend.expose(backend.launch)
    @api.va.__id__.launch.expose()
    def launch(self) -> bool:
        with self.lock():
            if self.can_launch():
                self._launch()

                # Commit to history
                self.commit()

                # Push events
                self.set_state(AnalyzerState.LAUNCHED)
                self.event(PushEvent.CONFIG, self.get_config())

                # State transition (may change from LAUNCHED ~ config)
                self.state_transition()

                return self.launched
            else:
                log.warning(f"{self.__class__.__qualname__} can not be launched.")  # todo: try to be more verbose
                return False

    @api.va.__id__.get_name.expose()
    def get_name(self) -> str:
        try:
            return self.model.get_name()
        except AttributeError:
            return self.id

    # @backend.expose(backend.get_db_id)
    @api.va.__id__.get_db_id.expose()
    def get_db_id(self) -> int:
        return self.model.get_id()

    @contextmanager
    def time(self, message: str = '', logger = log):
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

    @property
    def description(self):
        return self._description


class AnalyzerType(Factory):
    _type = BaseAnalyzer
    _mapping: Mapping[str, Type[Described]] = {}

    def get(self) -> Type[BaseAnalyzer]:
        t = super().get()
        assert issubclass(t, self._type)
        return t

    def config_schema(self) -> dict:
        return self.get().config_class()().schema()
