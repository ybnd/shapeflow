"""Tiny commands to be called from sf.py

* Calling from the commandline:
    ```
    python sf.py --do <command name> <arguments>
    ```

* Calling from Python:
    ```
    from shapeflow.commands import do
    do('<command name>', ['<arguments>'])
    ```
    to resolve command names in the IDE,
    ```
    do(Command.<command name>, ['<arguments>'])
    ```
"""

import time
import socket
import json
import requests
import re
import abc
from pathlib import Path
import argparse
import textwrap
from typing import List, Callable, Optional

import shapeflow
log = shapeflow.get_logger('shapeflow')

# type aliases
OptArgs = Optional[List[str]]
Parsing = Callable[[OptArgs], None]


class Command(abc.ABC):
    __command__: str
    __parser__: argparse.ArgumentParser

    args: argparse.Namespace

    def __init__(self, args: OptArgs = None):
        self.args = self.parse(args)
        self.__call__()

    @abc.abstractmethod
    def __call__(self) -> None:
        raise NotImplementedError

    @classmethod
    def parse(cls, args: List[str]) -> argparse.Namespace:
        return cls.__parser__.parse_args(args)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        cls.__parser__.prog = f"{cls.__parser__.prog} {cls.__command__}"

    @classmethod
    def __help__(cls) -> str:
        return cls.__parser__.format_help()

    @classmethod
    def __usage__(cls) -> str:
        # Replace 'usage: ' part with indent whitespace
        return "   " + cls.__parser__.format_usage()[7:].strip()


class Serve(Command):
    __command__ = 'serve'
    __parser__ = argparse.ArgumentParser(description="start the shapeflow server")

    HOST = '127.0.0.1'
    PORT = 7951

    __parser__.add_argument('--host', type=str, default=HOST,
                        help=f"the host to serve from (default: {HOST})")
    __parser__.add_argument('--port', type=int, default=PORT,
                        help=f"the port to serve from (default: {PORT}")
    __parser__.add_argument('--background', action='store_true',
                        help="don't open a browser window")

    def __call__(self):
        self._replace()

        from shapeflow.main import Main

        main = Main()
        main.serve(host=self.args.host, port=self.args.port, open=(not self.args.background))
        log.info('stopped')

    def _in_use(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.args.host, self.args.port)) == 0  # todo: look for actual return code

    def _replace(self):
        if self._in_use():
            log.info('address already in use')

            requests.post(f"http://{self.args.host}:{self.args.port}/api/quit")
            while self._in_use():
                time.sleep(0.1)

            log.info('previous server instance quit')


class Dump(Command):
    __command__ = 'dump'
    __parser__ = argparse.ArgumentParser(description="dump application schemas and settings to JSON")

    __parser__.add_argument('--pretty', action='store_true',
                        help='indent JSON')
    __parser__.add_argument('dir', nargs='?', type=Path, default=Path.cwd(),
                        help='directory to dump to')

    def __call__(self):

        from shapeflow.config import schemas

        if not self.args.dir.is_dir():
            log.warning(f"making directory '{self.args.dir}'")
            self.args.dir.mkdir()

        self._write('schemas', schemas())
        self._write('settings', shapeflow.settings.to_dict())

    def _write(self, file, d):
        with open(self.args.dir / (file + '.json'), 'w+') as f:
            f.write(json.dumps(d, indent=2 if self.args.pretty else None))


__commands__ = { c.__command__: c for c in Command.__subclasses__() }


def do(command: str, args: OptArgs = None):
    if command not in __commands__:
        raise ValueError(f"unknown command '{command}'")
    else:
        __commands__[command](args)
