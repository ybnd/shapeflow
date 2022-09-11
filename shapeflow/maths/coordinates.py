"""Some basic tools for working with coordinates.
"""
from typing import Any, Tuple

import numpy as np
import cv2
from pydantic import Field

from shapeflow.core.config import BaseConfig


class Coo(BaseConfig):
    """Coordinates of a point on a 2D image.
    Relative, and thus independent of the size of the image.
    """

    x: float = Field(default = 0)
    """The x-coordinate.
    """
    y: float = Field(default = 0)
    """The y coordinate.
    """

    def __repr__(self):
        return f"Coo({self.x}, {self.y})"

    @property
    def rel(self) -> Tuple[float, float]:
        """Get the relative coordinates.
        """
        return (self.y, self.x)

    @property
    def list(self) -> list:
        """Get the relative coordinates as a list.
        """
        return [self.x, self.y]


class ShapeCoo(Coo):
    """Coordinates of a point on a 2D image with a known size.
    """
    shape: Tuple[int, int]
    """The size of the image, from ``numpy.ndarray.shape``.
    """

    def __repr__(self):
        return f"Coo({self.x}, {self.y}) ~ {self.shape}"

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, ShapeCoo)

        return self.abs == other.abs and self.shape == other.shape

    @property
    def abs(self) -> Tuple[float, float]:
        """Get the absolute coordinates.
        """
        if self.shape is not None:
            return (self.y * self.shape[0], self.x * self.shape[1])
        else:
            raise ValueError('No shape provided')

    @property
    def idx(self) -> Tuple[int, int]:
        """Get (approximate) array indices ~ the absolute coordinate.
        """
        abs = self.abs
        return (int(round(abs[0])), int(round(abs[1])))

    @property
    def cv2(self):  # todo: the whole flip thing is confusing.
        """Get the absolute coordinates for ``OpenCV``.

        .. note::
           The order is flipped with respect to
           :func:`~shapeflow.maths.coordinates.ShapeCoo.abs`
        """
        abs = self.abs
        return (abs[1], abs[0])

    def value(self, image: np.ndarray) -> Any:
        """Get the value (color) of an image at this coordinate (approximately).

        Parameters
        ----------
        image: np.ndarray
            An image as a ``numpy`` array. Its ``shape`` should match
            :attr:`~shapeflow.maths.coordinates.ShapeCoo.shape`.

        Returns
        -------
        Any
            The value of the image array at this coordinate.
        """
        assert image.shape[0:2] == self.shape

        # todo: make sure x/y stuff is ok

        coo_idx = self.idx

        return image[
            coo_idx[0], coo_idx[1]
        ]

    def transform(self, matrix: np.ndarray, shape: Tuple[int, int]) -> None:
        """Transform this coordinate.

        Parameters
        ----------
        matrix: np.ndarray
            Transformation matrix. Should be a 2D matrix with dimensions
            [2x2], [2x3], [3x3] or [4x4]
        shape: Tuple[int, int]
        """
        # Transformation matrix should be [M x N]
        assert len(matrix.shape) == 2
        assert shape is not None

        # Transform coordinate vector
        if matrix.shape[0] == 2 and 1 < matrix.shape[1] < 4:
            trans_coo = cv2.transform(
                src = np.array([[self.cv2]]), m = matrix
            )
        elif matrix.shape == (3, 3) or matrix.shape == (4, 4):
            trans_coo = cv2.perspectiveTransform(
                src = np.array([[self.cv2]]), m = matrix
            )
        else:
            raise NotImplementedError(
                f"Transform must be [2x2], [2x3], [3x3] or [4x4]"
            )

        # Update to new shape & coordinates
        self.shape = shape
        self.x = trans_coo[0,0,0] / self.shape[1]
        self.y = trans_coo[0,0,1] / self.shape[0]


class Roi(BaseConfig):
    """A rectangular region of interest, composed of four points as
    :class:`~shapeflow.maths.coordinates.Coo` objects.
    """
    BL: Coo = Field(default=None)
    """The bottom-left corner.
    """
    TL: Coo = Field(default=None)
    """The top-left corner.
    """
    TR: Coo = Field(default=None)
    """The top-right corner.
    """
    BR: Coo = Field(default=None)
    """The bottom-right corner.
    """
