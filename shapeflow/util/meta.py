"""Metaprogramming utility functions.
"""

from typing import List, Union


def describe_function(f: Callable) -> str:
    """Return a function description.
    More specific than regular old ``__qualname__``.

    .. note::
        For nested functions, ``__qualname__`` contains ``<locals>``.
        ``diskcache.Cache`` can write keys containing ``<`` or ``>`` but
        crashes when trying to read these back. To prevent weird bugs,
        ``<`` and ``>`` are replaced with ``_``

    Parameters
    ----------
    f: Callable
        Any function or method

    Returns
    -------
    str
        A unique
    """
    """ 
    """
    return f"{f.__module__}." \
           f"{f.__qualname__.replace('<', '_').replace('>', '_')}"


def bases(c: type) -> List[type]:
    """Returns the bases of a class, including the bases of its bases.

    .. note::
        Just in general, don't do ``list(set())`` if the order is important!

    Parameters
    ----------
    c: type
        Any class

    Returns
    -------
    List[type]
        A list of all bases of ``c``
    """
    """ 
    """
    def _bases(c) -> List[type]:
        bases = list(c.__bases__)
        for b in bases:
            for bb in _bases(b):
                if bb not in bases:
                    bases.append(bb)
        return bases

    return _bases(c)[::-1]


def unbind(m):
    """Unbind a method from its instance.

    Parameters
    ----------
    m
        Any method

    Returns
    -------
    The method ``m``, not bound to any instance
    """
    try:
        return m.__func__
    except AttributeError:
        return m


def bind(instance, m):
    """Bind a method to an instance.

    https://stackoverflow.com/a/1015405/12259362

    Parameters
    ----------
    instance
        An object
    m
        Any bound or unbound method of the class of ``instance``

    Returns
    -------
    Callable
        The method ``m``, bound to ``instance``
    """

    bound_method = m.__get__(instance, instance.__class__)
    setattr(instance, m.__name__, bound_method)
    return bound_method
