from pyramid.httpexceptions import HTTPNotFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.settings import asbool
from pyramid.view import view_config, view_defaults
from sqlalchemy.orm import Session, joinedload, load_only

from ..historical import HistoricalStats
from ..models import Link, Node
from . import schema


@view_defaults(route_name="link-graph", http_cache=120)
class LinkGraphs:
    """Graph link data."""

    def __init__(self, request: Request):
        source_id = int(request.matchdict["source"])
        destination_id = int(request.matchdict["destination"])
        dbsession: Session = request.dbsession

        self.link = (
            dbsession.query(Link)
            .options(
                load_only(Link.source_id, Link.destination_id),
                joinedload(Link.destination).load_only(Node.name),
            )
            .get((source_id, destination_id))
        )
        if self.link is None:
            raise HTTPNotFound("Sorry, the specified link could not be found")

        self.name_in_title = asbool(request.GET.get("name_in_title", False))

        self.graph_params = schema.graph_params(request.GET)

        self.stats: HistoricalStats = request.find_service(HistoricalStats)

    @view_config(match_param="name=cost")
    def cost_graph(self):
        title_parts = (
            self.link.destination.name.lower() if self.name_in_title else "",
            "route cost",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_link_cost(
                self.link,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )

    @view_config(match_param="name=snr")
    def snr_graph(self):
        title_parts = (
            self.link.destination.name.lower() if self.name_in_title else "",
            "snr",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_link_snr(
                self.link,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )

    @view_config(match_param="name=quality")
    def quality_graph(self):
        title_parts = (
            self.link.destination.name.lower() if self.name_in_title else "",
            "link quality",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)
        return Response(
            self.stats.graph_link_quality(
                self.link,
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )
