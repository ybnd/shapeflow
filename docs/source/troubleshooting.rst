
Troubleshooting
===============

Application won't install
-------------------------

* The deployment script exits immediately
  (on Windows, if you ran the script by double clicking it in explorer, the command window may close immediately)

  * The deployment script logs to a hidden file ``.deploy.log``.
    After successfully deploying, this file is renamed to ``.success.log`` and will remain hidden.
    If the deployment fails, this file is renamed to ``failure.log`` and will no longer be hidden.

    These logs are very useful when trying to diagnose what's going wrong with a deployment.
    Make sure to include them when asking for help.

  * If you don't see a ``.deploy.log`` file (make sure to enable hidden files!), it's likely that something
    went wrong *before the script could even start*.
    This could be because you forgot to install Python and/or git

  * Check if **Python version 3.10** and **git** are installed and accessible from the
    terminal

    Open a terminal (``cmd.exe`` on Windows) and check if you get
    something like this ::

           > python --version
           Python 3.10.5
           > git --version
           git version 2.37.1

  * If either of these returns something like ‘command not found’,
    its executable isn’t included in the ``PATH``. On Windows, you can fix
    this `by adding it explicitly <add-path-win10_>`_, or in the case of
    Python, reinstalling and making sure you check the option
    ``add Python to PATH`` during the installation.


Application won’t run
---------------------

* Check if you have a ``failure.log`` file -- maybe the application was not deployed properly?
  In some cases the installation might fail in a way that wasn't picked up

* ``sf.py`` exits immediately
  (on Windows, if you ran the script by double clicking it in Windows Explorer, the command window may close immediately)

  * Your system’s configuration may have changed since the installation;
    follow the steps above to make sure everything is still correct.

* ``sf.py`` exits immediately and mentions **cairo**

  * `cairo <cairo_>`_ is one of the libraries we use to render the overlay and masks out of our design files. It’s a bit annoying to set up on Windows. Normally, the deployment scripts should install it in the virtual environment.

  * To make sure this library can be accessed, either

    * run ``python sf.py``

    * or download the **.zip of the latest release** from `preshing/cairo-windows <cairo-windows_>`_, extract it, and **copy the .dll** for your computer’s architecture (probably 64-bit) into ``C:\\Windows\\System32``.


* ``sf.py``  exits immediately and complains that it can’t import something

  * Most often this is due to a problem with the virtual environment.
    If your installation went correctly, it should be in the ``.venv/``
    directory. You can check whether it works properly by running ::

       > cd .venv/Scripts
       > activate
       > cd ../..
       (.venv) > python
       >>> import shapeflow

    in Command Prompt on Windows or ::

       > source .venv/bin/activate
       (.venv) > python
       >>> import shapeflow

    in a terminal everywhere else.

  * If you can activate the virtual environment but still get import errors on
    ``import shapeflow``, it may be that some (or all) of ``shapeflow``‘s
    dependencies aren’t installed. You can check this by running ``pip freeze``
    with the virtual environment activated (as in the previous step).
    To install the dependencies, run::

       (.venv) > pip install -r requirements.txt

    in the the ``shapeflow`` root directory.

Application runs, but the interface won't load (properly)
---------------------------------------------------------

* ``sf.py``  runs fine, but the page says **404 not found**

  * Check if you have a folder ``ui/dist/`` in your ``shapeflow`` directory and
    that there is a bunch of stuff in it.

  * If not, you can either

    * Run ::

         python sf.py get-compiled-ui

      in a terminal (or Command Prompt on Windows)

    * `download the files for your version <shapeflow-releases_>`_ and extract them into ``ui/dist/`` to try again.

  * This means your installation went wrong, please complain to the person
    responsible for making the deployment script.


Application runs, but something’s gone wrong
--------------------------------------------

* The application is unresponsive

  * Move to a different page and back

  * Refresh the page

  * The server may have crashed, run ``sf.py`` again.


* The images on the align/filter page don't load properly

  * Seek around the video to refresh the images

  * Move to a different page and back

  * Refresh the page

* Previous application state is not restored properly;
  e.g. unresponsive analyses are queued automatically,
  or the application opens but crashes immediately

  * You can manually clear the previous state by removing the ``state`` file in
    :attr:`the root directory <shapeflow.ROOTDIR>` and restarting the application.
    If the problem persists and this approach mitigates it, you can turn off
    restoring the previous state in :ref:`the settings <application-settings>`.

  * You can also try to remove ``history.db`` (note that this will clear all previously used files & analysis configuration)


.. _shapeflow-releases: https://github.com/ybnd/shapeflow/releases
.. _add-path-win10: https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/
.. _cairo: https://www.cairographics.org/manual/
.. _cairo-windows: https://github.com/preshing/cairo-windows