import shutil
import sqlite3

import diskcache

from shapeflow.core.logging import get_logger


log = get_logger(__name__)


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
