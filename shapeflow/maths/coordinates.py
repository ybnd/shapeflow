import copy
import warnings
from typing import Any, Optional, Tuple

import numpy as np
import cv2
from pydantic import Field, validator

from shapeflow.core.config import BaseConfig


class Coo(BaseConfig):
    """Image coordinate (relative)"""

    x: float = Field(default = 0)
    y: float = Field(default = 0)

    def __repr__(self):
        return f"Coo({self.x}, {self.y})"

    @property
    def rel(self) -> Tuple[float, float]:
        return (self.y, self.x)

    @property
    def list(self) -> list:
        return [self.x, self.y]


class ShapeCoo(Coo):
    shape: Tuple[int, int]

    def __repr__(self):
        return f"Coo({self.x}, {self.y}) ~ {self.shape}"

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, ShapeCoo)

        return self.abs == other.abs and self.shape == other.shape


    @property
    def abs(self) -> Tuple[float, float]:
        if self.shape is not None:
            return (self.y * self.shape[0], self.x * self.shape[1])
        else:
            raise ValueError('No shape provided')

    @property
    def idx(self) -> Tuple[int, int]:
        abs = self.abs
        return (int(round(abs[0])), int(round(abs[1])))

    @property
    def cv2(self):  # todo: the whole flip thing is confusing.
        abs = self.abs
        return (abs[1], abs[0])

    def value(self, image: np.ndarray) -> Any:
        # Image matrix should be [height x width]

        assert image.shape[0:2] == self.shape

        # todo: make sure x/y stuff is ok

        coo_idx = self.idx

        return image[
            coo_idx[0], coo_idx[1]
        ]

    def transform(self, matrix: np.ndarray, shape: Tuple[int, int]):
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
    """Region of interest"""

    BL: Coo = Field(default=None)
    TL: Coo = Field(default=None)
    TR: Coo = Field(default=None)
    BR: Coo = Field(default=None)
