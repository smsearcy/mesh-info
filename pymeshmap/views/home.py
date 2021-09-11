import sqlalchemy as sa
from pyramid.request import Request
from pyramid.view import view_config
from sqlalchemy.orm import Session

from ..models import CollectorStat, Link, LinkStatus, Node, NodeStatus


@view_config(route_name="home", renderer="pymeshmap:templates/home.jinja2")
def overview(request: Request):

    dbsession: Session = request.dbsession

    node_count = (
        dbsession.query(Node).filter(Node.status != NodeStatus.INACTIVE).count()
    )
    link_count = (
        dbsession.query(Link).filter(Link.status != LinkStatus.INACTIVE).count()
    )

    query = (
        dbsession.query(Node.firmware_version, sa.func.count(Node.id))
        .filter(Node.status == NodeStatus.ACTIVE)
        .group_by(Node.firmware_version)
    )
    firmware_stats = {version: count for version, count in query.all()}
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

    return {
        "node_count": node_count,
        "link_count": link_count,
        "last_run": last_run,
        "firmware_stats": firmware_stats,
        "band_stats": band_stats,
    }
