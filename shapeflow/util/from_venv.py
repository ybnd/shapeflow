import abc
import sys
from typing import List, Tuple
import os
import subprocess

environment = '.venv'


def from_venv(env: str) -> None:
    """Re-run the current script from a virtual environment.

    Gathers call arguments from ``sys.argv`` and starts a child process
    from the virtual environment.

    Parameters
    ----------
    env: str
        The directory of the virtual environment.
    """
    arguments = sys.argv[1:]  # pass the arguments on to a subprocess
    command, shell = _resolve(env, os.path.basename(sys.executable))

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
        self.env = env
        self.python = python

    @property
    def prepend(self) -> List[str]:
        return []

    @property
    def path(self) -> str:
        return os.path.abspath(os.path.join(self.env, self.subpath))

    def _executable(self, python: str) -> str:
        return os.path.join(self.path, python)

    def resolve(self) -> Tuple[List[str], bool]:
        if not os.path.isdir(self.path):
            raise EnvironmentError(f"'{self.env}' does not exist")

        pythons = [self.python] + [p for p in self.pythons if p != self.python]
        executables = [self._executable(python) for python in pythons]
        for executable in executables:
            if os.path.isfile(executable):
                return self.prepend + [executable], self.doshell

        raise EnvironmentError(f"'{self.env}' is not a virtual environment")


class _WindowsVenvCall(_VenvCall):
    subpath = 'Scripts'
    doshell = True

    @property
    def prepend(self) -> List[str]:
        return [f'PATH={self.path};%PATH%', '&&']


def _resolve(environment: str, python: str) -> Tuple[List[str], bool]:
    if os.name == 'nt':  # Windows
        return _WindowsVenvCall(environment, python).resolve()
    else:
        return _VenvCall(environment, python).resolve()


if __name__ == '__main__':
    if os.path.isdir(environment):
        from_venv(environment)
    else:
        raise EnvironmentError(f"No virtual environment in '{environment}'.")
