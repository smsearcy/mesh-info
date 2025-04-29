Development/Contributing
========================

Thank you for your interest in Mesh Info!
Here are some instructions and pointers to get you setup for development.

.. note::

    Mesh Info is only tested on Linux,
    so these instructions assume you are on Linux
    (although it could be a virtual machine or WSL).

    On the todo list is providing some sample data to load in a development environment.
    For now, you will either need to connect the development machine to a mesh (at least temporarily),
    or use the ``export`` and ``import`` commands to load data.

Installing
----------

For starters, you will need:

* Python 3.9 or greater, with the "dev" or "devel" libraries
* RRDtool libraries (``librrd-dev`` on Debian/Ubuntu or ``rrdtool-devel`` on Fedora).
* `uv <https://github.com/astral-sh/uv>`_ to manage the Python environment.
* `just <https://github.com/casey/just>`_ to run various tasks.
* Fork/clone the Git repository using your preferred tool and ``cd`` to the repository.

Then, setup the Python virtual environment and activate it:

.. code-block:: console

    uv sync
    just migrate-db
    . ./venv/bin/activate

Create a ``.env`` file in the ``mesh-info`` folder and add:

.. code-block:: ini

    MESH_INFO_ENV="development"
    # this is optional, but can be helpful
    MESH_INFO_LOG_LEVEL="DEBUG"
    # Set the node address if necessary
    #MESH_INFO_LOCAL_NODE="10.1.1.1"

.. tip::

    Setting the environment to ``development`` enables the Pyramid web framework's debug toolbar
    and puts the data directories in the current user's home folder.

To get data, either run ``uv run meshinfo collector``
or use ``uv run meshinfo import`` to import data.

Run the development web server via:

.. code-block:: console

   uv run meshinfo web

.. tip::

   With ``just`` installed you can run ``just run`` to run both the collector and web services.

Connect to the server at http://localhost:8000.


Testing
-------

There is a ``Justfile`` with some commonly used commands and tests.
Run ``just`` to run the general test suite.

just pre-commit
   Runs `pre-commit <https://pre-commit.com/>`_ to check/format files.

just fix
   Runs `Ruff <https://docs.astral.sh/ruff/>`_ to do static linting and formatting.

just mypy
   Run `mypy <http://mypy-lang.org/>`_ static type checker.

just test-all
   Run entire test suite.

   .. tip::

      Copy ``sysinfo.json`` samples into ``tests/data`` to verify they can be successfully parsed.

just docs
   Generate HTML documentation locally via `Sphinx <https://www.sphinx-doc.org/>`_.

just make-migration
   Create new database migrations via `Alembic <https://alembic.sqlalchemy.org/>`_.

just migrate-db
   Apply `Alembic <https://alembic.sqlalchemy.org/>`_ database migrations.


Architecture
------------

Organization
^^^^^^^^^^^^

Repository organization (and significant files)

.. code-block::

    alembic/    # database migrations/setup
    docs/       # documentation in Sphinx/reStructuredText
    meshinfo/
      models/       # SQLAlchemy database models
      static/       # static resources for the web site
      templates/    # Jinja2 templates for HTML rendering
      tests/        # pytest tests
      views/        # Pyramid view functions
                    # (provide the data that is passed to the templates)
      aredn.py      # AREDN node parsing functionality
      backup.py     # import/export tools
      cli.py        # command line entry points
      collector.py  # collects info and saves it
      config.py     # application configuration
      historical.py # saving and graphing historical data points
      poller.py     # polls the network
      report.py     # simple network report
      routes.py     # defines URL routes for Pyramid

Tools
^^^^^

Mesh Info leverages the following Python frameworks/libraries:

* `attrs <https://www.attrs.org/en/stable/>`_:
  classes without boilerplate
* `AIOHTTP <https://docs.aiohttp.org/en/stable/>`_:
  asynchronous polling of mesh nodes
* `Jinja <https://jinja.palletsprojects.com/>`_:
  template engine
* `Pyramid <https://trypyramid.com/>`_:
  web framework
* `SQLAlchemy <https://www.sqlalchemy.org/>`_:
  database ORM

The following frontend libraries/tools are vendored in this repository
(because the goal is that clients do not need internet access to use the tool):

* `Alpine.js <https://alpinejs.dev/>`_:
  Lightweight Javascript framework
* `Bulma <https://bulma.io/>`_:
  CSS framework
* `Leaflet <https://leafletjs.com/>`_:
  Javascript library for interactive maps
* `Leaflet Polyline Offset <https://github.com/bbecquet/Leaflet.PolylineOffset>`_:
  Leaflet plugin to offset lines
* `Grid.js <https://gridjs.io/>`_:
  Javascript table plugin
