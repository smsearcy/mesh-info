Mesh Info
=========

.. image:: https://github.com/smsearcy/mesh-info/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/smsearcy/mesh-info/actions

.. image:: https://readthedocs.org/projects/mesh-info-ki7onk/badge/?version=latest
   :target: https://mesh-info-ki7onk.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

|

`Project Documentation <http://mesh-info-ki7onk.readthedocs.io/>`_

.. -begin-content-

Collects information about an `AREDN <https://arednmesh.org/>`_ mesh network,
tracking and graphing historical data such as link quality and cost.

Inspired by based on KG6WXC's `MeshMap`_,
but redesigned for tracking the historical data.

Uses Python's `asyncio` library to concurrently query nodes for faster polling times.
Information about nodes and links is stored in RRDtool for graphing historical trends.

*TODO: Add some screenshots*


Goals
-----

This project started because I wanted to play with the `asyncio` library in Python
and crawling potentially slow AREDN mesh networks seemed like a good opportunity.
Thus I'm building off the work of KG6WXC's `MeshMap`_,
rather than re-inventing the wheel.
While I was thinking of keeping the same database design
(so this could be a drop-in replacement for the mapper)
I've decided to initially focus on storing historical time-series data and
will be working on map visualization after that.


Acknowledgements
----------------

As mentioned above, this is based on the work done by Eric (KG6WXC),
who has been very helpful when I had questions.

Project icon is from `here <https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg>`_.

.. _MeshMap: https://gitlab.kg6wxc.net/mesh/meshmap
