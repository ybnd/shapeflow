import inspect
import json
from inspect import _empty  # type: ignore
from typing import Union, Collection, Type, Callable, _GenericAlias, Optional  # type: ignore

import numpy as np
from schema import Optional as scOptional
from schema import Schema

from isimple.core.config import Config, EnforcedStr, HsvColor
from isimple.core.util import nbases, log, all_annotations, all_attributes


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
    # todo: We're assuming everything is Optional here! This is NOT always the case for return annotations!
    if container is None:
        container = t
    if k is None:
        try:
            k = t.__qualname__
        except AttributeError:
            k = 'none'

    sk = scOptional(k)

    print(t)

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
    elif t == HsvColor:
        return {
            sk: Schema({'h': float, 's': float, 'v': float})
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
    try:
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
            return schema
        else:
            return _type_to_schema(t, t, t)
    except TypeError:
        return _type_to_schema(t, t, t)


def get_config_schema(config: Type[Config]) -> Schema:
    return Schema(_schemify(config))


def get_method_schema(method: Callable) -> Schema:
    schema = {}
    for a,p in inspect.signature(method).parameters.items():
        t = p.annotation

        if t is _empty:
            raise TypeError(f"Can not generate schema for method {method.__qualname__}; "
                            f"the type of argument '{a}' is not annotated.")
        else:
            schema.update(
                _type_to_schema(t, method, a)
            )
    return Schema(schema)


def get_return_schema(method: Callable) -> Schema:
    schema: dict = {'return': []}
    if inspect.signature(method).return_annotation is not None:
        for v in _type_to_schema(inspect.signature(method).return_annotation, method, 'return').values():
            schema['return'].append(v)
        return Schema(schema)
    else:
        return Schema({})


def schema(obj) -> dict:
    id = obj.__qualname__ + '.json'
    try:
        if issubclass(obj, Config):
            return get_config_schema(obj).json_schema(id)
        else:
            raise TypeError
    except TypeError:
        return {
            'call': get_method_schema(obj).json_schema(id),
            'return': get_return_schema(obj).json_schema(id)
        }

