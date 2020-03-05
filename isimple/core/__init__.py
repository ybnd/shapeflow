import os
import pathlib
import re

import yaml

from _collections import defaultdict
from dataclasses import dataclass, field

import logging
VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")

# Get root directory
_user_dir = str(pathlib.Path.home())  # todo: where is this on Windows?
_subdirs = ['.local', 'share', 'isimple']  # todo: does this make sense on windows?

ROOTDIR = os.path.join(_user_dir, os.path.join(*_subdirs))
_SETTINGS_FILE = os.path.join(ROOTDIR, 'settings.yaml')
if not os.path.isdir(ROOTDIR):
    _path = _user_dir
    for _subdir in _subdirs:
        _path = os.path.join(_path, _subdir)
        if not os.path.isdir(_path):
            os.mkdir(_path)


@dataclass
class Settings(object):
    def to_dict(self):
        d = {k:v or v for k,v in self.__dict__.items()}
        d.update({k:v.to_dict() for k,v in d.items() if isinstance(v, Settings)})
        return d


_levels: dict = defaultdict(default_factory=lambda: logging.INFO)
_levels.update({
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'vdebug': VDEBUG,
    'notset': logging.NOTSET,
})


@dataclass
class LogSettings(Settings):  # todo: this class should track whether path exists
    path: str = field(default=os.path.join(ROOTDIR, 'log'))
    lvl_global: int = field(default=logging.INFO)
    lvl_console: int = field(default=logging.INFO)
    lvl_file: int = field(default=logging.INFO)

    def to_dict(self):
        d = super().to_dict()
        _inverse = {v: k for k, v in _levels.items()}
        d.update(
            {k:_inverse[v] for k,v in d.items()
            if k in ('lvl_global', 'lvl_console', 'lvl_file')}
        )
        return d


@dataclass
class CacheSettings(Settings):  # todo: this class should track whether path exists
    path: str = field(default=os.path.join(ROOTDIR, 'cache'))


@dataclass
class RenderSettings(Settings):  # todo: this class should track whether path exists
    path: str = field(default=os.path.join(ROOTDIR, 'render'))


@dataclass
class INI(Settings):
    log:    LogSettings = field(default=LogSettings())
    cache:  CacheSettings = field(default=CacheSettings())
    render: RenderSettings = field(default=RenderSettings())


def _load_ini(path: str = _SETTINGS_FILE) -> INI:
    with open(path, 'r') as f:
        settings = yaml.safe_load(f)

        if settings is not None:
            return INI(  # todo: could be included as a factory method in INI
                log=LogSettings(
                    **{k:_levels[str(v).lower()] for k,v in settings['log'].items()
                       if k in ('lvl_global', 'lvl_console', 'lvl_file')}
                ),
                cache=CacheSettings(**settings['cache']),
                render=RenderSettings(**settings['render']),
            )
        else:
            return INI()



def _save_ini(settings: Settings, path: str = _SETTINGS_FILE):
    with open(path, 'w+') as f:
        yaml.safe_dump(settings.to_dict(),f)


if not os.path.isfile(_SETTINGS_FILE):
    SETTINGS = INI()
else:
    SETTINGS = _load_ini(_SETTINGS_FILE)
_save_ini(SETTINGS)

VDEBUG = 9


class CustomLogger(logging.Logger):
    _pattern = re.compile('(\n|\r|\t| [ ]+)')

    def debug(self, msg, *args, **kwargs):
        super().debug(self._remove_newlines(msg))

    def info(self, msg, *args, **kwargs):
        super().info(self._remove_newlines(msg))

    def warning(self, msg, *args, **kwargs):
        super().warning(self._remove_newlines(msg))

    def error(self, msg, *args, **kwargs):
        super().error(self._remove_newlines(msg))

    def critical(self, msg, *args, **kwargs):
        super().critical(self._remove_newlines(msg))

    def vdebug(self, message, *args, **kwargs):
        if self.isEnabledFor(VDEBUG):
            self.log(
                VDEBUG, self._remove_newlines(message), *args, **kwargs
            )

    def _remove_newlines(self, msg: str) -> str:
        return self._pattern.sub(' ', msg)


def get_logger(name: str = __name__, settings: LogSettings = SETTINGS.log) -> CustomLogger:
    if settings is None:
        settings = LogSettings()

    log = CustomLogger(name)
    log.setLevel(settings.lvl_global)  # todo: should this be max([lvl_file, lvl_console])?

    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(settings.lvl_console)

    _file_handler = logging.FileHandler(settings.path)
    _file_handler.setLevel(settings.lvl_file)

    _formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _console_handler.setFormatter(_formatter)
    _file_handler.setFormatter(_formatter)

    log.addHandler(_console_handler)
    log.addHandler(_file_handler)

    return log
