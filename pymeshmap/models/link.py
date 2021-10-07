import pendulum
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from ..types import LinkId, LinkStatus, LinkType
from .meta import Base, PDateTime


class Link(Base):
    """Represents a link between two nodes."""

    __tablename__ = "link"

    source_id = sa.Column(sa.Integer, sa.ForeignKey("node.node_id"), primary_key=True)
    destination_id = sa.Column(
        sa.Integer, sa.ForeignKey("node.node_id"), primary_key=True
    )
    type = sa.Column(sa.Enum(LinkType), primary_key=True)
    status = sa.Column(sa.Enum(LinkStatus, native_enum=False), nullable=False)
    last_seen = sa.Column(PDateTime(), nullable=False, default=pendulum.now)

    olsr_cost = sa.Column(sa.Float)
    distance = sa.Column(sa.Float)
    bearing = sa.Column(sa.Float)

    signal = sa.Column(sa.Float)
    noise = sa.Column(sa.Float)
    tx_rate = sa.Column(sa.Float)
    rx_rate = sa.Column(sa.Float)
    quality = sa.Column(sa.Float)
    neighbor_quality = sa.Column(sa.Float)

    created_at = sa.Column(PDateTime(), default=pendulum.now, nullable=False)
    last_updated_at = sa.Column(
        PDateTime(),
        default=pendulum.now,
        onupdate=pendulum.now,
        nullable=False,
    )

    source = relationship("Node", foreign_keys="Link.source_id", back_populates="links")
    destination = relationship("Node", foreign_keys="Link.destination_id")

    @property
    def signal_noise_ratio(self):
        if self.signal is None or self.noise is None:
            return None
        return self.signal - self.noise

    @property
    def id(self) -> LinkId:
        """Simple link identifier (useful for consistent serialization)."""
        return LinkId(self.source_id, self.destination_id, self.type)

    def __repr__(self):
        return (
            f"<models.Link(source_id={self.source_id!r}, "
            f"destination_id={self.destination_id!r})>"
        )
