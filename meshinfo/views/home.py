from __future__ import annotations

import re
from collections import defaultdict

import sqlalchemy as sa
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import CollectorStat, Link, Node, NodeError
from ..types import LinkStatus, NodeStatus


@view_config(route_name="home", renderer="pages/home.jinja2")
def overview(request: Request):
    dbsession: Session = request.dbsession

    node_count = (
        dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE).count()
    )
    link_count = (
        dbsession.query(Link).filter(Link.status != LinkStatus.INACTIVE).count()
    )

    # Get node counts by firmware version
    query = (
        dbsession.query(Node.firmware_version, sa.func.count(Node.id))
        .filter(Node.status == NodeStatus.ACTIVE)
        .group_by(Node.firmware_version)
    )
    firmware_stats: defaultdict[str, int] = defaultdict(int)
    for version, count in query.all():
        if re.match(r"\d+\.\d+\.\d+\.\d+", version):
            # match typical AREDN version (e.g. 3.25.2.0)
            firmware_stats[version] = count
        elif re.match(r"\d{8}-[0-9A-Fa-f]+", version):
            # match AREDN nightly version of date and hexadecimal (as of April 2025)
            firmware_stats["Nightly"] += count
        else:
            firmware_stats["Unknown"] += count
    # Get node counts by API version
    query = (
        dbsession.query(Node.api_version, sa.func.count(Node.id))
        .filter(Node.status == NodeStatus.ACTIVE)
        .group_by(Node.api_version)
    )
    api_version_stats = {version: count for version, count in query.all()}

    # Get node counts by band
    query = (
        dbsession.query(Node.band, sa.func.count(Node.id))
        .filter(Node.status == NodeStatus.ACTIVE)
        .group_by(Node.band)
    )
    band_stats = {band: count for band, count in query.all()}

    last_run = (
        dbsession.query(CollectorStat)
        .order_by(sa.desc(CollectorStat.started_at))
        .first()
    )

    node_errors_by_type: dict[str, list[NodeError]] = {}
    if last_run:
        query = dbsession.query(NodeError).filter(
            NodeError.timestamp == last_run.started_at
        )
        for error in query.all():
            node_errors_by_type.setdefault(str(error.error_type), []).append(error)

    return {
        "api_stats": api_version_stats,
        "band_stats": band_stats,
        "firmware_stats": firmware_stats,
        "last_run": last_run,
        "link_count": link_count,
        "node_count": node_count,
        "node_errors": node_errors_by_type,
    }
