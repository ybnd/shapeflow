import abc
import re
from typing import Tuple, Any, Optional, List, Type, Generator
import os

import numpy as np
import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import frame_number_iterator
from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum
from isimple.core.backend import  BackendManager
from isimple.core.features import FeatureSet

from isimple.video import VideoAnalyzer
from isimple.gui import VideoAnalyzerGui


if __name__ == '__main__':
    frontend = VideoAnalyzerGui()

