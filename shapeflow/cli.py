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

import sys
import time
import socket
import json
import requests
import re
import abc
from pathlib import Path
import argparse
import textwrap
from typing import List, Callable, Optional, Tuple

from shapeflow import __version__, get_logger, settings
log = get_logger(__name__)

# type aliases
OptArgs = Optional[List[str]]
Parsing = Callable[[OptArgs], None]


class IterCommand(abc.ABCMeta):
    __entrypoint__: bool = False
    __command__: str

    def __str__(cls):
        try:
            return cls.__command__
        except AttributeError:
            return super().__str__()

    def __iter__(cls):
        return iter([c for c in cls.__subclasses__() if c.sub])

    @property
    def sub(cls):
        return hasattr(cls, '__command__')

    @property
    def dict(cls) -> dict:
        return {str(sub):sub for sub in cls}

    def __getitem__(cls, item: str) -> 'IterCommand':
        if item in cls.dict.keys():
            return cls.dict[item]
        else:
            return getattr(cls, item)

    @abc.abstractmethod
    def __usage__(cls) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __help__(cls) -> str:
        raise NotImplementedError


class Command(abc.ABC, metaclass=IterCommand):
    parser: argparse.ArgumentParser
    args: argparse.Namespace
    sub_args: List[str]

    def __init__(self, args: OptArgs = None):
        if args is None:
            args = sys.argv[1:]

        self.args, self.sub_args = self.parse(args)
        self.__call__()

    @abc.abstractmethod
    def __call__(self) -> None:
        raise NotImplementedError

    @classmethod
    def parse(cls, args: OptArgs) -> Tuple[argparse.Namespace, List[str]]:
        return cls.parser.parse_known_args(args)

    @classmethod
    def __help__(cls) -> str:
        return cls._fix_call(cls.parser.format_help())

    @classmethod
    def __usage__(cls) -> str:
        # Remove 'usage: ' part
        usage = cls.parser.format_usage()[7:].strip()
        return cls._fix_call(usage)

    @classmethod
    def _fix_call(cls, text: str) -> str:
        if cls.sub:
            call = ' '.join([cls.parser.prog, str(cls)])
            return text.replace(cls.parser.prog, call)
        else:
            return text




class Sf(Command):
    parser = argparse.ArgumentParser(
        description=f"""https://github.com/ybnd/shapeflow v{__version__}""",
        add_help=False
    )

    def __init__(self, args: OptArgs = None):
        self.parser.add_argument(
            '-h', '--help',
            action='store_true',
            help="show this help message"
        )
        self.parser.add_argument(
            '--version',
            action='store_true',
            help="show the version"
        )
        self.parser.add_argument(
            'command',
            default=None,
            nargs="?",
            choices=Command.dict,
            metavar='command',
            help="execute one of the commands listed below, default: serve"
        )
        super().__init__(args)

    def __call__(self):
        if self.args.help:
            if self.args.command is not None:
                print(Command[self.args.command].__help__())
            else:
                print(self.__help__())
                print("commands:")
                for c in Command:
                    print("   " + c.__usage__())
                print()
        elif self.args.version:
            print(__version__)
        else:
            if self.args.command is None:
                Command['serve'](self.sub_args)
            else:
                Command[self.args.command](self.sub_args)


class Serve(Command):
    __command__ = 'serve'
    parser = argparse.ArgumentParser(
        description="start the shapeflow server"
    )

    HOST = '127.0.0.1'
    PORT = 7951

    parser.add_argument(
        '--host',
        type=str,
        default=HOST,
        help=f"the host to serve from (default: {HOST})"
    )
    parser.add_argument(
        '--port',
        type=int,
        default=PORT,
        help=f"the port to serve from (default: {PORT}"
    )
    parser.add_argument(
        '--background',
        action='store_true',
        help="don't open a browser window"
    )

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
    parser = argparse.ArgumentParser(
        description="dump application schemas and settings to JSON"
    )

    parser.add_argument(
        '--pretty',
        action='store_true',
        help='indent JSON'
    )
    parser.add_argument(
        'dir',
        nargs='?',
        type=Path,
        default=Path.cwd(),
        help='directory to dump to'
    )

    def __call__(self):

        from shapeflow.config import schemas

        if not self.args.dir.is_dir():
            log.warning(f"making directory '{self.args.dir}'")
            self.args.dir.mkdir()

        self._write('schemas', schemas())
        self._write('settings', settings.to_dict())

    def _write(self, file, d):
        with open(self.args.dir / (file + '.json'), 'w+') as f:
            f.write(json.dumps(d, indent=2 if self.args.pretty else None))
