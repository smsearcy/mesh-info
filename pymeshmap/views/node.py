from pyramid.httpexceptions import HTTPNotFound
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session, joinedload

from ..models import Link, LinkStatus, Node


@view_config(route_name="node", renderer="pymeshmap:templates/node.jinja2")
def node_detail(request: Request):
    """Detailed view of a single node."""

    node_id = int(request.matchdict["id"])
    dbsession: Session = request.dbsession

    node = dbsession.query(Node).get(node_id)

    if node is None:
        raise HTTPNotFound("Sorry, the specified node could not be found")

    query = (
        dbsession.query(Link)
        .options(joinedload(Link.destination).load_only("name"))
        .filter(
            Link.source_id == node.id,
            Link.status != LinkStatus.INACTIVE,
        )
    )

    links = query.all()

    return {"node": node, "links": links}
