import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Unicode,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON

from .meta import Base


class NodeStatus(enum.Enum):
    """Enumerate possible polling statuses for nodes."""

    ACTIVE = enum.auto()
    INACTIVE = enum.auto()

    def __str__(self):
        return self.name.title()


class Node(Base):
    """Information about a node in the mesh network."""

    __tablename__ = "node"

    id = Column("node_id", Integer, primary_key=True)
    name = Column(String(70), nullable=False)
    status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE, nullable=False)

    wlan_ip = Column(String(15), nullable=False)
    description = Column(Unicode(200), nullable=False)

    # store MAC addresses without colons
    wlan_mac_address = Column(String(12), nullable=False)

    last_seen = Column(DateTime, nullable=False)

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

    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_updated_at = Column(DateTime, onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<models.Node(id={self.id!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.wlan_ip})"
