shapeflow
#########

A tool for extracting time-series data from video footage of microfluidic devices with complex channel geometry.
Written by Yury Bondarenko with moral and QA support of the `KU Leuven MeBioS Biosensors group <https://www.biw.kuleuven.be/biosyst/mebios/biosensors-group>`_.


Installation & usage
====================

1. Install `Python 3.8 <https://www.python.org/downloads/release/python-386/>`_ and `git <https://git-scm.com/downloads>`_, if you haven’t yet. On Windows, **make sure you select the option ‘Add Python to PATH’!**

2. Make a new folder in a convenient location

3. `Download a deployment script <https://github.com/ybnd/shapeflow/releases/download/0.4.1/deploy_shapeflow-0.4.1.py>`_ and save it to that folder

4. Run the deployment script.

5. Once the installation is done, you can start the application by running ``sf.py``. A new browser window or tab should open with the user interface.



Dependencies
============

* Backend

  - SVG layer splitting & rendering ~ `OnionSVG <https://github.com/ybnd/OnionSVG>`_

  - Image & data processing ~ `OpenCV <https://opencv.org/>`_, `numpy <https://numpy.org/>`_, `pandas <https://pandas.pydata.org/>`_

* Frontend

  - ...


.. toctree::
   :hidden:
   :maxdepth: 4

   tutorial
   troubleshooting
   developing
   changelog
   backend
   frontend