import json
import os
import time
import subprocess
from threading import Thread, Event, Lock
from typing import Optional

import flask
from flask import Flask, jsonify, request, Response, make_response, abort
import waitress
import webbrowser

import shapeflow
import shapeflow.config
import shapeflow.util as util
from shapeflow.core import DispatchingError
import shapeflow.core.streaming as streaming
from shapeflow.api import ApiDispatcher
from shapeflow.main import load, ShapeflowServerInterface

log = shapeflow.get_logger(__name__)
UI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'ui'
)
DIST = os.path.join(UI, 'dist')


class ServerThread(Thread, metaclass=util.Singleton):
    """A thread running a ``Flask`` app over a ``waitress`` server.
    """
    _app: Flask
    _host: str
    _port: int

    def __init__(self, app: Flask, host: str, port: int):
        self._app = app
        self._host = host
        self._port = port
        super().__init__(daemon=True)

    def run(self):
        """Serve until interrupted or stopped.

        If the current address is already in use, the server errors out & stops
        the current process with :func:`shapeflow.server.ServerThread.stop`.
        """
        try:
            waitress.serve(
                self._app,
                host=self._host,
                port=self._port,
                threads=shapeflow.settings.app.threads,
            )
        except OSError:
            log.warning("address already in use")
            self.stop()

    def stop(self):
        """Stop the thread & process with ``exit(0)``
        """
        os._exit(0)


class ShapeflowServer(ShapeflowServerInterface):
    """Wrapper for a ``Flask`` server
    """

    _host: str
    _port: int

    _app: Flask
    _api: Optional[ApiDispatcher]
    _server: ServerThread

    _api_lazy_load = Lock()
    _ping = Event()
    _unload = Event()
    _quit = Event()
    _done = Event()

    _timeout_suppress = 0.5  # todo: load from settings.yaml
    _timeout_unload = 5  # todo: load from settings.yaml
    _timeout_loop = 0.1  # todo: load from settings.yaml

    _eventstreamer = streaming.EventStreamer()

    def __init__(self):
        app = Flask(__name__)
        app.config.from_object(__name__)
        app.config['JSON_SORT_KEYS'] = False

        @app.route('/', methods=['GET'])
        def _index():
            try:
                r = self.get_file('index.html')

                # Make sure the index page isn't cached so we can pick up missing ui/dist/ right away
                r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                r.headers["Pragma"] = "no-cache"
                r.headers["Expires"] = "0"
                r.headers['Cache-Control'] = 'public, max-age=0'

                return r
            except FileNotFoundError:
                if not os.path.isdir(DIST) or not os.listdir(DIST):
                    log.error(f"no compiled UI in '{DIST}'")
                log.error(f"follow the instructions on the 404 page to restore the application")

                return flask.send_from_directory(UI, '404.html'), 404

        @app.route('/<path:file>', methods=['GET'])
        def _get_file(file: str):
            try:
                return self.get_file(file)
            except FileNotFoundError:
                abort(404)

        @app.route('/api/<path:address>', methods=['GET', 'POST', 'PUT'])
        def _call_api(address: str):
            return self.call_api(address)

        self._app = app
        self._api = None

    def serve(self, host: str, port: int, open: bool) -> None:
        self._host = host
        self._port = port

        log.info(f"serving on http://{host}:{port}")

        # Don't show waitress console output (server URL)
        with util.suppress_stdout():
            self._server = ServerThread(self._app, host, port)
            self._server.start()

            time.sleep(self._timeout_suppress)  # Wait for Waitress to catch up

        if open:
            time.sleep(0.1)  # Wait a bit for the server to initialize
            log.info("opening a browser window...")
            webbrowser.open(f"http://{host}:{port}/")

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

        self.api.dispatch('va/save_state')
        streaming.streams.stop()

        log.info('stopped serving.')

    def get_file(self, file: str):
        """Serve frontend files

        Parameters
        ----------
        file: str
            The file to send
        """
        self.active()

        path = os.path.join(DIST, *file.split("/"))
        if not os.path.isfile(path):
            log.error(f"no such file: '{file}'")
            raise FileNotFoundError
        log.debug(f"serving '{file}'")
        return flask.send_from_directory(
            os.path.dirname(path),
            os.path.basename(path)
        )

    def call_api(self, address: str) -> Response:
        self.active()

        kwargs = {}
        if request.data:
            try:
                kwargs.update(json.loads(request.data))
            except json.JSONDecodeError as e:
                log.error(f"could not decode '{str(request.data)}'")
                raise e
        if request.args.to_dict():
            try:
                kwargs.update({
                    k: v
                    for k, v in request.args.to_dict().items()
                    if v != ''
                })
            except json.JSONDecodeError as e:
                log.error(f"could not decode '{request.args.to_dict()}'")
                raise e

        try:
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
                for k, v in result.headers.items():
                    response.headers[k] = v
                return response
            else:
                return jsonify(result)
        except DispatchingError:
            abort(404)
        except Exception as e:
            log.error(f"'{address}' - {e.__class__.__name__}: {str(e)}")
            raise e

    def unload(self) -> None:
        self._unload.set()

    def quit(self) -> None:
        self._quit.set()

    def restart(self) -> None:

        self.quit()

        while not self._done.is_set():
            pass

        log.info("restarting server...")
        subprocess.Popen(
            [
                'python', 'sf.py', 'serve',
                '--host', self._host, '--port', str(self._port), '--background'
            ],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def active(self) -> None:
        if self._unload.is_set():
            log.info('incoming traffic - cancelling quit.')
            self._unload.clear()
            self._ping.set()

    @property
    def api(self) -> ApiDispatcher:
        if self._api is None:
            if self._api_lazy_load.locked():
                self._api_lazy_load.acquire()
                self._api_lazy_load.release()
                return self.api
            else:
                with self._api_lazy_load:
                    self._api = load(self)

        return self._api

    @property
    def eventstreamer(self) -> streaming.EventStreamer:
        return self._eventstreamer
