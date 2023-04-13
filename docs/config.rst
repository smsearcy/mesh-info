Configuration
=============

*Mesh Info* is configured via an environment file named ``.env`` in the same folder as the project was cloned into.
If you followed the :doc:`installation instructions <installation>` then it should be ``/opt/mesh-info/src/.env``.

Example
-------

.. code-block:: ini

   MESH_INFO_LOCAL_NODE="10.1.1.1"
   MESH_INFO_MAP_LATITUDE="37.405"
   MESH_INFO_MAP_LONGITUDE="-98.525"
   MESH_INFO_MAP_ZOOM="5"
   MESH_INFO_LOG_LEVEL=INFO
   MESH_INFO_DB_URL="postgresql+psycopg2://postgres:password@localhost:5432/postgres"


Options
-------

.. note::

   The options for ``meshinfo report`` are configured on the command line.

MESH_INFO_COLLECTOR_LINK_INACTIVE
   Number of days a link remains on the map in inactive state after it was last seen.
   Default is 1 day.

MESH_INFO_COLLECTOR_NODE_INACTIVE
   Number of days a node remains on the map in inactive state after it was last seen.
   Default is 7 days.

MESH_INFO_COLLECTOR_TIMEOUT
   Total number of seconds to fetch ``sysinfo.json`` information before timing out.
   Default is 30.

MESH_INFO_COLLECTOR_WORKERS
   Number of worker tasks polling the network simultaneously.
   Default is 50.

MESH_INFO_DB_URL
   Override the default SQLite database by pointing to a PostgreSQL server
   (or changing the default location).

MESH_INFO_ENVIRONMENT
   Either ``production`` or ``development``.
   Defaults to ``production``, use ``development`` to enable more debugging options.
   See :doc:`contributing` for more information.

MESH_INFO_LOCAL_NODE
   Specify the node name or IP address to connect to for OLSR information.
   Useful if *Mesh Info* server cannot resolve default of `localnode.local.mesh`.

MESH_INFO_LOG_LEVEL
   Controls how much information is logged/displayed in terminal.
   Can be one of the following (from most verbose to least):
   ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``.
   Default is ``WARNING``.

MESH_INFO_MAP_LATITUDE
   Latitude coordinate to center map on.

MESH_INFO_MAP_LONGITUDE
   Longitude coordinate to center map on.

MESH_INFO_MAP_MAX_ZOOM
   Set the max zoom level.
   Passed to Leaflet's `tileLayer()`_.
   Default is 18.

MESH_INFO_MAP_TILE_ATTRIBUTION
   The attribution to display on the map.
   Passed to Leaflet's `tileLayer()`_.
   Default is appropriate for the default tile server.

   .. warning::

      Because the attribution often contains HTML,
      special characters will *not* be escaped,
      and thus vulnerabilities could be introduced with a bad attribution.

MESH_INFO_MAP_TILE_URL
   The template URL for the tile server.
   Passed to Leaflet's `tileLayer()`_.
   Default is ``//stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg``

MESH_INFO_MAP_ZOOM
   Default zoom level.
   Passed to `Leaflet <https://leafletjs.com/>`_.

MESH_INFO_WEB_BIND
   TCP or Unix socket to bind web application to.
   Defaults to ``0.0.0.0:8000``.
   A Unix socket looks like ``unix:/run/mesh-info.sock``.


.. _tileLayer(): https://leafletjs.com/reference.html#tilelayer
