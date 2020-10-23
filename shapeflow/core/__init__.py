import abc
import threading
from typing import Callable, Dict, List, Tuple, Type, Optional, _GenericAlias, Any  # type: ignore
import collections
from contextlib import contextmanager

import uuid

from shapeflow import get_logger
from shapeflow.util.meta import all_attributes, get_overridden_methods, bind


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


class EnforcedStr(str):
    _options: List[str] = ['']
    _descriptions: Dict[str, str] = {}
    _str: str

    _default: Optional[str] = None

    def __init__(self, string: str = None):
        super().__init__()
        if string is not None:
            if string not in self.options:
                if string:
                    log.warning(f"Illegal {self.__class__.__name__} '{string}', "
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
        if self._default is not None:
            return self._default
        else:
            return self._options[0]

    @classmethod
    def set_default(cls, value: 'EnforcedStr'):
        if isinstance(value, cls) and value in cls().options:
            log.debug(f"setting default of '{cls.__name__}' to '{value}'")
            cls._default = value
        else:
            raise ValueError(
                f"cannot set default of '{cls.__name__}' to '{value}'"
            )

    def __hash__(self):  # todo: why?
        return hash(str(self))

    @classmethod
    def __modify_schema__(cls, field_schema):
        # pydantic
        temp = cls()
        field_schema.update(
            enum=temp.options,
            default=temp.default,
            descriptions=temp.descriptions
        )


class _Streaming(EnforcedStr):
    _options = ['off', 'image', 'json', 'plain']


stream_off = _Streaming('off')
stream_image = _Streaming('image')
stream_json = _Streaming('json')
stream_plain = _Streaming('plain')


class Endpoint(object):
    _name: str
    _registered: bool
    _signature: Type[Callable]
    _method: Optional[Callable]
    _streaming: _Streaming
    _update: Callable[['Endpoint'], None]

    def __init__(self, signature: _GenericAlias, streaming: _Streaming = stream_off):  # todo: type Callable[] correctly
        assert signature.__origin__ == collections.abc.Callable

        self._method = None
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

    def expose(self):
        """ Expose the endpoint """
        def wrapper(method):
            if self._method is not None:
                log.debug(  # todo: add traceback
                    f"Exposing '{method.__qualname__}' at endpoint '{self.name}' will override "
                    f"previously exposed method '{self._method.__qualname__}'."
                )  # todo: keep in mind we're also marking the methods themselves

            if not self.compatible(method):
                raise TypeError(
                    f"Cannot expose '{method.__qualname__}' at endpoint '{self.name}'. "
                    f"Incompatible signature: {method.__annotations__} vs. {self.signature}"
                )

            method._endpoint = self
            self._method = method
            try:
                self._update(self)
            except AttributeError:
                pass

            return method
        return wrapper

    @property
    def method(self) -> Optional[Callable]:
        return self._method

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
        try:
            return self._name
        except AttributeError:
            return ''

    def register(self, name: str, callback: Callable[['Endpoint'], None]):
        self._registered = True
        self._name = name
        self._update = callback


class Dispatcher(object):  # todo: these should also register specific instances & handle dispatching?
    _endpoints: Tuple[Endpoint, ...]  #type: ignore
    _dispatchers: Tuple['Dispatcher']

    _name: str
    _parent: Optional['Dispatcher']
    _address_space: Dict[str, Callable]

    _update: Callable[['Dispatcher'], None]

    _instance: Optional[object]

    def __init__(self, instance: object = None):
        if instance is not None:
            self._set_instance(instance)
        else:
            self._address_space = {}
            self._endpoints = tuple()
            self._dispatchers = tuple()

    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            return self.__class__.__name__

    @property
    def dispatchers(self) -> Tuple['Dispatcher']:
        return self._dispatchers

    @property
    def endpoints(self) -> Tuple[Endpoint]:
        return self._endpoints

    @property
    def address_space(self) -> Dict[str, Callable]:
        return self._address_space

    def _set_instance(self, instance: object):
        self._instance = instance
        self._address_space = {}
        self._endpoints = tuple()
        self._dispatchers = tuple()

        for attr, val in self.__class__.__dict__.items():
            if isinstance(val, Endpoint):  # todo: also register dispatchers
                self._add_endpoint(attr, val)
            elif isinstance(val, Dispatcher):
                self._add_dispatcher(attr, val)

    def _register(self, name: str, callback: Callable[['Dispatcher'], None]):
        self._update = callback
        self._name = name

    def _add_endpoint(self, name: str, endpoint: Endpoint):
        endpoint.register(name=name, callback=self._update_endpoint)

        if endpoint.method is not None and self._instance is not None:
            method = bind(self._instance, endpoint.method)
        else:
            method = endpoint.method

        self._address_space[name] = method
        self._endpoints = tuple(list(self._endpoints) + [endpoint])
        setattr(self, name, endpoint)

    def _add_dispatcher(self, name: str, dispatcher: 'Dispatcher'):
        dispatcher._register(name=name, callback=self._update_dispatcher)

        self._address_space.update({
            "/".join([name, address]): method
            for address, method in dispatcher.address_space.items()
            if method is not None and "__" not in address
        })
        self._dispatchers = tuple(list(self._dispatchers) + [dispatcher])
        setattr(self, name, dispatcher)

    def _update_endpoint(self, endpoint: Endpoint) -> None:
        self._address_space.update({
            endpoint.name: endpoint.method
        })
        try:
            self._update(self)
        except AttributeError:
            pass

    def _update_dispatcher(self, dispatcher: 'Dispatcher') -> None:
        self._address_space.update({  # todo: this doesn't take into account deleted keys!
            "/".join([dispatcher.name, address]): method
            for address, method in dispatcher.address_space.items()
            if method is not None and "__" not in address
        })
        try:
            self._update(self)
        except AttributeError:
            pass

    def dispatch(self, address: str, *args, **kwargs) -> Any:
        try:
            method = self.address_space[address]
            # todo: consider doing some type checking here, args/kwargs vs. method._endpoint.signature
            return method(*args, **kwargs)
        except KeyError:
            log.warning(f"'{self.name}' can't dispatch address {address}.")

    def __getitem__(self, item):
        return getattr(self, item)


class Described(object):  # todo: maybe this should be a metaclass?
    """..."""

    @classmethod
    def _description(cls):
        if cls.__doc__ is not None:
            return cls.__doc__.split('\n')[0]
        else:
            return cls.__name__


class Lockable(object):
    _lock: threading.Lock
    _cancel: threading.Event
    _error: threading.Event

    """Wrapper around threading.Lock & threading.Event    
    Doesn't need to __init__(); lock & events are created when they're needed.
    """

    @property
    def _ensure_lock(self) -> threading.Lock:
        try:
            return self._lock
        except AttributeError:
            self._lock = threading.Lock()
            return self._lock

    @property
    def _ensure_cancel(self) -> threading.Event:
        try:
            return self._cancel
        except AttributeError:
            self._cancel = threading.Event()
            return self._cancel

    @property
    def _ensure_error(self) -> threading.Event:
        try:
            return self._error
        except AttributeError:
            self._error = threading.Event()
            return self._error

    @contextmanager
    def lock(self):
        log.vdebug(f"Acquiring lock {self}...")
        locked = self._ensure_lock.acquire()
        original_lock = self._lock
        log.vdebug(f"Acquired lock {self}")
        try:
            log.vdebug(f"Locking {self}")
            yield locked
        finally:
            log.vdebug(f"Unlocking {self}")
            # Make 'sure' nothing weird happened to self._lock
            assert self._lock == original_lock
            self._lock.release()

    def cancel(self):
        self._ensure_cancel.set()

    def error(self):
        self._ensure_error.set()

    @property
    def canceled(self) -> bool:
        return self._ensure_cancel.is_set()

    @property
    def errored(self) -> bool:
        return self._ensure_error.is_set()

    def clear_cancel(self):
        return self._ensure_cancel.clear()

    def clear_error(self):
        return self._ensure_error.clear()


class RootInstance(Lockable):  # todo: basically deprecated
    _id: str

    def _set_id(self, id: str):
        self._id = id

    @property
    def id(self):
        return self._id