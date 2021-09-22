from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config, view_defaults

from ..historical import HistoricalStats
from . import schema


@view_config(
    route_name="network-graphs", renderer="pymeshmap:templates/network-graphs.jinja2"
)
def network_graphs(request: Request):
    """Page displaying graphs of particular data over different timeframes."""
    graph = request.matchdict["name"]
    return {
        "graph": graph,
        "graph_name": graph.title(),  # use a dictionary for more control of the name?
    }


@view_defaults(route_name="network-graph", http_cache=120)
class NetworkGraphs:
    def __init__(self, request: Request):
        self.graph_params = schema.graph_params(request.GET)
        self.stats: HistoricalStats = request.find_service(HistoricalStats)

    @view_config(match_param="name=info")
    def info(self):
        title_parts = (
            "network info",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)

        return Response(
            self.stats.graph_network_stats(
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )

    @view_config(match_param="name=poller")
    def poller(self):
        title_parts = (
            "poller stats",
            self.graph_params.title,
        )
        title = " - ".join(part for part in title_parts if part)

        return Response(
            self.stats.graph_poller_stats(
                start=self.graph_params.start,
                end=self.graph_params.end,
                title=title,
            ),
            status="200 OK",
            content_type="image/png",
        )
