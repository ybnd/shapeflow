from typing import Callable, Dict, List, Tuple, Type

from isimple.core.util import all_attributes, get_overridden_methods
from isimple.core.log import get_logger


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


class Endpoint(object):
    _name: str
    _registered: bool
    _signature: Type[Callable]

    def __init__(self, signature: Type[Callable]):
        self._registered = False
        if not hasattr(signature, '__args__'):
            raise SetupError('Cannot define an Endpoint without a signature!')
        self._signature = signature

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
    def registered(self):
        return self._registered

    def add(self, method):
        if not self.compatible(method):
            raise ValueError(f"Method '{method.__qualname__}' "
                             f"is incompatible with endpoint '{self._name}'. \n"
                             f"{method.__annotations__} vs. {self.signature}")  # todo: traceback to

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
                    f"Exposing '{method.__qualname__}' at endpoint '{endpoint._name}' will override "
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



class RootInstance(object):
    _endpoints: ImmutableRegistry
    _instances: List
    _instance_class = object
    _instance_mapping: Dict[Endpoint, List[Callable]]

    def connect(self, manager):
        raise NotImplementedError

    def _gather_instances(self):  # todo: needs major clean-up
        log.debug(f'{self.__class__.__name__}: gather nested instances')
        self._instance_mapping = {}
        instances = []
        attributes = [attr for attr in self.__dir__() if attr[0] != '_']   # todo: all_attributes fails here because that's ~ class!

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
            for attr in [attr for attr in all_attributes(instance, include_under=True, include_methods=True)]:
                value = getattr(instance, attr)  # bound method

                if hasattr(value, '__func__'):
                    implementations = get_overridden_methods(instance.__class__, getattr(instance.__class__, attr))

                    endpoint = None
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
                             f"'{endpoint._name}' to a bound method.")
        else:
            log.vdebug(f"{self.__class__.__name__}: get callback for "
                     f"endpoint '{endpoint._name}' with index {index}")
            methods = self._instance_mapping[endpoint]
            if index is None:
                index = 0
                if index+1 < len(methods):
                    log.vdebug(f"No index specified for endpoint '{endpoint._name}' "
                                  f"-- defaulting to entry 0 ({len(methods)} in total)")  # todo: traceback
            elif len(methods) == 1:
                index = 0  # Ignore the index if only one method is mapped
            return self._instance_mapping[endpoint][index]
