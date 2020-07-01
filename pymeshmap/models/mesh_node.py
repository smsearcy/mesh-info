import enum
import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String, Unicode
from sqlalchemy.types import TypeDecorator

from .meta import Base


class NodeStatus(enum.Enum):
    """Enumerate possible polling statuses for nodes."""

    ACTIVE = enum.auto()
    INACTIVE = enum.auto()
    REMOVED = enum.auto()

    def __str__(self):
        return self.name.title()


class JsonEncodedValue(TypeDecorator):
    """Represent structure as JSON-encoded string.

    *Attention:* This implementation will not detect changes to the object (but will
    detect when it is replaced which is what we would be doing).

    """

    impl = Unicode

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MeshNode(Base):
    """Information about a node in the mesh network.

    Using `NULL`/`None` to indicate missing values.

    """

    __tablename__ = "mesh_node"

    ip_address = Column(String(20), primary_key=True)
    name = Column(Unicode(70))
    description = Column(Unicode(200))
    polling_status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE)
    last_seen = Column(DateTime)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    grid_square = Column(String(20), nullable=True)

    wlan_mac_address = Column(String(50))
    lan_ip = Column(String(20), nullable=True)

    # TODO: double check these against the data class requirements
    model = Column(Unicode(100), nullable=True)
    board_id = Column(Unicode(100), nullable=True)
    firmware_version = Column(Unicode(50), nullable=True)
    firmware_manufacturer = Column(Unicode(100), nullable=True)
    api_version = Column(Unicode(50))
    uptime = Column(Unicode(50), nullable=True)
    load_average = Column(JsonEncodedValue(128))
    # TODO: make another table for services

    mesh_status = Column(String(10))
    ssid = Column(Unicode(100))
    channel = Column(String(25))
    channel_bandwidth = Column(String(25))
    band = Column(String(25))

    tunnel_installed = Column(Boolean)
    active_tunnel_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow())
    last_updated_at = Column(DateTime, onupdate=datetime.utcnow())

    def __repr__(self):
        return f"<models.MeshNode(ip_address={self.ip_address!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.ip_address}): {self.polling_status}"


class IgnoreReasons(enum.Enum):
    """Enumerate possible ignore reasons for nodes."""

    CONNECTION_ERROR = enum.auto()
    INFORMATION_ERROR = enum.auto()


class IgnoreNode(Base):
    """Track hosts to ignore for a period of time based on response."""

    __tablename__ = "ignore_node"

    ip_address = Column("ip_address", String(50), primary_key=True)
    reason = Column(Enum(IgnoreReasons))
    timestamp = Column(DateTime, default=datetime.utcnow())

    def __str__(self):
        return f"{self.ip_address}: {self.reason}"
