import numpy as np

from shapeflow.config import extend, ConfigType, Field
from shapeflow.maths.images import area_pixelsum
from shapeflow.video import MaskFunction, FeatureType, FeatureConfig


@extend(ConfigType, __name__.split('.')[-1])
class _Config(FeatureConfig):
    """Configuration for :class:`shapeflow.plugins.Volume_uL.Volume_uL`
        """
    h: float = Field(default=0.153, description='height (mm)')
    """The channel height of the chip.
    """


@extend(FeatureType, __name__.split('.')[-1])
class _Feature(MaskFunction):
    """Multiply :class:`~shapeflow.plugins.Area_mm2` by a channel height in mm
    to estimate the volume in µL.
    """
    _label = "Volume"
    _unit = "µL"

    _config_class = _Config

    def _function(self, frame: np.ndarray) -> float:
        return self.pxsq2mmsq(area_pixelsum(frame)) * self.config.h
