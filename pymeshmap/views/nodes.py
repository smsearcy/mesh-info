from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import Node, NodeStatus


@view_config(route_name="nodes", renderer="pymeshmap:templates/nodes.mako")
def node_list(request: Request):

    dbsession: Session = request.dbsession

    # TODO: parameters to determine which nodes to return
    query = dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
    nodes = query.all()

    return {"nodes": nodes}
