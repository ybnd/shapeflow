from enum import IntEnum, Enum

import diskcache
import abc
import time
import threading
from contextlib import contextmanager
from typing import Any, List, Optional, Dict, Type, Mapping

import pandas as pd

from shapeflow.config import BaseAnalyzerConfig
from shapeflow.core.caching import get_cache
from shapeflow.core.logging import get_logger, RootException
from shapeflow.api import api

from shapeflow.util.meta import describe_function
from shapeflow.util import Timer, Timing, Described, Lockable
from shapeflow.core.db import BaseAnalysisModel
from shapeflow.core.config import Factory, BaseConfig, Instance
from shapeflow.core.streaming import EventStreamer

log = get_logger(__name__)


class BackendSetupError(RootException):
    msg = 'Error while setting up backend'


class BackendError(RootException):
    msg = 'Error in backend'


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


_BLOCKED = 'BLOCKED'


class PushEvent(Enum):
    """Categories of server-pushed events.
    """
    STATUS = 'status'
    CONFIG = 'config'
    NOTICE = 'notice'


class AnalyzerState(IntEnum):
    """The state of an analyzer
    """
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
        """Returns ``True`` if an analyzer can launch from this state
        """
        return state in [
            cls.CAN_LAUNCH,
            cls.LAUNCHED,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.CANCELED,
        ]

    @classmethod
    def is_launched(cls, state: int) -> bool:
        """Returns ``True`` if an analyzer is launched in this state
        """
        return state in [
            cls.LAUNCHED,
            cls.CAN_FILTER,
            cls.CAN_ANALYZE,
            cls.DONE,
            cls.ANALYZING,
            cls.CANCELED,
        ]


class QueueState(IntEnum):
    """The state of the analysis queue
    """
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class CachingInstance(Instance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Cache method results with ``diskcache.Cache``
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

    def cached_call(self, method, *args, **kwargs):  # todo: kwargs necessary?
        """Call a method or get the result from the cache if available.

        Parameters
        ----------
        method
            The method to call
        args
            Any positional arguments to pass on to the method
        kwargs
            Any keyword arguments to pass on to the method

        Returns
        -------
        Any
            Whatever the method returns.
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
            self._cache = get_cache()
        else:
            self._cache = None

    def _close_cache(self):
        if self._cache is not None:
            log.debug(f"{self.__class__.__qualname__}: "
                      f"closing cache @ {settings.cache.dir}")
            self._cache.close()
            self._cache = None


class BaseAnalyzer(Instance, Lockable):
    """Abstract analyzer.
    """
    _id: str
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

    def _set_id(self, id: str):
        self._id = id

    @property
    def id(self):
        return self._id

    def set_model(self, model: BaseAnalysisModel):
        self._model = model
        if self.config.name is None:
            self.config(name=self.get_name())

        self._runs = self.model.get_runs()

    @property
    def model(self):
        """The database model associated with this analyzer.
        """
        return self._model

    @property
    def runs(self):
        """The number of runs performed for this analysis.
        """
        return self._runs

    def _new_run(self):
        self._runs += 1

    @property
    def eventstreamer(self):
        """Return the server-sent event streamer.
        """
        return self._eventstreamer

    def set_eventstreamer(self, eventstreamer: EventStreamer = None):
        """Set the server-sent event streamer.
        """
        self._eventstreamer = eventstreamer

    def event(self, category: PushEvent, data: dict) -> None:
        """Push an event.

        Parameters
        ----------
        category : PushEvent
            The category of event to push
        data : dict
            The data to push
        """
        if self.eventstreamer is not None:
            self.eventstreamer.event(category.value, self.id, data)

    def notice(self, message: str, persist: bool = False) -> None:
        """Push a notice.

        Parameters
        ----------
        message : str
            The notice message to push
        persist : bool
            Whether the notice should be persistent (i.e. stay up on the user
            interface until dismissed manually)
        """
        self.event(
            PushEvent.NOTICE,
            data={'message': message, 'persist': persist}
        )
        log.warning(f"'{self.id}': {message}")

    @api.va.__id__.commit.expose()
    def commit(self) -> bool:
        """Save video analysis configuration to history database

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.commit`
        """
        if self._model is not None:
            log.debug(f"committing '{self.id}'")
            self._model.store()
            return True
        else:
            return False

    @abc.abstractmethod
    def can_launch(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def can_filter(self) -> bool:
        raise NotImplementedError

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

    @api.va.__id__.state_transition.expose()
    def state_transition(self, push: bool = True) -> int:
        """Handle state transitions.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.state_transition`

        Parameters
        ----------
        push : bool
            Whether to push an event once the state is set.

        Returns
        -------
        int
            The resulting state ~ :class:`~shapeflow.backend.AnalyzerState`
        """
        # todo: actually type as AnalyzerState
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

    @api.va.__id__.cancel.expose()
    def cancel(self) -> None:
        """Cancel a running analysis.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.cancel`
        """
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

    @api.va.__id__.status.expose()
    def status(self) -> dict:
        """Get the analyzer's status.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.status`
        """
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

    @api.va.__id__.get_config.expose()
    def get_config(self, do_tag=False) -> dict:
        """Get the analyzer's configuration.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_config`
        """
        self._gather_config()
        config = self.config.to_dict(do_tag)
        return config

    @abc.abstractmethod
    def set_config(self, config: dict, silent: bool = False) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def _gather_config(self):
        raise NotImplementedError

    @api.va.__id__.launch.expose()
    def launch(self) -> bool:
        """Launch the analyzer.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.launch`

        If the analyzer's configuration is sufficiently filled out,
        the analyzer will instantiate any other objects it needs to start
        configuring the analysis further.

        To launch, the analyzer needs at least

        * A valid video file
        * A valid design file
        * At least one valid feature configuration

        Returns
        -------
        bool
            Whether the launch was successful or not.
        """
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

    def get_name(self) -> str:
        try:
            return self.model.get_name()
        except AttributeError:
            return self.id

    @api.va.__id__.get_db_id.expose()
    def get_db_id(self) -> int:
        """Get the database id of this analyzer.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_db_id`
        """
        return self.model.get_id()

    @contextmanager
    def time(self, message: str = ''):
        """A timing context.
        """
        try:
            self._timer.__enter__(message)
            yield self
        finally:
            self._timer.__exit__()

    @property
    def timing(self) -> Optional[Timing]:
        """Get the timing info from the latest run of :func:`~shapeflow.core.backend.BaseAnalyzer.time`
        """
        if self._timer.timing is not None:
            return Timing(*self._timer.timing)
        else:
            return None

    def export(self):
        raise NotImplementedError

    @property
    def description(self):
        return self._description

    def _set_id(self, id: str):
        self._id = id


class AnalyzerType(Factory):
    """Analyzer type factory
    """
    _type = BaseAnalyzer
    _mapping: Mapping[str, Type[Described]] = {}

    def get(self) -> Type[BaseAnalyzer]:
        """Return the analyzer type.
        """
        t = super().get()
        assert issubclass(t, self._type)
        return t

    def config_schema(self) -> dict:
        """Return the config schema of the analyzer type.
        """
        return self.get().config_class()().schema()
