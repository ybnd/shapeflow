import abc
import copy
import json

import numpy as np
from typing import Optional, Union, Type, Dict, Any
from functools import partial

from isimple import get_logger, __version__
from isimple.core import EnforcedStr
from isimple.util import ndarray2str, str2ndarray
from isimple.util.meta import resolve_type_to_most_specific, is_optional

from pydantic import BaseModel, Field, root_validator, validator


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

    @abc.abstractmethod
    def config_schema(self) -> dict:
        raise NotImplementedError


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
        arbitrary_types_allowed = False
        use_enum_value = True
        validate_assignment = True
        json_encoders = {
            np.ndarray: list,
        }

    @classmethod
    def _resolve_enforcedstr(cls, value, field):
        if isinstance(value, field.type_):
            return value
        elif isinstance(value, str):
            return field.type_(value)
        else:
            raise NotImplementedError

    def __call__(self, **kwargs) -> None:
        log.debug(f'{self}__call__{kwargs}')
        for kw, value in kwargs.items():
            setattr(self, kw, value)

    @classmethod
    def _get_field_type(cls, attr):
        return resolve_type_to_most_specific(cls.__fields__[attr].outer_type_)

    def to_dict(self, do_tag: bool = False) -> dict:  # todo: should be replaced by pydantic internals + serialization
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
    _mapping: Dict[str, Type[BaseConfig]] = {}

    def get(self) -> Type[BaseConfig]:
        config = super().get()
        if issubclass(config, BaseConfig):
            return config
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{config}'. "
                f"This is very weird and shouldn't happen, really."
            )

    def config_schema(self) -> dict:
        return self.get().schema()


class Configurable(object):
    _config_class: Type[BaseConfig]

    @classmethod
    def config_class(cls):
        return cls._config_class

    @classmethod
    def config_schema(cls):
        return cls.config_class().schema()


class Instance(Configurable):
    _config: BaseConfig

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
