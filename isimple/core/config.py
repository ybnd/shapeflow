import numpy as np
from typing import List, Optional, Union, Type, Dict
from dataclasses import dataclass
from functools import partial

from isimple import get_logger, __version__
from isimple.maths.colors import Color
from isimple.util import ndarray2str, str2ndarray


log = get_logger(__name__)

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
            if hasattr(self, '_mapping') and len(self._mapping):
                return list(self._mapping.keys())[0]
            else:
                return None

    @classmethod
    def _extend(cls, key: str, extension: type):
        if not hasattr(cls, '_mapping'):
            cls._mapping = {}

        if issubclass(extension, cls._type):
            log.debug(f"Extending Factory '{cls.__name__}' "
                      f"with {{'{key}': {extension}}}")
            cls._mapping.update({key: extension})
        else:
            raise TypeError(f"Attempting to extend Factory '{cls.__name__}' "
                            f"with incompatible class {extension.__name__}")


class extend(object):  # todo: can this be a function instead? look at the @dataclass decorator, something weird is going on there with * and /
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
class Config(object):
    """Abstract class for configuration data.
        * Default values for Config or Factory subclasses should be provided as
            None and '' respectively; in this way they should be caught by
            `self.resolve` and resolved at runtime. This is important to resolve
            to the latest version of the Factory, as it may have been extended.
    """
    def __init__(self, **kwargs):  # todo: cosider __call__(**defaults) if applying resolve() automatically
        self(**kwargs)

    def __call__(self, **kwargs):
        for kw, arg in kwargs.items():
            if hasattr(self, kw) and kw[0] != '_':
                # Handled initialization explicitly in __post_init__
                setattr(self, kw, arg)
            else:
                log.warning(f"{self.__class__.__name__}: "
                            f"unexpected argument {{'{kw}': {arg}}}.")

    def __post_init__(self):
        """Resolve attribute values here  todo: link specific resolve() calls to fields, these should be called at call also!
        """
        pass

    @staticmethod
    def resolve(val, type, iter: bool = False):
        """Resolve the value of an attribute to match a specific type
        :param val: current value
        :param type: type to resolve to
        :param iter: if True, resolve all elements of val
        :return: the resolved value for `val`; this should be written to the
                  original attribute, i.e. `self.attr = resolve(self.attr, type)`
        """
        def _resolve(val, type):
            if isinstance(val, type):
                pass
            elif isinstance(val, str):
                if issubclass(type, EnforcedStr):
                    val = type(val)
                elif issubclass(type, Color):
                    val = type.from_str(val)
                elif type == np.ndarray:
                    val = str2ndarray(val)
            elif isinstance(val, list):
                if type == np.ndarray:
                    val = np.array(val)
                else:
                    val = type(*val)
            elif isinstance(val, dict) and issubclass(type, Config):
                val = type(**untag(val))
            elif issubclass(type, Config) or issubclass(type, EnforcedStr):
                val = type()
            return val

        if iter:
            val = map(partial(_resolve, type=type), val)
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
                # Recurse, but don't tag
                return obj.to_dict(do_tag = False)
            if isinstance(obj, EnforcedStr):
                # Return str value
                try:
                    return str(obj)
                except TypeError:
                    return ''
            if isinstance(obj, tuple):
                # Convert to str to bypass YAML tuple representation
                return str(obj)
            if isinstance(obj, np.ndarray):
                # Convert to str to bypass YAML list representation
                return ndarray2str(obj)
            else:
                # Assume that `obj` is serializable
                return obj


        for attr, val in self.__dict__.items():
            try:
                if val is not None:
                    if any([
                        isinstance(val, list),
                        isinstance(val, tuple),
                    ]) and not any([
                        isinstance(val, Color),
                    ]):
                        output[attr] = type(val)([*map(_represent, val)])
                    elif isinstance(val, dict):
                        output[attr] = {k:_represent(v) for k,v in val.items()}
                    else:
                        output[attr] = _represent(val)
            except ValueError:
                log.debug(f"Config.to_dict() - skipping '{attr}': {val}")

        if do_tag:
            # todo: should only tag at the top-level (lots of unnecessary info otherwise)
            self.tag(output)

        return output

    def tag(self, d: dict) -> dict:
        d[VERSION] = __version__
        d[CLASS] = self.__class__.__name__
        return d


class ConfigType(Factory):
    _type = Config

    def get(self) -> Type[Config]:
        config = super().get()
        if issubclass(config, Config):
            return config
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{config}'. "
                f"This is very weird and shouldn't happen, really."
            )
