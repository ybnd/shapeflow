import os

import time
from functools import wraps
import inspect
from typing import Generator, Type, _GenericAlias, Union, Optional, Collection, Tuple  # type: ignore
import numpy as np
import json

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

def nbases(c: type) -> int:
    if c is None or c is type(None):
        return 0
    else:
        return len(bases(c))


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


def get_schema(config: Type[Config]):  # todo: check the schema package: https://github.com/keleshev/schema
    TITLE = 'title'
    TYPE = 'type'
    ITEMS = 'items'
    PROPERTIES = 'properties'
    DEFINITIONS = 'definitions'
    OBJECT = 'object'
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    ARRAY = 'array'
    NUMPY = {
        'contentEncoding': 'base64',
        'contentMediaType': 'application/x-numpy',
    }
    REF = '$ref'


    def REFKEY(t) -> str:
        return t.__qualname__


    def DEFINITION(t) -> str:
        return f"#/{DEFINITIONS}/{REFKEY(t)}"


    def handle_type(t, config, k) -> Tuple[dict, dict]:  # todo: how to type t here?
        definitions = {}

        if isinstance(t, _GenericAlias):
            # Extract typing info
            if hasattr(t, '__origin__'):
                if t.__origin__ == tuple:
                    if t.__args__[1] == Ellipsis:
                        item, item_def = handle_type(t.__args__[0], config, k)
                        definitions.update(item_def)
                        property = {
                            TYPE: ARRAY,
                            ITEMS: item
                        }
                    else:
                        raise NotImplementedError(f"Tuple ~ {t.__args__}")
                elif t.__origin__ == list:
                    raise NotImplementedError(f"List ~ {t.__args__}")
                elif t.__origin__ == dict:
                    raise NotImplementedError(f"Dict ~ {t.__args__}")
                else:
                    raise NotImplementedError(f"Can't handle {t}")
            else:
                raise NotImplementedError
        elif issubclass(t, Config):
            subschema = schemeify(t)
            definitions.update({
                REFKEY(t): {
                    TYPE: OBJECT,
                    **subschema[PROPERTIES]
                },
                **subschema[DEFINITIONS]
            })
            property = {
                REF: DEFINITION(t),
            }
        elif issubclass(t, EnforcedStr):
            log.warning(f"{config.__qualname__} property '{k}' is an EnforcedStr, "
                        f"but its available options are not yet included in the schema.")
            property = {
                TYPE: STRING,  # todo: integrate options into schema
            }
        elif t == str:
            property = {
                TYPE: STRING,  # todo: integrate options into schema
            }
        elif t == int:
            property = {
                TYPE: INTEGER,
            }
        elif t == float:
            property = {
                TYPE: FLOAT,
            }
        elif t == bool:
            property = {
                TYPE: BOOLEAN,
            }
        elif t == np.ndarray:  # todo: consider using BSON instead!
            property = {
                TYPE: STRING,
                **NUMPY
            }
        elif t == dict:
            log.warning(
                f"{config.__qualname__} property '{k}' is a {t.__qualname__}, "
                f"consider making it a subclass of isimple.core.config.config instead.")
            property = {
                TYPE: OBJECT
            }
        elif t == list:
            log.warning(
                f"{config.__qualname__} property '{k}' is a {t.__qualname__}, "
                f"consider making it more specific.")
            property = {
                TYPE: ARRAY,
            }
        elif t == tuple:
            log.warning(
                f"{config.__qualname__} property '{k}' is a {t.__qualname__}, "
                f"consider making it more specific.")
            property = {
                TYPE: ARRAY,
            }
        else:
            raise NotImplementedError(t)

        return property, definitions

    def schemeify(config: Type[Config]) -> dict:
        schema: dict = {
            TITLE: config.__name__,
            TYPE: OBJECT,
            PROPERTIES: {},
            DEFINITIONS: {},
        }
        for k in [k for k in config.__dict__.keys() if k[0] != '_']:  # todo: this is ugly :(
            t = resolve_type_to_most_specific(config.__annotations__[k])
            log.debug(f"{config.__qualname__} property '{k}' is a {t}")

            property, definitions = handle_type(t, config, k)

            if property is not None:
                schema[PROPERTIES][k] = property
            for k,v in definitions.items():
                schema[DEFINITIONS][k] = v
        return schema


    with open(
            os.path.join(
                os.path.dirname(__file__),
                'schemas', config.__name__ + '.json'
            ), 'w+') as f:
        json.dump(schemeify(config), f, indent=2)
