Commands
========

Documentation about the ``meshinfo`` command line functionality.

.. note::

    Examples presume that Mesh Info was installed per the :doc:`installation instructions <installation>`.

Network Report
--------------

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo report [-v] [--save-errors] [--path=.] [HOSTNAME]

Prints node and link details after polling all the nodes on the AREDN network,
does not use or require a database connection.

By default it connects to ``localnode.local.mesh``.

Amount of information logged to the console can be increased by passing ``-v`` up to ``-vvv``.

If you pass ``--save-errors`` then the response from any nodes that have issues will be saved as ``{ip_address}-response.txt``.
Change the directory those responses are saved to with ``--path``.

Export/Import
-------------

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo export FILENAME
    $ /opt/mesh-info/bin/meshinfo import FILENAME

Commands to export the RRD data files and SQLite database to a ``.tgz`` file and import them again.

Uses the currently configured data directory.

.. warning::

    The ``import`` command requires the RRDtool client installed,
    not just the libraries.

.. tip::

    RRD files are platform-specific,
    so you cannot copy ``.rrd`` files from a Raspberry Pi to desktop.
    Use this command instead.

Collector Service
-----------------

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo collector [--run-once]

Collects information from the network and stores to the database.
By default, it will run repeatedly, polling the network every 5 minutes
(while this period is configurable, the RRD files are built assuming that data is being fetched every 5 minutes).

Use the `--run-once` option to run once and exit.

The installation instructions setup this process as the Systemd service ``meshinfo-collector``.


Web Service
-----------

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo web [--bind=socket] [--workers=###]

Serves the web interface on http://localhost:8000 (by default).
Change the port/socket it binds to via the the ``--bind`` option (e.g. "0.0.0.0:80" or "unix:/run/mesh-info.sock").

The installation instructions setup this process as the Systemd service ``meshinfo-web``.
