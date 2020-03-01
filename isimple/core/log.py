import re
import logging


__log_file__ = '.log'
__lvl_global__ = logging.DEBUG
__lvl_console__ = logging.DEBUG
__lvl_file__ = logging.DEBUG


VDEBUG = 9
logging.addLevelName(VDEBUG, "VDEBUG")


def vdebug(self, message, *args, **kwargs):
    if self.isEnabledFor(VDEBUG):
        self._log(VDEBUG, message, *args, **kwargs)


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
            self._log(
                VDEBUG, self._remove_newlines(message), *args, **kwargs
            )

    def _remove_newlines(self, msg: str) -> str:
        return self._pattern.sub(' ', msg)


def get_logger(name: str = __name__) -> CustomLogger:
    log = CustomLogger(name)
    log.setLevel(__lvl_global__)

    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(__lvl_console__)

    _file_handler = logging.FileHandler(__log_file__)
    _file_handler.setLevel(__lvl_file__)

    _formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _console_handler.setFormatter(_formatter)
    _file_handler.setFormatter(_formatter)

    log.addHandler(_console_handler)
    log.addHandler(_file_handler)

    return log
