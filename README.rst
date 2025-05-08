Mesh Info
=========

.. image:: https://github.com/smsearcy/mesh-info/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/smsearcy/mesh-info/actions

.. image:: https://readthedocs.org/projects/mesh-info-ki7onk/badge/?version=latest
   :target: https://mesh-info-ki7onk.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
   :target: https://github.com/astral-sh/uv
   :alt: uv

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
   :target: https://github.com/astral-sh/ruff
   :alt: Ruff

|

`Project Documentation <https://mesh-info-ki7onk.readthedocs.io/>`_

.. -begin-content-

Collects information about an `AREDN <https://arednmesh.org/>`_ mesh network,
tracking and graphing historical data such as link quality and cost.

Inspired by and based on  KG6WXC's `MeshMap`_,
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
then started adding some basic map visualizations.


Acknowledgements
----------------

As mentioned above,
this is based on the work done by Eric (KG6WXC),
who has been very helpful when I had questions.
Besides learning that I could get all the nodes from OLSR and about AREDN's ``sysinfo.json``,
the map uses his icons and much of the Javascript is based on what he did.

Project icon is from `here <https://commons.wikimedia.org/wiki/File:FullMeshNetwork.svg>`_.

.. _MeshMap: https://gitlab.kg6wxc.net/mesh/meshmap
