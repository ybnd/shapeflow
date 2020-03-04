import re
import json
import numpy as np
from typing import List, Optional, Union, Type, Dict
from dataclasses import dataclass
from collections.abc import Iterable
import abc

from isimple.core.log import get_logger


log = get_logger(__name__)

__version__: str = '0.3'

# Metadata tags
VERSION: str = 'config_version'
CLASS: str = 'config_class'

TAGS = (VERSION, CLASS)

# Extension
__meta_ext__ = '.meta'

# Excel sheet name
__meta_sheet__ = 'metadata'


class EnforcedStr(object):
    _options: List[str] = ['']
    _str: str

    def __init__(self, string: str = None):
        if string is not None:
            if string not in self.options:
                log.debug(f"Illegal {self.__class__.__name__} '{string}', "
                              f"should be one of {self.options}. "
                              f"Defaulting to '{self.default}'.")
                self._str = self.default
            else:
                self._str = str(string)
        else:
            self._str = self.default

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self._str}'>"

    def __str__(self):
        return self._str

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
    def default(self):
        return self._options[0]

    def __hash__(self):
        return hash(str(self))


class Factory(EnforcedStr):  # todo: add a _class & issubclass check
    _mapping: Dict[str, type]
    _default: Optional[str] = None
    _type: type = object

    def get(self) -> type:
        if self._str in self._mapping:
            return self._mapping[self._str]
        else:
            raise ValueError(f"Factory {self.__class__.__name__} doesn't map "
                             f"{self._str} to a class.")

    @classmethod
    def get_str(cls, mapped_value):
        str = cls.default
        for k,v in cls._mapping.items():
            if mapped_value == v:
                str = k

        return str

    @property
    def options(self):
        return list(self._mapping.keys())

    @property
    def default(self):
        if self._default is not None:
            return self._default
        else:
            if len(self._mapping):
                return list(self._mapping.keys())[0]
            else:
                return None

    @classmethod
    def _extend(cls, key: str, extension: type):
        if not hasattr(cls, '_mapping'):
            cls._mapping = {}

        if issubclass(extension, cls._type):
            log.debug(f"Extending Factory '{cls.__name__}' with {key}:{extension}")
            cls._mapping.update({key: extension})
        else:
            raise TypeError(f"Attempting to extend Factory '{cls.__name__}' "
                            f"with incompatible class {extension.__name__}")


class extend(object):  # todo: can this be a function instead?
    _factory: Type[Factory]
    _key: Optional[str]

    def __init__(self, factory: Type[Factory], key: Optional[str] = None):
        self._factory = factory
        self._key = key

    def __call__(self, cls):
        if self._key is None:
            self._key = cls.__name__
        self._factory._extend(self._key, cls)
        return cls


def untag(d: dict) -> dict:
    for tag in TAGS:
        if tag in d:
            d.pop(tag)
    return d


@dataclass
class Config(abc.ABC):
    """Abstract class for configuration data.
        * Default values for Config or Factory subclasses should be provided as
            None and '' respectively; in this way they should be caught by
            `self.resolve` and resolved at runtime. This is important to resolve
            to the latest version of the Factory, as it may have been extended.
    """

    def __init__(self, **kwargs):
        """Initialize instance and call post-initialization method
        """
        for kw, arg in kwargs.items():
            if hasattr(self, kw) and kw[0] != '_':
                setattr(self, kw, arg)
        self.__post_init__()

    def __post_init__(self):
        """Resolve attribute values here
        """
        pass

    @staticmethod
    def resolve(val, type, iter=False, do_tag=False):
        """Resolve the value of an attribute to match a specific type
        :param val: current value
        :param type: type to resolve to
        :param iter: if True, interpret `val` as an iterable and resolve
                     all elements of `val` to `type`
        :return: the resolved value for `val`; this should be written to the
                  original attribute, i.e. `self.attr = resolve(self.attr, type)`
        """
        def _resolve(val, type):
            if isinstance(val, str):
                if issubclass(type, EnforcedStr):
                    val = type(val)
                elif issubclass(type, tuple):
                    val = Config.__str2namedtuple__(val, type)
                elif type == np.ndarray:
                    val = Config.__str2ndarray__(val)
            if isinstance(val, list):
                if type == np.ndarray:
                    val = np.array(val)
                else:
                    val = type(val)
            elif isinstance(val, dict) and issubclass(type, Config):
                val = type(**untag(val))
            return val

        if not isinstance(val, type):
            if iter and isinstance(val, Iterable):
                # Resolve every elemen,t in `val`
                val = [_resolve(v, type) for v in val]
            else:
                # Resolve `val`
                val = _resolve(val, type)
        return val

    def to_dict(self, do_tag: bool = False) -> dict:
        """Return this instances value as a serializable dict.
        """
        output: dict = {}
        def _represent(obj) -> Union[dict, str]:
            """Represent an object in a YAML-serializable way
            :param obj: object
            :return:
            """
            if isinstance(obj, Config):
                # Recurse
                return obj.to_dict()
            if isinstance(obj, EnforcedStr):
                # Return str value
                try:
                    return str(obj)
                except TypeError:
                    return ''
            if isinstance(obj, tuple):
                # Convert to str & bypass YAML tuple representation
                return str(obj)
            if isinstance(obj, np.ndarray):
                # Convert to str  & bypass YAML list representation
                return Config.__ndarray2json__(obj)
            else:
                # Assume that `obj` is serializable
                return obj


        for attr, val in self.__dict__.items():
            if val is not None:
                if (isinstance(val, list) or isinstance(val, tuple)) \
                        and not (attr in ['c0', 'c1', 'radius']):  # Filter out color attributes
                    output[attr] = []
                    for v in val:
                        output[attr].append(_represent(v))
                else:
                    output[attr] = _represent(val)

        # Add configuration metadata
        output[VERSION] = __version__
        output[CLASS] = self.__class__.__name__

        if do_tag:
            self.tag(output)

        return output

    def tag(self, d: dict) -> dict:
        d[VERSION] = __version__
        d[CLASS] = self.__class__
        return d

    @staticmethod
    def __ndarray2json__(array: np.ndarray) -> str:
        return str(json.dumps(array.tolist()))

    @staticmethod
    def __str2ndarray__(string: str) -> np.ndarray:
        return np.array(json.loads(str(string)))

    @staticmethod
    def __str2namedtuple__(t: str, type: Type[tuple]) -> tuple:
        return type(
            **{k:float(v.strip("'")) for k,v,_ in re.findall('([A-Za-z0-9]*)=(.*?)(,|\))', t)}  #type: ignore
        )  # todo: we're assuming tuples of floats here, will break for cases that are not colors!


class ConfigType(Factory):
    _mapping: dict = {}
    _type = Config
