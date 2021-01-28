import re
import logging

from shapeflow import VDEBUG, __version__
from shapeflow.settings import settings


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
_file_handler = logging.FileHandler(str(settings.log.path))
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
        min([settings.log.lvl_console.level, settings.log.lvl_file.level])
    )

    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

    logger.vdebug(f'new logger')
    return logger


# Define log handlers
_console_handler.setLevel(settings.log.lvl_console.level)
_file_handler.setLevel(settings.log.lvl_file.level)

_console_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)

# Handle logs from other packages
waitress.addHandler(_console_handler)
waitress.addHandler(_file_handler)
waitress.propagate = False

log = get_logger('shapeflow')

log.info(f"v{__version__}")
log.debug(f"settings: {settings.dict()}")


class RootException(Exception):
    """All ``shapeflow`` exceptions should be subclasses of this one.
    Automatically logs the exception class and message at the ``ERROR`` level.
    """
    msg = ''
    """The message to log
    """

    def __init__(self, *args):
        # https://stackoverflow.com/questions/49224770/
        # if no arguments are passed set the first positional argument
        # to be the default message. To do that, we have to replace the
        # 'args' tuple with another one, that will only contain the message.
        # (we cannot do an assignment since tuples are immutable)
        if not (args):
            args = (self.msg,)

        log.error(self.__class__.__name__ + ': ' + ' '.join(args))
        super(Exception, self).__init__(*args)