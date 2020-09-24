import numpy as np

from shapeflow.config import extend

from shapeflow.maths.images import area_pixelsum

from shapeflow.video import MaskFunction, FeatureType


@extend(FeatureType)
class Area_mm2(MaskFunction):
    "Area ~ masked & filtered pixels"
    _label = "Area"
    _unit = "mm²"

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame))
