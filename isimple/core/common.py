import warnings
from typing import Callable, Dict, List, Tuple, Type, Optional
import numpy as np
import abc


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
    _methods: List[Callable]

    def __init__(self, signature: Type[Callable]):
        if not hasattr(signature, '__args__'):
            raise TypeError('Cannot define Endpoint without specifying argument and return type')
        super(RegistryEntry, self).__init__()
        self._signature = signature
        self._methods = []

    def compatible(self, method: Callable) -> bool:
        if hasattr(method, '__annotations__'):
            args: List = []
            for arg in self.signature:
                if arg == type(None):
                    arg = None
                args.append(arg)
            return tuple(method.__annotations__.values()) == tuple(args)
        else:
            return False

    @property
    def signature(self):
        return self._signature.__args__

    def add(self, method):
        if self.compatible(method):
            self._methods.append(method)
        else:
            warnings.warn(f"Tried to add an incompatible method to endpoint")


class Registry(object):
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


class ImmutableRegistry(Registry):
    _entries: Tuple[RegistryEntry, ...]  #type: ignore

    def __init__(self):
        _entries = []
        for attr, val in self.__class__.__dict__.items():
            if isinstance(val, RegistryEntry):
                val.register(attr)
                _entries.append(val)

        self._entries = tuple(_entries)
        super(ImmutableRegistry, self).__init__()

    def _add_entry(self, entry: RegistryEntry):
        raise NotImplementedError


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
                    f"{self}: '{method.__name__}' @ '{endpoint._name}' will override "
                    f"previously exposed method '{self._callable_mapping[endpoint].__name__}'."
                )  # todo: keep in mind we're also marking the methods themselves
            try:
                self._entries.append(endpoint)
                endpoint.add(method)
                method._endpoint = endpoint
                self._callable_mapping.update({endpoint: method})
            except TypeError:
                raise TypeError(
                    f"Cannot expose '{method.__name__}' @ '{endpoint._name}'."
                    f"incompatible signature: {method.__annotations__} vs. {endpoint.signature}"
                )
            return method
        return wrapper

    def exposes(self, endpoint: Endpoint):
        return endpoint in self._callable_mapping

    def endpoints(self) -> List[Endpoint]:
        return list(self._callable_mapping.keys())


class InstanceRegistry(Registry):
    """This one is local, interfaces with the global registry
    """
    _endpoint_registry: EndpointRegistry

    def __init__(self, endpoint_registry):
        super(InstanceRegistry, self).__init__()
        self._endpoint_registry = endpoint_registry

    def _add_instance(self, instance):
        if instance not in self._entries:
            self._entries.append(instance)  # todo: if this is global for all children of something-something, this shit breaks down as soon as we've got multiples active?
                                            # todo: i.e. the first way I tried doing this was the right way after all? ugh...
    def expose(self, endpoint: Endpoint):
        return self._endpoint_registry.expose(endpoint)


class Manager(object):
    _instances: List
    _instance_class = object

    def _gather_instances(self):  # todo: how to handle nested instances?
        self._instances = []

        for attr in self.__dict__:
            value = getattr(self, attr)
            if isinstance(value, self._instance_class):
                self._instances.append(getattr(self, attr))
            elif isinstance(value, list) and all(isinstance(v, self._instance_class) for v in value):  # todo: be more general than list
                self._instances += list(value)
