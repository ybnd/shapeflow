import os
import abc
import glob
import shutil
import pathlib
import copy
import re
import datetime
import logging

from pathlib import Path
from enum import Enum

from contextlib import contextmanager

import yaml

from _collections import defaultdict
from pydantic import BaseModel, Field, FilePath, DirectoryPath, validator
from pydantic.error_wrappers import ValidationError, ErrorWrapper
from pydantic.errors import PathNotExistsError, PathNotADirectoryError, PathNotAFileError

import diskcache

# Library version
__version__: str = '0.3.13'

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
        d = {}
        for k,v in self.__dict__.items():
            if isinstance(v, _Settings):
                d.update({
                    k:v.to_dict()
                })
            elif isinstance(v, Enum):
                d.update({
                    k:v.value
                })
            elif isinstance(v, Path):
                d.update({
                    k:str(v)
                })
            else:
                d.update({
                    k:v
                })
        return d

    @contextmanager
    def override(self, overrides: dict):
        originals: dict = {}
        try:
            for attribute, value in overrides.items():
                originals[attribute] = copy.deepcopy(
                    getattr(self, attribute))
                setattr(self, attribute, value)
            yield
        finally:
            for attribute, original in originals.items():
                setattr(self, attribute, original)

    @classmethod
    def _validate_filepath(cls, value):
        if not isinstance(value, Path):
            value = Path(value)

        if not value.exists() and not value.is_file():
            value.touch()

        return value

    @classmethod
    def _validate_directorypath(cls, value):
        if not isinstance(value, Path):
            value = Path(value)

        if not value.exists() and not value.is_dir():
            value.mkdir()

        return value

class FormatSettings(_Settings):
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f', description="date/time format")
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S', description="file system date/time format")


VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")


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

class LoggingLevel(str, Enum):
    critical = 'critical'
    error =  'error'
    warning = "warning"
    info = "info"
    debug = "debug"
    vdebug = "vdebug"

class LogSettings(_Settings):
    path: FilePath = Field(default=os.path.join(ROOTDIR, 'current.log'), description='running log file')
    dir: DirectoryPath = Field(default=os.path.join(ROOTDIR, 'log'), description='log file directory')
    keep: int = Field(default=16, description="# of log files to keep")
    lvl_console: LoggingLevel = Field(default=LoggingLevel.info, description="logging level (Python console)")
    lvl_file: LoggingLevel = Field(default=LoggingLevel.info, description="logging level (file)")

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)
    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class CacheSettings(_Settings):
    dir: DirectoryPath = Field(default=os.path.join(ROOTDIR, 'cache'), description="cache directory")
    size_limit_gb: int = Field(default=4, description="cache size limit (GB)")
    do_cache: bool = Field(default=True, description="use the cache")
    do_background: bool = Field(default=True, description="cache in the background")
    resolve_frame_number: bool = Field(default=True, description="resolve to (nearest) cached frame numbers")
    block_timeout: float = Field(default=0.1, description="wait for blocked item (s)")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class RenderSettings(_Settings):
    dir: DirectoryPath = Field(default=os.path.join(ROOTDIR, 'render'), description="render directory")
    keep: bool = Field(default=False, description="keep files after rendering")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class DatabaseSettings(_Settings):
    path: FilePath = Field(default=os.path.join(ROOTDIR, 'history.db'), description="database file")

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class ResultSaveMode(str, Enum):
    skip = "skip"
    next_to_video = "next to video file"
    next_to_design = "next to design file"
    directory = "in result directory"


class ApplicationSettings(_Settings):
    save_state: bool = Field(default=True, description="save application state")
    load_state: bool = Field(default=False, description="load application state on start")
    state_path: FilePath = Field(default=os.path.join(ROOTDIR, 'state'), description="application state file")
    recent_files: int = Field(default=16, description="# of recent files to fetch")
    edit_json: bool = Field(default=False, description="show JSON configuration editor by default")
    save_result: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, description="result save mode")
    result_dir: DirectoryPath = Field(default=os.path.join(ROOTDIR, 'results'), description="result directory")

    _validate_dir = validator('result_dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)
    _validate_state_path = validator('state_path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class Settings(_Settings):
    log: LogSettings = Field(default=LogSettings(), description="Logging")
    cache: CacheSettings = Field(default=CacheSettings(), description="Caching")
    render: RenderSettings = Field(default=RenderSettings(), description="SVG Rendering")
    format: FormatSettings = Field(default=FormatSettings(), description="Formatting")
    db: DatabaseSettings = Field(default=DatabaseSettings(), description="Database")
    app: ApplicationSettings = Field(default=ApplicationSettings(), description="Application")

    @classmethod
    def from_dict(cls, settings: dict):
        for k in cls.__fields__.keys():
            if k not in settings:
                settings.update({k:{}})

        return cls(
            **{field.name:field.type_(**settings[field.name])
               for field in cls.__fields__.values()}
        )


global settings


def _load_settings(path: str = _SETTINGS_FILE) -> Settings:  # todo: if there are unexpected fields: warn, don't crash
    with open(path, 'r') as f:
        settings_yaml = yaml.safe_load(f)

        # Get settings
        if settings_yaml is not None:
            settings = Settings.from_dict(settings_yaml)
        else:
            settings = Settings()

        # Move the previous log file to ROOTDIR/log
        if settings.log.path.is_file():
            shutil.move(
                str(settings.log.path),  # todo: convert to pathlib
                os.path.join(
                    str(settings.log.dir),
                    datetime.datetime.fromtimestamp(
                        os.path.getmtime(str(settings.log.path))
                    ).strftime(settings.format.datetime_format_fs) + '.log'
                )
            )

        # If more files than specified in ini.log.keep, remove the oldest
        files = glob.glob(os.path.join(str(settings.log.dir), '*.log'))  # todo: convert to pathlib
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        while len(files) > settings.log.keep:
            os.remove(files.pop())

        return settings


def save_settings(settings: Settings, path: str = _SETTINGS_FILE):
    with open(path, 'w+') as f:
        yaml.safe_dump(settings.to_dict(),f)

if not os.path.isfile(_SETTINGS_FILE):
    settings = Settings()
else:
    settings = _load_settings(_SETTINGS_FILE)


save_settings(settings)


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
    _pattern = re.compile(r'(\n|\r|\t| [ ]+)')

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

_file_handler = logging.FileHandler(str(settings.log.path))
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
        directory=str(settings.cache.dir),
        size_limit=settings.cache.size_limit_gb * 1e9
    )


# cache = get_cache()  # todo: why is this required?


def get_logger(name: str, settings: LogSettings = settings.log) -> Logger:
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


log = get_logger(__name__)
log.info(f"v{__version__}")
log.debug(f"settings: {settings.dict()}")
