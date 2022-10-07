from __future__ import annotations

import pendulum
import sqlalchemy as sa

from .historical import HistoricalStats
from .models import CollectorStat, Link, Node, NodeError, session_scope


def main(
    days: int,
    dbsession_factory,
    historical_stats: HistoricalStats,
    *,
    update: bool | None,
):
    """Purge old data from the system."""

    cutoff = pendulum.now().subtract(days=days)
    print()
    print(f"Purging data prior to {cutoff.format('YYYY-MM-DD HH:mm:ss zz')}")

    while update is None:
        print()
        confirm_update = input("Run in update mode? (Yes/No) ")
        if confirm_update.lower() in {"y", "yes"}:
            update = True
        elif confirm_update.lower() in {"n", "no"}:
            update = False

    with session_scope(dbsession_factory) as dbsession:
        print()
        total_node_count = dbsession.query(Node).count()
        nodes = dbsession.query(Node).filter(Node.last_seen < cutoff).all()
        print(
            f"Identified {len(nodes):,d} nodes to purge (out of {total_node_count:,d})."
        )
        node_ids = [node.id for node in nodes]
        links = (
            dbsession.query(Link)
            .filter(
                sa.or_(Link.source_id.in_(node_ids), Link.destination_id.in_(node_ids))
            )
            .all()
        )
        print(f"Identified {len(links):,d} links to purge.")
        stats = (
            dbsession.query(CollectorStat)
            .filter(CollectorStat.started_at < cutoff)
            .all()
        )
        print(f"Identified {len(stats):,d} collector stats to purge.")
        errors = dbsession.query(NodeError).filter(NodeError.timestamp < cutoff).all()
        print(f"Identified {len(errors):,d} node error details to purge.")
        print()

        if not update:
            print("Aborting, no changes made.  Pass '--update' to purge data.")
            return

        for link in links:
            historical_stats.delete_link_data(link)
            dbsession.delete(link)
        for node in nodes:
            historical_stats.delete_node_data(node)
            dbsession.delete(node)
        for error in errors:
            dbsession.delete(error)
        for stat in stats:
            dbsession.delete(stat)

        print("Purge complete.")
