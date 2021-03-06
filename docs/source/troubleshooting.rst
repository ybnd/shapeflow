
Troubleshooting
===============

Application won't install
-------------------------


* The script exits immediately
  (on Windows, the command window may close immediately)

  * On Windows, if you just double-clicked the deployment script directly from
    explorer and the command window closed immediately,
    try running the script from the ``cmd``::

           cd <the directory you want to install in>
           python deploy_<...>.py

    Now the terminal window should stay up, and you’ll have time to scroll
    through the output and maybe get more of an idea as to what went wrong.

  * Check if ``python`` and ``git`` are installed and accessible from the
    terminal

  * Open a terminal (``cmd.exe`` on Windows) and check if you get
    something like this::

           > python --version
           Python 3.8.5
           > git --version
           git version 2.28.0

  * Instead, if either of these returns something like ‘command not found’,
    its executable isn’t included in the ``PATH``. On Windows, you can fix
    this `by adding it explicitly <add-path-win10_>`_, or in the case of
    ``python``, reinstalling and making sure you check the option
    ``add Python to PATH`` during the installation.

  * Check that your ``python`` installation is **either version 3.7 or 3.8**.


Application won’t run
---------------------

* The script exits immediately
  (on Windows, the command window may close immediately)

  * Your system’s configuration may have changed since the installation;
    follow the steps above

* The script exits immediately and mentions **cairo**

  * `cairo`_ is the library we use to
     render the overlay and masks out of our design files. It’s a bit annoying
     to set up on Windows. Normally, the deployment scripts should install it
     in the virtual environment.

  * Go to ``.venv/Scripts/`` in your install directory (it may be hidden) and
    check whether it contains the files ``cairo.dll`` and ``cairo.lib``. If it
    doesn't, something may have gone wrong with your install.

  * To add these files manually, download the .zip of the latest release from
    `preshing/cairo-windows <preshing_>`_,
    extract it, open the ``lib`` folder and copy the .dll and .lib files for
    your computer’s architecture (probably ``x64``\ ) into ``.venv/Scripts/``.

  * If this doesn't solve anything and your Python installation is 32-bit,
    try using the ``x86`` .dll and .lib files instead.

  * Finally, you can also try moving the .dll and .lib files
    to ``C:\Windows\System32\``.

* The script exits immediately and complains that it can’t import something
  (other than cairo)

  * Most often this is due to a problem with the virtual environment.
    If your installation went correctly, it should be in the ``.venv/``
    directory. You can check whether it works properly by running::

       > cd .venv/Scripts
       > activate
       > cd ../..
       (.venv) > python
       >>> import shapeflow

    in ``cmd``  on Windows or::

       > source .venv/bin/activate
       (.venv) > python
       >>> import shapeflow

    everywhere else.

  * If you can activate the virtual environment but still get import errors on
    ``import shapeflow``, it may be that some (or all) of ``shapeflow``‘s
    dependencies aren’t installed. You can check this by running ``pip freeze``
    with the virtual environment activated (as in the previous step).
    To install the dependencies, run::

       (.venv) > pip install -r requirements.txt

    in the the ``shapeflow`` root directory.

* The script runs fine, but the page says **404 not found**

  * Check if you have a folder ``ui/dist/`` in your ``shapeflow`` directory and
    that there is a bunch of stuff in it.

  * If not, you can `download the files for your version <shapeflow-releases_>`_
    and extract them into ``ui/dist/`` to try again.

  * This means your installation went wrong, please complain to the person
    responsible for making the deployment script.


Application runs, but something’s gone wrong
--------------------------------------------

* The application is unresponsive

  * Move to a different page and back

  * Refresh the page

  * The server may have crashed, run ``shapeflow.py`` again.


* The images on the align/filter page don't load properly

  * Seek around the video to refresh the images

  * Move to a different page and back

  * Refresh the page


.. _shapeflow-releases: https://github.com/ybnd/shapeflow/releases
.. _add-path-win10: https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/
.. _cairo: https://www.cairographics.org/manual
.. _preshing: https://github.com/preshing/cairo-windows/releases