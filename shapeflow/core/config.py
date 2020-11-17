import abc
import copy
import json

import numpy as np
from typing import Optional, Union, Type, Dict, Any, Mapping, List
from functools import partial

from shapeflow import get_logger, __version__
from shapeflow.core import EnforcedStr, Described
from shapeflow.util import ndarray2str, str2ndarray

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


# todo: move up to shapeflow.core
class Factory(EnforcedStr):  # todo: add a _class & issubclass check
    """An enforced string which maps its options to types.

    Included types should be subclasses of :class:`~shapeflow.core.Described`
    in order to generate descriptions for all options.
    """
    _mapping: Mapping[str, Type[Described]] = {}
    _default: Optional[str] = None
    _type: Type[Described] = Described

    def get(self) -> Type[Described]:
        """Get the type associated with the current string.
        """
        if self._str in self._mapping:
            return self._mapping[self._str]
        else:
            raise ValueError(f"Factory {self.__class__.__name__} doesn't map "
                             f"{self._str} to a class.")

    @classmethod
    def get_str(cls, mapped_value: Type[Described]):
        """Get the string for a specific type.
        """
        for k,v in cls._mapping.items():
            if mapped_value == v:
                return k

    @property
    def options(self) -> List[str]:
        """The options for this factory.
        """
        return list(self._mapping.keys())

    @property
    def descriptions(self) -> Dict[str, str]:
        """The descriptions for this factory.
        """
        return { k:v._description() for k,v in self._mapping.items() }

    @property
    def default(self) -> Optional[str]:
        """The default for this factory.
        """
        if self._default is not None:
            return self._default
        else:
            if hasattr(self, '_mapping') and len(self._mapping):
                return list(self._mapping.keys())[0]
            else:
                return None

    @classmethod
    def extend(cls, key: str, extension: Type[Described]):
        """Add a new type to this factory.
        Used to dynamically add options e.g. for including plugins.
        """
        if not hasattr(cls, '_mapping'):
            cls._mapping = {}

        assert isinstance(cls._mapping, dict)  # to put MyPy at ease

        if issubclass(extension, cls._type):
            log.debug(f"Extending Factory '{cls.__name__}' "
                      f"with {{'{key}': {extension}}}")
            cls._mapping.update({key: extension})
        else:
            raise TypeError(f"Attempting to extend Factory '{cls.__name__}' "
                            f"with incompatible class {extension.__name__}")

    @abc.abstractmethod
    def config_schema(self) -> dict:
        """The ``pydantic`` configuration schema for
        the members of this factory
        """
        raise NotImplementedError


class extend(object):  # todo: can this be a function instead? look at the @dataclass decorator, something weird is going on there with * and /
    """Decorator to extend :class:`~shapeflow.core.config.Factory` classes.
    Usage::
        from shapeflow.core.config import extend

        @extend(SomeFactory)
        class SomeClass:
            pass
    """
    _factory: Type[Factory]
    _key: Optional[str]

    def __init__(self, factory: Type[Factory], key: Optional[str] = None):
        self._factory = factory
        self._key = key

    def __call__(self, cls):
        if self._key is None:
            self._key = cls.__name__
        self._factory.extend(self._key, cls)
        return cls


def untag(d: dict) -> dict:
    """Remove the tags from a configuration ``dict``

    Parameters
    ----------
    d : dict
        Any configuration dict

    Returns
    -------
    dict
        The original configuration ``dict`` without class and version info
    """
    for tag in TAGS:
        if tag in d:
            d.pop(tag)
    return d


class BaseConfig(BaseModel, Described):
    """Abstract configuration class.
    All other configuration classes should derive from this one.

    Usage, where ``SomeConfig`` is a subclass of ``BaseConfig``::

            # instantiating
            config = SomeConfig()
            config = SomeConfig(field1=1.0, field2='text')
            config = SomeConfig(**dict_with_fields_and_values)

            # updating
            config(field1=1.0, field2='text')
            config(**dict_with_fields_and_values)

            # saving
            dict_with_fields_and_values = config.to_dict()

    When writing ``BaseConfig`` subclasses, use the
    :class:`~shapeflow.core.config.extends` decorator to make your
    configuration class accessible through the
    :class:`~shapeflow.core.config.ConfigType` factory. Configuration fields
     are declared as ``pydantic.Field`` instances and must be type-annotated
     for type resolution to work properly.

    Example::

        from pydantic import Field
        from shapeflow.core.config import BaseConfig

        @extend(ConfigType)
        class SomeConfig(BaseConfig):
            field1: int = Field(default=42)
            field2: SomeNestedConfig = Field(default_factory=SomeOtherConfig)


    """
    class Config:
        """``pydantic`` configuration class
        """
        arbitrary_types_allowed = False
        use_enum_value = True
        validate_assignment = True
        json_encoders = {
            np.ndarray: list,
            EnforcedStr: str,
        }

    @classmethod
    def _resolve_enforcedstr(cls, value, field):
        """Resolve :class:`~shapeflow.core.EnforcedStr` objects
        from regular ``str`` objects. To be used in ``pydantic`` validators.
        """
        if isinstance(value, field.type_):
            return value
        elif isinstance(value, str):
            return field.type_(value)
        else:
            raise NotImplementedError

    @classmethod
    def _odd_add(cls, value):
        """Make sure a value stays odd by incrementing even values.
        To be used in ``pydantic`` validators.
        """
        if value:
            if not (value % 2):
                return value + 1
            else:
                return value
        else:
            return 0

    @classmethod
    def _int_limits(cls, value, field):
        """Enforce ``pydantic`` field limits (`le`, `lt`, `ge`, `gt`)
        for ``int`` fields. To be used in ``pydantic`` validators.
        """
        if field.field_info.le is not None and not value <= field.field_info.le:
            return field.field_info.le
        elif field.field_info.lt is not None and not value < field.field_info.lt:
            return field.field_info.lt - 1
        elif field.field_info.ge is not None and not value >= field.field_info.ge:
            return field.field_info.ge
        elif field.field_info.gt is not None and not value > field.field_info.gt:
            return field.field_info.gt + 1
        else:
            return value

    @classmethod
    def _float_limits(cls, value, field):
        """Enforce ``pydantic`` field limits (`le`, `lt`, `ge`, `gt`)
        for ``float`` fields. To be used in ``pydantic`` validators.
        """
        if field.field_info.le is not None and not value <= field.field_info.le:
            return field.field_info.le
        elif field.field_info.lt is not None and not value < field.field_info.lt:
            log.warning(f"resolving float 'lt' as 'le' for field {field}")
            return field.field_info.lt
        elif field.field_info.ge is not None and not value >= field.field_info.ge:
            return field.field_info.ge
        elif field.field_info.gt is not None and not value > field.field_info.gt:
            log.warning(f"resolving float 'gt' as 'ge' for field {field}")
            return field.field_info.gt
        else:
            return value


    def __call__(self, **kwargs) -> None:
        # iterate over fields to maintain validation order
        for field in self.__fields__.keys():
            if field in kwargs:  # todo: inefficient
                if isinstance(getattr(self, field), BaseConfig) and isinstance(kwargs[field], dict):
                    # If field is a BaseConfig instance, resolve in place
                    getattr(self, field)(**kwargs[field])
                else:
                    # Otherwise, let the validators handle it
                    setattr(self, field, kwargs[field])

    def to_dict(self, do_tag: bool = False) -> dict:  # todo: should be replaced by pydantic internals + serialization
        """Return the configuration as a serializable dict.

        Parameters
        ----------
        do_tag : bool
            If `True`, add configuration class and version fields to the dict

        Returns
        -------
        dict
            A serializable representation of this configuration object.
        """
        """Return the configuration as a serializable dict.
        :param do_tag: if `True`, add configuration class and version fields to the dict
        :return: dict
        """
        output: dict = {}
        def _represent(obj) -> Union[dict, str]:
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
        """Tag a ``dict`` with this object's class and the library version.
        This information is used to deserialize correctly later on.
        """
        d[VERSION] = __version__
        d[CLASS] = self.__class__.__name__
        return d


class ConfigType(Factory):
    """Configuration type factory
    """
    _type = BaseConfig
    _mapping: Mapping[str, Type[Described]] = {}

    def get(self) -> Type[BaseConfig]:
        """Return the configuration type.
        """
        config = super().get()
        if issubclass(config, BaseConfig):
            return config
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' tried to return an unexpected type '{config}'. "
                f"This is very weird and shouldn't happen, really."
            )

    def config_schema(self) -> dict:
        """Return the configuration schema.
        """
        return self.get().schema()


class Configurable(Described):
    """A class with an associated configuration type.
    """
    _config_class: Type[BaseConfig] = BaseConfig
    """The configuration class as a class attribute. When subclassing, set this 
    attribute to a specific :class:`~shapeflow.core.config.BaseConfig` type to
    associate it with this class.
    """

    @classmethod
    def config_class(cls):
        """The configuration class.
        """
        return cls._config_class

    @classmethod
    def config_schema(cls):
        """The configuration schema.
        """
        return cls.config_class().schema()


class Instance(Configurable):  # todo: why isn't this just in Configurable?
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
