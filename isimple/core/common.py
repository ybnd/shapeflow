import warnings
from typing import Callable, Dict, List, Tuple, Type, Optional
import numpy as np
import abc

from isimple.core.util import all_attributes, get_overridden_methods, timing


class RootException(Exception):
    msg = ''
    def __init__(self, *args):
        #https://stackoverflow.com/questions/49224770/
        # if no arguments are passed set the first positional argument
        # to be the default message. To do that, we have to replace the
        # 'args' tuple with another one, that will only contain the message.
        # (we cannot do an assignment since tuples are immutable)
        if not (args):
            args = (self.msg,)

        # Call super constructor
        super(Exception, self).__init__(*args)


class SetupError(RootException):
    pass


class RegistryEntry(abc.ABC):  # todo: shouldn't allow instances
    _name: str
    _registered: bool

    def __init__(self):
        self._registered = False

    def register(self, name: str):
        self._registered = True
        self._name = name

    @property
    def registered(self):
        return self._registered


class Endpoint(RegistryEntry):
    _signature: Type[Callable]

    def __init__(self, signature: Type[Callable]):
        if not hasattr(signature, '__args__'):
            raise TypeError('Cannot define an Endpoint without a signature!')
        super(RegistryEntry, self).__init__()
        self._signature = signature

    def compatible(self, method: Callable) -> bool:
        if hasattr(method, '__annotations__'):
            args: List = []
            for arg in self.signature:
                if arg == type(None):
                    arg = None
                args.append(arg)
            # Don't be stringent with unannotated None-type return
            return tuple(method.__annotations__.values()) == tuple(args)
        else:
            return False

    @property
    def signature(self):
        return self._signature.__args__

    def add(self, method):
        if not self.compatible(method):
            raise ValueError(f"Method '{method.__qualname__}' "
                             f"is incompatible with endpoint '{self._name}'. \n"
                             f"{method.__annotations__} vs. {self.signature}")  # todo: traceback to


class Registry(object):     # todo: make these three into a single EndpointRegistry class if possible
    _entries: List

    def __init__(self):
        if not hasattr(self, '_entries'):
            _entries = []
            for attr, val in self.__class__.__dict__.items():
                if isinstance(val, RegistryEntry):
                    val.register(attr)
                    _entries.append(val)
            self._entries = _entries

    def _add_entry(self, entry: RegistryEntry):
        self._entries.append(entry)


class EndpointRegistry(Registry):  # todo: confusing names :)
    """This one is global, collects callables that expose endpoints
    """
    _entries: List[Endpoint]
    _callable_mapping: Dict[Endpoint, Callable]

    def __init__(self):
        super(EndpointRegistry, self).__init__()
        self._callable_mapping = {}

    def expose(self, endpoint: Endpoint):
        def wrapper(method):
            if endpoint in self._callable_mapping:
                warnings.warn(   # todo: add traceback
                    f"Exposing '{method.__qualname__}' at endpoint '{endpoint._name}' will override "
                    f"previously exposed method '{self._callable_mapping[endpoint].__qualname__}'."
                )  # todo: keep in mind we're also marking the methods themselves
            try:
                self._entries.append(endpoint)
                endpoint.add(method)
                method._endpoint = endpoint
                self._callable_mapping.update({endpoint: method})
            except TypeError:
                raise TypeError(
                    f"Cannot expose '{method.__qualname__}' at endpoint '{endpoint._name}'."
                    f"incompatible signature: {method.__annotations__} vs. {endpoint.signature}"
                )
            return method
        return wrapper

    def exposes(self, endpoint: Endpoint):
        return endpoint in self._callable_mapping

    @property
    def endpoints(self) -> List[Endpoint]:
        return list(self._callable_mapping.keys())


class ImmutableRegistry(Registry):  # todo: confusing naming scheme
    _entries: Tuple[RegistryEntry, ...]  #type: ignore
    _endpoints: EndpointRegistry            # todo: also very confusing wrapping situation

    def __init__(self, endpoints: EndpointRegistry = None):
        _entries = []
        for attr, val in self.__class__.__dict__.items():
            if isinstance(val, RegistryEntry):
                val.register(attr)
                _entries.append(val)

        if endpoints is not None:
            self._endpoints = endpoints
        else:
            self._endpoints = EndpointRegistry()

        self._entries = tuple(_entries)
        super(ImmutableRegistry, self).__init__()

    def _add_entry(self, entry: RegistryEntry):
        raise NotImplementedError

    def expose(self, endpoint: Endpoint):
        return self._endpoints.expose(endpoint)

    def exposes(self, endpoint: Endpoint):
        return self._endpoints.exposes(endpoint)

    @property
    def endpoints(self) -> List[Endpoint]:
        return self._endpoints.endpoints



class Manager(object):
    _endpoints: ImmutableRegistry
    _instances: List
    _instance_class = object
    _instance_mapping: Dict[Endpoint, List[Callable]]


    def connect(self, manager):
        raise NotImplementedError

    @timing
    def _gather_instances(self):  # todo: needs major clean-up
        self._instance_mapping = {}
        instances = []
        attributes = [attr for attr in self.__dir__() if attr[0:2] != '__']  # using iterator doubles count as _instances is also an attribute

        for attr in sorted(attributes):
            value = getattr(self, attr)

            if isinstance(value, self._instance_class) and not isinstance(value, list):
                instances.append(value)
            elif isinstance(value, list) and all(isinstance(v, self._instance_class) for v in value):
                instances += list(value)
            elif isinstance(value, dict) and all(isinstance(v, self._instance_class) for v in value.values()):
                instances += [v for v in value.values()]

        for instance in [self] + instances:
            self._add_instance(instance)

        for k,v in self._instance_mapping.items():
            self._instance_mapping[k] = list(set(v))  # todo: eliminate this!

        self._instances = instances

    def _add_instance(self, instance: object):
        if isinstance(instance, self._instance_class):
            for attr in [attr for attr in all_attributes(instance)]:
                value = getattr(instance, attr)  # bound method

                if hasattr(value, '__func__'):
                    implementations = get_overridden_methods(instance.__class__, getattr(instance.__class__, attr))

                    endpoint = None
                    for implementation in implementations:  # unbound methods
                        try:
                            endpoint = implementation._endpoint  # todo: won't catch endpoints defined at multiple placec in the methods inheritance tree
                        except AttributeError:
                            pass

                    if endpoint is not None:
                        if endpoint not in self._instance_mapping:
                            self._instance_mapping[endpoint] = [value]
                        else:
                            if value not in self._instance_mapping[endpoint]:
                                self._instance_mapping[endpoint].append(value)

            for k, v in self._instance_mapping.items():
                self._instance_mapping[k] = list(set(v))  # todo: eliminate this!
        else:
            pass

    def get(self, endpoint: Endpoint, index: int = None) -> Callable:
        if endpoint not in self._endpoints._entries:  # todo: oh god save me from this hell
            raise SetupError(f"'{endpoint}' is not defined in '{self._endpoints}'.")
        elif endpoint not in self._instance_mapping:
            raise SetupError(f"'{self.__class__.__name__}' does not map "
                             f"'{endpoint._name}' to a bound method.")
        else:
            if index is None:
                index = 0
                if index >= len(self._instance_mapping[endpoint]):
                    warnings.warn(f"No index specified for endpoint '{endpoint._name}' "
                                  f"-- defaulting to entry 0 ({len(self._instance_mapping[endpoint])} in total)")  # todo: traceback

            return self._instance_mapping[endpoint][index]

