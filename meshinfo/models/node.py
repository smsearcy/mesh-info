from __future__ import annotations

from typing import TYPE_CHECKING

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

from ..types import Band, NodeStatus
from .meta import Base, PDateTime

if TYPE_CHECKING:
    from .link import Link


class Node(Base):
    """Information about a node in the mesh network."""

    __tablename__ = "node"

    id = Column("node_id", Integer, primary_key=True)
    name = Column(String(70), nullable=False)
    status = Column(Enum(NodeStatus, native_enum=False), nullable=False)
    display_name = Column(String(70), nullable=False)

    # store the wireless/primary IP address
    ip_address = Column("wlan_ip", String(15), nullable=False)
    description = Column(Unicode(1024), nullable=False)

    # store the MAC address (without colons) corresponding the primary interface
    mac_address = Column("wlan_mac_address", String(12), nullable=False)

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
    band = Column(
        Enum(Band, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )

    services = Column(JSON(), nullable=False)

    # As of API v1.10 this is irrelevant (because it is always enabled)
    # (probably worth deleting at some point in the future)
    tunnel_installed = Column(Boolean(), nullable=False, default=True)
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

    links: list[Link] = relationship(
        "Link", foreign_keys="Link.source_id", back_populates="source"
    )

    # Is this premature optimization?
    Index("idx_mac_name", mac_address, name)

    @property
    def location(self) -> str:
        if self.longitude and self.latitude:
            return f"{self.longitude:.3f},{self.latitude:.3f}"
        if self.grid_square:
            return self.grid_square
        return "Unknown"

    def __repr__(self):
        return f"<models.Node(id={self.id!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.ip_address})"
