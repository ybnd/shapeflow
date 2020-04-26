import inspect
from inspect import _empty  # type: ignore
from typing import Union, Collection, Type, Callable, _GenericAlias  #type: ignore

import numpy as np
from schema import Optional, Schema, Or  #type: ignore

from isimple import get_logger, settings

from isimple.core.config import Config
from isimple.core import EnforcedStr
from isimple.maths.colors import HsvColor
from isimple.util.meta import nbases, all_attributes, all_annotations


log = get_logger(__name__)


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


def _type_to_schema(t, k=None) -> dict:  # todo: how to type t here?
    # todo: We're assuming everything is Optional here! This is NOT always the case for return annotations!
    if k is None:
        try:
            k = t.__qualname__
        except AttributeError:
            k = 'none'

    sk = Optional(k)

    if isinstance(t, _GenericAlias):  # todo: is there a way to check this without _GenericAlias?
        # Extract typing info
        if hasattr(t, '__origin__'):
            if t.__origin__ == tuple:
                if t.__args__[1] == Ellipsis:
                    return {
                        sk: [Schema(_schemify(t.__args__[0], k), name=k, as_reference=True)]
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
            sk: Schema(_schemify(t, k), name=k, as_reference=True),
        }
    elif t == HsvColor:
        return {
            sk: Schema({'h': float, 's': float, 'v': float})
        }
    elif t == str or t == int or t == float or t == bool:
        return {
            sk: t,
        }
    elif t == np.ndarray:  # Covers small numpy arrays; transform matrix, coordinates
        return {
            sk: str
        }
    elif issubclass(t, EnforcedStr):
        return {
            sk: Or(*t().options, 'default'),
        }
    elif t == tuple:
        log.warning(
            f"Property '{k}' is a {t.__qualname__}, "
            f"consider making it more specific.")
        return {
            sk: t,
        }
    elif t == _empty:
        return {
            sk: None,
        }
    else:
        return {
            sk: t,
        }


def _schemify(t: type, k: str = None) -> dict:
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
                        resolve_type_to_most_specific(at), a
                    )
                )
            return schema
        else:
            return _type_to_schema(t, k)
    except TypeError:
        return _type_to_schema(t, k)


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
                _type_to_schema(t, a)
            )
    return Schema(schema)


def get_return_schema(method: Callable) -> Schema:
    schema: dict = {'return': []}
    if inspect.signature(method).return_annotation is not None:
        for v in _type_to_schema(inspect.signature(method).return_annotation, 'return').values():
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


_d: dict = {}
for k,v in settings.to_dict().items():
    if isinstance(v, dict):
        _d[k] = {}
        for sk, sv in v.items():
            _d[k][sk] = type(sv)
    else:
        _d[k] = type(v)


settings_schema = Schema(_d).json_schema('settings.json')
