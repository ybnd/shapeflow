import warnings
from typing import Callable, Dict, List, Tuple, Type, FrozenSet, Optional, Any
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

    def __init__(self, signature: Type[Callable]):
        if not hasattr(signature, '__args__'):
            raise TypeError('Cannot define Endpoint without specifying argument and return type')
        super(RegistryEntry, self).__init__()
        self._signature = signature

    def isvalid(self, method: Callable) -> bool:
        if hasattr(method, '__annotations__'):
            args: List = []
            for arg in self._signature.__args__:
                if arg == type(None):
                    arg = None
                args.append(arg)
            return tuple(method.__annotations__.values()) == tuple(args)
        else:
            return False


class Registry(object):
    _entries: List[RegistryEntry]

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
    _entries = Tuple[RegistryEntry, ...]

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
    _callable_mapping: Dict[Endpoint, Callable]

    def __init__(self):
        super(EndpointRegistry, self).__init__()
        self._callable_mapping = {}

    def expose(self, endpoint: Endpoint):
        def wrapper(method):
            if endpoint in self._callable_mapping:
                warnings.warn(
                    f"{self}: '{method.__name__}' @ '{endpoint._name}' will override "
                    f"previously exposed method '{self._callable_mapping[endpoint].__name__}'."
                )
            if endpoint.isvalid(method):
                self._callable_mapping.update({endpoint: method})
                self._add_entry(endpoint)
            else:
                raise TypeError(
                    f"Cannot expose '{method.__name__}' @ '{endpoint._name}'."
                    f"incompatible signature: {method.__annotations__} vs. {endpoint._signature.__args__}"
                )
            return method
        return wrapper

    def exposes(self, endpoint: Endpoint):
        return endpoint in self._callable_mapping

    def endpoints(self) -> List[Endpoint]:
        return list(self._callable_mapping.keys())

# todo: everything below belongs in a separate file specifically for the video analysis case, everything above is generic


class ApplicationEndpointRegistry(ImmutableRegistry):  # todo: confusing naming
    get_raw_frame = Endpoint(Callable[[int], Optional[np.ndarray]])
    estimate_transform = Endpoint(Callable[[List], None])
    set_filter_from_color = Endpoint(Callable[[List], None])
    get_transformed_frame = Endpoint(Callable[[int], np.ndarray])
    get_transformed_overlaid_frame = Endpoint(Callable[[int], np.ndarray])

endpoints = ApplicationEndpointRegistry()
