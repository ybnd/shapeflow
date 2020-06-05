import os
import abc
import glob
import shutil
import pathlib
import re
import datetime
import logging

import yaml

from _collections import defaultdict
from pydantic import BaseModel, Field

import diskcache

# Library version
__version__: str = '0.3.10'

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


class _Settings(BaseModel):
    def to_dict(self):
        d = {k:v or v for k,v in self.__dict__.items()}
        d.update({k:v.to_dict() for k,v in d.items() if isinstance(v, _Settings)})
        return d


class FormatSettings(_Settings):
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f')
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S_%f')


_levels: dict = defaultdict(default_factory=lambda: logging.INFO)
_levels.update({
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'vdebug': VDEBUG,
    'notset': logging.NOTSET,
    'default': logging.INFO
})


class LogSettings(_Settings):  # todo: this class should track whether path exists
    path: str = Field(default=os.path.join(ROOTDIR, 'current.log'), description='Current log file')
    dir: str = Field(default=os.path.join(ROOTDIR, 'log'), description='Log file directory')
    keep: int = Field(default=3, description="Number of log files to keep")
    lvl_console: str = Field(default='info', description="Logging level (Python console)")
    lvl_file: str = Field(default='info', description="Logging level (file)")


class CacheSettings(_Settings):  # todo: this class should track whether path exists
    dir: str = Field(default=os.path.join(ROOTDIR, 'cache'))
    size_limit_gb: int = Field(default=4)
    resolve_frame_number: bool = Field(default=True)


class RenderSettings(_Settings):  # todo: this class should track whether path exists
    dir: str = Field(default=os.path.join(ROOTDIR, 'render'))
    keep: bool = Field(default=False)


class DatabaseSettings(_Settings):
    path: str = Field(default=os.path.join(ROOTDIR, 'history.db'))
    recent_files: int = Field(default=16)


class Settings(_Settings):
    log: LogSettings = Field(default=LogSettings())
    cache: CacheSettings = Field(default=CacheSettings())
    render: RenderSettings = Field(default=RenderSettings())
    format: FormatSettings = Field(default=FormatSettings())
    db: DatabaseSettings = Field(default=DatabaseSettings())

    @classmethod
    def from_dict(cls, settings: dict):
        for k in ('log', 'cache', 'render', 'format', 'db'):
            if k not in settings:
                settings.update({k:{}})

        return cls(
            log=LogSettings(**settings['log']),
            cache=CacheSettings(**settings['cache']),
            render=RenderSettings(**settings['render']),
            format=FormatSettings(**settings['format']),
            db=DatabaseSettings(**settings['db']),
        ) # type: ignore


def _load_settings(path: str = _SETTINGS_FILE) -> Settings:  # todo: if there are unexpected fields: warn, don't crash
    with open(path, 'r') as f:
        settings_yaml = yaml.safe_load(f)

        # Get settings
        if settings_yaml is not None:
            settings = Settings.from_dict(settings_yaml)
        else:
            settings = Settings()

        # Create directories if needed
        for dir in (settings.log.dir, settings.render.dir, settings.cache.dir):
            if not os.path.isdir(dir):
                os.mkdir(dir)

        # Move the previous log file to ROOTDIR/log
        if os.path.isfile(settings.log.path):
            shutil.move(
                settings.log.path,
                os.path.join(
                    settings.log.dir,
                    datetime.datetime.fromtimestamp(
                        os.path.getmtime(settings.log.path)
                    ).strftime(settings.format.datetime_format_fs) + '.log'
                )
            )

        # If more files than specified in ini.log.keep, remove the oldest
        files = glob.glob(os.path.join(settings.log.dir, '*.log'))
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        while len(files) > settings.log.keep:
            os.remove(files.pop())

        return settings


if not os.path.isfile(_SETTINGS_FILE):
    settings = Settings()
else:
    settings = _load_settings(_SETTINGS_FILE)


def save_settings(settings: Settings, path: str = _SETTINGS_FILE):
    with open(path, 'w+') as f:
        yaml.safe_dump(settings.to_dict(),f)


save_settings(settings)
# cache = diskcache.Cache(settings.cache.dir, settings.cache.size_limit_gb * 1e9) # todo: size limit should be in settings.cache


def update_settings(new_settings: dict):
    """Update global settings ~ dict
        Note: doing `settings = Settings(**new_settings)` would prevent
        importing modules from accessing the updated settings!
    """
    for cat, cat_new in new_settings.items():
        sub = getattr(settings, cat)
        for kw, val in cat_new.items():
            setattr(sub, kw, val)

    save_settings(settings)


class Logger(logging.Logger):
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
_console_handler.setLevel(_levels[settings.log.lvl_console])

_file_handler = logging.FileHandler(settings.log.path)
_file_handler.setLevel(_levels[settings.log.lvl_file])

_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
_console_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)

# Handle logs from other packages
waitress = logging.getLogger("waitress")
waitress.addHandler(_console_handler)
waitress.addHandler(_file_handler)
waitress.propagate = False


def get_cache(settings: Settings = settings) -> diskcache.Cache:
    return diskcache.Cache(
        directory=settings.cache.dir,
        size_limit=settings.cache.size_limit_gb * 1e9
    )


cache = get_cache()  # todo: why is this required?


def get_logger(name: str = __name__, settings: LogSettings = settings.log) -> Logger:
    if settings is None:
        settings = LogSettings()

    log = Logger(name)
    log.setLevel(
        max([_levels[settings.lvl_console], _levels[settings.lvl_file]])
    )

    log.addHandler(_console_handler)
    log.addHandler(_file_handler)

    log.vdebug(f'new logger')
    return log
