# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import os
import sys
import time
import json
from threading import Thread, Event, Lock
from typing import Dict, List
import webbrowser
from contextlib import contextmanager

from flask import Flask, jsonify, request, send_from_directory
import waitress

from isimple.util import suppress_stdout, Singleton
from isimple.core import get_logger, ROOTDIR
from isimple.core.schema import schema
from isimple.video import Analyzer, AnalyzerType
from isimple.history import History, AnalysisModel

log = get_logger('isimple')

# instantiate the app
app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)

UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'dist')


class ServerThread(Thread, metaclass=Singleton):
    _host: str
    _port: int

    def __init__(self, host, port):
        self._host = host
        self._port = port
        super().__init__(daemon=True)

    def run(self):
        waitress.serve(
            app,
            host=self._host,
            port=self._port,
        )


def respond(*args) -> str:
    return jsonify({'data': [*args]})


class Main(object, metaclass=Singleton):
    _instances: Dict[AnalyzerType, List[Analyzer]] = {}
    _locks: Dict[AnalyzerType, List[Lock]] = {}
    _models: List[AnalysisModel] = []
    _history = History()

    _host: str = 'localhost'
    _port: int = 8951

    _server: Thread

    _ping = Event()
    _unload = Event()
    _quit = Event()

    _suppress_timeout = 0.5
    _unload_timeout = 1

    def __init__(self):
        self._instances = {k:[] for k in AnalyzerType().options}
        self._locks = {k: [] for k in AnalyzerType().options}

        with suppress_stdout():  # Don't show waitress console output (wrong URL!)
            ServerThread(self._host, self._port).start()
            # Run in separate thread to revent Ctrl+C from closing browser if no tabs were open before
            Thread(
                target=lambda: webbrowser.open(
                    f"http://{self._host}:{self._port}/"
                )
            ).start()
            time.sleep(self._suppress_timeout)  # Wait for Waitress to catch up

    def loop(self):
        while not self._quit.is_set():
            self._ping.clear()
            if self._unload.is_set():
                log.debug(f'Unloaded from browser, waiting for ping.')
                time.sleep(self._unload_timeout)
                if not self._ping.is_set():
                    log.debug('No ping received; quitting.')
                    self._quit.set()
                else:
                    log.debug('Ping received; cancelling.')

    @contextmanager
    def lock(self, type: AnalyzerType, index: int, do_lock: bool = True):
        if do_lock:
            lock = self._locks[type][index].acquire()
            try:
                log.debug(f"Locking {type} {index}")
                yield lock
            finally:
                log.debug(f"Unlocking {type} {index}")
                self._locks[type][index].release()
        else:
            yield

    def add_instance(self, type: AnalyzerType) -> str:
        log.debug(f"Add instance of {type}")
        analyzer = type.get()()
        self._instances[type].append(analyzer)
        self._locks[type].append(Lock())
        self._models.append(self._history.add_analysis(analyzer))
        return respond(
            len(self._instances[type]) - 1
        )

    def get_schemas(self, type: AnalyzerType = None, index: int = None):
        if type is not None and index is not None:
            instance = self._instances[type][index]
        elif type is not None:
            instance = type.get()()
        else:
            return respond(None)

        return respond(
            {
                'config': schema(instance._config.__class__),
                'methods': {e.name:[schema(m) for m in ms]
                            for e,ms in instance.instance_mapping.items()}
            }
        )

    def call(self, type: AnalyzerType, index: int, method: str, data: dict, do_lock: bool = False) -> str:
        log.debug(f"{type} {index}: call '{method}'")
        # todo: sanity check this
        method = getattr(self._instances[type][index], method)
        assert hasattr(method, '__call__')

        # todo: some logic ~ which methods to lock and which methods not to lock

        with self.lock(type, index, do_lock):
            return respond(method(**{k:json.loads(v) for k,v in data.items()})) # type: ignore


main = Main()


@app.route('/', methods=['GET'])
def open_gui():
    return send_from_directory(UI, 'index.html')

@app.route('/<directory>/<file>', methods=['GET'])
def get_file(directory, file):
    return send_from_directory(os.path.join(UI, directory), file)

@app.route('/<file>', methods=['GET'])
def get_file2(file):
    return send_from_directory(os.path.join(UI), file)

@app.route('/api/<backendtype>/<index>/schemas', methods=['GET'])
def get_schemas(backendtype: str, index: int):
    bt = AnalyzerType(backendtype)
    index = int(index)
    i = __instances__[bt][index]
    return respond(
        {
            'config': schema(i._config.__class__),
            'methods': {e._name:schema(m[0]) for e, m in i._instance_mapping.items()},
        }
    )

@app.route('/api/<bt>/init', methods=['GET'])
def init(bt: str):
    return main.add_instance(AnalyzerType(bt))

@app.route('/api/<bt>/<index>/launch', methods=['GET'])
def launch(bt: str, index: int):
    main.call(AnalyzerType(bt), int(index), 'launch', {})
    return respond()

@app.route('/api/<bt>/<index>/<method>', methods=['GET'])
def call(bt: str, index: int, method: str):
    return main.call(AnalyzerType(bt), int(index), method, request.args.to_dict())

@app.route('/api/ping')
def ping():
    main._unload.clear()
    main._ping.set()
    return respond(True)

@app.route('/api/unload', methods=['GET', 'POST'])
def unload():
    main._unload.set()
    return respond(True)


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...
    # todo: server-level configuration

    main.loop()
