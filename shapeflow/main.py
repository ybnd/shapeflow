import os
import time
import pickle
from typing import Dict, List, Optional
from threading import Event, Lock, Thread
import datetime

import shortuuid
import cv2
from OnionSVG import check_svg

from shapeflow.util import open_path, sizeof_fmt
from shapeflow.util.filedialog import filedialog
from shapeflow import get_logger, get_cache, settings, update_settings, ROOTDIR
from shapeflow.core import stream_off
from shapeflow.api import api, _FilesystemDispatcher, _DatabaseDispatcher, _VideoAnalyzerManagerDispatcher, _VideoAnalyzerDispatcher, ApiDispatcher
from shapeflow.core.streaming import streams, EventStreamer, PlainFileStreamer
from shapeflow.core.backend import QueueState, AnalyzerState
from shapeflow.config import schemas, loads, BaseAnalyzerConfig
from shapeflow.video import VideoAnalyzer, init
import shapeflow.plugins
from shapeflow.server import ShapeflowServer

from shapeflow.db import History


log = get_logger(__file__)


class _Main(object):
    _lock: Lock
    _server: ShapeflowServer

    _log: Optional[PlainFileStreamer]

    def __init__(self, server: ShapeflowServer):
        self._server = server

        self._lock = Lock()
        self._log = None

    def active(self):
        if self._server._unload.is_set():
            log.debug('Uncoming traffic - cancelling quit.')
            self._server._unload.clear()
            self._server._ping.set()

    @api.ping.expose()
    def ping(self) -> bool:
        self.active()
        return True

    @api.map.expose()
    def map(self) -> dict:
        return {
            rule.rule: list(rule.methods)
            for rule in app.url_map.iter_rules()  # todo: replace with url map from _ApiDispatcher
            if rule.rule[:5] == '/api/'
        }

    @api.schemas.expose()
    def schemas(self) -> dict:
        return schemas()

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
        self._log = PlainFileStreamer(path=settings.log.path)

        return self._log

    @api.stop_log.expose()
    def stop_log(self) -> None:
        """Stop streaming log file
        """
        log.debug("stopping log file stream")
        self._log.stop()

    @api.unload.expose()
    def unload(self) -> bool:
        api.va.save_state.method()
        self._server._unload.set()
        return True

    @api.quit.expose()
    def quit(self) -> bool:
        api.va.save_state.method()
        self._server._quit.set()
        return True

    @api.restart.expose()
    def restart(self) -> bool:
        self.quit()

        while not self._server._done.is_set():
            pass

        self._server.restart()

        return True


@api.cache.clear.expose()
def _clear_cache() -> None:
    log.info(f"clearing cache")
    cache = get_cache(settings)
    cache.clear()
    cache.close()

@api.cache.size.expose()
def _cache_size() -> str:
    cache = get_cache(settings)
    size = sizeof_fmt(cache.size)
    cache.close()

    return size


class _Filesystem(object):
    @api.fs.select_video.expose()
    def select_video(self) -> str:
        return filedialog.load(
            title='Select a video file...',
            pattern=settings.app.video_pattern,
            pattern_description='Video files',
        )

    @api.fs.select_design.expose()
    def select_video(self) -> str:
        return filedialog.load(
            title='Select a design file...',
            pattern=settings.app.design_pattern,
            pattern_description='Design files',
        )

    @api.fs.check_video.expose()
    def check_video(self, path: str) -> bool:
        if os.path.isfile(path):
            try:
                capture = cv2.VideoCapture(path)
                if int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) > 0:
                    History().add_video_file(path)  # todo: overhead?
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False

    @api.fs.check_design.expose()
    def check_design(self, path: str) -> bool:
        if os.path.isfile(path):
            try:
                check_svg(path)
                History().add_design_file(path)  # todo: overhead?
                return True
            except:
                return False
        else:
            return False

    @api.fs.open_root.expose()
    def open_root(self) -> None:
        try:
            open_path(ROOTDIR)
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
    _server: ShapeflowServer
    _history: History

    _lock: Lock
    _q_thread: Thread
    _stop_q: Event
    _pause_q: Event
    _q_state: QueueState

    _dispatcher: _VideoAnalyzerManagerDispatcher
    __analyzers__: Dict[str, VideoAnalyzer] = {}  # todo: analyzer manager should register analyzers with api.va on init

    ID_LENGTH = 6

    def __init__(self, server: ShapeflowServer):
        self._server = server
        self._history = History()
        self._history.set_eventstreamer(server._eventstreamer)

        self._lock = Lock()
        self._stop_q = Event()
        self._pause_q = Event()
        self._q_state = QueueState.STOPPED

        self.load_state()

    def _set_dispatcher(self, dispatcher: _VideoAnalyzerManagerDispatcher):
        self._dispatcher = dispatcher

    def _add(self, analyzer: VideoAnalyzer) -> str:
        """Add a new analyzer instance


        Returns
        -------
        str
            The ``id`` of the new analyzer
        """
        id = shortuuid.ShortUUID().random(length=self.ID_LENGTH)

        # ensure that the id doesn't start with a number there's no collisions
        while id[0].isdigit() or id in self.__analyzers__.keys():
            id = shortuuid.ShortUUID().random(length=self.ID_LENGTH)

        analyzer._set_id(id)
        self.__analyzers__[id] = analyzer
        self._dispatcher._add_dispatcher(
            id, _VideoAnalyzerDispatcher(instance=analyzer)
        )
        self._dispatcher._update(self._dispatcher)  # todo: lame signature; also should be a part of _add_dispatcher probably
        return id

    def _remove(self, id: str):
        """Remove an analyzer instance

        Parameters
        ----------
        id: str
            The ``id`` of the analyzer to close
        """
        del self.__analyzers__[id]
        for k in filter(lambda k: id in k, list(self._dispatcher._address_space.keys())):  # todo: this is a bit lame
            del self._dispatcher._address_space[k]  # todo: there should be a _remove_dispatcher probably
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
    def q_start(self, q: List[str]) -> None:
        """Queue analysis

        Parameters
        ----------
        q: List[str]
            List of analyzer ``id`` to queue.
        """

        def target():
            if self._q_state == QueueState.STOPPED:
                self._q_state = QueueState.RUNNING
                if all(self.__analyzers__[id].can_analyze for id in q):  # todo: handle non-id entries in q
                    log.info(f"analyzing queue: {q}")
                    for id in q:
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

                    self._pause_q.clear()
                    self._stop_q.clear()
                    self._q_state = QueueState.STOPPED
                else:
                    log.info(f"Can't analyze all of {q}")
            else:
                log.info(f"already started analyzing queue!")

        self._q_thread = Thread(target=target)
        self._q_thread.run()

    @api.va.stop.expose()
    def q_stop(self) -> None:
        """Stop analysis queue"""
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
        """Cancel analysis queue"""
        for analyzer in self.__analyzers__.values():
            if analyzer.state == AnalyzerState.ANALYZING:
                analyzer.cancel()

    @api.va.state.expose()
    def state(self) -> dict:
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
                        config = loads(model.get_config_json())
                        assert isinstance(config, BaseAnalyzerConfig)
                        analyzer = init(config)
                        analyzer._set_id(id)
                        analyzer.set_eventstreamer(self._server._eventstreamer)

                        analyzer.launch()

                        self.__analyzers__[id] = analyzer
                        self._history.add_analysis(analyzer, model)
            except FileNotFoundError:
                pass
            except EOFError:
                pass

    @api.va.stream.expose()
    def stream(self, id: str, endpoint: str) -> None:
        self._check_streaming(id, endpoint)

        with self._lock:
            log.debug(f"stream '{id}/{endpoint}'")
            method = self._dispatcher[id][endpoint].method
            return streams.register(self.__analyzers__[id], method)

    @api.va.stream_stop.expose()
    def stream_stop(self, id: str, endpoint: str) -> None:
        self._check_streaming(id, endpoint)

        with self._lock:
            log.debug(f"stop stream '{id}/{endpoint}'")
            method = self._dispatcher[id][endpoint].method
            return streams.unregister(self.__analyzers__[id], method)

    def _check_streaming(self, id, endpoint):
        self._valid(id)
        if not endpoint in map(lambda e: e.name, api.va.__id__.endpoints):
            raise AttributeError(f"no such endpoint: '{endpoint}")
        if self._dispatcher[id][endpoint].streaming == stream_off:
            raise ValueError(f"endpoint '{endpoint}' doesn't stream")


def load(server: ShapeflowServer) -> ApiDispatcher:
    api._set_instance(_Main(server))
    api._add_dispatcher('db', _DatabaseDispatcher(History()))

    _vm = _VideoAnalyzerManager(server)
    _va = _VideoAnalyzerManagerDispatcher(_vm)
    _vm._set_dispatcher(_va)

    api._add_dispatcher('va', _va)

    return api
