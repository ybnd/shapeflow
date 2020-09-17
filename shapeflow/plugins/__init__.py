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
log.debug(f'loading {__all__}')

# import plugins
from . import *
