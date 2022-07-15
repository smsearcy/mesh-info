import csv
import io
from operator import attrgetter
from typing import List

import pendulum
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.request import Request, Response
from pyramid.view import view_config, view_defaults
from sqlalchemy.orm import Session, subqueryload

from ..models import CollectorStat, Node
from ..types import NodeStatus


@view_defaults(route_name="nodes")
class NodeListViews:
    def __init__(self, request: Request):
        dbsession: Session = request.dbsession

        # TODO: parameters to determine which nodes to return
        query = dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
        self.nodes: List[Node] = sorted(query.all(), key=attrgetter("name"))
        self.request = request

    @view_config(match_param="view=table", renderer="meshinfo:templates/nodes.jinja2")
    def table(self):
        return {"nodes": self.nodes}

    @view_config(match_param="view=csv")
    def csv(self):
        output = io.StringIO(newline="")
        csv_out = csv.writer(output)
        csv_out.writerow(
            (
                "Name",
                "WLAN IP",
                "Status",
                "Band",
                "Channel",
                "Channel Bandwidth",
                "Link Count",
                "Active Tunnel Count",
                "Firmware",
                "API Version",
                "Last Seen",
            )
        )
        for node in self.nodes:
            csv_out.writerow(
                (
                    node.name,
                    node.wlan_ip,
                    node.status,
                    node.band,
                    node.channel,
                    node.channel_bandwidth,
                    node.link_count,
                    node.active_tunnel_count,
                    node.firmware_version,
                    node.api_version,
                    node.last_seen,
                )
            )

        output.seek(0)
        response: Response = self.request.response
        response.text = output.read()
        response.content_type = "text/csv"
        response.content_disposition = "attachment; filename=node-export.csv"

        return response


@view_config(route_name="node-errors", renderer="meshinfo:templates/node-errors.jinja2")
def node_errors(request: Request):
    dbsession: Session = request.dbsession
    try:
        timestamp = pendulum.from_format(request.matchdict["timestamp"], "X")
    except Exception as exc:
        raise HTTPBadRequest("Invalid timestamp") from exc

    marked_row = request.GET.get("highlight")

    collector = (
        dbsession.query(CollectorStat)
        .options(subqueryload(CollectorStat.node_errors))
        .filter(CollectorStat.started_at == timestamp)
        .one_or_none()
    )
    if collector is None:
        raise HTTPNotFound(f"No collection statistics available for {timestamp}")

    return {
        "marked_ip": marked_row,
        "node_errors": collector.node_errors,
        "stats": collector,
    }
