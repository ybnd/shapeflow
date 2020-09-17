import numpy as np

from shapeflow import get_logger, settings
from shapeflow.config import extend, ConfigType, Field

from shapeflow.maths.images import area_pixelsum

from shapeflow.video import MaskFunction, Feature, FeatureType


@extend(FeatureType)
class PixelSum(MaskFunction):
    "Masked & filtered area as number of pixels"
    _label = "Pixels"
    _unit = "#"

    def _function(self, frame: np.ndarray) -> int:
        return area_pixelsum(frame)
