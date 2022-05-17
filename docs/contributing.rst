Development/Contributing
========================

Thank you for your interest in Mesh Info!
Here are some instructions and pointers to get you setup for development.

.. note::

    Mesh Info is only tested on Linux,
    so these instructions assume you are on Linux
    (although it could be a virtual machine or WSL).
    Work is being done in the ``dev-container`` branch to setup containers for development.

    Another item on the todo list is providing some sample data to load in a development environment.
    For now, you will either need to connect the development machine to a mesh (at least temporarily),
    or use the ``export`` and ``import`` commands to load data.

Installing
----------

For starters, you will need:

* Python 3.7 or greater, with the "dev" or "devel" libraries
  (I think Buster is still common enough on Raspberry Pis that it's worth targeting 3.7).
* RRDtool libraries (``librrd-dev`` on Debian/Ubuntu or ``rrdtool-devel`` on Fedora).
* PostgreSQL libraries (``libpq-dev`` on Debian/Ubuntu or ``libpq-devel`` on Fedora).
* Fork/clone the Git repository using your preferred tool.

Then, setup the Python virtual environment:

.. code-block:: console

    $ cd mesh-info
    $ python3 -m venv venv
    $ . ./venv/bin/activate
    (venv) $ pip install -U pip setuptools wheel
    (venv) $ pip install -r dev-requirements.txt -r requirements.txt
    (venv) $ pip install -e .
    (venv) $ make migrate-db
    # run the test suite locally
    (venv) $ make
    # run web service with development settings
    (venv) $ make web

Create a ``.env`` file in the ``mesh-info`` folder and add:

.. code-block:: ini

    MESH_INFO_ENV="development"
    # this is optional, but can be helpful
    MESH_INFO_LOG_LEVEL="DEBUG"
    # Set the node address if necessary
    #MESH_INFO_LOCAL_NODE="10.1.1.1"

.. tip::

    Setting the environment to ``development`` enables the Pyramid web framework's debug toolbar
    and puts the data directories in the current's user's home folder.


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
      templates/    # Jinja2 templates for the web site
      tests/        # pytest tests
      views/        # Pyramid view functions
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

* `AIOHTTP <https://docs.aiohttp.org/en/stable/>`_: asynchronous polling of mesh nodes
* `Pyramid <https://trypyramid.com/>`_: web framework
* `SQLAlchemy <https://www.sqlalchemy.org/>`_: database ORM

(TODO: flesh out this list some more?)
