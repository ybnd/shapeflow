from os.path import dirname, basename, isfile, join
import os
import glob

from isimple import get_logger

log = get_logger(__name__)

# list plugins
__all__ = [ basename(f).split('.')[0] for f in os.listdir(os.path.dirname(__file__)) if f != '__init__.py']
log.debug(f'loading {__all__}')

# import plugins
from . import *
