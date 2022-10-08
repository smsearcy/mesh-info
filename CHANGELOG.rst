Changelog
=========

Changes to **Mesh Info** that affect users or are of major impact to developers.


The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

**NOTE:** This project is currently in development (pre-1.0),
so breaking changes are possible but will be highlighted here.

..
    Recommended Sections:

    Added
    Changed
    Deprecated
    Removed
    Fixed
    Security

0.6.0 - Unreleased
------------------

Added
^^^^^

Changed
^^^^^^^

Fixed
^^^^^


0.5.1 - 2022-10-07
------------------

Fixed
^^^^^

* Corrected version typo.


0.5.0 - 2022-10-07
------------------

Added
^^^^^

* Add/expand project documentation. (`#28 <https://github.com/smsearcy/mesh-info/issues/28>`_)
* Basic implementation of network map.
  Client is required internet access to fetch tiles.
  All map elements rendered on single layer.
* Map legend (`#35 <https://github.com/smsearcy/mesh-info/issues/35>`_)
* Set starting map coordinates via configuration file. (`#45 <https://github.com/smsearcy/mesh-info/issues/45>`_)
* Save node polling errors to database. (`#55 <https://github.com/smsearcy/mesh-info/issues/55>`_)
* Display node polling errors. (`#47 <https://github.com/smsearcy/mesh-info/issues/47>`_)
* Configure map tile URL and attribution via configuration file.  (`#63 <https://github.com/smsearcy/mesh-info/issues/63>`_)

Changed
^^^^^^^

* Bumped current AREDN version (`#38 <https://github.com/smsearcy/mesh-info/issues/38>`_)
* Group nightly firmware versions and add API version statistics (`#42 <https://github.com/smsearcy/mesh-info/issues/42>`_)
* Cap link cost from API at 99.99 for consistency (`#81 <https://github.com/smsearcy/mesh-info/issues/81>`_)

Fixed
^^^^^

* Added new 2GHz channels (`#40 <https://github.com/smsearcy/mesh-info/issues/40>`_)
* Added new 5GHz channel (`#44 <https://github.com/smsearcy/mesh-info/issues/44>`_)
* Fix 3GHz icon color (`#49 <https://github.com/smsearcy/mesh-info/issues/49>`_)
* Fix link destination name issue (`#52 <https://github.com/smsearcy/mesh-info/issues/52>`_)
* Node list firmware sorted "naturally" (`#48 <https://github.com/smsearcy/mesh-info/issues/48>`_)
* Use node name for link to AREDN page (`#65 <https://github.com/smsearcy/mesh-info/issues/65>`_)


0.4.0 - 2022-06-02
------------------

Added
^^^^^

* Added SSID to the node table for searching/sorting (`#25 <https://github.com/smsearcy/mesh-info/issues/25>`_)

Changed
^^^^^^^

* **BREAKING CHANGE:** Renamed project and data folders (`#26 <https://github.com/smsearcy/mesh-info/issues/26>`_)

  * Renamed project from **pyMeshMap** to **Mesh Info**.
  * Renamed the Python package from ``pymeshmap`` to ``meshinfo``.
  * Data folders from ``pymeshmap` to ``mesh-info`` (in ``/var/lib/`` or ``~/.local/share/``).
  * The default SQLite database from ``pymeshmap.db`` to ``mesh-info.db``.
  * The GitHub repository from ``smsearcy/pymeshmap`` to ``smsearcy/mesh-info``.

* **BREAKING CHANGE:** Change default port for web service to 8000 (`#29 <https://github.com/smsearcy/mesh-info/issues/29>`_)

  Changed default port to 8000 (Gunicorn default)
  and configuration to use "bind" instead of "host" and "port"
  This enables binding to a Unix socket instead of a TCP port.

Fixed
^^^^^

* Fix import/export going into the ``rrd`` subdirectory with the RRD folders (`#19 <https://github.com/smsearcy/mesh-info/issues/19>`_)


0.3.0 - 2022-04-20
------------------

Added
^^^^^

* Start a changelog (`#21 <https://github.com/smsearcy/mesh-info/issues/21>`_)

Changed
^^^^^^^

* **BREAKING CHANGE:** Moved default data folder (`#18 <https://github.com/smsearcy/mesh-info/issues/18>`_)

  For *production*, moved from ``/usr/local/share/pymeshmap`` to ``/var/lib/pymeshmap``,
  to be better aligned with Linux Filesystem Hierarchy Standard.
  Moved RRD files into the ``rrd`` subfolder (i.e. ``/var/lib/pymeshmap/rrd``).

  For *development*, moved data folder into ``data`` subfolder (``~/.local/share/pymeshmap/data``),
  in preparation for needing a cache directory.
  Moved RRD files into the ``rrd`` subfolder, to mirror production (``~/.local/share/pymeshmap/data/rrd``).

Fixed
^^^^^

* Fix parse error due to changed tunnel data in nightly firmware (API v1.10).
  All nodes will now just report their tunnel count,
  so a 0 instead of "No" if the tunnel plugin is not installed.
  (`#23 <https://github.com/smsearcy/mesh-info/issues/23>`_)


0.2.0 - 2022-04-11
------------------

The version string has been "0.2.0" for a while,
starting the changelog here because this was an important fix.

Fixed
^^^^^

* Use Gunicorn instead of Waitress for better stability and performance while dynamically rendering graphs.
  (`#15 <https://github.com/smsearcy/mesh-info/issues/15>`_)
