import os
import yaml
import pathlib

from isimple.core import ROOTDIR
from isimple.core.config import Config

# Get settings


# Get subdirectories
RENDERDIR = os.path.join(ROOTDIR, 'render')
CACHEDIR = os.path.join(ROOTDIR, 'cache')


if not os.path.isdir(RENDERDIR):
    os.mkdir(RENDERDIR)

if not os.path.isdir(CACHEDIR):
    os.mkdir(CACHEDIR)


DB_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S.%f'
DB_LIST_SEPARATOR = '\n'
