import os
import abc
import glob
import shutil
import pathlib
import re
import datetime

import yaml

from _collections import defaultdict
from dataclasses import dataclass, field

import diskcache

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
class _Settings(abc.ABC):
    def to_dict(self):
        d = {k:v or v for k,v in self.__dict__.items()}
        d.update({k:v.to_dict() for k,v in d.items() if isinstance(v, _Settings)})
        return d


@dataclass
class FormatSettings(_Settings):
    datetime_format: str = field(default='%Y/%m/%d %H:%M:%S.%f')
    datetime_format_fs: str = field(default='%Y-%m-%d_%H-%M-%S_%f')



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
class LogSettings(_Settings):  # todo: this class should track whether path exists
    path: str = field(default=os.path.join(ROOTDIR, 'current.log'))
    dir: str = field(default=os.path.join(ROOTDIR, 'log'))
    keep: int = field(default=3)
    lvl_console: int = field(default=logging.INFO)
    lvl_file: int = field(default=logging.INFO)

    def to_dict(self):
        d = super().to_dict()
        _inverse = {v: k for k, v in _levels.items()}
        d.update(
            {k:_inverse[v] for k,v in d.items()
            if k in ('lvl_console', 'lvl_file')}
        )
        return d


@dataclass
class CacheSettings(_Settings):  # todo: this class should track whether path exists
    dir: str = field(default=os.path.join(ROOTDIR, 'cache'))
    size_limit: int = field(default=2**32)


@dataclass
class RenderSettings(_Settings):  # todo: this class should track whether path exists
    dir: str = field(default=os.path.join(ROOTDIR, 'render'))


@dataclass()
class DatabaseSettings(_Settings):
    path: str = field(default=os.path.join(ROOTDIR, 'history.db'))


@dataclass
class Settings(_Settings):
    log: LogSettings = field(default=LogSettings())
    cache: CacheSettings = field(default=CacheSettings())
    render: RenderSettings = field(default=RenderSettings())
    format: FormatSettings = field(default=FormatSettings())
    db: DatabaseSettings = field(default=DatabaseSettings())

    @classmethod
    def from_dict(cls, settings: dict):
        for k in ('log', 'cache', 'render', 'format', 'db'):
            if k not in settings:
                settings.update({k:{}})

        return cls(
            log=LogSettings(
                **{
                    k: _levels[str(v).lower()]
                    if k in ('lvl_console', 'lvl_file')
                    else v for k, v in settings['log'].items()
                }
            ),
            cache=CacheSettings(**settings['cache']),
            render=RenderSettings(**settings['render']),
            format=FormatSettings(**settings['format']),
            db=DatabaseSettings(**settings['db']),
        )


def _load_settings(path: str = _SETTINGS_FILE) -> Settings:  # todo: if there are unexpected fields: warn, don't crash
    with open(path, 'r') as f:
        settings = yaml.safe_load(f)

        # Get settings
        if settings is not None:
            ini = Settings.from_dict(settings)
        else:
            ini = Settings()

        # Create directories if needed
        for dir in (ini.log.dir, ini.render.dir, ini.cache.dir):
            if not os.path.isdir(dir):
                os.mkdir(dir)

        # Move the previous log file to ROOTDIR/log
        if os.path.isfile(ini.log.path):
            shutil.move(
                ini.log.path,
                os.path.join(
                    ini.log.dir,
                    datetime.datetime.fromtimestamp(
                        os.path.getmtime(ini.log.path)
                    ).strftime(ini.format.datetime_format_fs) + '.log'
                )
            )

        # If more files than specified in ini.log.keep, remove the oldest
        files = glob.glob(os.path.join(ini.log.dir, '*.log'))
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        while len(files) > ini.log.keep:
            os.remove(files.pop())

        return ini


def _save_settings(settings: _Settings, path: str = _SETTINGS_FILE):
    with open(path, 'w+') as f:
        yaml.safe_dump(settings.to_dict(),f)


if not os.path.isfile(_SETTINGS_FILE):
    settings = Settings()
else:
    settings = _load_settings(_SETTINGS_FILE)
_save_settings(settings)

cache = diskcache.Cache(settings.cache.dir, 2**32) # todo: size limit should be in settings.cache


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


# Define log handlers
_console_handler = logging.StreamHandler()
_console_handler.setLevel(settings.log.lvl_console)

_file_handler = logging.FileHandler(settings.log.path)
_file_handler.setLevel(settings.log.lvl_file)

_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_console_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)

# Handle logs from other packages
waitress = logging.getLogger("waitress")
waitress.addHandler(_console_handler)
waitress.addHandler(_file_handler)
waitress.propagate = False


def get_logger(name: str = __name__, settings: LogSettings = settings.log) -> CustomLogger:
    if settings is None:
        settings = LogSettings()

    log = CustomLogger(name)
    log.setLevel(max([settings.lvl_console, settings.lvl_file]))

    log.addHandler(_console_handler)
    log.addHandler(_file_handler)

    return log
