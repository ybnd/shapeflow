Developing
==========

Backend
-------

Setting up a development environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To work on shapeflow, you should set up a virtual environment in ``.venv``

.. code-block::

   python -m venv .venv
   (.venv) pip install -r requirements.txt

With this environment in place, the entrypoint ``shapeflow.py`` can be run either from ``(.venv)`` or with your the global Python interpreter. In the latter case, ``.venv`` will be used implicitly.

Writing plugins
^^^^^^^^^^^^^^^

Features, transforms and filters are handled by a plugin system. You can use existing plugins as examples.

* A plugin should be a subclass of its respective interface (:class:`~shapeflow.core.backend.Feature` for features, :class:`~shapeflow.core.interface.TransformInterface` for transforms and :class:`~shapeflow.core.interface.FilterInterface` for filters)
* If you define configuration for the plugin, it should derive from its respective configuration class as well (:class:`~shapeflow.core.backend.FeatureConfig` for features, :class:`~shapeflow.core.interface.TransformConfig` for transforms and :class:`~shapeflow.core.interface.FilterConfig` for filters), and should be linked to the plugin class itself as the class variable :attr:`~shapeflow.core.config.Configurable._class_config`. Configuration parameters should be defined as ``pydantic.Field`` instances, and should include a default and a description.
* Plugins should have a descriptive docstring
* :class:`~shapeflow.core.backend.Feature` subclasses should also define a :attr:`~shapeflow.core.backend.Feature._label` and :attr:`~shapeflow.core.backend.Feature._unit` as class variables. These values will be used to label the y-axis on the result page of the frontend.

All plugin files are automatically loaded when ``shapeflow.plugins`` is imported.


Frontend
--------

Setup
^^^^^


#.
   Install `npm <https://www.npmjs.com/get-npm>`_

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

      cd ui/ && npm run generate

   The compiled files are stored in ``ui/dist/``.

Running the frontend in development mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


#.
   (Set up)

#.
   Run the backend server (default address is http://localhost:7951)

   .. code-block::

      (.venv) $ python .server.py

#.
   Run the frontend development server (default address is http://localhost:3000)

   .. code-block:: bash

      cd ui/ && npm run dev

   The development server `hot-reloads <https://vue-loader.vuejs.org/guide/hot-reload.html>`_ content from the source code in ``ui/`` and proxies API calls to the backend server.


Generating deployment scripts
-----------------------------

Deployment scripts are generated with `gitploy <https://github.com/ybnd/gitploy>`_.


#. Tag the release in ``git``
#. Create a release on Github
#. Compile ``ui/dist/``\ , compress it with ``tar czf dist-<tag>.tar.gz dist/`` and attach it to that release as a binary
#. Create or update your .ploy file in ``shapeflow``\ ‘s root directory:

   #. Start from `ploy <ploy>`_
   #. Add the tag of your release
   #. Double check that the check / setup script paths are still correct

#. Run ``python -m gitploy`` in ``shapeflow``\ ‘s root directory.
