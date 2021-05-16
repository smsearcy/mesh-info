from operator import attrgetter

import sqlalchemy as sa
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import Link, LinkStatus, Node, NodeStatus


@view_config(route_name="nodes", renderer="pymeshmap:templates/nodes.jinja2")
def node_list(request: Request):
    """View a list of nodes as a web page."""

    dbsession: Session = request.dbsession

    # TODO: parameters to determine which nodes to return
    query = dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
    nodes = query.all()

    query = (
        dbsession.query(Link.source_id, sa.func.count(Link.source_id))
        .filter(Link.status == LinkStatus.CURRENT)
        .group_by(Link.source_id)
    )
    node_link_counts = {node_id: link_count for node_id, link_count in query.all()}

    return {
        "nodes": sorted(nodes, key=attrgetter("name")),
        "link_counts": node_link_counts,
    }
