pyMeshMap
=========

Application for mapping and displaying information about an
[AREDN](https://arednmesh.org/) Mesh Network, based on KG6WXC's
[MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap).

Uses Python's `asyncio` library to concurrently query nodes for faster polling times.
Information about nodes and links is stored in RRDtool for graphing historical trends.


Getting Started
---------------

**pyMeshMap** requires the following (the instructions below should walk you through the process):
* Python 3.7 or later
* [RRDtool](https://oss.oetiker.ch/rrdtool/index.en.html) development headers to be installed
(`librrd-dev` on Debian/Ubuntu or `rrdtool-devel` for Fedora/Red Hat)
* PostgreSQL libraries

By default it will use SQLite for the database (but PostgreSQL is also supported),
and "localnode.local.mesh" to get information about the network via OLSR.
The default data directory (for SQLite and RRD files) is `/usr/local/share/pymeshmap`.
Reference `.env.example` for how to customize settings via an `.env` file.

```shell script
$ sudo apt install python3 python3-virtualenv python3-dev python3-pip
$ sudo apt install libpq-dev librrd-dev
$ git clone https://github.com/smsearcy/pymeshmap.git
$ cd pymeshmap
# Create a virtual environment to isolate the Python dependencies
$ python3 -m venv .
$ ./bin/python -m pip install -U pip
$ ./bin/pip install -r requirements.txt
$ ./bin/pip install -e .
# Run a basic poll of the network to confirm that is working
$ ./bin/pymeshmap report
$ sudo mkdir -p /usr/local/share/pymeshmap
# Make sure the user that we're running as has write access to that folder
$ sudo chown [user] /user/local/share/pymeshmap
$ ./bin/alembic upgrade head
# These last two commands are the only ones that need to be ran going forward
$ ./bin/pymeshmap collector &
$ ./bin/pymeshmap web &
```

Commands
--------

*Commands are given assuming the Python "virtual environment" has been activated via `. ./bin/activate`.
Run `deactivate` to drop out of the virtualenv.*

### Network Report
```shell script
$ pymeshmap report [-v] [--save-errors] [--path=.] [HOSTNAME]
```

Prints node and link details *after* polling all the nodes on the network.

Similar to MeshMap's `scripts/get-map-info.php --test-mode-no-sql`
this command collects and displays information about an AREDN network
but does not require a database.
Amount of information logged to the console can be increased by passing `-v` up to `-vvv`.

By default it connects to `localnode.local.mesh`.

If you pass `--save-errors` then the response from any nodes that have issues
will be saved as `{ip_address}-response.txt`.
Change the directory those are saved with `--path`.

### Collector Service
```shell script
$ pymeshmap collector [--run-once]
```

Collects information from the network and stores to the database.
All configuration is via environment variables.
By default, it will run repeatedly, polling the network every 5 minutes
(while this period is configurable, the RRD files are built assuming that data is being fetched every 5 minutes).

Use the `--run-once` option to run once and exit.


### Web Service
```shell script
$ pymeshmap web
```

Serves the web interface on http://localhost:6543 (by default).

Goals
-----

This project started because I wanted to play with the `asyncio` library in Python
and crawling potentially slow AREDN mesh networks seemed like a good opportunity.
Thus I'm building off the work of KG6WXC's [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap),
rather than re-inventing the wheel.
While I was thinking of keeping the same database design
(so this could be a drop-in replacement for the mapper)
I've decided to initially focus on storing historical time-series data and
thus will be architecting the database for that
(while including enough information to be able to render current-state maps).


Acknowledgements
----------------

As mentioned above, this is based on the work done by Eric (KG6WXC),
who has been very helpful when I had questions.

From the [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap) site:

> Additional Credit to: Mark/N2MH and Glen/K6GSE for their work on this project
> and to the rest of the [AREDN](https://arednmesh.org/) team,
> without them this would not be a project.

Project icon is from [here](https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg).


Developing
----------

1. Fork/clone the Git repository via your preferred tool
and `cd` to that directory in a terminal.
2. Follow the directions above for installing pyMeshmap.
3. Activate the virtualenv via `. ./bin/activate` (this is necessary for the `Makefile` to find the commands).
4. Install the development requirements via `./bin/pip install -r dev-requirements.txt`
5. Create `.env` and set `PYMESHMAP_ENV = "development"`
(this enables the Pyramid debug toolbar
and changes the default data paths to be in the current user's home directory).
6. To run the `pymeshmap` command execute `pymeshmap [sub-command]`.
7. A `Makefile` is included to simplify various tasks such as running `pre-commit`, tests, and linters.
8. A `pyramid.ini` file is provided for use with the Pyramid development tools like `pserve` and `pshell`.
