"""Common elements.

* Application settings

* Logging

* Caching
"""

import os
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
"""Library version
"""

# Get root directory
_user_dir = pathlib.Path.home()
if os.name == 'nt':  # if running on Windows
    _subdirs = ['AppData', 'Roaming', 'shapeflow']
else:
    _subdirs = ['.local', 'share', 'shapeflow']

ROOTDIR = Path(_user_dir, *_subdirs)
"""Root directory of the application.

Linux: ``/home/<user>/.local/.share/shapeflow``

Windows: ``C:\\Users\\<user>\\AppData\\Roaming\\shapeflow``
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
        """Inject title & description into ``pydantic`` schema.

        These get lost due to some `bug`_ with ``Enum``.

        .. _bug: https://github.com/samuelcolvin/pydantic/pull/1749
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
    """Formatting settings
    """
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f', title="date/time format")
    """Base ``datetime`` `format string <dtfs_>`. 
    Defaults to ``'%Y/%m/%d %H:%M:%S.%f'``.

    .. _dtfs: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    """
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S', title="file system date/time format")
    """Filesystem-safe ``datetime`` `format string <dtfs_>`. 
    Used to append date & time to file names.
    Defaults to ``'%Y-%m-%d_%H-%M-%S'``.

    .. _dtfs: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    """


VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")


class LoggingLevel(str, Enum):
    """Logging level.
    """
    critical = "critical"
    """Only log critical (unrecoverable) errors
    """
    error = "error"
    """Only log errors
    """
    warning = "warning"
    """Only log warnings (or errors)
    """
    info = "info"
    """Log general information
    """
    debug = "debug"
    """Log debugging information
    """
    vdebug = "vdebug"
    """Log verbose debugging information
    """

    @property
    def level(self) -> int:
        """Return the ``int`` logging level for compatibility with built-in
        ``logging`` library
        """
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
    """Logging settings
    """
    path: FilePath = Field(default=str(ROOTDIR / 'current.log'), title='running log file')
    """The application logs to this file
    """
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'log'), title='log file directory')
    """This is the log directory. Logs from previous runs are stored here.
    """
    keep: int = Field(default=16, title="# of log files to keep")
    """The applications stores a number of old logs. 
    
    When the amount of log files in :attr:`shapeflow.LogSettings.dir` exceeds 
    this number, the oldest files are deleted.
    """
    lvl_console: LoggingLevel = Field(default=LoggingLevel.info, title="logging level (Python console)")
    """The level at which the application logs to the Python console.
    
    Defaults to :attr:`~shapeflow.LoggingLevel.info` to keep the console from 
    getting too spammy. 
    Set to a lower level such as :attr:`~shapeflow.LoggingLevel.debug` to show
    more detailed logs in the console.
    """
    lvl_file: LoggingLevel = Field(default=LoggingLevel.debug, title="logging level (file)")
    """The level at which the application logs to the log file at
    :attr:`~shapeflow.LogSettings.path`.
    
    Defaults to :attr:`shapeflow.LoggingLevel.debug`.
    """

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)
    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class CacheSettings(_Settings):
    """Caching settings
    """
    do_cache: bool = Field(default=True, title="use the cache")
    """Enables the cache. Set to ``True`` by default.
    
    Disabling the cache will make the application significantly slower.
    """
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'cache'), title="cache directory")
    """Where to keep the cache
    """
    size_limit_gb: float = Field(default=4.0, title="cache size limit (GB)")
    """How big the cache is allowed to get
    """
    resolve_frame_number: bool = Field(default=True, title="resolve to (nearest) cached frame numbers")
    """Whether to resolve frame numbers to the nearest requested frame numbers.
    
    Increases seeking performance, but may make it a bit more 'jumpy' if a low
    number of frames is requested for an analysis.
    """
    block_timeout: float = Field(default=0.1, title="wait for blocked item (s)")
    """How long to keep waiting for data that's actively being committed to the
    cache before giving up and computing it instead.
    
    In the rare case that two cachable data requests are being processed at the 
    same time, the first request will block the cache for those specific data
    and cause the second request to wait until it can grab this data from the 
    cache.
    This timeout prevents the second request from waiting forever until the
    first request finishes (for example, in case it crashes).
    """
    reset_on_error: bool = Field(default=False, title="reset the cache if it can't be opened")
    """Clear the cache if it can't be opened.
    
    In rare cases, ``diskcache`` may cache data in a way it can't read back.
    To recover from such an error, the cache will be cleared completely.
    The only downside to this is decreased performance for a short while.
    """

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class RenderSettings(_Settings):
    """Rendering settings
    """
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'render'), title="render directory")
    """The directory where SVG files should be rendered to
    """
    keep: bool = Field(default=False, title="keep files after rendering")
    """Keep rendered images after they've been used. 
    
    Disabled by default, you may want to enable this if you want to inspect the
    renders.
    """

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)


class DatabaseSettings(_Settings):
    """Database settings.
    """
    path: FilePath = Field(default=str(ROOTDIR / 'history.db'), title="database file")
    """The path to the database file
    """
    cleanup_interval: int = Field(default=7, title='clean-up interval (days)')
    """The database can get cluttered after a while, and will be cleaned at 
    this interval
    """

    _validate_path = validator('path', allow_reuse=True, pre=True)(_Settings._validate_filepath)


class ResultSaveMode(str, Enum):
    """Where (or whether) to save the results of an analysis
    """
    skip = "skip"
    """Don't save results at all
    """
    next_to_video = "next to video file"
    """Save results in the same directory as the video file that was analyzed
    """
    next_to_design = "next to design file"
    """Save results in the same directory as the design file that was analyzed
    """
    directory = "in result directory"
    """Save results in their own directory at 
    :attr:`shapeflow.ApplicationSettings.result_dir`
    """


class ApplicationSettings(_Settings):
    """Application settings.
    """
    save_state: bool = Field(default=True, title="save application state on exit")
    """Whether to save the application state when exiting the application
    """
    load_state: bool = Field(default=True, title="load application state on start")
    """Whether to load the application state when starting the application
    """
    state_path: FilePath = Field(default=str(ROOTDIR / 'state'), title="application state file")
    """Where to save the application state
    """
    recent_files: int = Field(default=16, title="# of recent files to fetch")
    """The number of recent files to show in the user interface
    """
    video_pattern: str = Field(default="*.mp4 *.avi *.mov *.mpv *.mkv", title="video file pattern")
    """Recognized video file extensions. 
    Defaults to `"*.mp4 *.avi *.mov *.mpv *.mkv"`.
    """
    design_pattern: str = Field(default="*.svg", title="design file pattern")
    """Recognized design file extensions. 
    Defaults to `"*.svg"`.
    """
    save_result_auto: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (auto)")
    """Where or whether to save results after each run of an analysis
    """
    save_result_manual: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (manual)")
    """Where or whether to save results that are exported manually 
    via the user interface
    """
    result_dir: DirectoryPath = Field(default=str(ROOTDIR / 'results'), title="result directory")
    """The path to the result directory
    """
    cancel_on_q_stop: bool = Field(default=False, title="cancel running analyzers when stopping queue")
    """Whether to cancel the currently running analysis when stopping a queue.
    
    Defaults to ``False``, i.e. the currently running analysis will be 
    completed first.
    """
    threads: int = Field(default=cpu_count(), title="# of threads")
    f"""The number of threads the server uses. Defaults to {cpu_count()}, the 
    number of logical cores of your machine's CPU.
    """

    _validate_dir = validator('result_dir', allow_reuse=True, pre=True)(_Settings._validate_directorypath)
    _validate_state_path = validator('state_path', allow_reuse=True, pre=True)(_Settings._validate_filepath)

    @validator('threads', pre=True, allow_reuse=True)
    def _validate_threads(cls, value):
        if value < 8:
            return 8  # At least 8 threads to run decently
        else:
            return value


class Settings(_Settings):
    """``shapeflow`` settings.

    * app: :class:`~shapeflow.ApplicationSettings`

    * log: :class:`~shapeflow.LogSettings`

    * cache: :class:`~shapeflow.CacheSettings`

    * render: :class:`~shapeflow.RenderSettings`

    * format: :class:`~shapeflow.FormatSettings`

    * db: :class:`~shapeflow.DatabaseSettings`
    """
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

settings: Settings
"""This global :class:`~shapeflow.Settings` object is used throughout the
   library
"""


def _load_settings() -> Settings:  # todo: if there are unexpected fields: warn, don't crash
    """Load :class:`~shapeflow.Settings` from .yaml
    """
    global settings

    if _SETTINGS_FILE.is_file():
        with open(_SETTINGS_FILE, 'r') as f:
            settings_yaml = yaml.safe_load(f)

            # Get settings
            if settings_yaml is not None:
                settings = Settings.from_dict(settings_yaml)
            else:
                settings = Settings()

            # Move the previous log file to ROOTDIR/log
            if Path(settings.log.path).is_file():
                shutil.move(
                    str(settings.log.path),  # todo: convert to pathlib
                    os.path.join(
                        settings.log.dir,
                        datetime.datetime.fromtimestamp(
                            os.path.getmtime(settings.log.path)
                        ).strftime(settings.format.datetime_format_fs) + '.log'
                    )
                )

            # If more files than specified in ini.log.keep, remove the oldest
            files = glob.glob(os.path.join(settings.log.dir, '*.log'))  # todo: convert to pathlib
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            while len(files) > settings.log.keep:
                os.remove(files.pop())
    else:
        settings = Settings()

    return settings


def save_settings(path: str = str(_SETTINGS_FILE)):
    """Save :data:`~shapeflow.settings` to .yaml
    """
    with open(path, 'w+') as f:
        yaml.safe_dump(settings.to_dict(), f)


# Instantiate global settings object
_load_settings()
save_settings()


def update_settings(s: dict) -> dict:
    """Update the global settings object.

    .. note::
       Just doing ``settings = Settings(**new_settings_dict)``
       would prevent other modules from accessing the updated settings!

    Parameters
    ----------
    s : dict
        new settings to integrate into the global settings

    Returns
    -------
    dict
        the current global settings as a ``dict``
    """
    global settings

    for cat, cat_new in s.items():
        sub = getattr(settings, cat)
        for kw, val in cat_new.items():
            setattr(sub, kw, val)

    save_settings()
    return settings.to_dict()


class Logger(logging.Logger):
    """``shapeflow`` logger.

    * Adds a verbose debug logging level :func:`~shapeflow.Logger.vdebug`

    * Strips newlines from log output to keep each log event on its own line
    """
    _pattern = re.compile(r'(\n|\r|\t| [ ]+)')

    def debug(self, msg, *args, **kwargs):
        """:meta private:"""
        super().debug(self._remove_newlines(msg))

    def info(self, msg, *args, **kwargs):
        """:meta private:"""
        super().info(self._remove_newlines(msg))

    def warning(self, msg, *args, **kwargs):
        """:meta private:"""
        super().warning(self._remove_newlines(msg))

    def error(self, msg, *args, **kwargs):
        """:meta private:"""
        super().error(self._remove_newlines(msg))

    def critical(self, msg, *args, **kwargs):
        """:meta private:"""
        super().critical(self._remove_newlines(msg))

    def vdebug(self, message, *args, **kwargs):
        """Log message with severity 'VDEBUG'.
        A slightly more verbose debug level for really dense logs.
        """
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


def get_logger(name: str) -> Logger:
    """Get a new :class:`~shapeflow.Logger` object

    Parameters
    ----------
    name : str
        name of the logger

    Returns
    -------
    Logger
        a fresh logging handle
    """
    logger = Logger(name)
    # log at the _least_ restrictive level
    logger.setLevel(
        min([settings.log.lvl_console.level, settings.log.lvl_file.level])
    )

    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

    logger.vdebug(f'new logger')
    return logger


log = get_logger(__name__)
log.info(f"v{__version__}")
log.debug(f"settings: {settings.dict()}")


def get_cache(retry: bool = False) -> diskcache.Cache:
    """Get a new :class:`diskcache.Cache` object
    In some rare cases this can fail due to a corrupt cache.
    If ``settings.cache.reset_on_error`` is on, and an exception is
    raised the cache directory is removed and :func:`get_cache` is
    called again with ``retry`` set to ``True``.

    Parameters
    ----------
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
            directory=str(settings.cache.dir),
            size_limit=settings.cache.size_limit_gb * 1e9
        )
    except sqlite3.OperationalError as e:
        log.error(f"could not open cache - {e.__class__.__name__}: {str(e)}")
        if not retry:
            if settings.cache.reset_on_error:
                log.error(f"removing cache directory")
                shutil.rmtree(str(settings.cache.dir))
            log.error(f"trying to open cache again...")
            get_cache(retry=True)
        else:
            log.error(f"could not open cache on retry")
            raise e
