import numpy as np

from isimple import get_logger, settings
from isimple.config import extend, ConfigType, Field

from isimple.maths.images import area_pixelsum

from isimple.video import MaskFunction, Feature, FeatureType, FeatureConfig


@extend(FeatureType)
class Area_mm2(MaskFunction):
    _label = "Area"
    _unit = "mm²"
    _description = "Area ~ masked & filtered pixels"

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame))
