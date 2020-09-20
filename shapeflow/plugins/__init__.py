from os.path import dirname, basename, isfile, join
import os
import glob

from shapeflow import get_logger

log = get_logger(__name__)

# list plugins
__all__ = [
    basename(f).split('.')[0] for f in os.listdir(os.path.dirname(__file__))
    if f not in ['__init__.py', '__pycache__']
]
log.info(f"loading plugins: {', '.join(__all__)}")

# import plugins
from . import *
from shapeflow.core.interface import TransformType, FilterType
from shapeflow.core.backend import FeatureType


TransformType.set_default(TransformType('PerspectiveTransform'))
FilterType.set_default(FilterType('HsvRangeFilter'))
FeatureType.set_default(FeatureType('Area_mm2'))
