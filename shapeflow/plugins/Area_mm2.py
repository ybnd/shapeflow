import numpy as np

from shapeflow import get_logger, settings
from shapeflow.config import extend, ConfigType, Field

from shapeflow.maths.images import area_pixelsum

from shapeflow.video import MaskFunction, Feature, FeatureType, FeatureConfig


@extend(FeatureType)
class Area_mm2(MaskFunction):
    "Area ~ masked & filtered pixels"
    _label = "Area"
    _unit = "mm²"

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame))
