from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Unicode,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import relationship

from .meta import Base, NodeStatus, utcnow


class Node(Base):
    """Information about a node in the mesh network."""

    __tablename__ = "node"

    id = Column("node_id", Integer, primary_key=True)
    name = Column(String(70), nullable=False)
    status = Column(Enum(NodeStatus), nullable=False)

    wlan_ip = Column(String(15), nullable=False)
    description = Column(Unicode(1024), nullable=False)

    # store MAC addresses without colons
    wlan_mac_address = Column(String(12), nullable=False)

    last_seen = Column(TIMESTAMP(timezone=True), nullable=False)

    up_time = Column(String(25), nullable=False)
    load_averages = Column(ARRAY(Float, dimensions=1))
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

    system_info = Column(JSON(), nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=utcnow(), nullable=False)
    last_updated_at = Column(
        TIMESTAMP(timezone=True),
        default=utcnow(),
        onupdate=utcnow(),
        nullable=False,
    )

    links = relationship("Link", foreign_keys="Link.source_id", back_populates="source")

    Index(
        "active_name", name, unique=True, postgresql_where=status == NodeStatus.ACTIVE
    )
    Index(
        "active_mac",
        wlan_mac_address,
        unique=True,
        postgresql_where=status == NodeStatus.ACTIVE,
    )
    Index(
        "active_ip", wlan_ip, unique=True, postgresql_where=status == NodeStatus.ACTIVE
    )

    def __repr__(self):
        return f"<models.Node(id={self.id!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.wlan_ip})"
