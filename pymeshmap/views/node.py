from pyramid.httpexceptions import HTTPNotFound
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session, joinedload

from ..models import Node


@view_config(route_name="node", renderer="pymeshmap:templates/node.mako")
def node_detail(request: Request):
    """Detailed view of a single node."""

    node_id = int(request.matchdict["id"])
    dbsession: Session = request.dbsession

    node = dbsession.query(Node).options(joinedload(Node.links)).get(node_id)

    if node is None:
        raise HTTPNotFound("Sorry, the specified node could not be found")

    return {"node": node}
