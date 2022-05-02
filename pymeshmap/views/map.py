"""Views for creating the interactive network map."""

from typing import Iterator

import sqlalchemy as sa
from loguru import logger
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session, aliased

from ..models import Link, Node
from ..types import LinkStatus, LinkType, NodeStatus

# TODO: make an enum for bands
NODE_ICONS = [
    ("900MHz", "magentaRadioCircle-icon.png"),
    ("2GHz", "purpleRadioCircle-icon.png"),
    ("3GHz", "blueRadioCircle-icon.png"),
    ("5GHz", "goldRadioCircle-icon.png"),
    ("Unknown", "greyRadioCircle-icon.png"),
]


@view_config(route_name="map", renderer="templates/map.jinja2")
def network_map(request: Request):
    """Network map view - basic page to load/define the necessary Javascript.

    Network data is then loaded via Javascript from the `map-data` view.

    """
    # TODO: read starting coordinates/zoom from query string

    node_icons = {
        key: request.static_url(f"pymeshmap:static/img/map/{filename}")
        for key, filename in NODE_ICONS
    }

    return {"node_icons": node_icons}


@view_config(route_name="map-data", renderer="json")
def map_data(request: Request):
    """Generate node and link data as GeoJSON to be loaded into Leaflet."""
    dbsession: Session = request.dbsession
    node_query = dbsession.query(Node).filter(
        Node.status != NodeStatus.INACTIVE,
        Node.latitude != sa.null(),
        Node.longitude != sa.null(),
    )
    source_nodes = aliased(Node, node_query.subquery())
    dest_nodes = aliased(Node, node_query.subquery())

    nodes = node_query.all()

    links = (
        dbsession.query(Link)
        .join(source_nodes, Link.source_id == source_nodes.id)
        .join(dest_nodes, Link.destination_id == dest_nodes.id)
        .filter(Link.status != LinkStatus.INACTIVE)
        .all()
    )
    return {
        "nodes": {
            "type": "FeatureCollection",
            "features": [_node_geo_json(node) for node in nodes],
        },
        "links": {
            "type": "FeatureCollection",
            "features": [_link_geo_json(link) for link in _dedupe_links(links)],
        },
    }


def _node_geo_json(node: Node) -> dict:
    """Convert node to GeoJSON feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            # GeoJSON coordinates are "backwards"
            "coordinates": [node.longitude, node.latitude],
        },
        "properties": {
            "id": str(node.id),
            "name": node.name,
            "band": node.band,
        },
    }


def _link_geo_json(link: Link) -> dict:
    """Convert link to GeoJSON feature."""
    geo_json = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            # GeoJSON coordinates are "backwards"
            "coordinates": [
                [link.source.longitude, link.source.latitude],
                [link.destination.longitude, link.destination.latitude],
            ],
        },
        "properties": {
            "id": link.id.dump(),
            "name": f"{link.source.name} / {link.destination.name} ({link.type})",
            "type": link.type.name,
        },
    }
    geo_json["properties"].update(_link_properties(link))
    return geo_json


def _link_properties(link: Link) -> dict:
    """Determine color of link line.

    Use fixed color for known tunnels and DTD links.
    Otherwise, base the color on the link cost.

    """
    # py310: match?
    if link.type == LinkType.DTD:
        return {
            "color": "#3388ff",
            "opacity": 0.5,
            "offset": 0,
        }
    if link.type == LinkType.TUN:
        return {
            "color": "#07070f",
            "opacity": 0.5,
            "offset": 0,
        }
    if link.olsr_cost is None or link.olsr_cost >= 99.99:
        return {
            "color": "#8b0000",
            "opacity": 0.5,
        }
    if link.olsr_cost >= 14:
        return {"color": "#dc143c"}
    # color calculations based on KG6WXC's Mesh Map
    tone = int((link.olsr_cost - 1) * 64)
    if link.olsr_cost >= 7:
        return {"color": f"#{tone:02x}ff00"}
    if link.olsr_cost > 1:
        return {"color": f"#ff{tone - 255:02x}00"}

    return {"color": "#00ff00"}


def _dedupe_links(links: list[Link]) -> Iterator[Link]:
    """Filter out redundant tunnels and DTD links."""
    # while it is unlikely that two nodes are connected by both types, this is safer
    seen_tunnels = set()
    seen_dtd = set()

    for link in links:
        if link.type not in {LinkType.DTD, LinkType.TUN}:
            yield link
            continue
        # reverse the nodes to see if the mirror version was returned
        link_nodes = (link.destination_id, link.source_id)
        if link.type == LinkType.DTD and link_nodes not in seen_dtd:
            seen_dtd.add((link.source_id, link.destination_id))
            yield link
        elif link.type == LinkType.TUN and link_nodes not in seen_tunnels:
            seen_tunnels.add((link.source_id, link.destination_id))
            yield link
