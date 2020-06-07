import abc
import copy
import json

import numpy as np
from typing import Optional, Union, Type, Dict, Any
from functools import partial

from isimple import get_logger, __version__
from isimple.core import EnforcedStr
from isimple.maths.colors import Color
from isimple.util import ndarray2str, str2ndarray
from isimple.util.meta import resolve_type_to_most_specific, is_optional

from pydantic import BaseModel, Field


log = get_logger(__name__)

# Metadata tags
VERSION: str = 'config_version'
CLASS: str = 'config_class'

TAGS = (VERSION, CLASS)

# Extension
__meta_ext__ = '.meta'

# Excel sheet name
__meta_sheet__ = 'metadata'


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


class NpArray(np.ndarray):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        # validate data...
        return v


class BaseConfig(BaseModel):
    """Abstract class for configuration data.

    * Usage, where `SomeConfig` is a subclass of `BaseConfig`:
        * Instantiating:
            ```
                config = SomeConfig()
                config = SomeConfig(field1=1.0, field2='text')
                config = SomeConfig(**dict_with_fields_and_values)
            ```
        * Updating:
            ```
                config(field1=1.0, field2='text')
                config(**dict_with_fields_and_values)
            ```

        * Saving:
            ```
                dict_with_fields_and_values = config.to_dict()
            ```

    * Writing `BaseConfig` subclasses:
        * Use the `@extends(ConfigType)` decorator to make your configuration
            class accessible from the `ConfigType` Factory (defined below)
        * Configuration keys are declared as pydantic `Field` instances
            - Must be type-annotated for type resolution to work properly!
            -
    ```
        from pydantic import Field
        from isimple.core.config import BaseConfig

        @extend(ConfigType)
        class SomeConfig(BaseConfig):
            field1: int = Field(default=42)
            field2: SomeNestedConfig = Field(default_factory=SomeOtherConfig)
    ```
    """
    class Config:
        """pydantic configuration class"""
        arbitrary_types_allowed = True
        json_encoders = {
            np.ndarray: list
        }

    def __init__(self, **kwargs):
        super().__init__()
        self.__call__(**kwargs)

    def resolve(self):
        """Passes fields to self.__call__() to resolve type
                """
        self(**self.__dict__)

    def __call__(self, **kwargs) -> None:
        """Set fields ~ (field, value) in kwargs.

            * Resolves value to field type ~ Config.resolve()

            * Handles the following schemes:
                1) nesting:
                    Config1
                        field a: Config2

                2) nesting ~ tuple:
                    Config1
                        field a: Tuple[Config2, ...]
                        field b: Tuple[Config3, EnforcedStr1]

                3) nesting ~ dict:
                    Config1
                        field a: Dict[str, Config2]
                        field b: Dict[EnforcedStr1, Config3]

                !! "Doubly nested" tuples or dicts are not handled !!
                    The type must be contained in the top level
                    of a tuple or dict for it to be resolved!

                    i.e. Config2 doesn't get resolved in
                        e.g.: Dict[str, Dict[str, Config2]
                        e.g.: Tuple[int, Tuple[Config2, ...]
        """

        for kw, value in kwargs.items():
            if kw in self.__fields__:
                field_type = self._get_field_type(kw)

                if value is None:
                    if self.__fields__[kw].allow_none:
                        setattr(self, kw, value)
                    else:
                        raise ValueError
                elif type(value) != field_type:
                    if hasattr(field_type, '__origin__'):
                        if field_type.__origin__ == tuple:
                            if field_type.__args__[1] == Ellipsis:
                                v_type = field_type.__args__[0]
                                setattr(
                                    self, kw,
                                    tuple([
                                        self._resolve_value(v, v_type)
                                        for v in value
                                    ])
                                )
                            else:
                                assert (len(field_type.__args__) == len(value))
                                setattr(
                                    self, kw,
                                    tuple([
                                        self._resolve_value(v, v_type)
                                        for v_type, v in zip(field_type.__args__, value)
                                    ])
                                )
                        elif field_type.__origin__ == dict:
                            k_type = resolve_type_to_most_specific(
                                field_type.__args__[0])
                            v_type = resolve_type_to_most_specific(
                                field_type.__args__[1])

                            try:
                                setattr(self, kw, {
                                    k_type(k): self._resolve_value(v, v_type)
                                    for k, v in value.items()
                                })
                            except TypeError:  # todo: not great
                                setattr(self, kw, {
                                    k_type(k): v for k, v in value.items()
                                })
                        else:
                            setattr(self, kw, self._resolve_value(value, field_type))
                    elif issubclass(field_type, BaseConfig):
                        # If field is an existing Config subclass, integrate value instead of overwriting
                        if not isinstance(getattr(self, kw), field_type):
                            # Resolve current value to correct type
                            setattr(self, kw, self._resolve_value(getattr(self, kw), field_type))
                        if isinstance(value, dict):
                            getattr(self, kw).__call__(**untag(value))
                        elif isinstance(value, BaseConfig):
                            getattr(self, kw).__call__(**untag(value.to_dict()))
                    else:
                        setattr(self, kw, self._resolve_value(value, field_type))
                else:
                    setattr(self, kw, value)
            elif hasattr(self, kw) and kw[0] != '_':
                setattr(self, kw, value)
            else:
                log.warning(f"{self.__class__.__name__}: "
                            f"unexpected field {{'{kw}': {value}}}.")

    def _get_field_type(self, attr):
        return resolve_type_to_most_specific(self.__fields__[attr].outer_type_)

    @staticmethod
    def _resolve_value(val, type, iter: bool = False):
        """Resolve the value of an attribute to match a specific type

        :param val: current value
        :param type: type to resolve to
        :param iter: if True, resolve all elements of val
        :return: the resolved value for `val`; this should be written to the
                  original attribute, i.e. `self.attr = resolve(self.attr, type)`
        """
        def __resolve_value(val, type):
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
            elif isinstance(val, dict) and issubclass(type, BaseConfig):
                val = type(**untag(val))
            elif issubclass(type, BaseConfig) or issubclass(type, EnforcedStr):
                val = type()
            return val

        if iter:
            val = map(partial(__resolve_value, type=type), val)
        else:
            # Resolve `val`
            val = __resolve_value(val, type)
        return val

    def to_dict(self, do_tag: bool = False) -> dict:
        """Return the configuration as a serializable dict.
        :param do_tag: if `True`, add configuration class and version fields to the dict
        :return: dict
        """
        output: dict = {}
        def _represent(obj) -> Union[dict, str]:
            """Represent an object in a YAML-serializable way
            :param obj: object
            :return:
            """
            if isinstance(obj, BaseConfig):
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
                        output[_represent(attr)] = type(val)([*map(_represent, val)])
                    elif isinstance(val, dict):
                        output[_represent(attr)] = {_represent(k):_represent(v) for k,v in val.items()}
                    else:
                        output[_represent(attr)] = _represent(val)
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
    _type = BaseConfig

    def get(self) -> Type[BaseConfig]:
        config = super().get()
        if issubclass(config, BaseConfig):
            return config
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{config}'. "
                f"This is very weird and shouldn't happen, really."
            )

class Instance(object):
    _config_class: Type[BaseConfig]
    _config: BaseConfig

    @classmethod
    def config_class(cls):
        return cls._config_class

    @property
    def config(self) -> BaseConfig:
        return self._config

    def __init__(self, config: BaseConfig = None):
        self._configure(config)
        super(Instance, self).__init__()

        log.debug(f'Initialized {self.__class__.__qualname__} with {self._config}')

    def _configure(self, config: BaseConfig = None):   # todo: adapt to dataclass implementation
        _type = self._config_class

        if config is not None:
            if isinstance(config, _type):
                # Each instance should have a *copy* of the config, not references to the actual values
                self._config = copy.deepcopy(config)
            elif isinstance(config, dict):
                log.warning(f"Initializing '{self.__class__.__name__}' from a dict, "
                            f"please initialize from '{_type}' instead.")
                self._config = _type(**untag(config))
            else:
                raise TypeError(f"Tried to initialize '{self.__class__.__name__}' with {type(config).__name__} '{config}'.")
        else:
            self._config = _type()
