import numpy as np

from isimple import get_logger, settings
from isimple.config import extend, ConfigType, Field

from isimple.maths.images import area_pixelsum

from isimple.video import MaskFunction, Feature, FeatureType


@extend(FeatureType)
class Volume_uL(MaskFunction):
    _label = "Volume"
    _unit = "µL"
    _description = "Volume ~ masked & filtered area multiplied by channel height"

    _parameters = ('h',)
    _parameter_defaults = {
        'h': 0.153
    }
    _parameter_descriptions = {
        'h': 'height (mm)'
    }

    def _function(self, frame: np.ndarray) -> float:
        h, = self.unpack()
        return self.pxsq2mmsq(area_pixelsum(frame)) * h  # todo: better parameter handling for Feature subclasses
