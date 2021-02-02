Road Map
========

A list of things I intend to accomplish in *pyMeshMap*
(for now I'm going to document them here instead of maintaining a list of issues).

While much of this is surely possible in PHP I am much more experience and fluent in Python,
hence the port instead of contributing to the existing project
(especially since I started with the `asyncio` poller).

Collector
---------

Rename the network mapping as `collector` and rewrite it to run as a service.
Track *statistics* of the mesh network in a time series database for reporting/visualization.  The goal is *not* to be able to view the historical state of the whole mesh, but to track numerical statistics, such as node count, link quality, etc.

### Metrics to capture
Polling:
* Count of nodes
* Run time
* Number of nodes with errors (broken down by type: timeout, parsing, etc)
* Firmware version counts
* API version counts

Nodes:
* Number of neighbors (broken down by RF/DTD/tunnel with API 1.7 data)
* Node uptime
* System load
* Service count

Links (most information is only available via API >= 1.7):
* OLSR link cost
* Signal level
* Noise level
* Link Quality & Neighbor Link Quality
* Transmission rate

### Implementation
Two initials ideas for implementation are [Graphite](https://graphiteapp.org/) and [RRDtool](https://oss.oetiker.ch/rrdtool/).
Graphite is a newer tool that appears to provide more flexibility based on my initial research.
However it is also an additional service, which might be an issue since I'm targeting a small footprint for running on a Raspberry Pi 3
(but that will require further investigation).
RRDtool appears to provide the functionality I'm looking for and likely with less overhead, but I think the management of RRD files for the different/nodes links could get confusing.

* Add Graphite container to `docker-compose` to test that out.

## Historical granularity
Both Graphite and RRDtool consolidate data as it ages, so the question is how much data to keep and for how long (this also depends on how long the polling process takes to run which will limit the frequency).  Here's an initial idea:
* Every 15 minutes for 48 hours.
* Every 30 minutes for a week.
* Hourly for a year.
* Daily data for two years.

Most of the consolidations will be averages, one exception is uptime which I would keep the maximum value (but there might be others).


Web Interface
-------------

pyMeshMap needs a web interface to view the information about the mesh network.

## Pages
For the MVP (focusing on historical data):
* List of nodes (include count of the links?)
* Node detail page, including list of current/recent links, and historical graphs

## Technologies
The following are tools I intend to use, based on familiarity and/or anticipated fit.
My current plan is to use an initial design of server side page generation
(because that's what I'm most familiar with),
incorporating Javascript tools to make the pages more usable.
Because application will typically be used on an amateur mesh network,
we cannot assume internet connectivity and thus need to host all our own resources
(which is relatively straight-forward until we add a geographical map).

* Python web framework: [Pyramid](https://trypyramid.com/)
* Template engine: Jinja or Mako (the former is more popular, the latter's syntax won't conflict with Javascript templates)
* Javascript framework: Vue.js (this seems like the best fit for the incremental/progressive design I'm intending)

I'm less of a frontend developer, but I want a simple way to make things look nice.
Since I'm planning on using Vue.js I'm going to see if I can use a [custom Bootstrap 3 package](https://getbootstrap.com/docs/3.4/customize/) without any jQuery for basic styling.

Additional Goals
----------------

* A basic logical map of the mesh without need for geography tiles via [NetworkX](https://networkx.github.io/documentation/stable/index.html)
  (or one that is more dynamic via some JavaScript tools).
* Geographic based map similar to [MeshMap](https://gitlab.kg6wxc.net/mesh/meshmap).
