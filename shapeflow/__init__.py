import os
import logging
from pathlib import Path

__version__: str = '0.4.3'

import pathlib

"""Library version
"""

VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")

# Get root directory
_user_dir = pathlib.Path.home()
if os.name == 'nt':  # if running on Windows
    _subdirs = ['AppData', 'Roaming', 'shapeflow']
else:
    _subdirs = ['.local', 'share', 'shapeflow']

ROOTDIR = Path(_user_dir, *_subdirs)
"""Root directory of the application.

Linux: ``/home/<user>/.local/share/shapeflow``

Windows: ``C:\\Users\\<user>\\AppData\\Roaming\\shapeflow``
"""

if not ROOTDIR.is_dir():
    _path = _user_dir
    for _subdir in _subdirs:
        _path = _path / _subdir
        if not _path.is_dir():
            _path.mkdir()