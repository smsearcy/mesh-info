User Guide
==========

Recent Nodes/Links
------------------

Throughout the site and documentation,
there are references to *current* and *recent* nodes and links.
Current nodes/links are ones that were seen in the most recent network scan.
A recent *node* was seen within the past seven days,
while a recent *link* was seen within the past 24 hours
(although those default thresholds can be overridden).

Both *current* and *recent* nodes are considered *active*.
Past that timeframe, a node or link is considered *inactive* but is still in the system
(however currently there is not a way to see them user interface).

If an *inactive* node shows up on network again,
it will get a new ID,
and thus all graphs will start over.

If a *recent*/*active* node is seen with a new name,
then the name will be updated for the existing node ID,
persisting the historical information.


Overview
--------

This page gives an overview of the mesh network,
including how many nodes and links,
how long the poller is taking to run,
and some statistics about types of nodes.


Map
---

Under development.


Nodes
-----

This page lists all the recent and active nodes on the network.
Use the search box to filter based on any of the text in the table.


Node Details
------------

Displays information about a node, including:

* basic information from the ARDEN page
* graphs of the number (and type) of neighbors
* list of current (and recent) neighbors
* graphs of link quality, cost, and SNR per link

This page can be arrived at from either the *Nodes* page or the *Map* page.
