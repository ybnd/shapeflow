from typing import Optional
import numpy as np

from shapeflow.config import extend
from shapeflow.maths.images import area_pixelsum
from shapeflow.video import MaskFunction, FeatureType


@extend(FeatureType, __name__.split('.')[-1])
class _Feature(MaskFunction):
    """The most basic feature: it just returns the number of
    ``True`` pixels the filtered frame.
    """
    _label = "Pixels"
    _unit = "#"

    def _function(self, frame: np.ndarray) -> Optional[int]:
        return area_pixelsum(frame)
