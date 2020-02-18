import time
from functools import wraps
import inspect
from typing import Generator
import numpy as np


def restrict(val, minval, maxval):
    """https://stackoverflow.com/questions/4092528
    """
    if val < minval:
        return minval
    if val > maxval:
        return maxval
    return val


def rotations(sequence) -> list:  # todo: clean up
    """Returns all rotations of a list.
    """

    def rotate(seq, n: int) -> list:
        return seq[n:] + seq[:n]

    rotation_list = []
    for N in range(len(sequence)):
        rotation_list.append(rotate(sequence, N))

    return rotation_list


def timing(f):
    """Function decorator to measure elapsed time.
    :param f: function
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        print(f"{f.__name__}() --> {te-ts} s elapsed.")
        return result
    return wrap


def describe_function(f):
    name = f.__name__

    if inspect.ismethod(f):
        if hasattr(f, '__self__'):
            classes = [f.__self__.__class__]
        else:
            #unbound method or regular function
            classes = [f.im_class]
        while classes:
            c = classes.pop()
            if name in c.__dict__:
                return f'{f.__module__}.{c.__name__}.{name}'
            else:
                classes = list(c.__bases__) + classes
    return f'{f.__module__}{name}'


def bases(c: type) -> list:
    b = [base for base in c.__bases__]
    for base in b:
        b += bases(base)
    return list(set(b))


def all_attributes(o: object) -> list:
    b = [o.__class__] + bases(o.__class__)
    attributes: list = []
    for base in b:
        attributes += base.__dict__
    return list(set(attributes))

def get_overridden_methods(c, m) -> list:
    b = [c] + bases(c)
    implementations = []
    for base in b:
        if m.__name__ in base.__dict__:
            implementations.append(getattr(base, m.__name__))

    return implementations


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
