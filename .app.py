# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import os
import time
import json
from threading import Thread, Event
from typing import Dict, List
import webbrowser

from flask import Flask, jsonify, request, send_from_directory
import waitress

from isimple.util import suppress_stdout, Singleton
from isimple.core import get_logger, cache
from isimple.core.schema import schema
from isimple.video import Analyzer, AnalyzerType, backend
from isimple.history import History, AnalysisModel

log = get_logger('isimple')


UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'dist')


def respond(*args) -> str:
    return jsonify({'data': [*args]})


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

    _roots: Dict[AnalyzerType, List[Analyzer]] = {}
    _models: List[AnalysisModel] = []
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
        self._roots = {k:[] for k in AnalyzerType().options}
        self.setup()

    def setup(self):
        app = Flask(__name__, static_url_path='')
        app.config.from_object(__name__)

        # Serve webapp
        @app.route('/', methods=['GET'])
        def open_gui():
            return send_from_directory(UI, 'index.html')

        @app.route('/<directory>/<file>', methods=['GET'])
        def get_file(directory, file):
            return send_from_directory(os.path.join(UI, directory), file)

        @app.route('/<file>', methods=['GET'])
        def get_file2(file):
            return send_from_directory(UI, file)

        # API
        @app.route('/api/<bt>/<index>/schemas', methods=['GET'])
        def get_schemas(bt: str, index: int):
            return respond(self.get_schemas(AnalyzerType(bt), int(index)))

        @app.route('/api/<bt>/init', methods=['GET'])
        def init(bt: str):
            return self.add_instance(AnalyzerType(bt))

        @app.route('/api/<bt>/<index>/launch', methods=['GET'])
        def launch(bt: str, index: int):
            self.call(AnalyzerType(bt), int(index), 'launch', {})
            return respond()

        @app.route('/api/<bt>/<index>/<endpoint>', methods=['GET'])
        def call(bt: str, index: int, endpoint: str):
            return self.call(AnalyzerType(bt), int(index), endpoint,
                             request.args.to_dict())

        @app.route('/api/ping')
        def ping():
            self._unload.clear()
            self._ping.set()
            return respond(True)

        @app.route('/api/unload', methods=['GET', 'POST'])
        def unload():
            self._unload.set()
            return respond(True)

        self._app = app

    def serve(self):
        # Don't show waitress console output (server URL)
        with suppress_stdout():
            ServerThread(self._app, self._host, self._port).start()

            # Run in separate thread to revent Ctrl+C from closing browser
            #  if no tabs were open before
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

    def add_instance(self, type: AnalyzerType) -> str:
        log.debug(f"Add instance of {type}")
        analyzer = type.get()()
        self._roots[type].append(analyzer)
        self._models.append(self._history.add_analysis(analyzer))
        return respond(
            len(self._roots[type]) - 1
        )

    def get_schemas(self, type: AnalyzerType = None, index: int = None):
        if type is not None and index is not None:
            root = self._roots[type][index]
        elif type is not None:
            root = type.get()()
        else:
            return respond(None)

        return respond(
            {
                'config': schema(root._config.__class__),
                'methods': {e.name:[schema(m) for m in ms]
                            for e,ms in root.instance_mapping.items()}
            }
        )

    def call(self, type: AnalyzerType, index: int, endpoint: str, data: dict) -> str:
        log.debug(f"{type} {index}: call '{endpoint}'")
        # todo: sanity check this
        method = self._roots[type][index].get(getattr(backend, endpoint))
        assert hasattr(method, '__call__')

        return respond(method(**{k:json.loads(v) for k,v in data.items()}))


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...
    # todo: server-level configuration

    Main().serve()

