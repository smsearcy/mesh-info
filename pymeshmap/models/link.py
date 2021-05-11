from sqlalchemy import TIMESTAMP, Column, Enum, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from ..aredn import LinkType
from .meta import Base, LinkStatus, utcnow


class Link(Base):
    """Represents a link between two nodes."""

    __tablename__ = "link"

    source_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    destination_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    status = Column(Enum(LinkStatus), nullable=False)
    last_seen = Column(TIMESTAMP(timezone=True), nullable=False, default=utcnow())

    olsr_cost = Column(Float)
    distance = Column(Float)
    bearing = Column(Float)

    type = Column(Enum(LinkType))
    signal = Column(Float)
    noise = Column(Float)
    tx_rate = Column(Float)
    rx_rate = Column(Float)
    quality = Column(Float)
    neighbor_quality = Column(Float)

    created_at = Column(TIMESTAMP(timezone=True), default=utcnow(), nullable=False)
    last_updated_at = Column(
        TIMESTAMP(timezone=True),
        default=utcnow(),
        onupdate=utcnow(),
        nullable=False,
    )

    source = relationship("Node", foreign_keys="Link.source_id", back_populates="links")
    destination = relationship("Node", foreign_keys="Link.destination_id")

    # is this a case of premature optimization?  (assuming it even does what I hope)
    Index(
        "recent_links",
        status,
        postgresql_where=status.in_((LinkStatus.CURRENT, LinkStatus.RECENT)),
    )

    @property
    def signal_noise_ratio(self):
        if self.signal is None or self.noise is None:
            return None
        return self.signal - self.noise

    def __repr__(self):
        return (
            f"<models.Link(source_id={self.source_id!r}, "
            f"destination_id={self.destination_id!r})>"
        )
