import diskcache
import sys
import os
import numpy as np
import abc
import time
import threading
from contextlib import contextmanager
import functools
import warnings
from typing import List, Optional, Any

from isimple.util import describe_function
from isimple.meta import EnforcedStr, Factory
from isimple.registry import Registry


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


class CacheAccessError(RootException):
    msg = 'Trying to access cache out of context'


class VideoAnalysisElement(abc.ABC):  # todo: more descriptive name, and probably shouldn't be in video
    __default__: dict
    __default__ = {  # EnforcedStr instances should be instantiated without
    }                #  arguments, otherwise there may be two defaults!

    __attributes__: List[str]
    __registry__: Registry

    # todo: interface with isimple.meta
    # todo: define legal values for strings so config can be validated at this level

    def __init__(self, config):
        self._config = self.handle_config(config)

    def handle_config(self, config: dict = None) -> dict:
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
        if config is None:
            config = {}

        # Gather default config from all parents
        default_config: dict = {}
        for base_class in self.__class__.__bases__:
            if hasattr(base_class, '__default__'):
                default_config.update(base_class.__default__)  #type: ignore
        default_config.update(self.__default__)

        self.__attributes__ = list(default_config.keys())

        _config = {}
        for key, default in default_config.items():
            if key in config:
                if isinstance(default, EnforcedStr):
                    # Pass config[key] through EnforcedStr
                    _config[key] = default.__class__(config[key])
                else:
                    _config[key] = config[key]
            else:
                _config[key] = default

            # Catch Factory instances, even if it's the default
            if isinstance(_config[key], Factory):
                # Get mapped class
                _config[key] = _config[key].get()  # type: ignore

        return _config

    def __getattr__(self, item):  # todo: relatively annoying as this can't be linted...
        """Get attribute value from self._config  
        """  # todo: interface with metadata -> should raise an exception if unexpected attribute is got
        if item in self._config.keys():
            return self._config[item]
        else:
            raise ValueError(
                f"Unexpected attribute '{item}'. "
                f"{self.__class__.__name__} recognizes the following "
                f"configuration attributes: {self.__attributes__}"
            )

    def __len__(self):
        pass # todo: this is a workaround, PyCharm debugger keeps polling __len__ for some reason

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    @classmethod
    def signatures(cls):
        if hasattr(cls, '__registry__'):
            return list(cls.__registry__.signatures())
        else:
            return []

    def exposes(self, signature):
        return self.__registry__.exposes(signature)

    def call(self, signature, *args, **kwargs):
        """Call the method specified in signature 
        """  # todo: check exposes here, or trust the implementation?
        if self.exposes(signature):
            method = self.__registry__._mapping[signature]
            return method(self, *args, **kwargs)
        else:
            raise NotImplementedError(f"{self.__class__.__name__} does not "
                                      f"expose {signature}")

    def get_callback(self, signature):
        if self.exposes(signature):
            method_name = self.__registry__._mapping[signature].__name__
            return getattr(self, method_name)
        else:
            raise NotImplementedError(f"{self.__class__.__name__} does not "
                                      f"expose {signature}")


class CachingVideoAnalysisElement(VideoAnalysisElement):  # todo: this should still be an abstract class though... and probably shouldn't be in video either
    """Interface to diskcache.Cache
    """
    _cache: Optional[diskcache.Cache]
    _background: Optional[threading.Thread]

    do_cache: bool
    do_background: bool
    cache_dir: str
    cache_size_limit: int
    block_timeout: float
    cache_consumer: bool

    __default__ = {
        'do_cache': True,
        'do_background': False,
        # True -> start background caching thread along with cache
        'cache_dir': os.path.join(os.getcwd(), '.cache'),
        'cache_size_limit': 2 ** 32,  # cache size limit
        'block_timeout': 1,
        'cache_consumer': False,
    }

    _BLOCKED = 'BLOCKED'


    def __init__(self, config):
        super(CachingVideoAnalysisElement, self).__init__(config)

        self._cache = None
        self._background = None

    @functools.lru_cache(maxsize=1000)
    def _get_key(self, method, *args) -> int:
        # key should be instance-independent to handle multithreading
        #  and caching between application runs
        #  i.e. hash __name__ instead of bound method
        return hash((describe_function(method), *args))

    def _to_cache(self, key: int, value: Any):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, value)

    def _from_cache(self, key: int) -> Optional[Any]:
        assert self._cache is not None, CacheAccessError
        return self._cache.get(key)

    def _block(self, key: int):
        assert self._cache is not None, CacheAccessError
        self._cache.set(key, self._BLOCKED)

    def _is_blocked(self, key: int) -> bool:
        assert self._cache is not None, CacheAccessError
        return key in self._cache \
               and isinstance(self._cache[key], str) \
               and self._from_cache(key) == self._BLOCKED

    def _drop(self, key: int):
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
                while self._is_blocked(key) and time.time() < t0 + self.timeout: # todo: clean up conditional
                    # Some other thread is currently reading the same frame
                    # Wait a bit and try to get from cache again
                    time.sleep(0.01)  # todo: DiskCache-level events?

                value = self._from_cache(key)
                if isinstance(value, str) and value == self._BLOCKED:
                    warnings.warn('Timed out waiting for blocked value.')
                    return None
                else:
                    return value
            if not self.cache_consumer:
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
        if self.do_cache:
            self._cache = diskcache.Cache(
                directory=self.cache_dir,
                size_limit=self.cache_size_limit,
            )
            if self.do_background:
                pass  # todo: can start caching frames in background thread here

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.do_cache:
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