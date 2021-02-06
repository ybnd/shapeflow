from logging import Logger


class RootException(Exception):
    """Automatically logs the exception class and message at the ``ERROR`` level.
    """
    _logger: Logger = None

    msg = ''
    """The default message to log
    """

    @classmethod
    def set_logger(cls, logger: Logger) -> None:
        """Set the loggerto log exceptions to

        Parameters
        ----------
        logger : Logger
        """
        cls._log = logger

    def __init__(self, *args):
        # https://stackoverflow.com/questions/49224770/
        # if no arguments are passed set the first positional argument
        # to be the default message. To do that, we have to replace the
        # 'args' tuple with another one, that will only contain the message.
        # (we cannot do an assignment since tuples are immutable)
        if not (args):
            args = (self.msg,)

        if self._logger is not None:
            self._logger.error(self.__class__.__name__ + ': ' + ' '.join(args))
        super(RootException, self).__init__(*args)
