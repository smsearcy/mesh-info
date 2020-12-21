from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from .meta import Base


class Link(Base):
    """Represents a link between two nodes."""

    __tablename__ = "link"

    source_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    destination_id = Column(Integer, ForeignKey("node.node_id"), primary_key=True)
    olsr_cost = Column(Float)
    distance = Column(Float)
    bearing = Column(Float)

    # link_info columns to add later
    # FIXME: make this an enum?
    # type = Column(String(10))  # "RF", "DTD", ???
    # signal = Column(Float)
    # noise = Column(Float)
    # tx_rate = Column(Float)
    # rx_rate = Column(Float)
    # link_quality = Column(Float)
    # neighbor_link_quality = Column(Float)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    source = relationship("Node", foreign_keys="Link.source_id", back_populates="links")
    destination = relationship("Node", foreign_keys="Link.destination_id")

    def __repr__(self):
        return (
            f"<models.Link(source_id={self.source_id!r}, "
            f"destination_id={self.destination_id!r})>"
        )
