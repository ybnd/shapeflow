# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/
# cheated off of https://stackoverflow.com/questions/39801718

import os
import sys
import time
import json
from threading import Thread, Event
from typing import Dict, List
import webbrowser

from flask import Flask, jsonify, request, send_from_directory
import waitress
import logging

from isimple.util import suppress_stdout, Singleton
from isimple.core import get_logger, ROOTDIR
from isimple.core.schema import schema
from isimple.video import Analyzer, AnalyzerType
from isimple.history import History, AnalysisModel

log = get_logger('isimple')

# todo: this should be an object.
__instances__: dict = {  # todo: would it be a good idea to pickle anything that's still running when the app closes, and check the previous state on the next run? Would solve concerns over closing the app 'prematurely'.
    AnalyzerType('VideoAnalyzer'): [],  # todo: should lock instances when they are running e.g. an analysis
}

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


def respond(*args) -> str:  # todo: use method schemas
    return jsonify({'data': [*args]})


class Main(object, metaclass=Singleton):
    _instances: Dict[AnalyzerType,List[Analyzer]] = {}
    _models: List[AnalysisModel]
    _history: History

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
        self._models = []
        self._history = History()

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
                    log.debug('No ping received, quitting.')
                    self._quit.set()

    def add_instance(self, type: AnalyzerType) -> str:  # todo: should return list of methods that don't rely on nested BackendInstances & their schemas
        log.debug(f"Add instance of {type}")
        analyzer = type.get()()
        self._instances[type].append(analyzer)  # todo: wow.
        self._models.append(self._history.add_analysis(analyzer))
        return respond(
            len(self._instances[type]) - 1
        )

    def call(self, type: AnalyzerType, index: int, method: str, data: dict) -> str:
        log.debug(f"{type} {index}: call '{method}'")
        method = getattr(self._instances[type][index], method)  # todo: sanity check this
        assert hasattr(method, '__call__')
        return respond(
            method(**{k:json.loads(v) for k,v in data.items()})  #type: ignore
        )


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

@app.route('/api/<bt>/init', methods=['GET'])
def init(bt: str):
    return main.add_instance(AnalyzerType(bt))

@app.route('/api/<bt>/<index>/launch', methods=['GET'])
def launch(bt: str, index: int):
    main.call(AnalyzerType(bt), int(index), 'launch', {})  # todo: should also cache all method pointers for __instances__[bt][index] so we don't call .get() a million times
    return respond()  # todo: should return all available methods & their schemas

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

@app.route('/api/<bt>/<index>/<method>', methods=['GET'])
def call(bt: str, index: int, method: str):
    return main.call(AnalyzerType(bt), int(index), method, request.args.to_dict())

@app.route('/api/ping')
def ping():
    log.debug('Ping received.')
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
