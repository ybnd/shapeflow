Changelog
=========


* ``0.4.3`` -- **API overhaul**

  * Add frontend tests
    * And also some general clean-up and fixes in the process

  * Deprecate caching contexts and related functionality
    * We’re assuming that caching will never be performed *in advance*
      of an analysis. Instead, we rely on caching during an analysis to
      speed up any subsequent analyses.

  * Separate internal routing from general ``Flask`` routing
    * API routes are organised based on :class:`shapeflow.core.Dispatcher`
    * :class:`~shapeflow.core.Dispatcher` instances map addresses to
      :class:`~shapeflow.core.Endpoint` instances
    * Nested :class:`~shapeflow.core.Dispatcher`s include the addresses
      of any child :class:`~shapeflow.core.Dispatcher` instances in their
      own address space
    * The top-level :class:`~shapeflow.core.Dispatcher` has a flat
      address space of all endpoints, which it uses to resolve requests
    * The Flask server delegates requests to this top-level
      :class:`~shapeflow.core.Dispatcher` for addresses
      starting with ``"/api/"``

  * Expose :class:`~shapeflow.core.Endpoint` instances with own
    :func:`~shapeflow.core.Endpoint.expose` method instead of global function

  * Deprecate ``RootInstance`` / ``BackendInstance``
    * Implementation should not care about routing

    .. note::
        This means that methods of ``BackendInstance`` subclass instances
        nested in :class:`~shapeflow.video.VideoAnalyzer` can no longer be
        exposed at :class:`~shapeflow.core.Endpoint` instances. Only methods
        of objects *directly* associated with
        :class:`~shapeflow.core.Dispatcher` instances can be exposed.

  * More sensible API structure
    * Global top-level API at :data:`shapeflow.api.api`
    * Group related functionality
      * ``api``: general stuff
      * ``api.fs``: dealing with files and directories
      * ``api.cache``: dealing with the cache
      * ``api.db``: dealing with the database
      * ``api.va``: dealing with analyzers
      * ``api.va.<id>``: dealing with a specific analyzer

  * Open analyzers are handled by new
    :class:`~shapeflow.core.Dispatcher` instances

    * Analyzer methods should be exposed with the placeholder
      :class:`~shapeflow.core.Dispatcher` at ``api.va.__id__``

      * By themselves, methods exposed in this way can’t be
        invoked since they don’t have an instance yet

    * New analyzers are opened from
      :class:`~shapeflow.main._VideoAnalyzerManager` and given an ``id``
      * Use shorter ``id`` strings for URL readability
      * Associate newly instantiated
        :class:`~shapeflow.video.VideoAnalyzer` with a new
        :class:`~shapeflow.core.Dispatcher` instance at ``api.va.<id>``
      * This :class:`~shapeflow.core.Dispatcher`, binds methods exposed in
        ``api.va.__id__`` to the :class:`~shapeflow.video.VideoAnalyzer`
        instance

      * *Now* these methods can be invoked
        when requested by ``/api/va/<id>/<endpoint>``

    * Included in top-level address space at launch
      to reduce address resolution overhead

  * Mirror API structure in frontend ``api.js``

* ``0.4.2`` -- **CLI overhaul**

  * Subcommands to divide up the functionality of the library. 

    * Implemented to make accessing backend schemas easier when testing the
      frontend; instead of starting the whole server,
      run ``sf.py dump <path>``. The server is now a subcommand, ``serve``.

    * Potentially useful commands to add in the future
      * ``analyze`` could run a single analysis as specified in a .json file
      * ``checkout`` could set the repository to a specific version
      * ``setup`` could replace in-repo setup scripts

    * It may also be interesting to make these commands accessible
      from the frontend

  * Some major naming changes
    * Entry point script ``shapeflow.py`` becomes ``sf.py``
    * Server-related stuff renamed from ``main`` to ``server``

* ``0.4.1`` -- **Usability improvements and tutorial**

  * Tutorials and high-level documentation

* ``0.4.0`` -- **Rebranding**

* **Clean-up git history**

  * The first year of development was at `isimple`_, named after the
    technology/the team that used it for some reason.

    Because the original repository was a bit too large, its git history was
    rewritten after moving to `shapeflow`_. The old repository is still up to
    preserve this history and to support legacy deployment scripts.

      * `gitsizer`_ and `bfg`_ are nifty tools.

  * Removed...

      * Compiled JavaScript from ``ui/dist/``

      * `An accidentally huge screenshot, mysteriously named datetime <rm1>`_

      * `An accidentally huge BMP file <rm2>`_

  * All in all, the repo went from almost 30MB to about 6MB.

  .. code-block:: bash

     bfg --delete-folders dist .
     bfg --delete-files datetime .
     bfg --delete-files img.bmp .

     git reflow expire --expire=now --all
     git --prune=now --aggressive

.. note::
    A short summary of the major changes in the older versions
    will be added soon.

.. _shapeflow: https://github.com/ybnd/shapeflow
.. _isimple: https://github.com/ybnd/isimple
.. _gitsizer: https://github.com/github/git-sizer
.. _bfg: https://rtyley.github.io/bfg-repo-cleaner

.. _rm1: https://github.com/ybnd/isimple/commit/b65a0fe914a44bff6b2bba4ed155a9cd24d54e10
.. _rm2: https://github.com/ybnd/isimple/commit/af1b251b90efcd670d220de8f25975ff7bc8321d