import numpy as np
from pydantic import Field

from shapeflow.config import extend, ConfigType
from shapeflow.maths.images import area_pixelsum
from shapeflow.video import MaskFunction, FeatureType, FeatureConfig


@extend(ConfigType, True)
class _Config(FeatureConfig):
    """Configuration for :class:`shapeflow.plugins.Volume_uL.Volume_uL`
        """
    h: float = Field(default=0.153, description='height (mm)')
    """The channel height of the chip.
    """


@extend(FeatureType, True)
class Volume_uL(MaskFunction):
    """Multiply :mod:`~shapeflow.plugins.Area_mm2` by a channel height in mm
    to estimate the volume in µL.
    """
    _label = "Volume"
    _unit = "µL"

    _config_class = _Config

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame)) * self.config.h