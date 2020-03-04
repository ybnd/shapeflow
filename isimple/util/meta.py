import inspect
from typing import List, Union, Dict, Any


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
