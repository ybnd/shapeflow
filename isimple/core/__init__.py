import abc
import threading
from typing import Callable, Dict, List, Tuple, Type, _GenericAlias  # type: ignore
import collections
from contextlib import contextmanager

import uuid

from isimple import get_logger
from isimple.util.meta import all_attributes, get_overridden_methods


log = get_logger(__name__)


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

        super(Exception, self).__init__(*args)


class SetupError(RootException):
    pass


class EnforcedStr(str):  # todo: should derive from enum.StrEnum instead
    _options: List[str] = ['']
    _descriptions: Dict[str, str] = {}
    _str: str

    def __init__(self, string: str = None):
        super().__init__()
        if string is not None:
            if string not in self.options:
                if string:
                    log.debug(f"Illegal {self.__class__.__name__} '{string}', "
                                  f"should be one of {self.options}. "
                                  f"Defaulting to '{self.default}'.")
                self._str = str(self.default)
            else:
                self._str = str(string)
        else:
            self._str = str(self.default)

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self._str}'>"

    def __str__(self):
        return str(self._str)  # Make SURE it's a string :(

    def __eq__(self, other):
        if hasattr(other, '_str'):
            return self._str == other._str
        elif isinstance(other, str):
            return self._str == other
        else:
            return False

    @property
    def options(self):
        return self._options

    @property
    def descriptions(self):
        return self._descriptions

    @property
    def describe(self):
        return self.descriptions[self._str]

    @property
    def default(self):
        return self._options[0]

    def __hash__(self):  # todo: why?
        return hash(str(self))


class _Streaming(EnforcedStr):
    _options = ['off', 'image', 'json']


stream_off = _Streaming('off')
stream_image = _Streaming('image')
stream_json = _Streaming('json')

class Endpoint(object):
    _name: str
    _registered: bool
    _signature: Type[Callable]
    _streaming: _Streaming

    def __init__(self, signature: _GenericAlias, streaming: _Streaming = stream_off):  # todo: type Callable[] correctly
        assert signature.__origin__ == collections.abc.Callable

        self._registered = False
        if not hasattr(signature, '__args__'):
            raise SetupError('Cannot define an Endpoint without a signature!')
        self._signature = signature
        self._streaming = streaming

    def compatible(self, method: Callable) -> bool:
        if hasattr(method, '__annotations__'):
            args: List = []
            for arg in self.signature:
                if arg == type(None):
                    arg = None
                args.append(arg)
            # Don't be too pedantic unannotated None-type return
            return tuple(method.__annotations__.values()) == tuple(args)
        else:
            return False

    @property
    def signature(self):
        return self._signature.__args__

    @property
    def streaming(self):
        return self._streaming

    @property
    def registered(self):
        return self._registered

    @property
    def name(self):
        return self._name

    def add(self, method):
        if not self.compatible(method):
            log.warning(f"Method '{method.__qualname__}' "
                             f"is incompatible with endpoint '{self.name}'. \n"
                             f"{method.__annotations__} vs. {self.signature}")

    def register(self, name: str):
        self._registered = True
        self._name = name


class EndpointRegistry(object):
    _entries: List

    def __init__(self):
        if not hasattr(self, '_entries'):
            _entries = []
            for attr, val in self.__class__.__dict__.items():
                if isinstance(val, Endpoint):
                    val.register(attr)
                    _entries.append(val)
            self._entries = _entries

    def _add_entry(self, entry: Endpoint):
        self._entries.append(entry)


class InstanceRegistry(EndpointRegistry):
    """This one is global, collects callables that expose endpoints
    """
    _entries: List[Endpoint]
    _callable_mapping: Dict[Endpoint, Callable]

    def __init__(self):
        super(InstanceRegistry, self).__init__()
        self._callable_mapping = {}

    def expose(self, endpoint: Endpoint):
        def wrapper(method):
            if endpoint in self._callable_mapping:
                log.debug(   # todo: add traceback
                    f"Exposing '{method.__qualname__}' at endpoint '{endpoint.name}' will override "
                    f"previously exposed method '{self._callable_mapping[endpoint].__qualname__}'."
                )  # todo: keep in mind we're also marking the methods themselves
            try:
                self._entries.append(endpoint)
                endpoint.add(method)
                try:
                    method._endpoint = endpoint
                except AttributeError:
                    method.__func__._endpoint = endpoint
                self._callable_mapping.update({endpoint: method})
            except TypeError:
                raise TypeError(
                    f"Cannot expose '{method.__qualname__}' at endpoint '{endpoint.name}'."
                    f"incompatible signature: {method.__annotations__} vs. {endpoint.signature}"
                )
            return method
        return wrapper

    def exposes(self, endpoint: Endpoint):
        return endpoint in self._callable_mapping

    @property
    def endpoints(self) -> List[Endpoint]:
        return list(self._callable_mapping.keys())


class ImmutableRegistry(EndpointRegistry):
    _entries: Tuple[Endpoint, ...]  #type: ignore
    _endpoints: InstanceRegistry

    def __init__(self, endpoints: InstanceRegistry = None):
        _entries = []
        for attr, val in self.__class__.__dict__.items():
            if isinstance(val, Endpoint):
                val.register(attr)
                _entries.append(val)

        if endpoints is not None:
            self._endpoints = endpoints
        else:
            self._endpoints = InstanceRegistry()

        self._entries = tuple(_entries)
        super(ImmutableRegistry, self).__init__()

    def _add_entry(self, entry: Endpoint):
        raise NotImplementedError

    def expose(self, endpoint: Endpoint):
        return self._endpoints.expose(endpoint)

    def exposes(self, endpoint: Endpoint):
        return self._endpoints.exposes(endpoint)

    @property
    def endpoints(self) -> List[Endpoint]:
        return self._endpoints.endpoints


class Lockable(abc.ABC):
    _lock: threading.Lock
    _cancel: threading.Event

    def __init__(self):
        self._lock = threading.Lock()
        self._cancel = threading.Event()

    @contextmanager
    def lock(self):
        log.vdebug(f"Acquiring lock {self}...")
        lock = self._lock.acquire()
        log.vdebug(f"Acquired lock {self}")
        try:
            log.vdebug(f"Locking {self}")
            yield lock
        finally:
            log.vdebug(f"Unlocking {self}")
            self._lock.release()

    def cancel(self):
        self._cancel.set()

    def clear(self):  # todo: wording
        self._cancel.clear()


class RootInstance(Lockable):
    _id: str

    _endpoints: ImmutableRegistry
    _instances: List
    _instance_class: type
    _instance_mapping: Dict[Endpoint, List[Callable]]

    def __init__(self):
        super().__init__()
        self.get_id()

    def get_id(self):
        self._id = str(uuid.uuid1())

    def _set_id(self, id: str):
        self._id = id

    @property
    def id(self):
        return self._id

    @property
    def instance_mapping(self):
        return self._instance_mapping

    def _gather_instances(self):  # todo: needs major clean-up
        log.debug(f'{self.__class__.__name__}: gather nested instances')
        self._instance_mapping = {}
        instances = []
        attributes = [attr for attr in self.__dir__()]   # todo: all_attributes fails here because that's ~ class!

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

        self._instances = instances

    def _add_instance(self, instance: object):
        if isinstance(instance, self._instance_class):
            for attr in [attr for attr in all_attributes(instance)]:
                value = getattr(instance, attr)  # bound method

                if hasattr(value, '__func__'):
                    endpoint = None
                    implementations = get_overridden_methods(instance.__class__, getattr(instance.__class__, attr))

                    # Returns an empty list for wrapped methods -> workaround
                    if len(implementations) == 0:
                        endpoint = value._endpoint
                        # todo: there will probably be some bugs with inheritance & wrapping

                    for implementation in implementations:  # unbound methods
                        try:
                            endpoint = implementation._endpoint  # todo: won't catch endpoints defined at multiple places in the methods inheritance tree
                        except AttributeError:
                            pass

                    if endpoint is not None:
                        if endpoint not in self._instance_mapping:
                            self._instance_mapping[endpoint] = [value]
                        else:
                            if value not in self._instance_mapping[endpoint]:
                                self._instance_mapping[endpoint].append(value)

        else:
            pass

    def get(self, endpoint: Endpoint, index: int = None) -> Callable:
        if endpoint not in self._endpoints._entries:
            raise SetupError(f"'{endpoint}' is not defined in '{self._endpoints}'.")
        elif endpoint not in self._instance_mapping:
            raise SetupError(f"'{self.__class__.__name__}' does not map "
                             f"'{endpoint.name}' to a bound method.")
        else:
            log.vdebug(f"{self.__class__.__name__}: get callback for "
                     f"endpoint '{endpoint.name}' with index {index}")
            methods = self._instance_mapping[endpoint]
            if index is None:
                index = 0
                if index+1 < len(methods):
                    log.vdebug(f"No index specified for endpoint '{endpoint.name}' "
                                  f"-- defaulting to entry 0 ({len(methods)} in total)")  # todo: traceback
            elif len(methods) == 1:
                index = 0  # Ignore the index if only one method is mapped
            return self._instance_mapping[endpoint][index]
