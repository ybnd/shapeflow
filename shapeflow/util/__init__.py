"""General utility functions & classes.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
import json
from logging import Logger
from functools import wraps
from typing import Generator, Optional, Union
from collections import namedtuple
import threading
import queue
import hashlib
from contextlib import contextmanager

import numpy as np


def ndarray2str(array: np.ndarray) -> str:
    return str(json.dumps(array.tolist()))


def str2ndarray(string: str) -> np.ndarray:
    return np.array(json.loads(str(string)))


Timing = namedtuple('Timing', ('t0', 't1', 'elapsed'))


def timed(f, logger: Logger):
    """Function decorator to measure elapsed time.
    Useful for profiling and debugging.

    Parameters
    ----------
    f
        Any function or method
    logger: Logger
        A logger to log to
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        logger.info(f"{f.__qualname__}() --> {te-ts} s elapsed.")
        return result
    return wrap


def logged(f, logger: Logger):
    """Function decorator to log before & after a function call.
    Useful for profiling and debugging.

    Parameters
    ----------
    f
        Any function or method
    logger: Logger
        A logger to log to
    """
    """Function decorator to log before & after call
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        logger.debug(f"{f.__qualname__}() --> call...")
        result = f(*args, **kwargs)
        logger.debug(f"{f.__qualname__}() --> done")
        return result
    return wrap


class Timer(object):
    """A timer context manager. Starts timing on ``__enter__`` and stops on
    ``__exit__``.
    Timing info can be retrieved with :attr:`~shapeflow.util.Timer.timing`.
    """
    _t0: float
    _t1: float
    _parent: object
    _logger: Logger
    _message: str
    _elapsed: Optional[float]

    def __init__(self, parent: object, logger: Logger):
        self._parent = parent
        self._elapsed = None
        self._logger = logger

    def __enter__(self, message: str = ''):
        self._message = message
        self._t0 = time.time()
        self._logger.info(f"{self._message}...")

    def __exit__(self):
        if hasattr(self, '_t0'):
            self._t1 = time.time()
            self._elapsed = self._t1 - self._t0
            self._logger.info(f"{self._message}: {self._elapsed} s. elapsed ")

    @property
    def timing(self) -> Optional[tuple]:
        """Optional[tuple]: start time, end time, elapsed time.
        """
        if all([hasattr(self, attr) for attr in ('_t0', '_t1', '_elapsed')]):
            return self._t0, self._t1, self._elapsed
        else:
            return None


def restrict(val, minval, maxval):
    """Clamp a value between a minimum and a maximum.
    """
    if val < minval:
        return minval
    if val > maxval:
        return maxval
    return val


def frame_number_iterator(total: int,
                          Nf: int = None,
                          dt: float = None, fps: float = None) \
        -> Generator[int, None, None]:
    """Get an iterator of frame numbers, based on either a number of frames
    ``Nf`` or a frame interval ``dt``.

    Parameters
    ----------
    total: int
        The total number of frames.
    Nf: int
        The number of frames to return. Defaults to ``None``.
    dt: float
        The frame interval to return. Defaults to ``None``.
        If using ``dt``, ``fps`` must also be provided.
    fps: float
        The framerate. Defaults to ``None``

    Raises
    ------
    ValueError
        When both ``Nf`` and ``dt`` are ``None``

    Returns
    -------
    Generator
        An iterator that returns the requested frame numbers.
    """
    if Nf is not None and (dt is None and fps is None):  # todo: very awkward, make two methods instead? also, this should be in shapeflow.video instead of here
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
    """Check whether ``version_a`` precedes ``version_b``.

    .. note::
       Only handles numerics, i.e. ``"1.25b.3v7"`` won't work.
    """
    return tuple(int(s) for s in version_a.split('.')) \
            < tuple(int(s) for s in version_b.split('.'))


def after_version(version_a, version_b):
    """Check whether ``version_a`` supercedes ``version_b``.

    .. note::
       Only handles numerics, i.e. ``"1.25b.3v7"`` won't work.
    """
    return not before_version(version_a, version_b)


def hash_file(path: str, blocksize: int = 1024) -> queue.Queue:
    """Start hashing a file without blocking the current thread.

    Parameters
    ----------
    path: str
        The path of the file to hash.
    blocksize: int
        The blocksize step to take when reading the file.
        Defaults to 1024.

    Returns
    -------
    queue.Queue
        A new ``queue.Queue`` object.
        Once the hash is ready, it will be pushed to this queue.
    """
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
    """Suppress ``stdout`` within a context.

    https://stackoverflow.com/questions/2125702/
    """
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def sizeof_fmt(size, suffix='B'):
    """Get a file size in bytes as a human-readable string.
    For example::

        >>> sizeof_fmt(10**3)
        "1 KB"
        >>> sizeof_fmt(10**9)
        "1 GB"

    Parameters
    ----------
    num
        A file size in bytes
    suffix: str
        The suffix to use. Defaults to ``"B"``.

    Returns
    -------
    str
        The file size as a human-readable string in decimal bytes.
    """
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(size) < 1000.0:
            return "%.0f %s%s" % (size, unit, suffix)
        size /= 1000.0
    return "%.1f %s%s" % (size, 'Y', suffix)


class Singleton(type):
    """A metaclass for singletons.
    """
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instances[cls]


def open_path(path: str) -> None:
    """Open a path in the file browser.
    """
    if os.path.isfile(path):
        path = os.path.dirname(os.path.realpath(path))

    if sys.platform == 'win32':
        os.startfile(path)  # type: ignore
    elif sys.platform == 'darwin':  # MacOS
        subprocess.Popen(['open', path])
    else:  # Something else, probably has xdg-open
        subprocess.Popen(['xdg-open', path])


@contextmanager
def ensure_path(path: Union[str, Path]):
    """ A hacky way to allow imports from arbitrary directories.
    Only use this for testing ``sf.py`` please :(
    """
    if isinstance(path, str):
        path = Path(path)

    path = Path(path).absolute()
    path_str = str(path)

    try:
        assert path.is_dir()
        sys.path.insert(0, path_str)
        yield
    except NotADirectoryError:
        raise
    finally:
        sys.path.remove(path_str)
