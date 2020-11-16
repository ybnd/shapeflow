"""Main functionality of the ``shapeflow`` server.

Implements ``shapeflow.api`` endpoints related to the global application and
analyzer management.

The classes defined below should not be instantiated individually, but as a
whole using :func:`shapeflow.main.load`, because their setup process is not
very intuitive.
"""

import os
import time
import pickle
from typing import Dict, List, Optional
from threading import Event, Lock, Thread
import datetime

import shortuuid
import diskcache
import cv2
from OnionSVG import check_svg

from shapeflow.util import open_path, sizeof_fmt
from shapeflow.util.filedialog import filedialog
from shapeflow import get_logger, get_cache, settings, update_settings, ROOTDIR
from shapeflow.core import stream_off, Endpoint, RootException
from shapeflow.api import api, _FilesystemDispatcher, _DatabaseDispatcher, _VideoAnalyzerManagerDispatcher, _VideoAnalyzerDispatcher, _CacheDispatcher, ApiDispatcher
from shapeflow.core.streaming import streams, EventStreamer, PlainFileStreamer, BaseStreamer
from shapeflow.core.backend import QueueState, AnalyzerState, BaseAnalyzer
from shapeflow.config import schemas, normalize_config, loads, BaseAnalyzerConfig
from shapeflow.video import init, VideoAnalyzer
import shapeflow.plugins
from shapeflow.server import ShapeflowServer

from shapeflow.db import History


log = get_logger(__name__)


class _Main(object):
    """Implements root-level endpoints of :module:`shapeflow.api`.
    """
    _lock: Lock
    _server: ShapeflowServer

    _log: Optional[PlainFileStreamer]

    def __init__(self, server: ShapeflowServer):
        self._server = server

        self._lock = Lock()
        self._log = None

    @api.ping.expose()
    def ping(self) -> bool:
        self._server.active()
        return True

    @api.map.expose()
    def map(self) -> Dict[str, List[str]]:
        # todo: this is a hacky replacement of Flask map
        map = {
            '/api/' + k: ['GET', 'PUT', 'POST', 'OPTIONS']
            for k in api.address_space.keys()
        }
        va_id_map = {
            '/api/va/__id__/' + k: ['GET', 'PUT', 'POST', 'OPTIONS']
            for k in api.va.__id__.__dir__()
            if isinstance(getattr(api.va.__id__, k), Endpoint)
        }
        return {**map, **va_id_map}

    @api.schemas.expose()
    def schemas(self) -> dict:
        return schemas()

    @api.normalize_config.expose()
    def normalize_config(self, config: dict) -> dict:
        return normalize_config(config)

    @api.get_settings.expose()
    def get_settings(self) -> dict:
        return settings.to_dict()

    @api.set_settings.expose()
    def set_settings(self, settings: dict) -> dict:
        new_settings = update_settings(settings)
        self.restart()
        return new_settings

    @api.events.expose()
    def events(self) -> EventStreamer:  # todo: att Flask server level, should catch & convert to stream response
        return self._server._eventstreamer

    @api.stop_events.expose()
    def stop_events(self) -> None:
        self._server._eventstreamer.stop()

    @api.log.expose()
    def log(self) -> PlainFileStreamer:
        """Start streaming log file
        """
        if self._log is not None:
            self.stop_log()

        log.debug("streaming log file")
        self._log = PlainFileStreamer(path=str(settings.log.path))

        return self._log

    @api.stop_log.expose()
    def stop_log(self) -> None:
        """Stop streaming log file
        """
        log.debug("stopping log file stream")
        if self._log is not None:
            self._log.stop()

    @api.unload.expose()
    def unload(self) -> bool:
        self._server._unload.set()
        return True

    @api.quit.expose()
    def quit(self) -> bool:
        self._server._quit.set()
        return True

    @api.restart.expose()
    def restart(self) -> bool:
        self._server.restart()
        return True

    @api.pid_hash.expose()
    def pid_hash(self) -> str:
        import hashlib
        return hashlib.sha1(bytes(os.getpid())).hexdigest() + '\n'


class _Cache(object):
    """Implements :data:`shapeflow.api.api.cache` endpoints.
    """
    _cache: diskcache.Cache

    def __init__(self):
        self._cache = get_cache(settings)

    @api.cache.clear.expose()
    def _clear_cache(self) -> None:
        log.info(f"clearing cache")
        self._cache.clear()

    @api.cache.size.expose()
    def _cache_size(self) -> str:
        size = sizeof_fmt(self._cache.size)

        return size


class _Filesystem(object):
    """Implements :data:`shapeflow.api.api.fs` endpoints.
    """
    _history: History

    def __init__(self):
        self._history = History()

    @api.fs.select_video.expose()
    def select_video(self) -> Optional[str]:
        return filedialog.load(
            title='Select a video file...',
            pattern=settings.app.video_pattern,
            pattern_description='Video files',
        )

    @api.fs.select_design.expose()
    def select_design(self) -> Optional[str]:
        return filedialog.load(
            title='Select a design file...',
            pattern=settings.app.design_pattern,
            pattern_description='Design files',
        )

    @api.fs.check_video.expose()
    def check_video(self, path: str) -> bool:
        log.debug(f"checking video file '{path}'")
        if os.path.isfile(path):
            try:
                capture = cv2.VideoCapture(path)
                if int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) > 0:
                    self._history.add_video_file(path)  # todo: overhead?
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False

    @api.fs.check_design.expose()
    def check_design(self, path: str) -> bool:
        log.debug(f"checking design file '{path}'")
        if os.path.isfile(path):
            try:
                check_svg(path)
                self._history.add_design_file(path)  # todo: overhead?
                return True
            except:
                return False
        else:
            return False

    @api.fs.open_root.expose()
    def open_root(self) -> None:
        try:
            open_path(str(ROOTDIR))
        except Exception as e:
            log.error(f"Could not open {ROOTDIR}: "
                      f"{e.__class__.__name__}: {e}")


class _Database(object):
    _server: ShapeflowServer
    _history: History

    def __init__(self, server: ShapeflowServer):
        self._server = server
        self._history = History()
        self._history.set_eventstreamer(server._eventstreamer)

    def check_history(self):  # todo: move to shapeflow.db
        if self._history.check():
            self._history.clean()
        else:
            timestamp = datetime.datetime.fromtimestamp(
                time.time()
            ).strftime(settings.format.datetime_format_fs)
            backup_path = f"{settings.db.path}_broken_{timestamp}"
            log.warning(f"backing up old history database @ {backup_path}")
            os.rename(settings.db.path, backup_path)



class _VideoAnalyzerManager(object):
    """Implements :data:`shapeflow.api.api.va` endpoints.

    Manages :class:`BaseAnalyzer` instances
    * Adds / removes instances
    * Handles saving / loading of application state
    * Handles analysis queueing
    * Handles analyzer-specific streams
    """

    _server: ShapeflowServer
    _history: History

    _lock: Lock
    _q_thread: Thread
    _stop_q: Event
    _pause_q: Event
    _q_state: QueueState

    _dispatcher: _VideoAnalyzerManagerDispatcher
    __analyzers__: Dict[str, BaseAnalyzer]  # todo: analyzer manager should register analyzers with api.va on init
    """The currently active analyzers.
    """

    ID_LENGTH = 6
    """Length of ``id`` strings. Kept relatively short for readable URLs.
    """

    def __init__(self, server: ShapeflowServer):
        self.__analyzers__ = {}

        self._server = server
        self._history = History()
        self._history.set_eventstreamer(server._eventstreamer)

        self._lock = Lock()
        self._stop_q = Event()
        self._pause_q = Event()
        self._q_state = QueueState.STOPPED

    def _set_dispatcher(self, dispatcher: _VideoAnalyzerManagerDispatcher):
        self._dispatcher = dispatcher

    def _add(self, analyzer: BaseAnalyzer) -> str:
        if not hasattr(analyzer, 'id'):
            id = shortuuid.ShortUUID().random(length=self.ID_LENGTH)

            # ensure that the id doesn't start with a number there's no collisions
            while id[0].isdigit() or id in self.__analyzers__.keys():
                id = shortuuid.ShortUUID().random(length=self.ID_LENGTH)

            analyzer._set_id(id)


        self.__analyzers__[analyzer.id] = analyzer
        self._dispatcher._add_dispatcher(
            analyzer.id, _VideoAnalyzerDispatcher(instance=analyzer)
        )
        assert self._dispatcher._update is not None
        self._dispatcher._update(self._dispatcher)  # todo: lame signature; also should be a part of _add_dispatcher probably
        return analyzer.id

    def _remove(self, id: str):
        del self.__analyzers__[id]
        for k in filter(lambda k: id in k, list(self._dispatcher._address_space.keys())):  # todo: this is a bit lame
            del self._dispatcher._address_space[k]  # todo: there should be a _remove_dispatcher probably
        assert self._dispatcher._update is not None
        self._dispatcher._update(self._dispatcher)  # todo: lame signature

    def _commit(self):
        for analyzer in self.__analyzers__.values():
            analyzer.commit()

    def _valid(self, id: str):
        if not id in self.__analyzers__:
            raise KeyError(f"no such id: '{id}")

    def notice(self, message: str, persist: bool = False):
        """Push a notice to the server's ``EventStreamer``

        Parameters
        ----------
        message: str
            The message to push
        """
        self._server._eventstreamer.event(
            'notice', id='', data={'message': message, 'persist': persist}
        )

    @api.va.init.expose()
    def init(self) -> str:
        """Initialize a new analyzer. A short unique ``ìd`` will be generated.
        For example, a new analyzer with ``rG7bgH`` as its ``id`` can be
        addressed via ``/api/va/rG7bgH``.

        Returns
        -------
        str
            The ``id`` string of the newly added analyzer
        """
        with self._lock:
            analyzer = VideoAnalyzer()
            analyzer.set_eventstreamer(self._server._eventstreamer)
            self._history.add_analysis(analyzer)
            self._add(analyzer)

            log.info(f"init '{analyzer.id}'")

        self.save_state()
        return analyzer.id

    @api.va.close.expose()
    def close(self, id: str) -> bool:
        """Remove an analyzer.

        Parameters
        ----------
        id: str
            The ``id`` string of the analyzer to remove

        Returns
        -------
        bool
            Whether the analyzer was removed successfully
        """
        self._valid(id)

        with self._lock:
            log.info(f"close '{id}'")
            analyzer = self.__analyzers__[id]
            with analyzer.lock():
                analyzer.commit()
            self._remove(id)

        self.save_state()
        return True

    @api.va.start.expose()
    def q_start(self, queue: List[str]) -> bool:
        """Start analyzing a queue.

        Parameters
        ----------
        queue: List[str]
            List of analyzer ``id`` to queue.
        """
        with self._lock:
            stopped = Event()

            def target():
                if self._q_state == QueueState.STOPPED:
                    self._q_state = QueueState.RUNNING
                    if all(self.__analyzers__[id].can_analyze for id in queue):  # todo: handle non-id entries in q
                        log.info(f"analyzing queue: {queue}")
                        for id in queue:
                            while self._pause_q.is_set():
                                self._q_state = QueueState.PAUSED
                                time.sleep(0.5)
                            self._q_state = QueueState.RUNNING

                            if self._stop_q.is_set():
                                break

                            if not self.__analyzers__[id].done:
                                self.__analyzers__[id].analyze()
                            else:
                                self.__analyzers__[id].notice(
                                    f"already analyzed "
                                    f"'{self.__analyzers__[id].get_name}' "
                                    f"with the current configuration."
                                )
                                log.info(f"skipping '{id}'")
                        self._q_state = QueueState.STOPPED
                    else:
                        log.info(f"Can't analyze all of {queue}")
                else:
                    log.info(f"already started analyzing queue!")

            self._q_thread = Thread(target=target)
            self._q_thread.start()
            self._q_thread.join()

            self._pause_q.clear()

            if self._stop_q.is_set():
                self._stop_q.clear()
                return False
            else:
                return True

    @api.va.stop.expose()
    def q_stop(self) -> None:
        """Stop analyzing the current queue.
        """
        log.info('stopping analysis queue')
        if self._pause_q.is_set():
            self._pause_q.clear()
        self._stop_q.set()
        if settings.app.cancel_on_q_stop:
            self.q_cancel()
        else:
            for analyzer in self.__analyzers__.values():
                if analyzer.state == AnalyzerState.ANALYZING:
                    self.notice(f"waiting for {analyzer.config.name} to finish")

    @api.va.cancel.expose()
    def q_cancel(self) -> None:
        """Cancel analyzing the current queue.
        """
        for analyzer in self.__analyzers__.values():
            if analyzer.state == AnalyzerState.ANALYZING:
                analyzer.cancel()

    @api.va.state.expose()
    def state(self) -> dict:
        """Get the queue state and the status of all analyzers.

        Returns
        -------
        dict
            A ``dict`` of the form::
                {
                    "q_state": 0,  # QueueState
                    "ids": [""]
                }
        """
        with self._lock:
            return {
                'q_state': self._q_state,
                'ids': [k for k in self.__analyzers__.keys()],
                'status': [a.status() for a in self.__analyzers__.values()],
            }

    @api.va.save_state.expose()
    def save_state(self) -> None:
        """Save application state to ``shapeflow.settings.app.state_path``
        """
        if settings.app.save_state:
            log.debug(f"saving application state")

            self._commit()

            with open(settings.app.state_path, 'wb') as f:
                pickle.dump({
                    id: analyzer.model.get('id')
                    for id, analyzer in self.__analyzers__.items()
                    if not analyzer.done
                }, f)

    @api.va.load_state.expose()
    def load_state(self) -> None:
        """Load application state from ``shapeflow.settings.app.state_path``
        """
        if settings.app.load_state:
            log.info(f"loading application state")

            try:
                with open(settings.app.state_path, 'rb') as f:
                    S = pickle.load(f)

                for id, model_id in S.items():
                    assert isinstance(id, str)
                    assert isinstance(model_id, int)

                    model = self._history.fetch_analysis(model_id)

                    if model is not None:
                        model.connect(self._history)

                        config_json = model.get_config_json()
                        if config_json is not None:
                            config = loads(config_json)
                        else:
                            raise RootException('invalid config from database')
                        assert isinstance(config, BaseAnalyzerConfig)

                        analyzer = init(config)
                        analyzer._set_id(id)
                        analyzer.set_eventstreamer(self._server._eventstreamer)

                        analyzer.launch()

                        self._add(analyzer)
                        self._history.add_analysis(analyzer, model)
            except FileNotFoundError:
                pass
            except EOFError:
                pass

    @api.va.stream.expose()
    def stream(self, id: str, endpoint: str) -> BaseStreamer:
        """Stream something.

        Parameters
        ----------
        id: str
            The ``id`` of an analyzer
        endpoint: str
            The endpoint to stream

        Returns
        -------
        BaseStreamer
            A stream handler object
        """
        self._check_streaming(id, endpoint)

        with self._lock:
            log.debug(f"stream '{id}/{endpoint}'")
            method = self._dispatcher[id][endpoint].method
            return streams.register(self.__analyzers__[id], method)

    @api.va.stream_stop.expose()
    def stream_stop(self, id: str, endpoint: str) -> None:
        """Stop streaming something.

        Parameters
        ----------
        id: str
            The ``id`` of an analyzer
        endpoint: str
            The endpoint to stop streaming
        """
        try:
            self._check_streaming(id, endpoint)

            with self._lock:
                log.debug(f"stop stream '{id}/{endpoint}'")
                method = self._dispatcher[id][endpoint].method
                return streams.unregister(self.__analyzers__[id], method)
        except KeyError:
            # id is not valid anymore (probably already closed)
            pass

    def _check_streaming(self, id, endpoint):
        self._valid(id)
        if not endpoint in map(lambda e: e.name, api.va[id].endpoints):
            raise AttributeError(f"no such endpoint: '{endpoint}")
        if self._dispatcher[id][endpoint].streaming == stream_off:
            raise ValueError(f"endpoint '{endpoint}' doesn't stream")


def load(server: ShapeflowServer) -> ApiDispatcher:
    """Initialize :data:`~shapeflow.api.api` and return a reference to it.

    Parameters
    ----------
    server: ShapeflowServer
        The ``shapeflow`` server object

    Returns
    -------
    ApiDispatcher
        A reference to :data:`~shapeflow.api.api`
    """
    api._set_instance(_Main(server))

    history = History()
    history.set_eventstreamer(server._eventstreamer)

    api._add_dispatcher('db', _DatabaseDispatcher(history))
    api._add_dispatcher('fs', _FilesystemDispatcher(_Filesystem()))
    api._add_dispatcher('cache', _CacheDispatcher(_Cache()))

    _vm = _VideoAnalyzerManager(server)
    _va = _VideoAnalyzerManagerDispatcher(_vm)
    _vm._set_dispatcher(_va)

    api._add_dispatcher('va', _va)

    if settings.app.load_state:
        api.dispatch('va/load_state')

    return api
