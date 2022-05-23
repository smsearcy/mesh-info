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

0.4.0 - Unreleased
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
