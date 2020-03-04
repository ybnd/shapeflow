import os
import pathlib


_user_dir = str(pathlib.Path.home())  # todo: where is this on Windows?
_subdirs = ['.local', 'share', 'isimple']

ROOTDIR = os.path.join(
    _user_dir, '/'.join(_subdirs)
)

if not os.path.isdir(ROOTDIR):
    _path = _user_dir
    for _subdir in _subdirs:
        _path = os.path.join(_path, _subdir)
        if not os.path.isdir(_path):
            os.mkdir(_path)
