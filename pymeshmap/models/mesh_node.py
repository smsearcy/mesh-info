import enum
import json

from sqlalchemy import Boolean, Column, DateTime, Float, String
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

    *Attention:* This implementation will not detect changes to the object
    (but it will detect when replaced which is what we should be doing).

    """

    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MeshNode(Base):
    """Information about a node in the mesh network."""

    __tablename__ = "node_info"

    wlan_ip = Column(String(50), primary_key=True)
    name = Column("node", String(70), unique=True)
    lan_ip = Column(String(50))

    last_seen = Column(DateTime)

    up_time = Column("uptime", String(50))
    load_average = Column("loadavg", JsonEncodedValue(128))
    model = Column(String(50))
    board_id = Column(String(50))
    firmware_version = Column(String(50))
    firmware_manufacturer = Column("firmware_mfg", String(100))
    api_version = Column(String(50))

    latitude = Column("lat", Float, nullable=True)
    longitude = Column("lon", Float, nullable=True)
    grid_square = Column(String(20))
    # Indicates manually entered location
    fixed_location = Column("location_fix", Boolean(), default=False)

    wlan_mac_address = Column("wifi_mac_address", String(50), unique=True)

    ssid = Column(String(50))
    channel = Column(String(50))
    channel_bandwidth = Column("chanbw", String(50))

    # should this be JSON?
    services = Column(JsonEncodedValue(2048))

    # matching existing column types
    tunnel_installed = Column(String(50))
    active_tunnel_count = Column(String(50))

    # not in MeshMap
    # description = Column(Unicode(200))
    # band = Column(String(25))
    # polling_status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE)
    # created_at = Column(DateTime, default=datetime.utcnow())
    # last_updated_at = Column(DateTime, onupdate=datetime.utcnow())

    def __repr__(self):
        return f"<MeshNode(wlan_ip={self.wlan_ip!r}, name={self.name!r})>"

    def __str__(self):
        return f"{self.name} ({self.wlan_ip}; {self.last_seen})"
