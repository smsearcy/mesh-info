import csv
import io
from operator import attrgetter
from typing import List

import attrs
from pyramid.request import Request, Response
from pyramid.view import view_config, view_defaults
from sqlalchemy.orm import Session

from ..models import Node
from ..types import NodeStatus


@attrs.define
class Page:
    number: int
    url: str
    classes: list[str] = attrs.Factory(list)


@view_defaults(route_name="nodes")
class NodeListViews:
    def __init__(self, request: Request):
        self.dbsession: Session = request.dbsession
        self.request = request

    @view_config(match_param="view=table", renderer="pages/nodes.jinja2")
    def table(self):
        current_page = int(self.request.GET.get("page", 1))
        per_page = int(self.request.GET.get("per_page", 25))

        # TODO: add search/sort parameters

        query = self.dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
        nodes: List[Node] = sorted(query.all(), key=attrgetter("name"))

        page_count = (len(nodes) // per_page) + 1
        pages = []
        for page_nbr in range(1, page_count + 1):
            page = Page(
                number=page_nbr,
                url=self.request.route_url(
                    "nodes", view="table", _query={"page": page_nbr}
                ),
            )
            if page_nbr == current_page:
                page.classes.append("is-current")
            pages.append(page)

        nodes = nodes[(current_page - 1) * per_page : current_page * per_page]
        return {"nodes": nodes, "pages": pages}

    @view_config(match_param="view=csv")
    def csv(self) -> Response:
        output = io.StringIO(newline="")
        csv_out = csv.writer(output)
        csv_out.writerow(
            (
                "Name",
                "IP Address",
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
        query = self.dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE)
        for node in sorted(query.all(), key=attrgetter("name")):
            csv_out.writerow(
                (
                    node.name,
                    node.ip_address,
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
