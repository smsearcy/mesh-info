from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import Node, NodeStatus


@view_config(route_name="nodes", renderer="pymeshmap:templates/nodes.mako")
def overview(request: Request):

    dbsession: Session = request.find_service(name="db")

    query = dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
    nodes = query.all()

    return {"nodes": nodes}
