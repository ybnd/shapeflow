Developing
==========

Backend
-------

Setting up a development environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To work on shapeflow, you should set up a virtual environment in ``.venv`` ::

   python -m venv .venv
   (.venv) pip install -r requirements.txt

With this environment in place, the entrypoint ``sf.py`` can be run
either from ``(.venv)`` or with your the global Python interpreter.
In the latter case, ``.venv`` will be used implicitly.

Writing plugins
^^^^^^^^^^^^^^^

Features, transforms and filters are handled by a plugin system.
You can use existing plugins as examples.

* A plugin should be a subclass of its respective interface
  (:class:`~shapeflow.core.backend.Feature` for features,
  :class:`~shapeflow.core.interface.TransformInterface` for transforms
  and :class:`~shapeflow.core.interface.FilterInterface` for filters)

* If you define configuration for the plugin, it should derive from its
  respective configuration class as well
  (:class:`~shapeflow.core.backend.FeatureConfig` for features,
  :class:`~shapeflow.core.interface.TransformConfig` for transforms
  and :class:`~shapeflow.core.interface.FilterConfig` for filters),
  and should be linked to the plugin class itself as the class variable
  :attr:`~shapeflow.core.config.Configurable._config_class`.
  Configuration parameters should be defined as ``pydantic.Field`` instances,
  and should include a default and a description.

* Plugins should have a descriptive docstring

* :class:`~shapeflow.core.backend.Feature` subclasses should also define a
  :attr:`~shapeflow.core.backend.Feature._label`
  and :attr:`~shapeflow.core.backend.Feature._unit` as class variables.
  These values will be used to label the y-axis on the result page
  of the frontend.

All plugin files are automatically loaded when ``shapeflow.plugins`` is imported.


Frontend
--------

Setup
^^^^^


#.
   Install Install `NodeJS & npm <npm>`_

#.
   Navigate to this directory and install the dependencies

   .. code-block:: bash

      cd ui/ && npm install

Compiling the frontend
^^^^^^^^^^^^^^^^^^^^^^


#.
   (Set up)

#.
   Compile

   .. code-block:: bash

      cd ui/ && npm run build

   The compiled files are stored in ``ui/dist/``.

Running the frontend in development mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


#.
   (Set up)

#.
   Run the backend server (default address http://localhost:7951)

   .. code-block::

      (.venv) $ python .server.py

#.
   Run the frontend development server (default address http://localhost:3000)

   .. code-block:: bash

      cd ui/ && npm run dev

   The development server `hot-reloads <vue-hot-reload>`_ content from the
   source code in ``ui/`` and proxies API calls to the backend server.


Generating deployment scripts
-----------------------------

Deployment scripts are generated with `gitploy`_.


#. Tag the release in ``git``

#. Create a release on Github

#. Compile ``ui/dist/``\ , compress it with ``tar czf dist-<tag>.tar.gz dist/``
   and attach it to that release as a binary

#. Create or update your .ploy file in the root directory of this repository:

   #. Start from `shapeflow/setup/ploy <ploy>`_

   #. Add the tag of your release

   #. Double check that the check / setup script paths are still correct

#. Run ``python -m gitploy`` in the root directory of this repository.


TODO
----

Some known problems and minor feature ideas. Not everything in this list is 
worth spending time on, and some ideas are serious feature creep. 
Open `issues`_ for important stuff. 

* Check performance on slower hardware

* Sidebar nav icon&text should aligned vertically

* Frame & state image can get desynchronized sometimes

* Dragging the seek control doesn't update streams, but clicking/arrows do
  (sometimes, sometimes it's ok)
  
* Alt scrolls through sidebar navs for some reason

* Select previous results of the same analyzer in the results page

* Masks misbehave when increasing DPI, 
  work fine when decreasing DPI (????)
  
* Skipped masks should be grayed out in the state image

* Set a max width/height for graph (depending on number of features?)

* Add ``AnalyzerState`` assertions to test_main.py

* Sometimes roi resize gets applied to current & opposite side, jumpy

* Highlight masks on hover in frontend

* Set default filter/transform configuration when adding a new analysis

* Optimize ``SchemaForm`` rendering speed

* Add an option to export ``.meta`` files

* Add an option to import analyses from ``.meta`` files and ``.xlsx`` files

* Configure sidebar should have a fade on the bottom

* Don't catch events outside of frame boundary (``v-bind`` ``style`` to ``div``?)

* *Really* fix oscillating parameter override categories

* Two of the same feature should yield two separate graphs

* On Windows, ``tkinter`` file dialogs don't open when debugging

* Support Anaconda environments

* When current analyzer page becomes disabled, route away or gray out page


Already fixed?
^^^^^^^^^^^^^^

* ``get_overlay`` & ``get_overlay_png`` take 5 seconds to run sometimes

* Align/Filter page: seek event on page load doesn't always come through, 
  or the streamed image doesn't get updated

* Frontend can freeze when adding a second/third/... analyzer

* Adding new analyzers with large Nf is slow

* Fix ROI rotation 
  (probably need to initialize moveable with the aspect ratio of the design)
  
* ``ConfigModel`` is made in doubles

* CtrlZ / CtrlShiftZ requests ``undo_config``/``redo_config`` twice

* When switching between analyzers, ROI sometimes gets stuck; 
  modifying ``moveable`` doesn't cause actual ROI to jump to the wrong one
  
* Config events are sometimes missed on ``set_filter_click``

* Issues with page rebuild after switching analyzers multiple (3+ times)

* Shouldn't continue on to ``/api/va/<id>/launch`` if ``/api/va/<id>/set_config`` raises HTTP500

* Reset filters state update should disable 'Analyze' button









.. _npm: https://nodejs.org/en/
.. _vue-hot-reload: https://vue-loader.vuejs.org/guide/hot-reload.html
.. _gitploy: https://github.com/ybnd/gitploy
.. _ploy: https://github.com/ybnd/shapeflow/blob/master/shapeflow/setup/ploy
.. _issues: https://github.com/ybnd/shapeflow/issues
