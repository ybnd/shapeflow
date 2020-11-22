import abc
from typing import Type, Tuple, Optional, Dict, Mapping

import numpy as np

from shapeflow import get_logger
from shapeflow.core import Described
from shapeflow.core.config import BaseConfig, Configurable, Factory
from shapeflow.maths.colors import Color
from shapeflow.maths.coordinates import ShapeCoo, Roi

from pydantic import validator

log = get_logger(__name__)


class InterfaceType(Factory):
    """Interface type factory.
    """
    _type: Type[Configurable]
    _mapping: Mapping[str, Type[Configurable]] = {}
    _config_type: Type[BaseConfig] = BaseConfig

    def get(self) -> Type[Configurable]:
        """Get the interface type.
        """
        interface = super().get()
        assert issubclass(interface, Configurable)
        return interface

    def config_schema(self) -> dict:
        """Get the config schema for this interface type.
        """
        return self.get().config_schema()

    @classmethod
    def __modify_schema__(cls, field_schema):
        """Modify ``pydantic`` schema to include the interface.
        """
        super().__modify_schema__(field_schema)
        field_schema.update(interface=cls._config_type.__name__)


class Handler(abc.ABC):
    """Abstract class to wrap an interface implementation and its configuration
    """
    _implementation: Configurable
    _implementation_factory: Type[InterfaceType]
    _implementation_class: Type[Configurable]

    def set_implementation(self, implementation: str) -> str:
        """Set the implementation.
        """
        impl_type: type = self._implementation_factory(implementation).get()
        assert issubclass(impl_type, self._implementation_class)

        self._implementation = impl_type()
        return self._implementation_factory.get_str(  # todo: this is not necessary when using @extend(<Factory>)
            self._implementation.__class__
        )

    def get_implementation(self) -> str:
        """Get the current implementation.
        """
        return self._implementation.__class__.__qualname__

    def implementation_config(self) -> BaseConfig:  # todo: wait what?
        pass


class HandlerConfig(BaseConfig, abc.ABC):
    """Abstract handler configuration.
    """
    type: InterfaceType
    """The handler's interface implementation.
    """
    data: BaseConfig
    """The implementation's configuration.
    """

    @validator('type', pre=True)
    def _validate_type(cls, value, values: dict):
        if isinstance(value, cls.__fields__['type'].type_):
            return value
        else:
            return cls.__fields__['type'].type_(value)

    @validator('data', pre=True)
    def _validate_data(cls, value, values: dict):
        if isinstance(value, values['type'].get().config_class()):
            return value
        elif isinstance(value, dict):
            return values['type'].get().config_class()(**value)
        else:
            raise NotImplementedError


class TransformConfig(BaseConfig):
    """Abstract transform configuration.
    """


class TransformInterface(Configurable, abc.ABC):
    """Transform interface.
    Handles transforming frames based on ROI coordinates.

    All transform plugins should derive from this class
    and implement its methods.
    """
    @abc.abstractmethod
    def validate(self, matrix: Optional[np.ndarray]) -> bool:
        """Check whether a transformation matrix is valid.

        Parameters
        ----------
        matrix : Optional[np.ndarray]
            A transformation matrix or ``None`` if not set yet.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def from_coordinates(self, roi: Roi, from_shape: tuple) -> np.ndarray:
        """Make relative video-space coordinates absolute
        and compatible with ``numpy`` / ``OpenCV``.

        Parameters
        ----------
        roi : Roi
            A region of interest in the video (in relative coordinates)
        from_shape : tuple
            The dimensions of the video (in pixels)

        Returns
        -------
        np.ndarray
            An array of absolute video-space coordinates
        """
        raise NotImplementedError

    @abc.abstractmethod
    def to_coordinates(self, to_shape: tuple) -> np.ndarray:
        """Get the edges of the design in design-space coordinates

        Parameters
        ----------
        to_shape : tuple
            The dimensions of the design (in pixels)

        Returns
        -------
        np.ndarray
            An array of absolute design-space coordinates
        """
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, roi: Roi, from_shape: tuple, to_shape: tuple) -> Optional[np.ndarray]:
        """Estimate the transformation matrix from
        :func:`~shapeflow.core.interface.TransformInterface.from_coordinates`
        to :func:`~shapeflow.core.interface.TransformInterface.to_coordinates`

        Parameters
        ----------
        roi : Roi
            A region of interest in the video (in relative coordinates)
        from_shape : tuple
            The dimensions of the video (in pixels)
        to_shape : tuple
            The dimensions of the design (in pixels)

        Returns
        -------
        Optional[np.ndarry]
            The estimated transformation matrix. Returns ``None`` if one of the
            arguments is invalid or if some other exception occurs.
        """
        raise NotImplementedError

    def invert(self, matrix: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Invert a transformation matrix

        Parameters
        ----------
        matrix : Optional[np.ndarray]
            The transformation matrix to invert. Can be ``None`` if not set yet.

        Returns
        -------
        Optional[np.ndarray]
            The inverse transformation matrix. Returns ``None`` if ``matrix``
            is ``None`` or if some exception occurs during inversion.
        """
        if matrix is not None:
            return np.linalg.inv(matrix)
        else:
            return None

    @abc.abstractmethod
    def transform(self, transform: np.ndarray, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        """Transform a frame from video-space to design-space.

        Parameters
        ----------
        transform : np.ndarray
            The transformation matrix
        img : np.ndarray
            The frame to transform
        shape : tuple
            The shape of the design to transform to

        Returns
        -------
        np.ndarray
            The transformed frame
        """
        # todo: naming convention fail transform method vs. transform matrix
        raise NotImplementedError

    @abc.abstractmethod
    def coordinate(self, transform: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
        """Transform an (x,y) coordinate from video-space to design-space.

        Parameters
        ----------
        transform : np.ndarray
            The transformation matrix
        coordinate : ShapeCoo
            The coordinate to transform
        shape : tuple
            The shape of the design to transform to

        Returns
        -------
        ShapeCoo
            The transformed coordinate
        """
        # todo: naming convention fail transform method vs. transform matrix
        raise NotImplementedError


class FilterConfig(BaseConfig):
    """Abstract filter configuration"""

    @property
    def ready(self):
        """Return true if filter can be applied ~ this configuration.
            Override for specific filter implementations
        """
        raise NotImplementedError


class FilterInterface(Configurable, abc.ABC):
    """Filter interface.
    Handles filtering color images to binary.

    All filter plugins should derive from this class
    and implement its methods.
    """

    @abc.abstractmethod
    def set_filter(self, filter, color: Color) -> FilterConfig:
        """Set the filter to a specific color.

        Parameters
        ----------
        filter : FilterConfig
            The filter configuration
        color : Color
            The color to set the filter to

        Returns
        -------
        FilterConfig
            The updated filter configuration
        """
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> Color:
        """Get the mean color from a filter configuration

        Parameters
        ----------
        filter : FilterConfig
            The filter configuration

        Returns
        -------
        Color
            The configuration's mean color
        """
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, filter, image: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        """Filter a frame.

        Parameters
        ----------
        filter : FilterConfig
            The filter configuration
        image : np.ndarray
            The frame to filter
        mask : Optional[np.ndarray]
            The mask to apply to the frame

        Returns
        -------
        np.ndarray
            The filtered frame
        """
        raise NotImplementedError


class FilterType(InterfaceType):
    """Filter type factory.
    """
    _type = FilterInterface
    _mapping: Mapping[str, Type[FilterInterface]] = {}
    _config_type = FilterConfig

    def get(self) -> Type[FilterInterface]:
        """Get the filter type.
        """
        interface = super().get()
        assert issubclass(interface, FilterInterface)
        return interface


class TransformType(InterfaceType):
    """Transform type factory.
    """
    _type = TransformInterface
    _mapping: Mapping[str, Type[TransformInterface]] = {}
    _config_type = TransformConfig

    def get(self) -> Type[TransformInterface]:
        """Get the transform type.
        """
        interface = super().get()
        assert issubclass(interface, TransformInterface)
        return interface
