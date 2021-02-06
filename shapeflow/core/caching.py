import shutil
import sqlite3

import diskcache
from pydantic import Field, DirectoryPath, validator

from shapeflow import ROOTDIR
from shapeflow.core.logging import get_logger
from shapeflow.core.settings import Category, settings

log = get_logger(__name__)


class CacheSettings(Category):
    """Caching settings
    """
    do_cache: bool = Field(default=True, title="use the cache")
    """Enables the cache. Set to ``True`` by default.

    Disabling the cache will make the application significantly slower.
    """
    dir: DirectoryPath = Field(default=str(ROOTDIR / 'cache'),
                               title="cache directory")
    """Where to keep the cache
    """
    size_limit_gb: float = Field(default=4.0, title="cache size limit (GB)")
    """How big the cache is allowed to get
    """
    resolve_frame_number: bool = Field(default=True,
                                       title="resolve to (nearest) cached frame numbers")
    """Whether to resolve frame numbers to the nearest requested frame numbers.

    Increases seeking performance, but may make it a bit more 'jumpy' if a low
    number of frames is requested for an analysis.
    """
    block_timeout: float = Field(default=0.1,
                                 title="wait for blocked item (s)")
    """How long to keep waiting for data that's actively being committed to the
    cache before giving up and computing it instead.

    In the rare case that two cachable data requests are being processed at the 
    same time, the first request will block the cache for those specific data
    and cause the second request to wait until it can grab this data from the 
    cache.
    This timeout prevents the second request from waiting forever until the
    first request finishes (for example, in case it crashes).
    """
    reset_on_error: bool = Field(default=False,
                                 title="reset the cache if it can't be opened")
    """Clear the cache if it can't be opened.

    In rare cases, ``diskcache`` may cache data in a way it can't read back.
    To recover from such an error, the cache will be cleared completely.
    The only downside to this is decreased performance for a short while.
    """

    _validate_dir = validator('dir', allow_reuse=True, pre=True)(
        Category._validate_directorypath)


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
            directory=str(settings.get(CacheSettings).dir),
            size_limit=settings.get(CacheSettings).size_limit_gb * 1e9
        )
    except sqlite3.OperationalError as e:
        log.error(f"could not open cache - {e.__class__.__name__}: {str(e)}")
        if not retry:
            if settings.get(CacheSettings).reset_on_error:
                log.error(f"removing cache directory")
                shutil.rmtree(str(settings.get(CacheSettings).dir))
            log.error(f"trying to open cache again...")
            get_cache(retry=True)
        else:
            log.error(f"could not open cache on retry")
            raise e


