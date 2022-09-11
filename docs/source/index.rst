`shapeflow <shapeflow_>`_
#########################

A tool for extracting time-series data from video footage of microfluidic
devices with complex channel geometry.
Written by Yury Bondarenko with moral and QA support of the
`KU Leuven MeBioS Biosensors group <biosensors_>`_.


Installation & usage
====================

#. Make sure the following software is installed on your system

  - `Python 3.10 <python310_>`_

    On Windows, **make sure you select the option ‘Add Python to PATH’!**

  - `git`_

  - Three options are available for SVG rendering, from fastest to slowest:

    - `cairo <https://www.cairographics.org/>`_

      On Windows, run ``sf.py setup-cairo`` after installing shapeflow.

    - `ImageMagick <https://imagemagick.org/>`_

      To install on 64-bit Windows you can use `this installer <https://download.imagemagick.org/ImageMagick/download/binaries/ImageMagick-7.0.11-3-Q8-x64-dll.exe>`_

    - `Inkscape <https://inkscape.org/>`_

      This is the slowest option, but can serve as a convenient fallback.


#. Make a new folder in a convenient location

#. `Download a deployment script <deploy_>`_ and save it to that folder

#. Run the deployment script (on Windows you can just double-click it from explorer)

#. Once the installation is done, you can start the application by running ``sf.py``.
   A new browser window or tab should open with the user interface.



Dependencies
============

* Backend

  - Image & data processing ~ `OpenCV <https://opencv.org/>`_, `numpy <https://numpy.org/>`_, `pandas <https://pandas.pydata.org/>`_

* Frontend

  - ...


.. toctree::
   :hidden:
   :maxdepth: 4

   tutorial
   troubleshooting
   changelog
   developing
   python-library


.. _shapeflow: https://www.github.com/ybnd/shapeflow

.. _biosensors: https://www.biw.kuleuven.be/biosyst/mebios/biosensors-group
.. _python310: https://www.python.org/downloads/release/python-3105/
.. _git: https://git-scm.com/downloads

.. _deploy: https://github.com/ybnd/shapeflow/releases/download/0.4.4/deploy_shapeflow-0.4.4.py

