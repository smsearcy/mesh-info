"""Views for creating the interactive network map."""

from typing import Any, Dict, Iterator

import attr
import sqlalchemy as sa
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


@attr.s(auto_attribs=True, slots=True)
class LinkProperties:
    color: str
    opacity: float = 1.0
    weight: int = 2
    offset: int = 2


@view_config(route_name="map", renderer="templates/map.jinja2")
def network_map(request: Request):
    """Network map view - basic page to load/define the necessary Javascript.

    Network data is then loaded via Javascript from the `map-data` view.

    """
    # TODO: read starting coordinates/zoom from query string
    # (and/or use https://github.com/mlevans/leaflet-hash)

    node_icons = {
        key: request.static_url(f"meshinfo:static/img/map/{filename}")
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
            "features": [_node_geo_json(node, request) for node in nodes],
        },
        "links": {
            "type": "FeatureCollection",
            "features": [
                _link_geo_json(link, request) for link in _dedupe_links(links)
            ],
        },
    }


def _node_geo_json(node: Node, request: Request) -> dict:
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
            "previewUrl": request.route_url("node-preview", id=node.id),
        },
    }


def _link_geo_json(link: Link, request: Request) -> dict:
    """Convert link to GeoJSON feature."""
    geo_json: Dict[str, Any] = {
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
            "previewUrl": request.route_url(
                "link-preview",
                source=link.source_id,
                destination=link.destination_id,
                type=link.type.name.lower(),
            ),
        },
    }
    geo_json["properties"].update(attr.asdict(_link_properties(link)))
    return geo_json


def _link_properties(link: Link) -> LinkProperties:
    """Determine color of link line.

    Use fixed color for known tunnels and DTD links.
    Otherwise, base the color on the link cost.

    """
    # py310: match?
    if link.type == LinkType.DTD:
        properties = LinkProperties(
            color="#3388ff",
            offset=0,
        )
    elif link.type == LinkType.TUN:
        properties = LinkProperties(
            color="#707070",
            offset=0,
        )
    elif link.olsr_cost is not None:
        # Base color on OLSR cost, similar to KG6WXC's MeshMap
        # I think the OLSR cost is 1 / (LQ * NLQ), so this incorporates the
        # link quality but on a logarithmic scale, rather than linear
        # (if we used LQ & NLQ for RF links).
        hue = _calc_hue(link.olsr_cost, green=1, red=14)
        properties = LinkProperties(
            color=f"hsl({hue}, 100%, 50%)",
        )
    else:
        properties = LinkProperties(
            color="#8b0000",
        )

    if link.status != LinkStatus.CURRENT:
        # make non-current links mostly transparent
        properties.opacity = 0.2

    return properties


def _calc_hue(value: float, *, red: float, green: float) -> int:
    """Calculate the hue between red and green, with the median being yellow."""
    range_ = abs(green - red)
    if red < green:
        percent = max(min(value, green) - red, 0) / range_
    else:
        percent = 1 - max(min(value, red) - green, 0) / range_

    # red hue is 0, green is 120, so just multiply the percentage by 120
    return round(120 * percent)


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
