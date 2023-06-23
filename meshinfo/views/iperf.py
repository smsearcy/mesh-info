from __future__ import annotations

from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import Node
from ..types import NodeStatus


@view_config(route_name="iperf-tool", renderer="pages/iperf.jinja2")
def overview(request: Request):
    dbsession: Session = request.dbsession

    nodes = dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE).all()
    return {"nodes": nodes}
