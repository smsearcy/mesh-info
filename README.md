pyMeshMap
=========

Application for mapping and displaying displaying information about an
[AREDN](https://arednmesh.org/) Mesh Network, based on KG6WXC's
[MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap).

Uses Python's `asyncio` library to concurrently query nodes for faster polling times.


Getting Started
---------------

**pyMeshMap** requires Python 3.7 or greater and
uses [Poetry](https://python-poetry.org/) to manage dependencies
so you will need that [installed](https://python-poetry.org/docs/#installation).

*Some of required packages might need a C compiler as well,
that's why one future goal is a container for easy deployment.*

```shell script
$ git clone https://gitlab.com/smsearcy/pymeshmap.git
$ cd pymeshmap
$ poetry install --no-dev
$ poetry run pymeshmap [command]
```

The `--no-dev` option assumes you just want to use **pyMeshMap**.
If you want to contribute then leave that off to get extra dependencies for development and testing.

Commands
--------

### network-report
```shell script
$ poetry run pymeshmap network-report [-v] [--save-errors] [--path=.] [HOSTNAME]
```

Prints node and link details *after* polling all the nodes on the network.

Similar to MeshMap's `scripts/get-map-info.php --test-mode-no-sql`
this command collects and displays information about an AREDN network
but does not require a database.
Amount of information logged to the console can be increased by passing `-v` up to `-vvv`.

By default it will connect to `localnode.local.mesh`.

If you pass `--save-errors` then the response from any nodes that have issues
will be saved as `{ip_address}-response.txt`.
Change the directory those are saved with `--path`.


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

**Other Goals:**

* Unit tests for validating the parsing of `sysinfo.json` for different versions of the AREDN firmware.
* A basic logical map of the mesh without need for geography tiles via [NetworkX](https://networkx.github.io/documentation/stable/index.html).
* Deployment via containers
(possibly with in-memory SQLite database for very basic setup).
* Eventually, geographic based map similar to [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap).

While much of that is surely possible in PHP I am much more experience and fluent in Python,
hence the port instead of contributing to the existing project.


Acknowledgements
----------------

As mentioned above, this is based on the work done by Eric Satterlee (KG6WXC) and licensed under the GPL v3.

From the [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap) site:

> Additional Credit to: Mark/N2MH and Glen/K6GSE for their work on this project
> and to the rest of the [AREDN](https://arednmesh.org/) team,
> without them this would not be a project.

Project icon is from [here](https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg).


Developing
----------

`pymeshmap` uses [Poetry](https://python-poetry.org/)
so you will need that installed and available in your path.
Once you have that:

1. Fork/clone the Git repository via your preferred tool
and `cd` to that directory in a terminal.
2. To create a virtualenv and install the package with its dependencies
(including development dependencies) run `poetry install`.
*If running in a virtual environment already then it will use that virtual environment.*
3. To configure your IDE to use the correct virtual environment
run `poetry env info`
and update your IDE to use the Virtualenv path specified.
4. To run the `pymeshmap` command either
execute `poetry run pymeshmap [sub-command]`
or if the virtual environment is active just run `pymeshmap [sub-command]`
