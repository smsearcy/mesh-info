pyMeshMap
=========

Application for mapping and displaying displaying information about an
[AREDN](https://arednmesh.org/) Mesh Network, based on KG6WXC's
[MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap).

Goals
-----

This project started because I wanted to play with the `asyncio` library in
Python and crawling potentially slow AREDN mesh networks seemed like a good
opportunity.  Thus I'm building off the work of KG6WXC's
[MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap), leveraging the database
design he has so that if this works and performs well it could be an alternate
implementation of the network poller even if the rest of my goals do not get
completed.

**Other Goals:**

* Unit tests for validating the parsing of `sysinfo.json` for different versions
of the AREDN firmware.
* A basic logical map of the mesh without need for geography tiles via
[NetworkX](https://networkx.github.io/documentation/stable/index.html).
* Simpler deployment via containers (possibly with in-memory SQLite database for
very basic setup).
* Eventually, geographic based map similar to
[MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap) so this could be a complete
replacement.

While much of that is surely possible in PHP I am much more experience and
fluent in Python, hence the port instead of contributing to the existing
project.


Acknowledgements
----------------

As mentioned above, this is based on the work done by Eric Satterlee (KG6WXC)
and licensed under the GPL v3.

From the [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap) site:

> Additional Credit to: Mark/N2MH and Glen/K6GSE for their work on this project
> and to the rest of the [AREDN](https://arednmesh.org/) team, without them this
> would not be a project.

Project icon is from [here](https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg).


Developing
----------

`pymeshmap` uses [Poetry](https://python-poetry.org/) so you will
need that installed and available in your path.  Once you have that:

1. Fork/clone the Git repository via your preferred tool and `cd` to that
directory in a terminal.
2. To create a virtualenv and install the package with its dependencies
(including development dependencies) run `poetry install`.  *If running in a
virtual environment already then it will use that virtual environment.*
3. To configure your IDE to use the correct virtual environment run `poetry env
info` and update your IDE to use the Virtualenv path specified.
4. To run the command line scripts (defined in `pyproject.toml`) run `poetry run
{command}`.
