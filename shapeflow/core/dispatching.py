import collections
from typing import Type, Callable, Optional, List, Tuple, Dict, Any, _GenericAlias

from shapeflow.core.logging import get_logger, RootException
from shapeflow.core.streaming import Stream
from shapeflow.util.meta import bind


log = get_logger(__name__)


class DispatchingError(RootException):
    """An error dispatching a method call or exposing an endpoint.
    """


class Endpoint(object):
    """An endpoint for an internal method.
    """
    _name: str
    _registered: bool
    _signature: Type[Callable]
    _method: Optional[Callable]
    _streaming: Stream
    _update: Optional[Callable[['Endpoint'], None]]

    def __init__(self, signature: _GenericAlias, streaming: Stream = Stream.off):  # todo: type Callable[] correctly
        try:
            assert signature.__origin__ == collections.abc.Callable
            assert hasattr(signature, '__args__')
        except Exception:
            raise TypeError('Invalid Endpoint signature')

        self._method = None
        self._update = None
        self._registered = False
        self._signature = signature
        self._streaming = streaming

    def compatible(self, method: Callable) -> bool:
        """Checks whether a method is compatible with the endpoint's signature

        Parameters
        ----------
        method : Callable
            Any method or function

        Returns
        -------
        bool
            ``True`` if the method is compatible, ``False`` if it isn't.
        """
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
        """ Expose a method at this endpoint.
        Used as a decorator::
            @endpoint.expose()
            def some_method():
                pass
        """
        def wrapper(method):
            if self._method is not None:
                log.debug(  # todo: add traceback
                    f"Exposing '{method.__qualname__}' at endpoint '{self.name}' will override "
                    f"previously exposed method '{self._method.__qualname__}'."
                )  # todo: keep in mind we're also marking the methods themselves

            if not self.compatible(method):
                raise DispatchingError(
                    f"Cannot expose '{method.__qualname__}' at endpoint '{self.name}'. "
                    f"Incompatible signature: {method.__annotations__} vs. {self.signature}"
                )

            method._endpoint = self
            self._method = method
            if self._update is not None:
                self._update(self)

            return method
        return wrapper

    @property
    def method(self) -> Optional[Callable]:
        """The method exposed at this endpoint. Can be ``None``
        """
        return self._method

    @property
    def signature(self) -> tuple:
        """The signature of this endpoint.
        """
        return self._signature.__args__  # type: ignore

    @property
    def streaming(self) -> Stream:
        """What or whether this endpoint streams.
        """
        return self._streaming

    @property
    def registered(self) -> bool:
        """Whether this endpoint is registered.
        """
        return self._registered

    @property
    def name(self) -> str:
        """The name of this endpoint.
        Taken from its attribute name in the object where it is registered.
        """
        try:
            return self._name
        except AttributeError:
            return ''

    def register(self, name: str, callback: Callable[['Endpoint'], None]):
        """Register the endpoint in some other object.
        """
        self._registered = True
        self._name = name
        self._update = callback


class Dispatcher(object):  # todo: these should also register specific instances & handle dispatching?
    """Dispatches requests to :class:`shapeflow.core.Endpoint` objects.
    """
    _endpoints: Tuple[Endpoint, ...]  #type: ignore
    _dispatchers: Tuple['Dispatcher', ...]

    _name: str
    _parent: Optional['Dispatcher']
    _address_space: Dict[str, Optional[Callable]]

    _update: Optional[Callable[['Dispatcher'], None]]

    _instance: Optional[object]

    def __init__(self, instance: object = None):
        self._update = None
        if instance is not None:
            self._set_instance(instance)
        else:
            self._address_space = {}
            self._endpoints = tuple()
            self._dispatchers = tuple()

    @property
    def name(self) -> str:
        """The name of this dispatcher.
        """
        try:
            return self._name
        except AttributeError:
            return self.__class__.__name__

    @property
    def dispatchers(self) -> Tuple['Dispatcher', ...]:
        """The dispatchers nested in this dispatcher.
        """
        return self._dispatchers

    @property
    def endpoints(self) -> Tuple[Endpoint, ...]:
        """The endpoints contained in this dispatcher.
        """
        return self._endpoints

    @property
    def address_space(self) -> Dict[str, Optional[Callable]]:
        """The address-method mapping of this dispatcher.
        """
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
        """Register this dispatcher within another dispatcher.
        """
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

        if self._update is not None:
            self._update(self)

    def _add_dispatcher(self, name: str, dispatcher: 'Dispatcher'):
        dispatcher._register(name=name, callback=self._update_dispatcher)

        self._address_space.update({
            "/".join([name, address]): method
            for address, method in dispatcher.address_space.items()
            if method is not None and "__" not in address
        })
        self._dispatchers = tuple(list(self._dispatchers) + [dispatcher])
        setattr(self, name, dispatcher)

        if self._update is not None:
            self._update(self)

    def _update_endpoint(self, endpoint: Endpoint) -> None:
        self._address_space.update({
            endpoint.name: endpoint.method
        })
        if self._update is not None:
            self._update(self)

    def _update_dispatcher(self, dispatcher: 'Dispatcher') -> None:
        self._address_space.update({  # todo: this doesn't take into account deleted keys!
            "/".join([dispatcher.name, address]): method
            for address, method in dispatcher.address_space.items()
            if method is not None and "__" not in address
        })

        if self._update is not None:
            self._update(self)

    def dispatch(self, address: str, *args, **kwargs) -> Any:
        """Dispatch a request to a method.

        Parameters
        ----------
        address : str
            The address to dispatch to
        args
            Any positional arguments to pass on to the method
        kwargs
            Any keyword arguments to pass on to the method

        Returns
        -------
        Any
            Whatever the method returns.
        """
        try:
            method = self.address_space[address]

            if method is not None:
                # todo: consider doing some type checking here, args/kwargs vs. method._endpoint.signature
                return method(*args, **kwargs)
        except KeyError:
            raise DispatchingError(
                f"'{self.name}' can't dispatch address '{address}'."
            )

    def __getitem__(self, item):
        return getattr(self, item)