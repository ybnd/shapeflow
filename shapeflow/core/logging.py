import re
import logging
from enum import Enum

from pydantic import FilePath, Field, DirectoryPath, validator

from shapeflow import VDEBUG, __version__
from shapeflow.core import RootException
from shapeflow.core.settings import Category, settings, ROOTDIR


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


class LogSettings(Category):
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

    _validate_path = validator('path', allow_reuse=True, pre=True)(
        Category._validate_filepath)
    _validate_dir = validator('dir', allow_reuse=True, pre=True)(
        Category._validate_directorypath)


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
_console_handler = logging.StreamHandler()
_file_handler = logging.FileHandler(str(settings.get(LogSettings).path))


_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)


waitress = logging.getLogger("waitress")
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
        min([settings.get(LogSettings).lvl_console.level,
             settings.get(LogSettings).lvl_file.level])
    )

    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

    logger.vdebug(f'new logger')
    return logger
# Define log handlers

_console_handler.setLevel(settings.get(LogSettings).lvl_console.level)
_file_handler.setLevel(settings.get(LogSettings).lvl_file.level)

_console_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)
# Handle logs from other packages
waitress.addHandler(_console_handler)

waitress.addHandler(_file_handler)

waitress.propagate = False
log = get_logger('shapeflow')

RootException.set_logger(log)
log.info(f"v{__version__}")
log.debug(f"settings: {settings.as_dict()}")