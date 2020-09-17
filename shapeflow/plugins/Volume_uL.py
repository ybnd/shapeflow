import numpy as np

from shapeflow import get_logger, settings
from shapeflow.config import extend, ConfigType, Field

from shapeflow.maths.images import area_pixelsum

from shapeflow.video import MaskFunction, Feature, FeatureType, FeatureConfig


@extend(ConfigType)
class Volume_uL_Config(FeatureConfig):
    h: float = Field(default=0.153, description='height (mm)')


@extend(FeatureType)
class Volume_uL(MaskFunction):
    "Volume ~ masked & filtered area multiplied by channel height"

    _label = "Volume"
    _unit = "µL"

    _config_class = Volume_uL_Config

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame)) * self.config.h
