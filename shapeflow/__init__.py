import os
import abc
import glob
import shutil
import pathlib
import copy
import re
import datetime
import logging

from typing import Dict, Any, Type
from pathlib import Path
from enum import IntEnum

from contextlib import contextmanager

import yaml

from pydantic import BaseModel, Field, FilePath, DirectoryPath, validator
from pydantic.error_wrappers import ValidationError, ErrorWrapper
from pydantic.errors import PathNotExistsError, PathNotADirectoryError, PathNotAFileError

import diskcache

# Library version
__version__: str = '0.4.0'

# Get root directory
_user_dir = pathlib.Path.home()
if os.name == 'nt':  # if running on Windows
    _subdirs = ['AppData', 'Roaming', 'shapeflow']
else:
    _subdirs = ['.local', 'share', 'shapeflow']

ROOTDIR = Path(_user_dir, *_subdirs)

_SETTINGS_FILE = ROOTDIR / 'settings.yaml'

if not ROOTDIR.is_dir():
    _path = _user_dir
    for _subdir in _subdirs:
        _path = _path / _subdir
        if not _path.is_dir():
            _path.mkdir()


class _Settings(BaseModel):
    class Config:
        validate_assignment = True

    def to_dict(self):
        d = {}
        for k,v in self.__dict__.items():
            if isinstance(v, _Settings):
                d.update({
                    k:v.to_dict()
                })
            elif isinstance(v, IntEnum):
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
                    getattr(self, attribute)
                )
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

    @classmethod
    def schema(cls, by_alias: bool = True) -> Dict[str, Any]:
        """
        Inject title & description into schema ~ lost due to Enum bugs.
        https://github.com/samuelcolvin/pydantic/pull/1749
        """

        schema = super().schema(by_alias)

        def _inject(class_: Type[_Settings], schema, definitions):
            for field in class_.__fields__.values():
                if 'properties' in schema and field.alias in schema['properties']:
                    if 'title' not in schema['properties'][field.alias]:
                        schema['properties'][field.alias][
                            'title'] = field.field_info.title
                    if field.field_info.description is not None and 'description' not in schema['properties'][field.alias]:
                        schema['properties'][field.alias]['description'] = field.field_info.description
                if issubclass(field.type_, _Settings):
                    # recurse into nested _Settings classes
                    _inject(field.type_, definitions[field.type_.__name__], definitions)
            return schema

        return _inject(cls, schema, schema['definitions'])


class FormatSettings(_Settings):
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f', description="date/time format")
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S', description="file system date/time format")


VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")


class LoggingLevel(IntEnum):
    critical: int = logging.CRITICAL
    error: int = logging.ERROR
    warning: int = logging.WARNING
    info: int = logging.INFO
    debug: int = logging.DEBUG
    vdebug: int = VDEBUG
    notset: int = logging.NOTSET


class LogSettings(_Settings):
    path: FilePath = Field(default=str(ROOTDIR / 'current.log'), title='running log file')
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'log'), title='log file directory')
    keep: int = Field(default=16, title="# of log files to keep")
    lvl_console: LoggingLevel = Field(default=LoggingLevel.debug, title="logging level (Python console)")
    lvl_file: LoggingLevel = Field(default=LoggingLevel.debug, title="logging level (file)")

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)
    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class CacheSettings(_Settings):
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'cache'), title="cache directory")
    size_limit_gb: float = Field(default=4.0, title="cache size limit (GB)")
    do_cache: bool = Field(default=True, title="use the cache")
    resolve_frame_number: bool = Field(default=True, title="resolve to (nearest) cached frame numbers")
    block_timeout: float = Field(default=0.1, title="wait for blocked item (s)")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class RenderSettings(_Settings):
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'render'), title="render directory")
    keep: bool = Field(default=False, title="keep files after rendering")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class DatabaseSettings(_Settings):
    path: FilePath = Field(default=str(ROOTDIR / 'history.db'), title="database file")
    cleanup_interval: int = Field(default=7, title='clean-up interval (days)')

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class ResultSaveMode(IntEnum):
    skip: int = 0
    next_to_video: int = 1
    next_to_design: int = 2
    directory: int = 3


class ApplicationSettings(_Settings):
    save_state: bool = Field(default=True, title="save application state on exit")
    load_state: bool = Field(default=False, title="load application state on start")
    state_path: FilePath = Field(default=str(ROOTDIR / 'state'), title="application state file")
    recent_files: int = Field(default=16, title="# of recent files to fetch")
    save_result: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode")
    result_dir: DirectoryPath = Field(default=str(ROOTDIR / 'results'), title="result directory")
    cancel_on_q_stop: bool = Field(default=False, title="cancel running analyzers when stopping queue")

    _validate_dir = validator('result_dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)
    _validate_state_path = validator('state_path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class Settings(_Settings):
    app: ApplicationSettings = Field(default=ApplicationSettings(), title="Application")
    log: LogSettings = Field(default=LogSettings(), title="Logging")
    cache: CacheSettings = Field(default=CacheSettings(), title="Caching")
    render: RenderSettings = Field(default=RenderSettings(), title="SVG Rendering")
    format: FormatSettings = Field(default=FormatSettings(), title="Formatting")
    db: DatabaseSettings = Field(default=DatabaseSettings(), title="Database")

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
            s = Settings.from_dict(settings_yaml)
        else:
            s = Settings()

        # Move the previous log file to ROOTDIR/log
        if Path(s.log.path).is_file():
            shutil.move(
                s.log.path,  # todo: convert to pathlib
                os.path.join(
                    s.log.dir,
                    datetime.datetime.fromtimestamp(
                        os.path.getmtime(s.log.path)
                    ).strftime(s.format.datetime_format_fs) + '.log'
                )
            )

        # If more files than specified in ini.log.keep, remove the oldest
        files = glob.glob(os.path.join(s.log.dir, '*.log'))  # todo: convert to pathlib
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        while len(files) > s.log.keep:
            os.remove(files.pop())

        return s


def save_settings(s: Settings, path: str = _SETTINGS_FILE):
    with open(path, 'w+') as f:
        yaml.safe_dump(s.to_dict(), f)


if not os.path.isfile(_SETTINGS_FILE):
    settings = Settings()
else:
    settings = _load_settings(_SETTINGS_FILE)


save_settings(settings)


def update_settings(s: dict):
    """Update global settings ~ dict
        Note: doing `settings = Settings(**new_settings)` would prevent
        importing modules from accessing the updated settings!
    """
    for cat, cat_new in s.items():
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
_console_handler.setLevel(settings.log.lvl_console)

_file_handler = logging.FileHandler(str(settings.log.path))
_file_handler.setLevel(settings.log.lvl_file)

_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
_console_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)

# Handle logs from other packages
waitress = logging.getLogger("waitress")
waitress.addHandler(_console_handler)
waitress.addHandler(_file_handler)
waitress.propagate = False


def get_cache(s: Settings = settings) -> diskcache.Cache:
    return diskcache.Cache(
        directory=str(s.cache.dir),
        size_limit=s.cache.size_limit_gb * 1e9
    )


def get_logger(name: str, s: LogSettings = settings.log) -> Logger:
    if s is None:
        s = LogSettings()

    log = Logger(name)
    log.setLevel(
        max([s.lvl_console, s.lvl_file])
    )

    log.addHandler(_console_handler)
    log.addHandler(_file_handler)

    log.vdebug(f'new logger')
    return log


log = get_logger(__name__)
log.info(f"v{__version__}")
log.debug(f"settings: {settings.dict()}")
