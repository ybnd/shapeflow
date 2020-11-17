import numpy as np

from shapeflow.config import extend, ConfigType, Field
from shapeflow.maths.images import area_pixelsum
from shapeflow.video import MaskFunction, FeatureType, FeatureConfig


@extend(ConfigType)
class Volume_uL_Config(FeatureConfig):
    h: float = Field(default=0.153, description='height (mm)')
    """The channel height of the chip.
    """


@extend(FeatureType)
class Volume_uL(MaskFunction):
    """Multiply :class:`~shapeflow.plugins.Area_mm2` by a channel height in mm
    to estimate the volume in µL.
    """
    _label = "Volume"
    _unit = "µL"

    _config_class = Volume_uL_Config

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame)) * self.config.h
