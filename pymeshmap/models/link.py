from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from .meta import Base, LinkStatus


class Link(Base):
    """Represents a link between two nodes."""

    __tablename__ = "link"

    source_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    destination_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    status = Column(Enum(LinkStatus), nullable=False)
    last_seen = Column(DateTime, nullable=False)

    olsr_cost = Column(Float)
    distance = Column(Float)
    bearing = Column(Float)

    # link_info columns to add later
    # TODO: make this an enum?
    # type = Column(String(10))  # "RF", "DTD", "TUN"
    # signal = Column(Float)
    # noise = Column(Float)
    # tx_rate = Column(Float)
    # rx_rate = Column(Float)
    # link_quality = Column(Float)
    # neighbor_link_quality = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)
    last_updated_at = Column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False
    )

    source = relationship("Node", foreign_keys="Link.source_id", back_populates="links")
    destination = relationship("Node", foreign_keys="Link.destination_id")

    # is this a case of premature optimization?  (assuming it even does what I hope)
    Index(
        "recent_links",
        status,
        postgresql_where=status.in_((LinkStatus.CURRENT, LinkStatus.RECENT)),
    )

    def __repr__(self):
        return (
            f"<models.Link(source_id={self.source_id!r}, "
            f"destination_id={self.destination_id!r})>"
        )
