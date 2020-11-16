Python library
##############

shapeflow
=========

.. automodule:: shapeflow
   :members:
   :show-inheritance:

.. toctree::
   :maxdepth: 4

   shapeflow.core
   shapeflow.maths
   shapeflow.plugins


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
   :private-members: _resolve_enforcedstr, _odd_add, _int_limits, _float_limits
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
   :special-members: __modify_schema__
   :show-inheritance:


maths
=====

colors
------

.. automodule:: shapeflow.maths.colors
   :members:
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
   :undoc-members:
   :show-inheritance:

Filters
-------

HsvRangeFilter
^^^^^^^^^^^^^^

.. automodule:: shapeflow.plugins.HsvRangeFilter
   :members:
   :undoc-members:
   :show-inheritance:

BackgroundFilter
^^^^^^^^^^^^^^^^

.. automodule:: shapeflow.plugins.BackgroundFilter
   :members:
   :undoc-members:
   :show-inheritance:

Features
--------

PixelSum
^^^^^^^^

.. automodule:: shapeflow.plugins.PixelSum
   :members:
   :undoc-members:
   :show-inheritance:

Area_mm2
^^^^^^^^

.. automodule:: shapeflow.plugins.Area_mm2
   :members:
   :undoc-members:
   :show-inheritance:

Volume_uL
^^^^^^^^^

.. automodule:: shapeflow.plugins.Volume_uL
   :members:
   :undoc-members:
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
