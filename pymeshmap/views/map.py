import sqlalchemy as sa
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session, aliased

from ..models import Link, Node
from ..types import LinkStatus, NodeStatus

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
    # TODO: read starting coordinates/zoom from query string

    node_icons = {
        key: request.static_url(f"pymeshmap:static/img/map/{filename}")
        for key, filename in NODE_ICONS
    }

    return {"node_icons": node_icons}


@view_config(route_name="map-data", renderer="json")
def map_data(request: Request):
    """Generate map data as GeoJSON."""
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
            "features": [_link_geo_json(link) for link in links],
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
    return {
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
            "type": link.type,
            "cost": link.olsr_cost,
        },
    }
