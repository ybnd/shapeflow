"""Tiny commands to be called from sf.py

Calling from the commandline::

   python sf.py --do <command name> <arguments>
"""

import os
import sys
import time
import glob
import socket
import json
import abc
from pathlib import Path
import argparse
import shutil
from functools import lru_cache
from typing import List, Callable, Optional, Tuple
from subprocess import Popen, PIPE
from urllib.request import urlretrieve
from zipfile import ZipFile

from distutils.util import strtobool
import git
import requests

from shapeflow import __version__, get_logger, settings
from shapeflow.util import before_version, after_version


log = get_logger(__name__)

# type aliases
OptArgs = Optional[List[str]]
Parsing = Callable[[OptArgs], None]


class CliError(Exception):
    pass


class IterCommand(abc.ABCMeta):
    """Command iterator metaclass.

    Iterates over its subclasses, skipping any without a ``__command__``.
    If any of these should remain abstract, they shouldn't define one.
    """
    __command__: str
    """Command name. This is how the command is addressed from the commandline.
    """  # todo: nope, doesn't work'

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
            self.command()
        except argparse.ArgumentError as e:
            raise CliError(
                f'{self.__class__}: could not parse arguments'
            )
        except TypeError as e:
            raise CliError(
                f'{self.__class__}: type error'
            )

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
        add_help=False  # we're defining a custom --help that should override
                        #  the built-in one
    )
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help="show this help message; "
             "for help with a specific command, call --help [command]"
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
        '--dir',
        type=Path,
        default=Path.cwd(),
        help='directory to dump to'
    )

    def command(self):
        from shapeflow.config import schemas

        if not self.args.dir.is_dir():
            log.warning(f"making directory '{self.args.dir}'")
            self.args.dir.mkdir()

        self._write('schemas', schemas())
        self._write('settings', settings.to_dict())

    def _write(self, file, d):
        with open(self.args.dir / (file + '.json'), 'w+') as f:
            f.write(json.dumps(d, indent=2 if self.args.pretty else None))


class GitMixin(abc.ABC):
    """Metaclass for commands interacting with the git repository
    """

    URL = 'https://github.com/ybnd/shapeflow/'

    _repo = None
    _latest = None

    @property
    def repo(self) -> git.Repo:
        if self._repo is None:
            self._repo = git.Repo()
            self._repo.remote().fetch()
        return self._repo

    @property
    def latest(self) -> str:
        if self._latest is None:
            response = requests.head(self.URL + 'releases/latest')
            self._latest = response.headers['location'].split('/')[-1]
        return self._latest

    @lru_cache()
    def is_up_to_date(self, tag) -> bool:
        if self.is_at_release(tag):
            return not before_version(tag, self.latest)
        else:
            return self.repo.head.commit.hexsha == self.repo.remote().repo.head.commit.hexsha  # todo: can also be _after_ though

    @property
    def tag(self) -> str:
        try:
            return self.repo.git.describe('--exact-match', '--tag')
        except git.GitCommandError:
            return ''

    @lru_cache()
    def is_at_release(self, tag: str) -> bool:
        return requests.head(self.URL + 'releases/tag/' + tag).status_code == 200

    @property
    def ui_url(self) -> str:
        return self.URL + f'releases/download/{self.tag}/dist-{self.tag}.tar.gz'

    def _is_a_ref(self, ref: str) -> bool:
        try:
            return len(self.repo.git.rev_list('-n', '1', ref)) > 0
        except git.GitCommandError:
            return False

    def _is_after_0_4_4(self, ref: str) -> bool:
        try:
            return before_version('0.4.4', ref)
        except ValueError:
            # ~ https://stackoverflow.com/a/3006050/12259362
            branch = git.Head(self.repo, 'refs/heads/' + ref).commit.hexsha
            t0_4_4 = git.TagReference(self.repo, 'refs/heads/0.4.4').commit.hexsha

            return branch == t0_4_4 or len(
                self.repo.git.rev_list('--boundary', f'{t0_4_4}..{branch}')
            ) > 0

    def _get_compiled_ui(self) -> None:
        if self.is_at_release(self.tag):
            if after_version(self.tag, '0.3'):
                try:
                    from urllib.request import urlopen
                    from tarfile import open

                    open(
                        fileobj=urlopen(self.ui_url),
                        mode='r|gz'
                    ).extractall(path='ui/')
                    print('Downloaded compiled UI.')
                except:
                    raise CliError(
                        f'No compiled UI for "{self.tag}" at {self.ui_url}.\n'
                        f'This is probably an issue with this release, '
                        f'please inform the maintaner.'
                    )
        else:
            raise CliError(
                'No compiled UI can be downloaded because the repository '
                'is currently not at a release version.\n'
                'Please check out a release or compile the UI yourself with'
                '\n\n\tcd ui && npm run build\n'
            )

    def _handle_local_changes(self, force: bool) -> bool:
        if self.repo.is_dirty():
            if force or self._prompt_discard_changes():
                self.repo.head.reset(working_tree=True)
            else:
                return False
        return True

    def _prompt_discard_changes(self) -> bool:
        changed = "\n\t".join(
            [item.a_path for item in self.repo.index.diff(None)] \
                + self.repo.untracked_files
        )
        return bool(strtobool(input(
            f'Local changes to\n\n {changed} \n\n'
            f'will be overwritten. Continue? (y/n) '
        )))


class Update(Command, GitMixin):
    """Update the application
    """

    __command__ = 'update'
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        '--discard-changes',
        action='store_true',
        help='discard local changes without prompting'
    )

    def command(self):
        if not self.is_up_to_date(self.tag):
            if self._handle_local_changes(self.args.discard_changes):
                self._update()
        else:
            print('Already up to date.')

    def _update(self) -> None:
        if self.repo.head.is_detached:
            # repo is at a tag, get the latest release
            self.repo.git.checkout(self.latest)
            self._get_compiled_ui()
        else:
            # repo is at a branch, pull the branch if there are new commits
            result = self.repo.git.pull()
            print(result)
            print(
                'Note: the repository is at a branch. Please recompile the UI '
                '\n\n\t cd ui && npm run build \n\n'
            )


class Checkout(Command, GitMixin):
    """Check out a specific version of the application. Please not you will
    not have access to this command if you check out a version before 0.4.4
    """

    __command__ = 'checkout'
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        'ref',
        type=str,
        help="the tag or branch to check out"
    )
    parser.add_argument(
        '--discard-changes',
        action='store_true',
        help='discard local changes without prompting'
    )

    def command(self) -> None:
        if not self._is_a_ref(self.args.ref):
            raise CliError(f'Not a valid reference: "{self.args.ref}"')

        if self._is_after_0_4_4(self.args.ref) or self._checkout_anyway():
            if self._handle_local_changes(self.args.discard_changes):
                self.repo.git.checkout(self.args.ref)
                print(f'Checked out "{self.args.ref}"')
                self._get_compiled_ui()

    def _checkout_anyway(self) -> bool:
        return bool(strtobool(input(
            f'After checking out "{self.args.ref}" you won\'t be able to use '
            f'the "update" or "checkout" commands (they were added later, '
            f'in v0.4.4) Continue? (y/n) '
        )))


class GetCompiledUi(Command, GitMixin):
    """Get the compiled UI for the current version
    """

    __command__ = 'get-compiled-ui'
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        '--replace',
        action='store_true',
        help='replace the current UI without prompting'
    )

    def command(self) -> None:
        ui_dir = Path('ui/dist/')
        exists = ui_dir.exists()

        if exists:
            if not any(ui_dir.iterdir()):
                ui_dir.rmdir()
            elif self.args.replace or self._prompt_replace_ui():
                shutil.rmtree(ui_dir)
            else:
                return None

        self._get_compiled_ui()

    def _prompt_replace_ui(self) -> bool:
        return bool(strtobool(input('Replace the current UI? (y/n) ')))


class SetupCairo(Command):
    """Set up cairo DLLs (Windows) ~ https://github.com/preshing/cairo-windows/
    """

    __command__ = 'setup-cairo'
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    URL = 'https://github.com/preshing/cairo-windows/releases/download/with-tee/cairo-windows-1.17.2.zip'

    def command(self) -> None:
        if self._on_windows():
            self._cleanup()
            self._setup()
        else:
            print(f'Not on Windows.')
            return None

    def _cleanup(self) -> None:
        """Remove cairo files from the current Python environment.
        """
        for file in self.env.glob('cairo'):
            file.unlink()

    def _setup(self) -> None:
        """Install cairo into the current Python environment.

        This DLL has been known to behave weirdly with regards to
        Windows/Python combinations of different 'bitness', so the strategy
        here is to try both versions and keep whichever works.
        """

        if not self._cairo_works():
            self._get_cairo_dlls()

            try:
                # try with x64 cairo.dll
                for file in Path().glob('cairo*/lib/x64/cairo.*'):
                    file.replace(self.env / file.name)

                if self._cairo_works():
                    print('Installed x64 cairo DLL')
                    return None

                # try with x86 cairo.dll
                for file in Path().glob('cairo*/lib/x86/cairo.*'):
                    file.replace(self.env / file.name)

                if self._cairo_works():
                    print('Installed x86 cairo DLL')
                    return None
                else:
                    raise EnvironmentError('Could not install cairo DLL')
            finally:
                for f in Path().glob('cairo*'):
                    shutil.rmtree(f)

        else:
            print('It seems that cairo is already working properly.')

    @classmethod
    def _get_cairo_dlls(cls) -> None:
        urlretrieve(cls.URL, 'cairo.zip')
        with ZipFile('cairo.zip', 'r') as z:
            z.extractall()

        Path('cairo.zip').unlink()

    @staticmethod
    def _cairo_works() -> bool:
        process = Popen([sys.executable, '-c', '"import cairosvg"'], PIPE)
        return process.poll() == 0

    @staticmethod
    def _on_windows() -> bool:
        return os.path == 'nt'

    @property
    def env(self) -> Path:
        return Path(sys.executable).parent


class Declutter(Command):
    """Hide clutter files from the repository
    """

    CLUTTER = ['mypy.ini', 'tox.ini', '__pycache__']

    __command__ = 'declutter'
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        '--undo',
        action='store_true',
        help='unhide clutter'
    )

    def command(self) -> None:
        if not self.args.undo:
            self._declutter()
        else:
            self._reclutter()

    def _declutter(self) -> None:
        if os.name == 'nt':
            # Pre-emptively create __pycache__ so we can hide it now.
            if not os.path.isdir('__pycache__'):
                os.mkdir('__pycache__')

            for file in self.CLUTTER + glob.glob('.*'):
                if Path(file).exists():
                    os.system("attrib +h " + file)
        elif os.name == 'darwin':
            pass  # todo: .hidden doesn't work
        else:
            with open('.hidden', 'w+') as f:
                f.write('\n'.join(self.CLUTTER))

    def _reclutter(self) -> None:
        if os.name == 'nt':
            for file in self.CLUTTER + glob.glob('.*'):
                if Path(file).exists():
                    os.system("attrib -h " + file)
        elif os.name == 'darwin':
            pass  # todo: .hidden doesn't work
        else:
            Path('.hidden').unlink()


