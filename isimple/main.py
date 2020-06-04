# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import json
import pickle
import os
from contextlib import contextmanager
import time
import webbrowser
from threading import Thread, Event, Lock
from typing import Dict, Any, List, Optional
from enum import IntEnum

import cv2
from flask import Flask, send_from_directory, jsonify, request, Response, make_response
import waitress

from OnionSVG import check_svg

import isimple
import isimple.util as util
import isimple.util.filedialog
import isimple.core.backend as backend
import isimple.core.schema as schema
import isimple.core.streaming as streaming
import isimple.history as history
import isimple.video as video

log = isimple.get_logger('isimple')
UI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    , 'ui', 'dist'
)


def respond(*args) -> str:
    return jsonify(*args)


class ServerThread(Thread, metaclass=util.Singleton):
    _app: Flask
    _host: str
    _port: int
    _stopevent = Event()

    def __init__(self, app, host, port):
        self._app = app
        self._host = host
        self._port = port
        super().__init__(daemon=True)

    def run(self):
        while not self._stopevent.is_set():
            waitress.serve(
                self._app,
                host=self._host,
                port=self._port,
                threads=64,
            )

    def stop(self):
        self._stopevent.set()


class QueueState(IntEnum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class Main(isimple.core.Lockable):
    __metaclass__ = util.Singleton
    _app: Flask

    _roots: Dict[str, backend.BaseVideoAnalyzer] = {}
    _models: Dict[str, history.VideoAnalysisModel] = {}
    _history = history.History()

    _host: str = 'localhost'  # todo: load from settings.yaml
    _port: int = 7951  # todo: load from settings.yaml

    _server: ServerThread

    _lock = Lock()
    _ping = Event()
    _unload = Event()
    _quit = Event()

    _timeout_suppress = 0.5  # todo: load from settings.yaml
    _timeout_unload = 5  # todo: load from settings.yaml
    _timeout_loop = 0.1  # todo: load from settings.yaml

    _stop_log: Event
    _latest: List[history.VideoAnalysisModel]
    _latest_configs: List[dict]

    _eventstreamer = streaming.EventStreamer()

    _q_state: int
    _pause_q: Event
    _stop_q: Event


    def __init__(self):
        super().__init__()
        app = Flask(__name__, static_url_path='')
        app.config.from_object(__name__)

        self._stop_log = Event()  # todo: these could be class attributes instead
        self._pause_q = Event()
        self._stop_q = Event()
        self._q_state = QueueState.STOPPED

        self.get_latest()  # todo: should update once in a while

        # Serve webapp (bypassed when frontend runs in development mode)
        @app.route('/', methods=['GET'])
        def index_html():
            log.debug(f"Serving 'index.html'")
            return send_from_directory(UI, 'index.html')

        @app.route('/<file>')
        @app.route('/<directory1>/<file>')
        @app.route('/<directory1>/<directory2>/<file>')
        def get_file(file, directory1 = '', directory2 = ''):
            directory = os.path.join(UI, directory1, directory2)
            log.debug(f"Serving '{os.path.join(directory,file)}'")
            return send_from_directory(directory, file)

        # API: general
        def active():
            self._unload.clear()
            self._ping.set()

        @app.route('/api/ping', methods=['GET'])
        def ping():  # todo: deprecated
            active()
            return respond(True)

        @app.route('/api/unload', methods=['POST'])
        def unload():
            self._unload.set()
            return respond(True)

        @app.route('/api/settings_schema')
        def settings_schema():
            return respond(schema.settings_schema)

        @app.route('/api/get_settings', methods=['GET'])
        def get_settings():
            return respond(isimple.settings)

        @app.route('/api/set_settings', methods=['POST'])
        def set_settings():
            # todo: check if anything's changed, don't reload if not!

            new_settings = json.loads(request.data)['settings']
            log.info(f'setting settings: {new_settings}')

            isimple.update_settings(new_settings)

            # todo: restart the server with original

            return respond(isimple.settings)

        @app.route('/api/options/<for_type>', methods=['GET'])
        def get_options(for_type):
            log.debug(f"get options for '{for_type}'")
            if for_type == "state":
                return respond(dict(video.AnalyzerState.__members__))
            elif for_type == "analyzer":
                return respond(video.AnalyzerType().options)
            elif for_type == "feature":
                ft = video.FeatureType()
                features = [video.FeatureType(k).get() for k in ft.options]
                return respond({
                    'options': ft.options,
                    'labels': {
                        k: feature.label() for k, feature
                        in zip(ft.options, features)
                    },
                    'units': {
                        k: feature.unit() for k, feature
                        in zip(ft.options, features)
                    },
                    'descriptions': {
                        k: feature.description() for k, feature
                        in zip(ft.options, features)
                    },
                    'parameters': {
                        k: feature.parameters() for k, feature
                        in zip(ft.options, features)
                    },
                    'parameter_defaults': {
                        k: feature.parameter_defaults() for k, feature
                        in zip(ft.options, features)
                    },
                    'parameter_descriptions': {
                        k: feature.parameter_descriptions() for k, feature
                        in zip(ft.options, features)
                    },
                })
            elif for_type == "frame_interval_setting":
                fis = video.FrameIntervalSetting()
                return respond(
                    {'options': fis.options, 'descriptions': fis.descriptions}
                )
            elif for_type == "filter":
                return respond({
                    'options': video.FilterType().options,
                    'descriptions': video.FilterType().descriptions
                })
            elif for_type == "transform":
                return respond({
                    'options': video.TransformType().options,
                    'descriptions': video.TransformType().descriptions
                })
            elif for_type == "video_path":
                return respond(
                    list(set([config['video_path'] for config in self._latest_configs]))
                )
            elif for_type == "design_path":
                return respond(
                    list(set([config['design_path'] for config in self._latest_configs]))
                )
            else:
                raise ValueError(f"No options for '{for_type}'")

        @app.route('/api/select_video_path', methods=['GET'])
        def select_video():
            return respond(isimple.util.filedialog.select_video())  # todo: should not be able to spawn multiple windows

        @app.route('/api/select_design_path', methods=['GET'])      # todo: should not be able to spawn multiple windows
        def select_design():
            return respond(isimple.util.filedialog.select_design())

        @app.route('/api/check_video_path', methods=['PUT'])
        def check_video():
            try:
                path = json.loads(request.data)['video_path']
                log.debug(f"Checking video file {path}")
                if os.path.isfile(path):
                    try:
                        capture = cv2.VideoCapture(path)
                        if int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) > 0:
                            return respond(True)
                    finally:
                        pass
            except KeyError:
                pass
            return respond(False)

        @app.route('/api/check_design_path', methods=['PUT'])
        def check_design():
            try:
                path = json.loads(request.data)['design_path']
                log.debug(f"Checking design file {path}")
                if os.path.isfile(path):
                    try:
                        check_svg(path)
                        return respond(True)
                    finally:
                        pass
            except KeyError:
                pass
            return respond(False)

        @app.route('/api/start', methods=['POST'])
        def start():
            data = json.loads(request.data)
            if 'queue' in data:
                queue = data['queue']
            else:
                queue = list(self._roots.keys())
            return respond(self.q_start(queue))

        @app.route('/api/stop', methods=['POST'])
        def stop():
            return respond(self.q_stop())

        @app.route('/api/q_state', methods=['GET'])
        def get_q_state():
            return respond(self._q_state)

        # API: working with Analyzer instances
        @app.route('/api/init', methods=['POST'])
        def init():  # todo: also add a model instance to self._models
            active()
            if 'type' in request.args.to_dict():
                bt = request.args.to_dict()['type']
            else:
                bt = None
            return respond(self.add_instance(video.AnalyzerType(bt)))

        @app.route('/api/<id>/call/get_schemas', methods=['GET'])
        def get_schemas(id: str):
            active()
            return respond(self.get_schemas(id))

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

        @app.route('/api/<id>/remove', methods=['POST'])
        def remove(id: str):
            with self.lock():
                return respond(self.remove_instance(id))

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
        @app.route('/api/<id>/stream/<endpoint>', methods=['GET'])
        def stream(id: str, endpoint: str):
            """Start streaming data ~ id & endpoint

            :param id: analyzer UUID
            :param endpoint: string corresponding to an attribute of isimple.endpoints.BackendRegistry
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

        @app.route('/api/<id>/stream/<endpoint>/stop', methods=['GET'])
        def stop_stream(id: str, endpoint: str):
            """Stop streaming data ~ id & endpoint

            :param id: analyzer UUID
            :param endpoint: string corresponding to an attribute of isimple.endpoints.BackendRegistry
            """
            # todo: sanity check if `endpoint' is streamable
            self.stop_stream(id, endpoint)
            return respond(True)

        @app.route('/api/stream/events', methods=['GET'])
        def stream_events():
            """Stream application events (
            """
            return Response(
                self.events.stream(),
                mimetype = self.events.mime_type()
            )

        # API: utility
        @app.route('/api/list', methods=['GET'])
        def get_list():
            """List instances in self._roots
            """
            active()
            return respond([k for k in self._roots.keys()])

        @app.route('/api/get_log')
        def get_log():
            # todo: move to core.streaming
            # todo: try to refactor ~ isimple.core.streaming
            """Start streaming log file
            """
            # cheated off of https://stackoverflow.com/questions/35540885/
            log.debug("streaming log file")

            # Stop previous log reader if active
            if hasattr(self, '_stop_log'):
                self._stop_log.set()

            self._stop_log.clear()

            def generate():
                with open(isimple.settings.log.path) as f:
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

        self._app = app

    def serve(self, open_in_browser: bool):
        # Don't show waitress console output (server URL)
        with util.suppress_stdout():
            self._server = ServerThread(self._app, self._host, self._port)
            self._server.start()

            # Run in separate thread to revent Ctrl+C from closing browser
            #  if no tabs were open before  todo: doesn't seem to work anymore?
            if open_in_browser:
                Thread(
                    target=lambda: webbrowser.open(
                        f"http://{self._host}:{self._port}/"
                    )
                ).start()

            time.sleep(self._timeout_suppress)  # Wait for Waitress to catch up

        while not self._quit.is_set():
            if self._ping.is_set():
                self._ping.clear()
            if self._unload.is_set():
                log.debug(f'Unloaded from browser, waiting for ping.')
                time.sleep(self._timeout_unload)
                if not self._ping.is_set():
                    log.debug('No ping received; quitting.')
                    self._quit.set()
                else:
                    log.debug('Ping received; cancelling.')
            time.sleep(self._timeout_loop)

    def cleanup(self):
        log.debug('cleaning up')
        self._server.stop()
        self._server.join()
        streaming.streams.stop()

    def get_latest(self):
        self._latest = self._history.get_latest_analyses()
        self._latest_configs = [json.loads(model['config']) for model in self._latest]

    def add_instance(self, type: video.AnalyzerType = None) -> str:
        with self.lock():
            if type is None:
                type = video.AnalyzerType()

            analyzer = type.get()()
            analyzer.set_eventstreamer(self._eventstreamer)

            log.info(f"Adding {{'{analyzer.id}': {analyzer}}}")
            self._roots[analyzer.id] = analyzer
            assert isinstance(analyzer, video.VideoAnalyzer)
            self._history.add_analysis(analyzer)
            return analyzer.id

    def remove_instance(self, id: str) -> bool:
        with self.valid(id):
            analyzer = self._roots.pop(id)
            with analyzer.lock():
                analyzer.commit()
                del analyzer
                return True

    def q_start(self, q: List[str]) -> bool:
        if self._q_state == QueueState.STOPPED:
            done = False

            if all(self._roots[id].can_analyze for id in q):
                log.info(f"analyzing queue: {q}")
                for id in q:
                    while self._pause_q.is_set():
                        self._q_state = QueueState.PAUSED
                        time.sleep(0.5)
                    self._q_state = QueueState.RUNNING

                    if self._stop_q.is_set():
                        done = False
                        break

                    if not self._roots[id].done:
                        self._roots[id].analyze()
                    else:
                        log.info(f"skipping {id}")
                    done = True

                self._pause_q.clear()
                self._stop_q.clear()
                self._q_state = QueueState.STOPPED
                return done
            else:
                log.info(f"CAN'T ANALYZE FOR ALL ANALYZERS")
                return False
        else:
            log.info(f"already started analyzing queue!")
            return False

    def q_stop(self):
        log.info('stopping analysis queue')
        if self._pause_q.is_set():
            self._pause_q.clear()
        self._stop_q.set()

    def save_state(self):
        log.debug("saving application state...")

        s = {
            k:{'config': root.config, 'state': root.state} for k,root in self._roots.items()
        }

        with open(os.path.join(isimple.ROOTDIR, 'state'), 'wb') as f:
            pickle.dump(s, f)

    def load_state(self):
        log.debug("loading application state...")
        # todo: check if instances retain reference to self._eventstreamer!

        try:
            with open(os.path.join(isimple.ROOTDIR, 'state'), 'rb') as f:
                S = pickle.load(f)

            for k,s in S.items():
                analyzer = video.init(s['config'])
                analyzer._set_id(k)

                if video.AnalyzerState.can_launch(s['state']):
                    analyzer.launch()

                self._roots[k] = analyzer
                assert isinstance(analyzer, video.VideoAnalyzer)
                self._history.add_analysis(analyzer)

        except FileNotFoundError:
            pass

    def get_schemas(self, id: str) -> Optional[dict]:
        if self.valid(id):
            log.debug(f"Providing schemas for '{id}'")
            root = self._roots[id]
            return {
                    'config': schema.schema(root._config.__class__),
                    'methods': {e.name:[schema.schema(m) for m in ms] for e,ms in root.instance_mapping.items()}
            }
        else:
            return None

    def call(self, id: str, endpoint: str, data: dict = {}) -> Any:
        if self.valid(id):
            t0 = time.time()
            log.debug(f"{self._roots[id]}: call '{endpoint}'")
            # todo: sanity check this
            method = self._roots[id].get(getattr(backend.backend, endpoint))

            result = method(**data)
            log.debug(f"{self._roots[id]}: return '{endpoint}' "
                      f"({time.time() - t0} s elapsed)")
            return result
        else:
            return None

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
