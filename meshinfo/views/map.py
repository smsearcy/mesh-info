"""Views for creating the interactive network map."""

from __future__ import annotations

from collections.abc import Iterator

import attrs
import sqlalchemy as sa
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session, aliased

from ..config import AppConfig
from ..models import Link, Node
from ..types import Band, LinkId, LinkStatus, LinkType, NodeStatus

# map legend uses the order of the bands here
NODE_ICONS = [
    (Band.FIVE_GHZ, "gold-radio-small.png"),
    (Band.THREE_GHZ, "blue-radio-small.png"),
    (Band.TWO_GHZ, "purple-radio-small.png"),
    (Band.NINE_HUNDRED_MHZ, "magenta-radio-small.png"),
    (Band.OFF, "grey-radio-small.png"),
]


@attrs.define
class GeoNode:
    """Node data for rendering to GeoJSON."""

    id: int
    name: str
    band: Band
    latitude: float
    longitude: float

    @classmethod
    def from_model(cls, node: Node) -> GeoNode:
        return cls(
            id=node.id,
            name=node.name,
            band=node.band,
            latitude=node.latitude,
            longitude=node.longitude,
        )

    def __json__(self, request: Request):
        """Called by Pyramid's JSON renderer to dump the object to JSON."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                # GeoJSON coordinates are "backwards"
                "coordinates": [self.longitude, self.latitude],
            },
            "properties": {
                "id": str(self.id),
                "name": self.name,
                "band": self.band.value,
                "previewUrl": request.route_url("node-preview", id=self.id),
            },
        }


@attrs.define
class GeoLink:
    """Link data for rendering to GeoJSON."""

    id: LinkId
    name: str
    type: LinkType
    status: LinkStatus
    cost: float
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float

    @property
    def color(self) -> str:
        if self.type == LinkType.DTD:
            return "#3388ff"
        if self.type == LinkType.TUN:
            return "#707070"
        if self.cost is not None:
            if self.cost >= 99.99:
                # infinite link cost
                return "#000000"
            hue = _calc_hue(self.cost, green=1, red=10)
            return f"hsl({hue}, 100%, 50%)"
        # unknown link cost
        return "#8b0000"

    @property
    def opacity(self) -> float:
        opacity = 1.0 if self.status == LinkStatus.CURRENT else 0.2
        return opacity

    @property
    def offset(self) -> int:
        if self.type == LinkType.RF:
            return 2
        return 0

    @classmethod
    def from_model(cls, link: Link) -> GeoLink:
        return cls(
            id=link.id,
            name=f"{link.source.name} / {link.destination.name} ({link.type})",
            type=link.type,
            status=link.status,
            cost=link.olsr_cost,
            start_latitude=link.source.latitude,
            start_longitude=link.source.longitude,
            end_latitude=link.destination.latitude,
            end_longitude=link.destination.longitude,
        )

    def __json__(self, request: Request):
        """Called by Pyramid's JSON renderer to dump the object to JSON."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                # GeoJSON coordinates are "backwards"
                "coordinates": [
                    [self.start_longitude, self.start_latitude],
                    [self.end_longitude, self.end_latitude],
                ],
            },
            "properties": {
                "id": self.id.dump(),
                "name": self.name,
                "type": self.type.name,
                "color": self.color,
                "weight": 2,
                "offset": self.offset,
                "opacity": self.opacity,
                "previewUrl": request.route_url(
                    "link-preview",
                    source=self.id.source,
                    destination=self.id.destination,
                    type=self.type.name.lower(),
                ),
            },
        }


@view_config(route_name="map", renderer="pages/map.jinja2")
def network_map(request: Request):
    """Network map view - basic page to load/define the necessary Javascript.

    Network data is then loaded via Javascript from the `map-data` view.

    """
    # TODO: read starting coordinates/zoom from query string
    # (and/or use https://github.com/mlevans/leaflet-hash)

    config: AppConfig = request.registry.settings["app_config"]

    node_icons = {
        key: request.static_url(f"meshinfo:static/img/map/{filename}")
        for key, filename in NODE_ICONS
    }
    # FIXME: add map layers

    return {
        "node_icons": node_icons,
        "latitude": config.map.latitude,
        "longitude": config.map.longitude,
        "zoom": config.map.zoom,
        "max_zoom": config.map.max_zoom,
        "tile_url": config.map.tile_url,
        "tile_attribution": config.map.tile_attribution,
    }


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
            "features": [GeoNode.from_model(node) for node in nodes],
        },
        "links": {
            "type": "FeatureCollection",
            "features": [GeoLink.from_model(link) for link in _dedupe_links(links)],
        },
    }


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
