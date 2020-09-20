import os
import subprocess
import sys
import time
import json
from distutils.util import strtobool
from functools import wraps, lru_cache
from typing import Any, Generator, Optional
from collections import namedtuple
import threading
import queue
import hashlib
from contextlib import contextmanager

import numpy as np

from shapeflow import get_logger, settings, Logger

log = get_logger(__name__)


def str2bool(value: str) -> bool:
    return strtobool(value)


def ndarray2str(array: np.ndarray) -> str:
    return str(json.dumps(array.tolist()))


def str2ndarray(string: str) -> np.ndarray:
    return np.array(json.loads(str(string)))


Timing = namedtuple('Timing', ('t0', 't1', 'elapsed'))


def timed(f):
    """Function decorator to measure elapsed time.
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        log.info(f"{f.__qualname__}() --> {te-ts} s elapsed.")
        return result
    return wrap


def logged(f):
    """Function decorator to log before & after call
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        log.debug(f"{f.__qualname__}() --> call...")
        result = f(*args, **kwargs)
        log.debug(f"{f.__qualname__}() --> done")
        return result
    return wrap


class Timer(object):
    _t0: float
    _t1: float
    _parent: object
    _logger: Logger
    _message: str
    _elapsed: Optional[float]

    def __init__(self, parent: object):
        self._parent = parent
        self._elapsed = None
        self.set_logger()

    def __enter__(self, message: str = ''):
        self._message = message
        self._t0 = time.time()
        self._logger.info(f"{self._message}...")

    def __exit__(self):
        if hasattr(self, '_t0'):
            self._t1 = time.time()
            self._elapsed = self._t1 - self._t0
            self._logger.info(f"{self._message}: {self._elapsed} s. elapsed ")

    def set_logger(self, logger: Logger = log):
        self._logger = logger

    @property
    def timing(self) -> Optional[tuple]:
        if all([hasattr(self, attr) for attr in ('_t0', '_t1', '_elapsed')]):
            return self._t0, self._t1, self._elapsed
        else:
            return None


def restrict(val, minval, maxval):
    if val < minval:
        return minval
    if val > maxval:
        return maxval
    return val


def frame_number_iterator(total: int,
                          Nf: int = None,
                          dt: float = None, fps: float = None) \
        -> Generator[int, None, None]:
    if Nf is not None and (dt is None and fps is None):  # todo: a bit awkward, make two methods instead?
        Nf = min(Nf, total)
        for f in np.linspace(0, total, Nf):
            yield int(f)
    elif (dt is not None and fps is not None) and Nf is None:
        df = restrict(dt * fps, 1, total)
        for f in np.arange(0, total, df):
            yield int(f)
    else:
        ValueError()


def before_version(version_a, version_b):
    """Check whether `version_a` precedes `version_b`.
        Only handles numerics, i.e. no '1.25b.3v7'
    """
    return tuple(int(s) for s in version_a.split('.')) \
            < tuple(int(s) for s in version_b.split('.'))


def after_version(version_a, version_b):
    return not before_version(version_a, version_b)


def hash_file(path: str, blocksize: int = 1024) -> queue.Queue:
    if os.path.isfile:
        q: queue.Queue = queue.Queue()
        def _hash_file():
            nonlocal q

            m = hashlib.sha1()
            with open(path, 'rb') as f:
                while True:
                    buf = f.read(blocksize)
                    if not buf:
                        break
                    m.update(buf)
                hash = m.hexdigest()
                q.put(hash)
        threading.Thread(target=_hash_file, daemon=True).start()
        return q


@contextmanager
def suppress_stdout():
    """https://stackoverflow.com/questions/2125702/
    """
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%.0f %s%s" % (num, unit, suffix)
        num /= 1000.0
    return "%.1f %s%s" % (num, 'Y', suffix)


class Singleton(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instances[cls]


def open_path(path: str) -> None:
    if os.path.isfile(path):
        path = os.path.dirname(os.path.realpath(path))

    if os.name == 'nt':  # Windows
        os.startfile(path)
    elif os.name == 'darwin':  # MacOS
        subprocess.Popen(['open', path])
    else:  # Something else, probably has xdg-open
        subprocess.Popen(['wdg-open', path])
