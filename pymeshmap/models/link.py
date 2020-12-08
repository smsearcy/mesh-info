from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from .meta import Base


class Link(Base):
    """Represents a link between two nodes."""

    __tablename__ = "link"

    source_id = Column(Integer, ForeignKey("node.id"), primary_key=True)
    destination_id = Column(Integer, ForeignKey("node.id"), primary_key=True)
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
    updated_at = Column(DateTime, onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<models.Link(source_id={self.source_id!r}, destination_id={self.destination_id!r})>"
