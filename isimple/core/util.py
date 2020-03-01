import os

import time
from functools import wraps
import inspect
from inspect import _empty  # type: ignore
from typing import Generator, Type, _GenericAlias, Union, Collection, Dict, Any, Tuple, Callable, List  # type: ignore
import numpy as np
import json

from schema import Schema, Optional

from isimple.core.log import get_logger
from isimple.core.config import EnforcedStr, Config


log = get_logger(__name__)


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
        log.info(f"{f.__name__}() --> {te-ts} s elapsed.")
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


def bases(c: type) -> List[type]:
    b = [base for base in c.__bases__]
    for base in b:
        b += bases(base)
    return list(set(b))

def nbases(c: type) -> int:
    if c is None or c is type(None):
        return 0
    else:
        return len(bases(c))


def all_attributes(
        t: Union[object, type],
        include_under: bool = True,
        include_methods: bool = True,
        include_mro: bool = False,
) -> List[str]:
    if not isinstance(t, type):
        t = t.__class__

    b = [t] + bases(t)
    attributes: list = []
    for base in b:
        attributes += base.__dict__
    attributes = list(set(attributes))

    if not include_under:
        attributes = [a for a in attributes if a[0] != '_']
    if not include_methods:
        attributes = [a for a in attributes if not hasattr(getattr(t,a),'__call__')] # todo: this is hacky
    if not include_mro:
        attributes = [a for a in attributes if a[0:3] != 'mro']

    return attributes

def all_annotations(t: Union[object, type]) -> Dict[str, type]:
    if not isinstance(t, type):
        t = object.__class__

    b = [t] + bases(t)
    annotations: Dict[str, Any] = {}

    # todo: in order to get the correct annotation, bases must be ordered from most generic to most specific
    for base in sorted(b, key=nbases):
        try:
            annotations.update(base.__annotations__)
        except AttributeError:
            pass

    return annotations


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


def before_version(version_a, version_b):
    """Check whether `version_a` precedes `version_b`.
        Only handles numerics, i.e. no '1.25b.3v7'
    """
    return tuple(int(s) for s in version_a.split('.')) \
            < tuple(int(s) for s in version_b.split('.'))


def after_version(version_a, version_b):
    """Check whether `version_a` doesn't precede `version_b`.
            Only handles numerics, i.e. no '1.25b.3v7'
    """
    return not before_version(version_a, version_b)


def resolve_type_to_most_specific(t: _GenericAlias) -> _GenericAlias:
    """Resolve Union in a type annotation to its most specific element
        * Use case:
        todo: extend to Optional
    :param t:
    :return:
    """
    if hasattr(t, '__origin__'):
        if t.__origin__ == Union:
        # Return the argument with the highest number of bases
        #   * If there are multiple 'specific options', return the first one (!)
        #   * Doesn't cover nested Union which seems to be resolved to
        #       a flat Union at runtime anyway.
            candidates = tuple(
                [a for a in t.__args__
                 if nbases(a) == nbases(max(t.__args__, key=nbases))]
            )
            if len(candidates) == 1:
                return candidates[0]
            else:
                return t.__args__[0]
        elif issubclass(t.__origin__, Collection):
        # Recurse over arguments
            t.__args__ = tuple(
                [resolve_type_to_most_specific(a) for a in t.__args__]
            )
            return t
    else:
        return t


def _type_to_schema(t, container=None, k=None) -> dict:  # todo: how to type t here?
    # todo: We're assuming everything is optional here!
    if container is None:
        container = t
    if k is None:
        k = t.__qualname__

    sk = Optional(k)

    if isinstance(t, _GenericAlias):
        # Extract typing info
        if hasattr(t, '__origin__'):
            if t.__origin__ == tuple:
                if t.__args__[1] == Ellipsis:
                    return {
                        sk: [Schema(_schemify(t.__args__[0]), name=k, as_reference=True)]
                    }
                else:
                    raise NotImplementedError(f"Tuple ~ {t.__args__}")
            elif t.__origin__ == list:
                raise NotImplementedError(f"List ~ {t.__args__}")
            elif t.__origin__ == dict:
                raise NotImplementedError(f"Dict ~ {t.__args__}")
            elif t.__origin__ == Union:
                return {
                    sk: resolve_type_to_most_specific(t),  # todo: doesn't handle unresolvable Unions
                }
            else:
                raise NotImplementedError(f"Can't handle {t}")
        else:
            raise NotImplementedError(t)
    elif issubclass(t, Config):
        return {
            sk: Schema(_schemify(t), name=k, as_reference=True),
        }
    elif t == str or t == int or t == float or t == bool:
        return {
            sk: t,
        }
    elif t == np.ndarray:  # todo: consider using BSON instead!
        return {
            sk: {
                'type': 'string',
                'contentEncoding': 'base64',
                'contentMediaType': 'application/x-numpy',
            },
        }
    elif issubclass(t, EnforcedStr):
        log.warning(f"{container.__qualname__} property '{k}' is an EnforcedStr, "
                    f"but its available options are not included in the schema.")
        return {
            sk: str,  # todo: integrate options into schema
        }
    elif t == dict:
        log.warning(
            f"{container.__qualname__} property '{k}' is a {t.__qualname__}, "
            f"consider making it a subclass of isimple.core.config.config instead.")
        return {
            sk: t
        }
    elif t == list:
        log.warning(
            f"{container.__qualname__} property '{k}' is a {t.__qualname__}, "
            f"consider making it more specific.")
        return {
            sk: t,
        }
    elif t == tuple:
        log.warning(
            f"{container.__qualname__} property '{k}' is a {t.__qualname__}, "
            f"consider making it more specific.")
        return {
            sk: t,
        }
    else:
        raise NotImplementedError(t)


def _schemify(t: type) -> dict:
    if issubclass(t, Config):
        schema = {}
        annotations = all_annotations(t)
        for a in all_attributes(t, include_under=False, include_methods=False):
            if hasattr(t, '__annotations__'):
                at = annotations[a]
            else:
                at = type(getattr(t, a))
            schema.update(
                _type_to_schema(
                    resolve_type_to_most_specific(at),
                    t, a
                )
            )
    else:
        schema = _type_to_schema(t, t, t)
    return schema


def get_config_schema(config: Type[Config]) -> Schema:
    return Schema(_schemify(config))


# noinspection PyUnresolvedReferences
def get_method_schema(method: Callable) -> Schema:
    schema = {}
    for a,p in inspect.signature(method).parameters.items():
        t = p.annotation

        if t is _empty:
            raise TypeError(f"Can not generate schema for method {method.__qualname__}; "
                            f"the type of argument '{a}' is not annotated.")
        else:
            if p.default is not _empty:
                sa = Optional(a)
            else:
                sa = a
            schema.update(
                {sa: _type_to_schema(t, method, a)}
            )
    return Schema(schema)


def dumps_schema(obj) -> str:
    try:
        if issubclass(obj, Config):
            schema = get_config_schema(obj)
        else:
            raise TypeError
    except TypeError:
        schema = get_method_schema(obj)

    return json.dumps(
        schema.json_schema(obj.__qualname__ + '.json'), indent = 2,
    )