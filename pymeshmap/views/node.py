from pyramid.httpexceptions import HTTPNotFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.settings import asbool
from pyramid.view import view_config, view_defaults
from sqlalchemy.orm import Session, joinedload, load_only

from ..aredn import VersionChecker
from ..historical import HistoricalStats
from ..models import Link, LinkStatus, Node
from . import schema


@view_config(route_name="node", renderer="pymeshmap:templates/node.jinja2")
def node_detail(request: Request):
    """Detailed view of a single node."""

    node_id = int(request.matchdict["id"])
    dbsession: Session = request.dbsession
    version_checker: VersionChecker = request.find_service(VersionChecker)

    node = dbsession.query(Node).get(node_id)

    if node is None:
        raise HTTPNotFound("Sorry, the specified node could not be found")

    firmware_status = version_checker.firmware(node.firmware_version)
    api_status = version_checker.api(node.api_version)

    query = (
        dbsession.query(Link)
        .options(joinedload(Link.destination).load_only("name"))
        .filter(
            Link.source_id == node.id,
            Link.status != LinkStatus.INACTIVE,
        )
    )

    links = query.all()

    return {
        "node": node,
        "links": links,
        "firmware_status": firmware_status,
        "api_status": api_status,
    }


@view_defaults(route_name="node-graph", http_cache=120)
class NodeGraphs:
    """Graph node data."""

    def __init__(self, request: Request):
        node_id = int(request.matchdict["id"])
        dbsession: Session = request.dbsession

        self.node = (
            dbsession.query(Node).options(load_only(Node.id, Node.name)).get(node_id)
        )
        if self.node is None:
            raise HTTPNotFound("Sorry, the specified node could not be found")

        self.graph_params = schema.graph_params(request.GET)
        self.name_in_title = asbool(request.GET.get("name_in_title", False))

        self.stats: HistoricalStats = request.find_service(HistoricalStats)

    @view_config(match_param="name=links")
    def links(self):
        title_parts = (
            self.node.name.lower() if self.name_in_title else "",
            "links",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_node_links(
                self.node,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )

    @view_config(match_param="name=load")
    def load(self):
        title_parts = (
            self.node.name.lower() if self.name_in_title else "",
            "load",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_node_load(
                self.node,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )

    @view_config(match_param="name=uptime")
    def uptime(self):
        title_parts = (
            self.node.name.lower() if self.name_in_title else "",
            "uptime",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_node_uptime(
                self.node,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )
