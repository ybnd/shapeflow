# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import json
import os
import time
import uuid
import webbrowser
from threading import Thread, Event
from typing import Dict, Any

from flask import Flask, send_from_directory, jsonify, request, Response
import waitress

from isimple import get_logger
from isimple.core.backend import AnalyzerType, backend
from isimple.core.schema import schema
from isimple.core.streaming import JpegStreamer
from isimple.history import VideoAnalysisModel, History
from isimple.util import Singleton, suppress_stdout
from isimple.video import VideoAnalyzer

log = get_logger('isimple')
UI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    , 'ui', 'dist'
)


def respond(*args) -> str:
    return jsonify(*args)


class ServerThread(Thread, metaclass=Singleton):
    _app: Flask
    _host: str
    _port: int

    def __init__(self, app, host, port):
        self._app = app
        self._host = host
        self._port = port
        super().__init__(daemon=True)

    def run(self):
        waitress.serve(
            self._app,
            host=self._host,
            port=self._port,
        )


class Main(object, metaclass=Singleton):
    _app: Flask

    _roots: Dict[str, VideoAnalyzer] = {}
    _models: Dict[str, VideoAnalysisModel] = {}
    _streams: Dict[str, Dict[str, JpegStreamer]] = {}
    _history = History()

    _host: str = 'localhost'
    _port: int = 7951

    _server: Thread

    _ping = Event()
    _unload = Event()
    _quit = Event()

    _timeout_suppress = 0.5
    _timeout_unload = 1
    _timeout_loop = 0.1

    def __init__(self):
        app = Flask(__name__, static_url_path='')
        app.config.from_object(__name__)

        # Serve webapp
        @app.route('/', methods=['GET'])
        def index_html():
            return send_from_directory(UI, 'index.html')

        @app.route('/<directory>/<file>', methods=['GET'])  # todo: these three should be ONE method!
        def get_file(directory, file):
            return send_from_directory(os.path.join(UI, directory), file)

        @app.route('/<file>', methods=['GET'])
        def get_file2(file):
            return send_from_directory(UI, file)

        @app.route('/<directory1>/<directory2>/<file>', methods=['GET'])
        def get_file3(directory1, directory2, file):
            return send_from_directory(os.path.join(UI, directory1, directory2), file)

        # API: general
        @app.route('/api/ping', methods=['GET'])
        def ping():
            self._unload.clear()
            self._ping.set()
            return respond(True)

        @app.route('/api/unload', methods=['POST'])
        def unload():
            self._unload.set()
            return respond(True)

        # API: working with Analyzer instances
        @app.route('/api/init', methods=['POST'])
        def init():  # todo: also add a model instance to self._models
            if 'type' in request.args.to_dict():
                bt = request.args.to_dict()['type']
            else:
                bt = None

            return respond(self.add_instance(AnalyzerType(bt)))

        @app.route('/api/list', methods=['GET'])
        def list():
            return respond([k for k in self._roots.keys()])

        @app.route('/api/<id>/schemas', methods=['GET'])
        def get_schemas(id: str):
            return respond(self.get_schemas(str(id)))

        @app.route('/api/<id>/launch', methods=['GET'])
        def launch(id: str):
                return respond(self.call(str(id), 'launch', {}))

        @app.route('/api/<id>/can_launch', methods=['GET'])
        def can_launch(id: str):
            return respond(self.call(str(id), 'can_launch', {}))

        @app.route('/api/<id>/call/<endpoint>', methods=['GET'])
        def call(id: str, endpoint: str):
            result = self.call(str(id), endpoint, request.args.to_dict())
            if result is None:
                result = True
            return respond(result)

        # Streaming
        @app.route('/stream/<id>/<endpoint>')
        def stream(id: str, endpoint: str):
            if id in self._streams:
                if endpoint in self._streams[id]:
                    return Response(self._streams[id][endpoint].stream())

        self._app = app

    def serve(self, open_in_browser: bool):
        # Don't show waitress console output (server URL)
        with suppress_stdout():
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
        self._server.join()
        for streams in self._streams.values():
            for stream in streams.values():
                stream.stop()

    def add_instance(self, type: AnalyzerType = None) -> str:
        if type is None:
            type = AnalyzerType()

        id = str(uuid.uuid1())
        analyzer = type.get()()
        analyzer._multi = True
        log.debug(f"Added instance {{'{id}': {analyzer}}}")
        self._roots[id] = analyzer
        assert isinstance(analyzer, VideoAnalyzer)
        self._models[id] = self._history.add_analysis(analyzer)
        return id

    def get_schemas(self, id: str) -> dict:
        log.debug(f"Providing schemas for '{id}'")
        root = self._roots[id]
        return {
                'config': schema(root._config.__class__),
                'methods': {e.name:[schema(m) for m in ms] for e,ms in root.instance_mapping.items()}
        }

    def call(self, id: str, endpoint: str, data: dict) -> Any:
        log.debug(f"{self._roots[id]}: call '{endpoint}'")
        # todo: sanity check this
        method = self._roots[id].get(getattr(backend, endpoint))
        assert hasattr(method, '__call__')

        if endpoint in ('set_config',):
            pass  # todo: store to self._history

        return method(**{k:json.loads(v) for k,v in data.items()})