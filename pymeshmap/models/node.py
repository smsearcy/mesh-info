import pendulum
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Unicode,
)
from sqlalchemy.orm import relationship

from ..types import NodeStatus
from .meta import Base, PDateTime


class Node(Base):
    """Information about a node in the mesh network."""

    __tablename__ = "node"

    id = Column("node_id", Integer, primary_key=True)
    name = Column(String(70), nullable=False)
    status = Column(Enum(NodeStatus, native_enum=False), nullable=False)

    # FIXME: need to handle multiple IP addresses (RF(s), DTD, tunnel)
    # (can use IP address type to determine link type on older API)
    wlan_ip = Column(String(15), nullable=False)
    description = Column(Unicode(1024), nullable=False)

    # store MAC addresses without colons
    wlan_mac_address = Column(String(12), nullable=False)

    last_seen = Column(PDateTime(), nullable=False)

    up_time = Column(String(25), nullable=False)
    up_time_seconds = Column(Integer)
    load_averages = Column(JSON())
    model = Column(String(50), nullable=False)
    board_id = Column(String(50), nullable=False)
    firmware_version = Column(String(50), nullable=False)
    firmware_manufacturer = Column(String(100), nullable=False)
    api_version = Column(String(5), nullable=False)

    latitude = Column(Float)
    longitude = Column(Float)
    grid_square = Column(String(20), nullable=False)

    ssid = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)
    channel_bandwidth = Column(String(50), nullable=False)
    band = Column(String(25), nullable=False)

    services = Column(JSON(), nullable=False)

    tunnel_installed = Column(Boolean(), nullable=False)
    active_tunnel_count = Column(Integer(), nullable=False)

    link_count = Column(Integer())
    radio_link_count = Column(Integer())
    dtd_link_count = Column(Integer())
    tunnel_link_count = Column(Integer())

    system_info = Column(JSON(), nullable=False)

    created_at = Column(PDateTime(), default=pendulum.now, nullable=False)
    last_updated_at = Column(
        PDateTime(),
        default=pendulum.now,
        onupdate=pendulum.now,
        nullable=False,
    )

    links = relationship("Link", foreign_keys="Link.source_id", back_populates="source")
    # TODO: add active_links relationship

    # Is this premature optimization?
    Index("idx_mac_name", wlan_mac_address, name)

    @property
    def location(self) -> str:
        if self.longitude and self.latitude:
            return f"{self.longitude:.3f},{self.latitude:.3f}"
        elif self.grid_square:
            return self.grid_square
        else:
            return "Unknown"

    def __repr__(self):
        return f"<models.Node(id={self.id!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.wlan_ip})"
