Python library
##############


.. autodata:: shapeflow.__version__


shapeflow
=========

.. automodule:: shapeflow
   :members:
   :exclude-members: settings, save_settings, update_settings, Logger, get_logger, get_cache
   :private-members: _Settings
   :show-inheritance:

.. autodata:: shapeflow.settings
   :annotation: = shapeflow.Settings()

.. autofunction:: shapeflow.save_settings

.. autofunction:: shapeflow.update_settings

.. autoclass:: shapeflow.Logger

.. autofunction:: shapeflow.get_logger

.. autofunction:: shapeflow.get_cache


util
====

.. automodule:: shapeflow.util
   :members:
   :show-inheritance:

.. automodule:: shapeflow.util.meta
   :members:

.. automodule:: shapeflow.util.from_venv
   :members:
   :show-inheritance:

.. automodule:: shapeflow.util.filedialog
   :members:
   :show-inheritance:


core
====

.. automodule:: shapeflow.core
   :members:
   :special-members: __modify_schema__
   :show-inheritance:

streaming
---------

.. automodule:: shapeflow.core.streaming
   :members:
   :show-inheritance:

db
--

.. automodule:: shapeflow.core.db
   :members:
   :show-inheritance:

config
------

.. automodule:: shapeflow.core.config
   :members:
   :private-members: _resolve_enforcedstr, _odd_add, _int_limits, _float_limits, _config_class
   :show-inheritance:

interface
---------

.. automodule:: shapeflow.core.interface
   :members:
   :special-members: __modify_schema__
   :show-inheritance:

backend
-------

.. automodule:: shapeflow.core.backend
   :members:
   :private-members: _label, _unit
   :special-members: __modify_schema__
   :show-inheritance:


maths
=====

colors
------

.. automodule:: shapeflow.maths.colors
   :members:
   :private-members: _colorspace, _conversion_map
   :undoc-members:
   :show-inheritance:


coordinates
-----------

.. automodule:: shapeflow.maths.coordinates
   :members:
   :undoc-members:
   :show-inheritance:


images
------

.. automodule:: shapeflow.maths.images
   :members:
   :undoc-members:
   :show-inheritance:


plugins
=======

Transforms
----------

PerspectiveTransform
^^^^^^^^^^^^^^^^^^^^

.. automodule:: shapeflow.plugins.PerspectiveTransform
   :members:
   :private-members: _Config, _Transform
   :show-inheritance:

Filters
-------

HsvRangeFilter
^^^^^^^^^^^^^^

.. automodule:: shapeflow.plugins.HsvRangeFilter
   :members:
   :private-members: _Config, _Filter
   :show-inheritance:

BackgroundFilter
^^^^^^^^^^^^^^^^

.. automodule:: shapeflow.plugins.BackgroundFilter
   :members:
   :private-members: _Config, _Filter
   :show-inheritance:

Features
--------

PixelSum
^^^^^^^^

.. automodule:: shapeflow.plugins.PixelSum
   :members:
   :private-members: _Feature
   :show-inheritance:

Area_mm2
^^^^^^^^

.. automodule:: shapeflow.plugins.Area_mm2
   :members:
   :private-members: _Feature
   :show-inheritance:

Volume_uL
^^^^^^^^^

.. automodule:: shapeflow.plugins.Volume_uL
   :members:
   :private-members: _Config, _Feature
   :show-inheritance:


api
===

.. automodule:: shapeflow.api
   :members:
   :private-members:
   :show-inheritance:


config
======

.. automodule:: shapeflow.config
   :members:
   :exclude-members: ColorSpace, FrameIntervalSetting
   :show-inheritance:


db
==

.. automodule:: shapeflow.db
   :members:
   :show-inheritance:


video
=====

.. automodule:: shapeflow.video
   :members:
   :show-inheritance:


server
======

.. automodule:: shapeflow.server
   :members:
   :show-inheritance:


main
====

.. automodule:: shapeflow.main
   :members:
   :private-members: _Main, _Cache, _Filesystem, _VideoAnalyzerManager
   :special-members: __analyzers__
   :show-inheritance:


cli
===

.. automodule:: shapeflow.cli
   :members:
   :undoc-members:
   :private-members: __command__
   :special-members: __command__, __getitem__, __usage__, __help__
   :exclude-members: parser, args, sub_args, command
   :show-inheritance:
