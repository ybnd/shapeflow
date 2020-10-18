"""
Execute a Python script from virtual environment
"""

import abc
import sys
from typing import List, Tuple
import os
import subprocess

environment = '.venv'


def from_venv():
    arguments = sys.argv[1:]  # pass the arguments on to a subprocess
    command, shell = resolve(environment, os.path.basename(sys.executable))

    try:
        subprocess.check_call(
            command + arguments,
            shell=shell
        )
    except KeyboardInterrupt:
        # don't print exception on Ctrl+C
        pass
    except subprocess.CalledProcessError as e:
        exit(e.returncode)
    except Exception:
        # re-raise any other exceptions
        raise

class _VenvCall(object):
    env: str
    python: str

    subpath: str = 'bin'
    doshell: bool = False
    pythons = ['python3', 'python']

    def __init__(self, env: str, python: str):
        self.environment = env
        self.python = python

    @property
    def prepend(self) -> List[str]:
        return []

    @property
    def path(self) -> str:
        return os.path.join(self.environment, self.subpath)

    def _executable(self, python: str) -> str:
        return os.path.join(self.path, python)

    def resolve(self) -> Tuple[List[str], bool]:
        if not os.path.isdir(self.path) or len(os.listdir(self.path)) == 0:
            raise EnvironmentError(f"Can't resolve virtual environment '{self.env}'")

        pythons = [self.python] + [p for p in self.pythons if p != self.python]
        executables = [self._executable(python) for python in pythons]
        for executable in executables:
            if os.path.isfile(executable):
                return self.prepend + [executable], self.doshell


class _WindowsVenvCall(_VenvCall):
    subpath = 'Scripts'
    doshell = True


def resolve(environment: str, python: str) -> Tuple[List[str], bool]:
    if os.name == 'nt':  # Windows
        return _WindowsVenvCall(environment, python).resolve()
    else:
        return _VenvCall(environment, python).resolve()


if __name__ == '__main__':
    if os.path.isdir(environment):
        from_venv()
    else:
        raise EnvironmentError(f"No virtual environment in '{environment}'.")
