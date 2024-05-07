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

Displays nodes and links on a map.
Click on the node or link for a popup with more information
and a hyperlink the the node details page.

*Recent* links
(which were not available during the last polling of the network)
are hidden by default,
but can be enabled on the *layers* menu.
They will be faded/translucent.

.. note::

   As of v0.5.0,
   the client's browser needs internet access to download the map tiles.

Node Legend
^^^^^^^^^^^

* 900MHz - Magenta
* 2GHz - Purple
* 3GHz - Blue
* 5GHz - Orange
* No RF - Grey
* Unknown - Red

Link Legend
^^^^^^^^^^^

* Radio - Green to Red gradiant, based on link cost
* DTD - Blue
* Tunnel (Legacy & Wireguard) - Grey
* Unknown Cost - Maroon
* Infinite Cost (ETX >= 99.99) - Black


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
