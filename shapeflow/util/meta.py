import inspect
from typing import List, Union, Dict, Any, Collection, _GenericAlias  # type: ignore


def describe_function(f):
    """ Returns a function description.
        Note: __qualname__ may contain `<locals>`
              diskcache can write but not read (!!!) keys containing < or >.
    """
    return f"{f.__module__}." \
           f"{f.__qualname__.replace('<', '_').replace('>', '_')}"


def bases(c: type) -> list:
    """ Returns the bases of a class, including the bases of its bases.
        Note: don't use list(set()) if the order is important!
    """
    def _bases(c) -> list:
        bases = list(c.__bases__)
        for b in bases:
            for bb in _bases(b):
                if bb not in bases:
                    bases.append(bb)
        return bases

    return _bases(c)[::-1]


def all_attributes(
        t: Union[object, type],
        include_under: bool = True,
        include_methods: bool = True,
        include_mro: bool = False,
) -> List[str]:
    if not isinstance(t, type):
        t = t.__class__

    attributes: list = []
    for base in [t] + bases(t):
        attributes += base.__dict__

    return list(filter(lambda a: a[0:3] != 'mro', set(attributes)))


def get_overridden_methods(c, m) -> list:
    b = [c] + bases(c)
    implementations = []
    for base in b:
        if m.__name__ in base.__dict__:
            implementations.append(getattr(base, m.__name__))

    return implementations


def unbind(m):
    try:
        return m.__func__
    except AttributeError:
        return m


def bind(instance, func):
    # https://stackoverflow.com/a/1015405/12259362
    bound_method = func.__get__(instance, instance.__class__)
    setattr(instance, func.__name__, bound_method)
    return bound_method


def separate(m):
    assert hasattr(m, '__self__')
    return m.__self__, unbind(m)
