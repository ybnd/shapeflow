# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import json
import pickle
import os
import time
import datetime
import subprocess
from threading import Thread, Event, Lock
from typing import Dict, Any, List, Optional
from enum import IntEnum

import cv2
from flask import Flask, send_from_directory, jsonify, request, Response, make_response
import waitress
import webbrowser

from OnionSVG import check_svg

import shapeflow
import shapeflow.config
import shapeflow.util as util
import shapeflow.util.filedialog
import shapeflow.core.backend as backend
import shapeflow.core.streaming as streaming
import shapeflow.db as db
import shapeflow.video as video
import shapeflow.plugins as plugins

log = shapeflow.get_logger(__name__)
UI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    , 'ui', 'dist'
)


def respond(*args) -> str:
    return jsonify(*args)


def open_in_browser(host, port):
    # time.sleep(0.1)  # Wait a bit for the server to initialize
    log.info('opening a browser window')
    webbrowser.open(f"http://{host}:{port}/")


def restart_server(host: str, port: int):
    log.info('restarting server...')

    subprocess.Popen(
        f'sleep 1; python .venv.py .server.py --host {host} --port {port}',
        shell=True,
         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


def check_history():
    history = db.History()

    if history.check():
        history.clean()
    else:
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(shapeflow.settings.format.datetime_format_fs)
        backup_path = f"{shapeflow.settings.db.path}_broken_{timestamp}"
        log.warning(f"backing up old history database @ {backup_path}")
        os.rename(shapeflow.settings.db.path, backup_path)


check_history()


class ServerThread(Thread, metaclass=util.Singleton):
    _app: Flask
    _host: str
    _port: int

    def __init__(self, app, host, port):
        self._app = app
        self._host = host
        self._port = port
        super().__init__(daemon=True)

    def run(self):
        try:
            waitress.serve(
                self._app,
                host=self._host,
                port=self._port,
                threads=32,
            )
        except OSError:
            log.warning('address already in use')
            self.stop()

    def stop(self):
        os._exit(0)


class QueueState(IntEnum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class Main(shapeflow.core.Lockable):
    __metaclass__ = util.Singleton
    _app: Flask

    _roots: Dict[str, backend.BaseVideoAnalyzer] = {}
    _models: Dict[str, db.AnalysisModel] = {}
    _history: db.History

    _server: ServerThread

    _lock = Lock()
    _ping = Event()
    _unload = Event()
    _quit = Event()
    _done = Event()

    _timeout_suppress = 0.5  # todo: load from settings.yaml
    _timeout_unload = 5  # todo: load from settings.yaml
    _timeout_loop = 0.1  # todo: load from settings.yaml

    _raise_call_exceptions = False

    _stop_log: Event

    _eventstreamer = streaming.EventStreamer()

    _q_state: int
    _q_thread: Thread
    _pause_q: Event
    _stop_q: Event

    _host: str
    _port: int


    def __init__(self, open_in_browser: bool = False):
        self._history = db.History()
        super().__init__()
        app = Flask(__name__, static_url_path='')

        app.config.from_object(__name__)
        app.config['JSON_SORT_KEYS'] = False

        self._stop_log = Event()  # todo: these could be class attributes instead
        self._pause_q = Event()
        self._stop_q = Event()
        self._q_state = QueueState.STOPPED

        # Serve webapp (bypassed when frontend runs in development mode)
        @app.route('/', methods=['GET'])
        def index_html():
            log.debug(f"Serving 'index.html'")
            return send_from_directory(UI, 'index.html')

        @app.route('/<file>')
        @app.route('/<d1>/<file>')
        @app.route('/<d1>/<d2>/<file>')
        @app.route('/<d1>/<d2>/<d3>/<file>')
        @app.route('/<d1>/<d2>/<d3>/<d4>/<file>')
        def get_file(file, d1 ='', d2 ='', d3 ='', d4=''):
            directory = os.path.join(UI, d1, d2, d3, d4)
            log.debug(f"Serving '{os.path.join(directory,file)}'")
            return send_from_directory(directory, file)

        # API: general
        def active():
            if self._unload.is_set():
                log.debug('Incoming traffic - cancelling quit.')
                self._unload.clear()
                self._ping.set()

        @app.route('/api/ping', methods=['GET'])
        def ping():
            log.vdebug('received ping')
            active()
            return respond(True)

        @app.route('/api/pid_hash', methods=['GET'])
        def get_pid_hash():
            import hashlib
            return hashlib.sha1(bytes(os.getpid())).hexdigest() + '\n'

        @app.route('/api/unload', methods=['POST'])
        def unload():
            self.save_state()
            self._unload.set()
            return respond(True)

        @app.route('/api/quit', methods=['POST'])
        def quit():
            self._quit.set()
            return respond(True)

        @app.route('/api/restart', methods=['POST'])
        def restart():
            quit()

            while not self._done.is_set():
                pass

            restart_server(self._host, self._port)

            return respond(True)

        @app.route('/api/settings_schema')
        def settings_schema():
            return respond(shapeflow.settings.schema())

        @app.route('/api/get_settings', methods=['GET'])
        def get_settings():
            return respond(shapeflow.settings.to_dict())

        @app.route('/api/set_settings', methods=['POST'])
        def set_settings():
            # todo: check if anything's changed, don't reload if not!

            new_settings = json.loads(request.data)['settings']
            log.info(f'setting settings: {new_settings}')

            shapeflow.update_settings(new_settings)
            restart()

            return respond(shapeflow.settings.to_dict())

        @app.route('/api/schemas', methods=['GET'])
        def get_schemas():
            return {
                'config': video.VideoAnalyzerConfig.schema(),
                'settings': shapeflow.settings.schema(),
                'analyzer_state': dict(backend.AnalyzerState.__members__),
                'queue_state': dict(QueueState.__members__),
            }

        @app.route('/api/select_video_path', methods=['GET'])
        def select_video():
            return respond(shapeflow.util.filedialog.select_video())  # todo: should not be able to spawn multiple windows

        @app.route('/api/select_design_path', methods=['GET'])      # todo: should not be able to spawn multiple windows
        def select_design():
            return respond(shapeflow.util.filedialog.select_design())

        @app.route('/api/check_video_path', methods=['PUT'])
        def check_video():
            return respond(self.check_video_path(json.loads(request.data)['video_path']))

        @app.route('/api/check_design_path', methods=['PUT'])
        def check_design():
            return respond(self.check_design_path(json.loads(request.data)['design_path']))

        @app.route('/api/start', methods=['POST'])
        def start():
            data = json.loads(request.data)
            if 'queue' in data:
                queue = data['queue']
            else:
                queue = list(self._roots.keys())
            self.q_start(queue)
            return respond(self.app_state())

        @app.route('/api/stop', methods=['POST'])
        def stop():
            self.q_stop()
            return respond(self.app_state())

        @app.route('/api/cancel', methods=['POST'])
        def cancel():
            return respond(self.q_cancel())

        # API: working with Analyzer instances
        @app.route('/api/init', methods=['POST'])
        def init():  # todo: also add a model instance to self._models
            active()
            if 'type' in request.args.to_dict():
                bt = request.args.to_dict()['type']
            else:
                bt = None
            return respond(self.add_instance(video.AnalyzerType(bt)))

        @app.route('/api/<id>/launch', methods=['POST'])
        def launch(id: str):
            active()
            return respond(self.call(id, 'launch', {}))

        @app.route('/api/<id>/can_launch', methods=['GET'])
        def can_launch(id: str):
            return respond(self.call(id, 'can_launch', {}))

        @app.route('/api/<id>/get_state', methods=['GET'])
        def get_state(id: str):
            return respond(self._roots[id].state)

        @app.route('/api/<id>/close', methods=['POST'])
        def remove(id: str):
            return respond(self.close_instance(id))

        @app.route('/api/<id>/call/<endpoint>', methods=['GET','PUT','POST'])
        def call(id: str, endpoint: str):
            active()

            if request.data:
                data = json.loads(request.data)
            else:
                data = {k:json.loads(v) for k,v in request.args.to_dict().items() if v != ''}

            result = self.call(id, endpoint, data)

            if result is None:
                result = True

            if isinstance(result, bytes):
                return make_response(result)
            else:
                return respond(result)

        # API: streaming
        @app.route('/api/stream/<id>/<endpoint>', methods=['GET'])
        def stream(id: str, endpoint: str):
            """Start streaming data ~ id & endpoint

            :param id: analyzer UUID
            :param endpoint: string corresponding to an attribute of shapeflow.endpoints.BackendRegistry
            """
            # todo: sanity check if `endpoint' is streamable
            stream = self.stream(id, endpoint)
            if stream is not None:
                response = Response(
                    stream.stream(),
                    mimetype = stream.mime_type(),
                )
                # response.cache_control.no_cache = True
                return response
            else:
                return respond(None)

        @app.route('/api/stream/<id>/<endpoint>/stop', methods=['POST'])
        def stop_stream(id: str, endpoint: str):
            """Stop streaming data ~ id & endpoint

            :param id: analyzer UUID
            :param endpoint: string corresponding to an attribute of shapeflow.endpoints.BackendRegistry
            """
            # todo: sanity check if `endpoint' is streamable
            self.stop_stream(id, endpoint)
            return respond(True)

        @app.route('/api/stream/events', methods=['GET'])
        def stream_events():
            """Stream application events (
            """
            log.debug('streaming events')
            return Response(
                self.events.stream(),
                mimetype = self.events.mime_type()
            )

        @app.route('/api/stream/events/stop', methods=['POST'])
        def stop_events_stream():
            self.events.stop()
            return respond(True)

        # API: utility
        @app.route('/api/app_state', methods=['GET'])
        def get_app_state():
            """List instances in self._roots
            """
            active()
            return respond(self.app_state())

        @app.route('/api/get_log')
        def get_log():
            # todo: move to core.streaming
            # todo: try to refactor ~ shapeflow.core.streaming
            """Start streaming log file
            """
            # cheated off of https://stackoverflow.com/questions/35540885/
            log.debug("streaming log file")

            # Stop previous log reader if active
            if hasattr(self, '_stop_log'):
                self._stop_log.set()

            self._stop_log.clear()

            def generate():
                with open(shapeflow.settings.log.path) as f:
                    while not self._stop_log.is_set():
                        yield f.read()
                        time.sleep(1)

            response = Response(generate(), mimetype='text/plain')
            response.headers['Content-Disposition'] = \
                'attachment; filename=current.log'
            return response

        @app.route('/api/stop_log', methods=['PUT'])
        def stop_log():
            """Stop streaming log file
            """
            log.debug("stopping log file stream")
            self._stop_log.set()
            return respond(True)

        # API: application
        @app.route('/api/app-state/save')
        def save_state():
            with self.lock():
                self.save_state()
                return respond(True)

        @app.route('/api/app-state/load')
        def load_state():
            with self.lock():
                self.load_state()
                return respond(True)

        @app.route('/api/cache/clear', methods=['POST'])
        def clear_cache():
            log.info('clearing cache')
            cache = shapeflow.get_cache(shapeflow.settings)
            cache.clear()
            cache.close()
            return respond(True)

        @app.route('/api/cache/disk-size', methods=['GET'])
        def get_cache_size_mb():
            cache = shapeflow.get_cache()
            size = util.sizeof_fmt(cache.size)
            cache.close()

            return respond(size)

        @app.route('/api/db/disk-size', methods=['GET'])
        def get_db_size_mb():
            return respond(util.sizeof_fmt(os.path.getsize(shapeflow.settings.db.path)))

        @app.route('/api/db/<endpoint>', methods=['GET', 'POST', 'PUT'])
        def db_call(endpoint):
            active()

            if request.data:
                data = json.loads(request.data)
            else:
                data = {k: json.loads(v) for k, v in
                        request.args.to_dict().items() if v != ''}

            result = self.db_call(endpoint, data)

            if isinstance(result, bytes):
                return make_response(result)
            else:
                return respond(result)

        @app.before_first_request
        def initialize():
            self.load_state()

        self._app = app

    def serve(self, host, port, open):
        """Serve the application

        Parameters
        ----------
        host: str
            Host address
        port: int
            Host port
        """
        # Don't show waitress console output (server URL)
        self._host = host
        self._port = port

        log.info(f"serving on http://{host}:{port}")

        if open:
            open_in_browser(host, port)

        with util.suppress_stdout():
            self._server = ServerThread(self._app, host, port)
            self._server.start()

            time.sleep(self._timeout_suppress)  # Wait for Waitress to catch up

        try:
            while not self._quit.is_set():
                if self._ping.is_set():
                    self._ping.clear()
                if self._unload.is_set():
                    log.debug(f'Unloaded from browser, waiting for traffic.')
                    time.sleep(self._timeout_unload)
                    if not self._ping.is_set():
                        log.debug(f'No traffic for {self._timeout_unload} seconds - quitting...')
                        self._quit.set()
                time.sleep(self._timeout_loop)
        except KeyboardInterrupt:
            log.info('interrupted by user')
        self._done.set()

        self.save_state()
        streaming.streams.stop()

        log.info('Main.serve() stopped.')

    def check_video_path(self, path: str) -> bool:
        """Check whether the path is a valid video and add it to
        the history database"""
        try:
            log.debug(f"Checking video file {path}")
            if os.path.isfile(path):
                try:
                    capture = cv2.VideoCapture(path)
                    if int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) > 0:
                        self._history.add_video_file(path)
                        return True
                finally:
                    pass
        except KeyError:
            pass
        return False

    def check_design_path(self, path: str) -> bool:
        """Check whether the path is a valid design and add it to
        the history database"""
        try:
            log.debug(f"Checking design file {path}")
            if os.path.isfile(path):
                try:

                    check_svg(path)
                    self._history.add_design_file(path)
                    return True
                finally:
                    pass
        except KeyError:
            pass
        return False

    def add_instance(self, type: video.AnalyzerType = None) -> str:
        """Add a new analyzer instance

        Parameters
        ----------
        type: AnalyzerType
            Type of ``BaseVideoAnalyzer`` to instantiate

        Returns
        -------
        str
            The ``id`` of the new analyzer
        """
        with self.lock():
            if type is None:
                type = video.AnalyzerType()

            analyzer = type.get()()
            analyzer.set_eventstreamer(self._eventstreamer)

            log.info(f"Adding {{'{analyzer.id}': {analyzer}}}")
            self._roots[analyzer.id] = analyzer
            assert isinstance(analyzer, video.VideoAnalyzer)
            self._models[analyzer.id] = self._history.add_analysis(analyzer)

        self.save_state()
        return analyzer.id

    def close_instance(self, id: str) -> bool:
        """Close an analyzer instance

        Parameters
        ----------
        id: str
            The ``id`` of the analyzer to close
        """
        with self.lock():
            if self.valid(id):
                log.info(f"Removing '{id}'")
                analyzer = self._roots.pop(id)
                with analyzer.lock():
                    analyzer.commit()
                    del analyzer
                    self.save_state()
                    return True
            else:
                raise ValueError

    def app_state(self) -> dict:
        return {
            'q_state': self._q_state,
            'ids': [k for k in self._roots.keys()],
            'status': [a.status() for a in self._roots.values()],
        }

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
                if all(self._roots[id].can_analyze for id in q):  # todo: handle non-id entries in q
                    log.info(f"analyzing queue: {q}")
                    for id in q:
                        while self._pause_q.is_set():
                            self._q_state = QueueState.PAUSED
                            time.sleep(0.5)
                        self._q_state = QueueState.RUNNING

                        if self._stop_q.is_set():
                            break

                        if not self._roots[id].done:
                            self._roots[id].analyze()
                        else:
                            self._roots[id].notice('already analyzed with the current configuration.')
                            log.info(f"skipping '{id}'")

                    self._pause_q.clear()
                    self._stop_q.clear()
                    self._q_state = QueueState.STOPPED
                else:
                    log.info(f"CAN'T ANALYZE FOR ALL ANALYZERS")
            else:
                log.info(f"already started analyzing queue!")

        self._q_thread = Thread(target=target)
        self._q_thread.run()

    def q_stop(self):
        """Stop analysis queue"""
        log.info('stopping analysis queue')
        if self._pause_q.is_set():
            self._pause_q.clear()
        self._stop_q.set()
        if shapeflow.settings.app.cancel_on_q_stop:
            self.q_cancel()
        else:
            for root in self._roots.values():
                if root.state == backend.AnalyzerState.ANALYZING:
                    self.notice(f"waiting for {root.config.name} to finish")

    def q_cancel(self):
        for root in self._roots.values():
            if root.state == backend.AnalyzerState.ANALYZING:
                root.cancel()

    def _commit(self):
        for root in self._roots.values():
            root.commit()

    def save_state(self):
        """Save application state to ``shapeflow.settings.app.state_path``
        """
        if shapeflow.settings.app.save_state:
            log.info("saving application state")

            self._commit()

            s = {
                id: root.model.get('id')
                for id,root in self._roots.items()
                if not root.done
            }

            with open(shapeflow.settings.app.state_path, 'wb') as f:
                pickle.dump(s, f)

    def load_state(self):
        """Load application state from ``shapeflow.settings.app.state_path``"""
        if shapeflow.settings.app.load_state:
            with self.lock():
                log.info("loading application state")
                # todo: check if instances retain reference to self._eventstreamer!

                try:
                    with open(shapeflow.settings.app.state_path, 'rb') as f:
                        S = pickle.load(f)

                    for id,model_id in S.items():
                        assert isinstance(id, str)
                        assert isinstance(model_id, int)

                        model = self._history.fetch_analysis(model_id)

                        if model is not None:
                            model.connect(self._history)
                            analyzer = video.init(shapeflow.config.loads(model.get_config_json()))
                            analyzer._set_id(id)
                            analyzer.set_eventstreamer(self._eventstreamer)

                            analyzer.launch()

                            self._roots[id] = analyzer
                            self._models[id] = self._history.add_analysis(analyzer, model)

                except FileNotFoundError:
                    pass
                except EOFError:
                    pass

    def call(self, id: str, endpoint: str, data: dict = None) -> Any:
        """Call an analyzer endpoint

        Parameters
        ----------
        id: str
            Analyzer id
        endpoint: str
            Endpoint name, should correspond to a :class:`shapeflow.endpoints.BackendRegistry`
            attribute
        data
        """
        if data is None:
            data = {}
        if self.valid(id):
            t0 = time.time()
            log.debug(f"{self._roots[id]}: call '{endpoint}'")

            try:
                method = self._roots[id].get(getattr(backend.backend, endpoint))
                result = method(**data)

                log.debug(f"{self._roots[id]}: return '{endpoint}' "
                          f"({time.time() - t0} s elapsed)")
                return result

            except Exception as e:
                self._roots[id].notice(f"Error @ '{endpoint}': {e.args}")
                if self._raise_call_exceptions:
                    raise
                return False
        else:
            return None

    def db_call(self, endpoint: str, data: dict = None) -> Any:
        with self.lock():
            if data is None:
                data = {}

            log.debug(f"db: call '{endpoint}' {data}")
            try:
                method = self._history.get(getattr(db.history, endpoint))
                result = method(**data)
            except Exception as e:
                self.notice(f"Error @ '{endpoint}': {e.args}")
                if self._raise_call_exceptions:
                    raise
                return False

            return result

    def stream(self, id: str, endpoint: str) -> Optional[streaming.BaseStreamer]:  # todo: extend to handle json streaming also
        with self.lock():
            if self.valid(id):
                # todo: sanity check this also
                method = self._roots[id].get(getattr(backend.backend, endpoint))  # todo: check whether endpoint.streaming is not _Streaming('off')
                self._roots[id].cache_open()

                new_stream = streaming.streams.register(method.__self__, method)  # type: ignore

                log.debug(f"{self._roots[id]}: stream '{endpoint}'")
                return new_stream
            else:
                return None

    def stop_stream(self, id: str, endpoint: str):
        with self.lock():
            if self.valid(id):
                method = self._roots[id].get(getattr(backend.backend, endpoint))

                # todo: type / assert properly
                streaming.streams.unregister(method.__self__, method)  # type: ignore
                log.debug(f"{self._roots[id]}: stopped streaming '{endpoint}'")

    def valid(self, id):
        if id in self._roots:
            return True
        else:
            log.warning(f"{id} is not a valid analyzer id or refers to an analyzer from a previous session")
            return False

    @property
    def events(self) -> streaming.EventStreamer:
        return self._eventstreamer

    def notice(self, message: str, persist: bool = False):
        self._eventstreamer.event(
            'notice', id='', data={'message': message, 'persist': persist}
        )


wsgi = Main()._app
