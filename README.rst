Mesh Info
=========

.. -begin-content-

Collects information about an `AREDN <https://arednmesh.org/>`_ mesh network,
tracking and graphing historical data such as link quality and cost.

Inspired by based on KG6WXC's `MeshMap`_,
but redesigned for tracking the historical data.

Uses Python's `asyncio` library to concurrently query nodes for faster polling times.
Information about nodes and links is stored in RRDtool for graphing historical trends.


Goals
-----

This project started because I wanted to play with the `asyncio` library in Python
and crawling potentially slow AREDN mesh networks seemed like a good opportunity.
Thus I'm building off the work of KG6WXC's `MeshMap`_,
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

Project icon is from `here <https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg>`_.

.. _MeshMap: https://gitlab.kg6wxc.net/mesh/meshmap
