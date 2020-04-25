# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import json
import pickle
import os
import time
import webbrowser
from threading import Thread, Event, Lock
from typing import Dict, Any, List

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
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # todo: cleaner pls
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
            )

    def stop(self):
        self._stopevent.set()


class Main(object, metaclass=util.Singleton):
    _app: Flask

    _roots: Dict[str, backend.BaseVideoAnalyzer] = {}
    _models: Dict[str, history.VideoAnalysisModel] = {}
    _history = history.History()

    _host: str = 'localhost'  # todo: load from settings.yaml
    _port: int = 7951  # todo: load from settings.yaml

    _server: ServerThread

    _ping = Event()
    _unload = Event()
    _quit = Event()

    _timeout_suppress = 0.5  # todo: load from settings.yaml
    _timeout_unload = 5  # todo: load from settings.yaml
    _timeout_loop = 0.1  # todo: load from settings.yaml

    _stop_log: Event
    _latest: List[history.VideoAnalysisModel]
    _latest_configs: List[dict]

    def __init__(self):
        app = Flask(__name__, static_url_path='')
        app.config.from_object(__name__)

        self.get_latest()

        # Serve webapp
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
        def ping():
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

            isimple.save_settings(isimple.Settings(**new_settings))

            # todo: restart the server with original

            return respond(isimple.settings)

        @app.route('/api/options/<for_type>', methods=['GET'])
        def get_options(for_type):
            log.debug(f"get_enum for type '{for_type}'")
            if for_type == "state":
                return respond([
                    name for name, _ in video.AnalyzerState.__members__.items()
                ])
            elif for_type == "analyzer":
                return respond(video.AnalyzerType().options)
            elif for_type == "feature":
                return respond({
                    k: video.FeatureType(k).get().parameters() for k in video.FeatureType().options
                })
            elif for_type == "frame_interval_setting":
                return respond(video.FrameIntervalSetting().options)
            elif for_type == "filter":
                return respond(video.FilterType().options)
            elif for_type == "transform":
                return respond(video.TransformType().options)
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

        # API: working with Analyzer instances
        @app.route('/api/init', methods=['POST'])
        def init():  # todo: also add a model instance to self._models
            active()
            if 'type' in request.args.to_dict():
                bt = request.args.to_dict()['type']
            else:
                bt = None
            return respond(self.add_instance(video.AnalyzerType(bt)))

        @app.route('/api/list', methods=['GET'])
        def get_list():
            active()
            log.vdebug(f"Listing analyzers")
            return respond({
                'ids': [k for k in self._roots.keys()],  # todo: goes through self._roots 3 times!
                'states': [v.state for v in self._roots.values()],
                'progress': [v.progress for v in self._roots.values()],
            })

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

        @app.route('/api/<id>/call/get_overlay_png', methods=['GET'])
        def get_overlay_png(id: str):
            null: dict = {}
            return make_response(self.call(id, 'get_overlay_png', null))

        @app.route('/api/<id>/call/<endpoint>', methods=['GET','PUT','POST'])
        def call(id: str, endpoint: str):
            active()
            if request.data:
                data = json.loads(request.data)
            else:
                data = {k:json.loads(v) for k,v in request.args.to_dict().items()}
            result = self.call(id, endpoint, data)
            if result is None:
                result = True
            return respond(result)

        # Streaming
        @app.route('/api/<id>/stream/<endpoint>', methods=['GET'])
        def stream(id: str, endpoint: str):
            return Response(
                self.stream(id, endpoint).stream(),
                mimetype = "multipart/x-mixed-replace; boundary=frame",
            )

        @app.route('/api/get_log')
        def get_log():
            # cheated off of https://stackoverflow.com/questions/35540885/
            log.debug("streaming log file")

            # Stop previous log reader if active
            if hasattr(self, '_stop_log'):
                self._stop_log.set()

            def generate():
                self._stop_log = Event()
                with open(isimple.settings.log.path) as f:
                    while not self._stop_log.is_set():
                        yield f.read()
                        time.sleep(1)

            response = Response(generate(), mimetype='text/plain')
            response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
            return response

        @app.route('/api/stop_log', methods=['PUT'])
        def stop_log():
            log.debug("stopping log file stream")
            self._stop_log.set()
            return respond(True)

        # State
        @app.route('/api/state/save')
        def save_state():
            self.save_state()
            return respond(True)

        @app.route('/api/state/load')
        def load_state():
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
        if type is None:
            type = video.AnalyzerType()

        analyzer = type.get()()
        log.debug(f"Added instance {{'{analyzer.id}': {analyzer}}}")
        self._roots[analyzer.id] = analyzer
        assert isinstance(analyzer, video.VideoAnalyzer)
        self._history.add_analysis(analyzer)
        return analyzer.id

    def save_state(self):
        log.debug("saving state")

        s = {
            k:{'config': root.config, 'state': root.state} for k,root in self._roots.items()
        }

        with open(os.path.join(isimple.ROOTDIR, 'state'), 'wb') as f:
            pickle.dump(s, f)

    def load_state(self):
        log.debug("loading state")

        try:
            with open(os.path.join(isimple.ROOTDIR, 'state'), 'rb') as f:
                S = pickle.load(f)

            for k,s in S.items():
                analyzer = video.init(s['config'])
                analyzer._set_id(k)

                if video.AnalyzerState.do_launch(s['state']):
                    analyzer.launch()

                self._roots[k] = analyzer
                assert isinstance(analyzer, video.VideoAnalyzer)
                self._history.add_analysis(analyzer)

        except FileNotFoundError:
            pass

    def get_schemas(self, id: str) -> dict:
        log.debug(f"Providing schemas for '{id}'")
        root = self._roots[id]
        return {
                'config': schema.schema(root._config.__class__),
                'methods': {e.name:[schema.schema(m) for m in ms] for e,ms in root.instance_mapping.items()}
        }

    # @util.timed
    def call(self, id: str, endpoint: str, data: dict) -> Any:
        try:
            t0 = time.time()
            log.debug(f"{self._roots[id]}: call '{endpoint}'")
            # todo: sanity check this
            method = self._roots[id].get(getattr(backend.backend, endpoint))

            if endpoint in ('set_config',):
                pass  # todo: store to self._history & update latest configs

            result = method(**data)
            log.debug(f"{self._roots[id]}: return '{endpoint}' "
                      f"({time.time() - t0} s elapsed)")
            return result
        except KeyError:
            log.debug(f"{self._roots[id]}: KeyError @ '{endpoint}'")

    def stream(self, id: str, endpoint: str) -> streaming.FrameStreamer:
        # todo: sanity check this also
        method = self._roots[id].get(getattr(backend.backend, endpoint))
        self._roots[id].cache_open()

        new_stream = streaming.streams.register(method.__self__, method)  # type: ignore  # todo: type / assert properly

        log.debug(f"{self._roots[id]}: stream '{endpoint}'")
        return new_stream
