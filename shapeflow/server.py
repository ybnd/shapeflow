# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import json
import pickle
import os
import time
import requests
import datetime
import subprocess
from threading import Thread, Event, Lock
from typing import Dict, Any, List, Optional

from flask import Flask, send_from_directory, jsonify, request, Response, make_response
import waitress
import webbrowser

import shapeflow
import shapeflow.config
import shapeflow.util as util
import shapeflow.core.streaming as streaming
from shapeflow.api import ApiDispatcher

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
        [
            'python', 'sf.py', 'serve',
            '--host', str(host), '--port', str(port), '--background'
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


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
                threads=shapeflow.settings.app.threads,
            )
        except OSError:
            log.warning('address already in use')
            self.stop()

    def stop(self):
        os._exit(0)


class ShapeflowServer(shapeflow.core.Lockable):
    __metaclass__ = util.Singleton
    _app: Flask
    _api: Optional[ApiDispatcher]
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


    def __init__(self):
        self._api = None
        super().__init__()
        app = Flask(__name__)

        app.config.from_object(__name__)
        app.config['JSON_SORT_KEYS'] = False

        @app.route('/', defaults={'file': 'index.html'}, methods=['GET'])
        @app.route('/<path:file>', methods=['GET'])
        def get_file(file: str):
            """Serve frontend files

            Parameters
            ----------
            file: str
                The file to send
            """
            print('/<path:file>')
            print(file)
            path = os.path.join(UI, *file.split("/"))
            if not os.path.isfile(path):
                raise FileNotFoundError
            log.debug(f"serving '{file}'")
            return send_from_directory(
                os.path.dirname(path),
                os.path.basename(path)
            )

        @app.route('/api/<path:address>', methods=['GET', 'POST'])
        def call_api(address: str):
            """Dispatch request to the API

            Parameters
            ----------
            address: str
                The address of the endpoint to dispatch to
            """
            if self.api is None:
                self.load_api()

            if request.data:
                kwargs = json.loads(request.data)
            else:
                kwargs = {
                    k:json.loads(v)
                    for k,v in request.args.to_dict().items()
                    if v != ''
                }

            result = self.api.dispatch(address, **kwargs)

            if result is None:
                result = True

            if isinstance(result, bytes):
                return make_response(result)
            elif isinstance(result, streaming.BaseStreamer):
                response = Response(
                    result.stream(),
                    mimetype=result.mime_type()
                )
                for k,v in result.headers.items():
                    response.headers[k] = v
                return response
            else:
                return respond(result)

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
        self._host = host
        self._port = port

        log.info(f"serving on http://{host}:{port}")

        if open:
            open_in_browser(host, port)

        # Don't show waitress console output (server URL)
        with util.suppress_stdout():
            self._server = ServerThread(self._app, host, port)
            self._server.start()

            time.sleep(self._timeout_suppress)  # Wait for Waitress to catch up

        try:
            while not self._quit.is_set():
                if self._ping.is_set():
                    self._ping.clear()
                if self._unload.is_set():
                    log.info(f'unloaded from browser, waiting {self._timeout_unload}s for traffic...')
                    time.sleep(self._timeout_unload)
                    if not self._ping.is_set():
                        log.info(f'no traffic.')
                        self._quit.set()
                time.sleep(self._timeout_loop)
        except KeyboardInterrupt:
            log.info('interrupted by user')
        self._done.set()

        if self.api is None:
            self.load_api()
        self.api.va.save_state.method()
        streaming.streams.stop()

        log.info('stopped serving.')

    def load_api(self):
        from shapeflow.main import load
        self._api = load(self)

    @property
    def api(self):
        return self._api
