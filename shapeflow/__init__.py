import os
import abc
import glob
import shutil
import pathlib
import copy
import re
import sqlite3
import datetime
import logging
from multiprocessing import cpu_count

from typing import Dict, Any, Type
from pathlib import Path
from enum import Enum

from contextlib import contextmanager

import yaml

from pydantic import BaseModel, Field, FilePath, DirectoryPath, validator
import diskcache


__version__: str = '0.4.3'
"""shapeflow library version
"""

# Get root directory
_user_dir = pathlib.Path.home()
if os.name == 'nt':  # if running on Windows
    _subdirs = ['AppData', 'Roaming', 'shapeflow']
else:
    _subdirs = ['.local', 'share', 'shapeflow']

ROOTDIR = Path(_user_dir, *_subdirs)
"""application root directory
"""

_SETTINGS_FILE = ROOTDIR / 'settings.yaml'

if not ROOTDIR.is_dir():
    _path = _user_dir
    for _subdir in _subdirs:
        _path = _path / _subdir
        if not _path.is_dir():
            _path.mkdir()


class _Settings(BaseModel):
    """Abstract application settings
    """

    class Config:
        validate_assignment = True

    def to_dict(self) -> dict:
        """
        Returns
        -------
        dict
            Application settings as a dict

        """
        d: dict = {}
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
                    k:str(v)  # type: ignore
                })            # todo: fix ` Dict entry 0 has incompatible type "str": "str"; expected "str": "Dict[str, Any]" `
            else:
                d.update({
                    k:v
                })
        return d

    @contextmanager
    def override(self, overrides: dict):  # todo: consider deprecating in favor of mocks
        """Override some parameters of the settings in a context.
        Settings will only be modified within this context and restored to
        their previous values afterwards.
        Usage::
            with settings.override({"parameter": "override value"}):
                <do something>

        Parameters
        ----------
        overrides: dict
            A ``dict`` mapping field names to values with which to
            override those fields
        """
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
    def schema(cls, by_alias: bool = True, ref_template: str = '') -> Dict[str, Any]:
        """Inject title & description into schema ~ lost due to Enum bugs.
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
    """Format settings"""
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f', description="date/time format")
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S', description="file system date/time format")


VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")


class LoggingLevel(str, Enum):
    critical = "critical"
    error = "error"
    warning = "warning"
    info = "info"
    debug = "debug"
    vdebug = "vdebug"

    @property
    def level(self) -> int:
        _levels: dict = {
            LoggingLevel.critical: logging.CRITICAL,
            LoggingLevel.error: logging.ERROR,
            LoggingLevel.warning: logging.WARNING,
            LoggingLevel.info: logging.INFO,
            LoggingLevel.debug: logging.DEBUG,
            LoggingLevel.vdebug: VDEBUG
        }
        return _levels[self]


class LogSettings(_Settings):
    """Log settings"""

    path: FilePath = Field(default=str(ROOTDIR / 'current.log'), title='running log file')
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'log'), title='log file directory')
    keep: int = Field(default=16, title="# of log files to keep")
    lvl_console: LoggingLevel = Field(default=LoggingLevel.debug, title="logging level (Python console)")
    lvl_file: LoggingLevel = Field(default=LoggingLevel.debug, title="logging level (file)")

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)
    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class CacheSettings(_Settings):
    """Cache settings"""

    dir: DirectoryPath = Field(default=str(ROOTDIR / 'cache'), title="cache directory")
    size_limit_gb: float = Field(default=4.0, title="cache size limit (GB)")
    do_cache: bool = Field(default=True, title="use the cache")
    resolve_frame_number: bool = Field(default=True, title="resolve to (nearest) cached frame numbers")
    block_timeout: float = Field(default=0.1, title="wait for blocked item (s)")
    reset_on_error: bool = Field(default=False, title="reset the cache if it can't be opened")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class RenderSettings(_Settings):
    """Rendering settings"""

    dir: DirectoryPath = Field(default=str(ROOTDIR / 'render'), title="render directory")
    keep: bool = Field(default=False, title="keep files after rendering")

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class DatabaseSettings(_Settings):
    """Database settings"""

    path: FilePath = Field(default=str(ROOTDIR / 'history.db'), title="database file")
    cleanup_interval: int = Field(default=7, title='clean-up interval (days)')

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class ResultSaveMode(str, Enum):
    """Where (or whether) to save results"""

    skip = "skip"
    next_to_video = "next to video file"
    next_to_design = "next to design file"
    directory = "in result directory"


class ApplicationSettings(_Settings):
    """Application settings"""

    save_state: bool = Field(default=True, title="save application state on exit")
    load_state: bool = Field(default=False, title="load application state on start")
    state_path: FilePath = Field(default=str(ROOTDIR / 'state'), title="application state file")
    recent_files: int = Field(default=16, title="# of recent files to fetch")
    video_pattern: str = Field(default="*.mp4 *.avi *.mov *.mpv *.mkv", title="video file pattern")
    design_pattern: str = Field(default="*.svg", title="design file pattern")
    save_result_auto: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (auto)")
    save_result_manual: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (manual)")
    result_dir: DirectoryPath = Field(default=str(ROOTDIR / 'results'), title="result directory")
    cancel_on_q_stop: bool = Field(default=False, title="cancel running analyzers when stopping queue")
    threads: int = Field(default=cpu_count(), title="# of threads")

    _validate_dir = validator('result_dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)
    _validate_state_path = validator('state_path', allow_reuse=True, pre=True)(_Settings._validate_filepath)

    @validator('threads', pre=True)
    def _validate_threads(cls, value):
        if value < 8:
            return 8  # At least 8 threads to run decently
        else:
            return value


class Settings(_Settings):
    """shapeflow settings"""

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
"""This global :class:`~shapeflow.Settings` instance is used throughout the
    library
"""


def _load_settings(path: str = str(_SETTINGS_FILE)) -> Settings:  # todo: if there are unexpected fields: warn, don't crash
    """Load the settings from .yaml"""

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


def save_settings(s: Settings, path: str = str(_SETTINGS_FILE)):
    """Save the settings to .yaml"""
    with open(path, 'w+') as f:
        yaml.safe_dump(s.to_dict(), f)


# Instantiate global settings object
if not os.path.isfile(_SETTINGS_FILE):
    settings = Settings()
else:
    settings = _load_settings(str(_SETTINGS_FILE))


save_settings(settings)


def update_settings(s: dict) -> dict:
    """Update the global settings instance.
    Note: doing `settings = Settings(**new_settings)` would prevent
    importing modules from accessing the updated settings!

    Parameters
    ----------
    s : dict
        new settings to integrate into the global settings

    Returns
    -------
    dict
        the current global settings as a ``dict``
    """
    for cat, cat_new in s.items():
        sub = getattr(settings, cat)
        for kw, val in cat_new.items():
            setattr(sub, kw, val)

    save_settings(settings)
    return settings.to_dict()


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
_console_handler.setLevel(settings.log.lvl_console.level)

_file_handler = logging.FileHandler(str(settings.log.path))
_file_handler.setLevel(settings.log.lvl_file.level)

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


def get_logger(name: str, log_settings: LogSettings = settings.log) -> Logger:
    """Get a new :class:`~shapeflow.Logger` object

    Parameters
    ----------
    name : str
        name of the logger
    log_settings : LogSettings
        logger settings (the global settings `shapeflow.settings.log` are used
        by default)

    Returns
    -------
    Logger
        a fresh logging handle
    """
    if log_settings is None:
        log_settings = LogSettings()

    logger = Logger(name)
    # log at the _least_ restrictive level
    logger.setLevel(
        min([log_settings.lvl_console.level, log_settings.lvl_file.level])
    )

    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

    logger.vdebug(f'new logger')
    return logger


log = get_logger(__name__)
log.info(f"v{__version__}")
log.debug(f"settings: {settings.dict()}")


def get_cache(s: Settings = settings, retry: bool = False) -> diskcache.Cache:
    """Get a new :class:`diskcache.Cache` object
    In some rare cases this can fail due to a corrupt cache.
    If ``settings.cache.reset_on_error`` is on, and an exception is
    raised the cache directory is removed and :func:`get_cache` is
    called again with ``retry`` set to ``True``.

    Parameters
    ----------
    s : Settings

    retry : bool
        Whether this call is a "retry call".
        Defaults to ``False``, i.e. a first call

    Returns
    -------
    diskcache.Cache
        a fresh cache handle

    """
    try:
        return diskcache.Cache(
            directory=str(s.cache.dir),
            size_limit=s.cache.size_limit_gb * 1e9
        )
    except sqlite3.OperationalError as e:
        log.error(f"could not open cache - {e.__class__.__name__}: {str(e)}")
        if not retry:
            if settings.cache.reset_on_error:
                log.error(f"removing cache directory")
                shutil.rmtree(str(s.cache.dir))
            log.error(f"trying to open cache again...")
            get_cache(settings, retry=True)
        else:
            log.error(f"could not open cache on retry")
            raise e
