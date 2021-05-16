from sqlalchemy import Column, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSON

from .meta import Base, PDateTime, utcnow


class CollectorStat(Base):
    """Statistics from the collection process."""

    __tablename__ = "collector_stat"

    started_at = Column(PDateTime(), primary_key=True)
    finished_at = Column(PDateTime(), default=utcnow(), nullable=False)
    node_count = Column(Integer, nullable=False)
    link_count = Column(Integer, nullable=False)
    error_count = Column(Integer, nullable=False)
    polling_duration = Column(Numeric(8, 4), nullable=False)
    total_duration = Column(Numeric(8, 4), nullable=False)
    other_stats = Column(JSON(), nullable=False)

    def __repr__(self):
        return f"<models.CollectorStat(started_at={self.started_at})>"
