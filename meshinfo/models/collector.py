import pendulum
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from ..poller import PollingError
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

    node_errors = relationship(
        "NodeError", foreign_keys="NodeError.timestamp", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<models.CollectorStat(started_at={self.started_at})>"


class NodeError(Base):
    """Information about nodes with errors during collection."""

    __tablename__ = "node_error"

    timestamp = sa.Column(
        PDateTime(), sa.ForeignKey("collector_stat.started_at"), primary_key=True
    )
    ip_address = sa.Column(sa.String(15), primary_key=True)
    dns_name = sa.Column(sa.String(70), nullable=False)
    error_type = sa.Column(sa.Enum(PollingError, native_enum=False), nullable=False)
    details = sa.Column(sa.UnicodeText, nullable=False)
