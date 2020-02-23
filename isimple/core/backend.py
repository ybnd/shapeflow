import diskcache
import sys
import copy
import time
import threading
from contextlib import contextmanager
from typing import Any, Callable

from isimple.core.util import describe_function
from isimple.core.config import *
from isimple.core.common import RootException, SetupError, Manager  # todo: RootException should probably be in a separate file


class BackendSetupError(SetupError):
    msg = 'Error while setting up backend'


class BackendError(RootException):
    msg = 'Error in backend'


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


class BackendInstance(object):
    _config: BackendInstanceConfig
    _default = BackendInstanceConfig()

    __attributes__: List[str]

    # todo: interface with isimple.core.meta
    #  define legal values for strings in isimple.core.meta

    def __init__(self, config: Optional[BackendInstanceConfig]):
        self._configure(config)
        super(BackendInstance, self).__init__()

    def _configure(self, config: BackendInstanceConfig = None):   # todo: adapt to dataclass implementation
        """Handle a (flat) configuration dict
            - Look through __default__ dict of all classes in __bases__
            - For all of the keys defined in __default__:
                -> if key not in config, use the default key
                -> if default value is an EnforcedStr and key is present in
                    config, validate the value
                -> if default value is a Factory and key is present in
                    config, validate and resolve to the associated class
            - Keys in config that are not defined in __default__ are skipped
        :param config:
        :return:
        """
        if config is not None:
        # # Gather default config from all bases
        # default_config: dict = {}
        # for base_class in self.__class__.__bases__:
        #     if hasattr(base_class, '__default__'):
        #         default_config.update(base_class.__default__)  #type: ignore
        # default_config.update(self.__default__)
        #
        # self.__attributes__ = list(default_config.keys())
        #
        # _config = {}
        # for key, default in default_config.items():
        #     if key in config:
        #         if isinstance(default, EnforcedStr):
        #             # Pass config[key] through EnforcedStr
        #             _config[key] = default.__class__(config[key])
        #         else:
        #             _config[key] = config[key]
        #     else:
        #         _config[key] = default
        #
        #     # Catch Factory instances, even if it's the default
        #     if isinstance(_config[key], Factory):
        #         # Get mapped class
        #         _config[key] = _config[key].get()  # type: ignore

            self._config = copy.deepcopy(config)  # Each instance should have a *copy* of the config, not references to the actual values
        else:
            self._config = copy.deepcopy(self._default)


__BLOCKED__ = 'BLOCKED'


class CachingBackendInstance(BackendInstance):  # todo: consider a waterfall cache: e.g. 2 GB in-memory, 4GB on-disk, finally the actual video
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]
    _background: Optional[threading.Thread]
    _background_task: Callable

    _config: CachingBackendInstanceConfig
    _default = CachingBackendInstanceConfig()

    def __init__(self, config: CachingBackendInstanceConfig = None):
        super(CachingBackendInstance, self).__init__(config)

        self._cache = None
        self._background = None

    def _get_key(self, method, *args) -> str:
        # Key should be instance-independent to handle multithreading
        #  and caching between application runs.
        # Hashing the string is a significant performance hit.
        return f"{describe_function(method)}:{args}"

    def _to_cache(self, key: str, value: Any):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, value)

    def _from_cache(self, key: str) -> Optional[Any]:  # todo: implement memory/disk cache waterfall, maybe?
        assert self._cache is not None, CacheAccessError
        return self._cache.get(key)

    def _block(self, key: str):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, __BLOCKED__)

    def _is_blocked(self, key: str) -> bool:
        assert self._cache is not None, CacheAccessError
        return key in self._cache \
               and isinstance(self._cache[key], str) \
               and self._from_cache(key) == __BLOCKED__

    def _drop(self, key: str):
        assert self._cache is not None, CacheAccessError
        del self._cache[key]

    def _cached_call(self, method, *args, **kwargs):
        """Wrapper for a method, handles caching 'at both ends'
        """  # todo can't use this as a decorator :(
        key = self._get_key(method, *args)
        if self._cache is not None:
            # Check if the file's already cached
            if key in self._cache:
                t0 = time.time()
                while self._is_blocked(key) and time.time() < t0 + self._config.block_timeout:
                    # Some other thread is currently reading the same frame
                    # Wait a bit and try to get from cache again
                    time.sleep(0.01)  # todo: DiskCache-level events?

                value = self._from_cache(key)
                if isinstance(value, str) and value == __BLOCKED__:
                    warnings.warn('Timed out waiting for blocked value.')
                    return None
                else:
                    return value
            if not self._config.cache_consumer:
                # Cache a temporary string to 'block' the key
                self._block(key)
                value = method(*args, **kwargs)
                if value is not None:
                    self._to_cache(key, value)
                    return value
                else:
                    self._drop(key)
                    return None
            else:
                return None
        else:
            return method(*args, **kwargs)

    def __enter__(self):
        if self._config.do_cache:
            self._cache = diskcache.Cache(
                directory=self._config.cache_dir,
                size_limit=self._config.cache_size_limit,
            )
            if self._config.do_background:
                pass  # todo: can start caching frames in background thread here

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._config.do_cache:
            if self._cache is not None:
                self._cache.close()
                self._cache = None

            if self._background is not None and self._background.is_alive():
                pass  # todo: can stop background thread here (gracefully)
                #        ...also: self._background.is_alive() doesn't recognize self...

            if exc_type is not None:
                return False
            else:
                return True

    @contextmanager
    def caching(self):
        try:
            self.__enter__()
            yield self
        finally:
            self.__exit__(*sys.exc_info())


class DynamicHandler(object):  # todo: implementations of CachingBackendInstance in `_implementation` will not be found by `_gather_instances`
    """
    """

    _implementation: object
    _implementation_factory = Factory
    _implementation_class = object  # actually, it's type, but that doesn't fly with MyPy for some reason

    def set_implementation(self, implementation: str) -> str:
        impl_type: type = self._implementation_factory(implementation).get()
        assert issubclass(impl_type, self._implementation_class)

        self._implementation = impl_type()
        return self._implementation_factory.get_str(
            self._implementation.__class__
        )

    def get_implementation(self) -> str:
        return self._implementation.__class__.__qualname__


class BackendManager(BackendInstance, Manager):  # todo: naming :(
    _instances: List[BackendInstance]
    _instance_class = BackendInstance

    def __init__(self, config: BackendManagerConfig = None):
        super(BackendManager, self).__init__(config)

    @contextmanager
    def caching(self):
        """Caching contest on VideoAnalysis: propagate context to
            every contained BackendElement that implements caching
        """
        caching_instances = [
            e for e in self._instances if
            isinstance(e, CachingBackendInstance)
        ]
        try:
            for element in caching_instances:
                element.__enter__()
            yield self
        finally:
            for element in caching_instances:
                element.__exit__(*sys.exc_info())

    def save(self):
        raise NotImplementedError
