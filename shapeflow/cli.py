"""Tiny commands to be called from sf.py

Calling from the commandline::

   python sf.py --do <command name> <arguments>
"""

import sys
import time
import socket
import json
import requests
import abc
from pathlib import Path
import argparse
from typing import List, Callable, Optional, Tuple

from shapeflow import __version__
from shapeflow.settings import settings
from shapeflow.core import get_logger
from shapeflow.core.logging import RootException

log = get_logger(__name__)

# type aliases
OptArgs = Optional[List[str]]
Parsing = Callable[[OptArgs], None]


class CliError(RootException):
    pass


class IterCommand(abc.ABCMeta):
    """Command iterator metaclass.

    Iterates over its subclasses, skipping any without a ``__command__``.
    If any of these should remain abstract, they shouldn't define one.
    """
    __command__: str
    """Command name. This is how the command is addressed from the commandline.
    """

    def __str__(cls):
        try:
            return cls.__command__
        except AttributeError:
            return super().__str__()

    @property
    def sub(cls):
        """Returns True if this class is a subcommand
        """
        return hasattr(cls, '__command__')

    def __iter__(cls):
        return iter([c for c in cls.__subclasses__() if c.sub])

    @property
    def dict(cls) -> dict:
        """Get a ``dict`` mapping all defined command names to their
        respective class
        """
        return {str(sub):sub for sub in cls}

    def __getitem__(cls, item: str) -> 'IterCommand':
        """Get a subcommand by its __command__
        """
        if item in cls.dict.keys():
            return cls.dict[item]
        else:
            return getattr(cls, item)

    @abc.abstractmethod
    def __usage__(cls) -> str:
        """Usage string"""
        raise NotImplementedError

    @abc.abstractmethod
    def __help__(cls) -> str:
        """Help string"""
        raise NotImplementedError


class Command(abc.ABC, metaclass=IterCommand):
    """Abstract command.

    * handles argument parsing & execution

    * subclasses can implement their functionality in :meth:`Command.command()`
    """
    parser: argparse.ArgumentParser
    args: argparse.Namespace
    sub_args: List[str]

    def __init__(self, args: OptArgs = None):
        if args is None:
            # gather commandline arguments
            args = sys.argv[1:]
        try:
            self.args, self.sub_args = self._parse(args)

            # only the root Command is allowed to pass on sub_args
            if len(self.sub_args) > 0 and hasattr(self, "__command__"):
                raise CliError(f"unrecognized argument(s) {self.sub_args}")

            self.command()
        except argparse.ArgumentError:
            raise CliError
        except TypeError:
            raise CliError

    @abc.abstractmethod
    def command(self) -> None:
        raise NotImplementedError

    @classmethod
    def __help__(cls) -> str:
        """Cleaned-up help string
        """
        return cls._fix_call(cls.parser.format_help())

    @classmethod
    def __usage__(cls) -> str:
        """Cleaned-up usage string
        """
        usage = cls.parser.format_usage()[7:].strip()
        return cls._fix_call(usage)

    @classmethod
    def _parse(cls, args: OptArgs) -> Tuple[argparse.Namespace, List[str]]:
        return cls.parser.parse_known_args(args)

    @classmethod
    def _fix_call(cls, text: str) -> str:
        """Fix text by appending __command__ to the program name
        """
        if cls.sub:
            call = ' '.join([cls.parser.prog, str(cls)])
            return text.replace(cls.parser.prog, call)
        else:
            return text


class Sf(Command):
    """Commandline entry point.
    This is the command that gets called first and calls any subcommands
    if requested.
    """
    parser = argparse.ArgumentParser(
        description=f"""https://github.com/ybnd/shapeflow v{__version__}""",
        add_help=False
    )
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help="show this help message"
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help="show the version"
    )
    def __init__(self, args: OptArgs = None):
        # note: if the command argument is added as a class attribute,
        #       Command subclasses will be left out of the choices if they
        #       are defined _after_ this class.
        self.parser.add_argument(
            'command',
            default=None,
            nargs="?",
            choices=Command.dict,
            metavar='command',
            help="execute one of the commands listed below, default: serve"
        )
        super().__init__(args)

    def command(self) -> None:
        if self.args.help:
            if self.args.command is not None:
                # print the help string of the requested command
                print(Command[self.args.command].__help__())
            else:
                # print own help string
                print(self.__help__())
                # print usage of commands
                print("commands:")
                for c in Command:
                    print("   " + c.__usage__())
                print()
        elif self.args.version:
            print(__version__)
        else:
            if self.args.command is None:
                # default command
                Command['serve'](self.sub_args)
            else:
                # dispatch arguments to command
                Command[self.args.command](self.sub_args)


class Serve(Command):
    """Starts the ``shapeflow`` server.
    """

    __command__ = 'serve'
    parser = argparse.ArgumentParser(
        description=__doc__
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

    def command(self):
        self._replace()

        from shapeflow.server import ShapeflowServer

        server = ShapeflowServer()
        server.serve(
            host=self.args.host,
            port=self.args.port,
            open=(not self.args.background)
        )
        log.info('exit')

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
    """Dump application schemas and settings to JSON
    """

    __command__ = 'dump'
    parser = argparse.ArgumentParser(
        description=__doc__
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

    def command(self):
        from shapeflow.main import schemas

        if not self.args.dir.is_dir():
            log.warning(f"making directory '{self.args.dir}'")
            self.args.dir.mkdir()

        self._write('schemas', schemas())
        self._write('settings', settings.to_dict())

    def _write(self, file, d):
        with open(self.args.dir / (file + '.json'), 'w+') as f:
            f.write(json.dumps(d, indent=2 if self.args.pretty else None))
