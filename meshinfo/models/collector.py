import pendulum
import sqlalchemy as sa

from .meta import Base, PDateTime


class CollectorStat(Base):
    """Statistics from the collection process."""

    __tablename__ = "collector_stat"

    started_at = sa.Column(PDateTime(), primary_key=True)
    finished_at = sa.Column(PDateTime(), default=pendulum.now, nullable=False)
    node_count = sa.Column(sa.Integer, nullable=False)
    link_count = sa.Column(sa.Integer, nullable=False)
    error_count = sa.Column(sa.Integer, nullable=False)
    polling_duration = sa.Column(sa.Float, nullable=False)
    total_duration = sa.Column(sa.Float, nullable=False)
    other_stats = sa.Column(sa.JSON, nullable=False)

    def __repr__(self):
        return f"<models.CollectorStat(started_at={self.started_at})>"
