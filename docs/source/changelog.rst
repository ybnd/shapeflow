Changelog
=========

0.4.5
-----

* Fixed some issues with file/directory selection dialogs on Windows and MacOS

0.4.4
-----

* Triumphant return of the readthedocs page

  * Tutorial

  * Major step forward documenting the Python library, along with multiple
    tiny tweaks to the Python codebase. Mainly cleaned up & removed unused
    methods.

* Fix disappearing ``feature_parameters`` in new analysis dialog and on the
  configure page

* Add CLI commands to interact with the git repository

  * For end users that may not want to deal with git

  * Throwback to the "mandatory update system" of the olden days:

    update to new release versions if any are available, but when you

    *actually want to*.

* Setup ~ CLI commands

  * Deployment scripts execute ``shapeflow/setup/post-deploy.py``

    as a setup step

  * :class:`shapeflow.cli.GetCompiledUi`

  * :class:`shapeflow.cli.SetupCairo`

  * :class:`shapeflow.cli.Declutter`

* Make |cairo|_ an optional dependency

  * No longer depend on |OnionSVG|_; design file rendering is now handled by
    :class:`shapeflow.design.onions.Peeler` and
    :class:`shapeflow.design.render.Renderer`.
  * SVG layer operations (|lxml|_) are decoupled from rendering
  * Renderers are selected based on the system configuration: |cairo|_ is
    still the go-to option, but we can now fall back on
    |Wand|_ (`ImageMagick`_)
    and the commandline interface of a Windows installation of `Inkscape`_.

* Fix ``tkinter`` dialog windows not appearing on Windows

  * ``tkinter`` can't handle not being in the main thread, which was the case
    in the "updated" version of :module:``shapeflow.util.filedialog``.

  * Should not have deprecated subprocess-based filedialog script; it was
    added in the first place to solve this issue.

  * Made subprocess-based file dialogs complain on cancel / error; this bug
    stayed unnoticed because they used to be silent about it.

0.4.3
-----

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

0.4.2
-----

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

0.4.1
-----

  * Tutorials and high-level documentation

0.4.0
-----

Clean-up git history
--------------------

* The first year of development was at `isimple`_, named after the
  technology/the team that used it for some reason.

  Because the original repository was a bit too large, its git history was
  rewritten after moving to `shapeflow`_. The old repository is still up to
  preserve this history and to support legacy deployment scripts.

    * `gitsizer`_ and `bfg`_ are nifty tools.

* Removed...

    * Compiled JavaScript from ``ui/dist/``

    * `An accidentally huge screenshot, mysteriously named datetime <rm1_>`_

    * `An accidentally huge BMP file <rm2_>`_

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


.. |cairo| replace:: ``cairo``
.. |cairosvg| replace:: ``cairosvg``
.. |lxml| replace:: ``lxml``
.. |Wand| replace:: ``Wand``
.. |OnionSVG| replace:: ``OnionSVG``
.. _cairosvg: https://cairosvg.org/
.. _cairo: https://www.cairographics.org/
.. _lxml: https://lxml.de/
.. _Wand: https://docs.wand-py.org/en/0.6.6/
.. _ImageMagick: https://imagemagick.org/index.php
.. _Inkscape: https://inkscape.org/
.. _OnionSVG: https://github.com/ybnd/OnionSVG