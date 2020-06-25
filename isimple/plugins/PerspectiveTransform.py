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
    """Perspective transform"""
    pass


@extend(TransformType)
class PerspectiveTransform(TransformInterface):
    _config_class = PerspectiveTransformConfig

    def validate(self, matrix: Optional[np.ndarray]) -> bool:
        if matrix is not None:
            return matrix.shape == (3, 3)
        else:
            return False

    def from_coordinates(self, roi: Roi) -> np.ndarray:
        return np.float32(
            [getattr(roi, corner).list
             for corner in ['BL', 'TL', 'TR', 'BR']]
        )

    def to_coordinates(self, shape: tuple) -> np.ndarray:
        return np.float32(
                np.array(  # selection rectangle: bottom left to top right
                    [
                        [0, shape[1]],          # BL: (x,y)
                        [0, 0],                 # TL
                        [shape[0], 0],          # TR
                        [shape[0], shape[1]],   # BR
                    ]
                )
            )

    def estimate(self, roi: Roi, shape: tuple) -> np.ndarray:
        log.debug(f'Estimating transform ~ coordinates {roi} & shape {shape}')

        return cv2.getPerspectiveTransform(
            self.from_coordinates(roi),
            self.to_coordinates(shape)
        )

    def transform(self, matrix: np.ndarray, img: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.warpPerspective(
            img, matrix, shape,   # can't set destination image here! it's the wrong shape!
            borderValue=(255,255,255),  # makes the border white instead of black ~https://stackoverflow.com/questions/30227979/
        )

    def coordinate(self, inverse: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
        coordinate.transform(inverse, shape)
        return coordinate
