from typing import Optional, Tuple

import cv2
import numpy as np

from isimple import get_logger, settings
from isimple.config import extend, ConfigType, Field

from isimple.core.interface import TransformConfig, TransformInterface, TransformType

from isimple.maths.coordinates import ShapeCoo, Roi

log = get_logger(__name__)

@extend(ConfigType)
class PerspectiveTransformConfig(TransformConfig):
    pass


@extend(TransformType)
class PerspectiveTransform(TransformInterface):
    """Perspective transform"""

    _config_class = PerspectiveTransformConfig

    def validate(self, matrix: Optional[np.ndarray]) -> bool:
        if matrix is not None:
            return matrix.shape == (3, 3) and np.isfinite(np.linalg.cond(matrix))
        else:
            return False

    def from_coordinates(self, roi: Roi, from_shape: tuple) -> np.ndarray:
        return np.float32(
            [[relative * total
              for relative, total in zip(
                    getattr(roi, corner).list, from_shape
                )]
             for corner in ['BL', 'TL', 'TR', 'BR']]
        )

    def to_coordinates(self, to_shape: tuple) -> np.ndarray:
        return np.float32(
                np.array(  # selection rectangle: bottom left to top right
                    [
                        [0, to_shape[1]],          # BL: (x,y)
                        [0, 0],                 # TL
                        [to_shape[0], 0],          # TR
                        [to_shape[0], to_shape[1]],   # BR
                    ]
                )
            )

    def estimate(self, roi: Roi, from_shape: tuple, to_shape: tuple) -> np.ndarray:
        log.debug(f'Estimating transform ~ coordinates {roi} & shape {to_shape}')

        matrix = cv2.getPerspectiveTransform(
            self.from_coordinates(roi, from_shape),
            self.to_coordinates(to_shape)
        )

        if self.validate(matrix):
            return matrix
        else:
            raise ValueError(
                f'Cannot estimate a valid matrix from {roi} and {to_shape}'
            )

    def transform(self, matrix: np.ndarray, img: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.warpPerspective(
            img, matrix, shape,   # can't set destination image here! it's the wrong shape!
            borderValue=(255,255,255),  # makes the border white instead of black ~https://stackoverflow.com/questions/30227979/
        )

    def coordinate(self, inverse: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
        coordinate.transform(inverse, shape)
        return coordinate
