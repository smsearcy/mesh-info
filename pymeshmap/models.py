"""Data models for the pyMeshMap application.

Implemented as SQLAlchemy models for ease of integration with the ORM.  Models are based
on the models from *MeshMap* with some adaptations.

Not yet implemented:
* marker_info

*NOTE:* All timestamps in the database must be stored in UTC.

SQLAlchemy setup based on
[Pyramid's Cookiecutter](https://github.com/Pylons/pyramid-cookiecutter-starter)

"""
import enum
import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Unicode,
    UnicodeText,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import MetaData
from sqlalchemy.types import TypeDecorator

# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class NodeStatus(enum.Enum):
    """Enumerate possible polling statuses for nodes."""

    ACTIVE = enum.auto()
    INACTIVE = enum.auto()
    REMOVED = enum.auto()


class IgnoreReasons(enum.Enum):
    """Enumerate possible ignore reasons for nodes."""

    NOT_FOUND = enum.auto()
    NO_ROUTE = enum.auto()
    REFUSED = enum.auto()


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


metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)


class IgnoreHost(Base):
    """Track hosts to ignore for a period of time based on response."""

    __tablename__ = "hosts_ignore"

    name = Column(Unicode(70), primary_key=True)
    ip_address = Column("ip", String(50), index=True)
    reason = Column(Enum(IgnoreReasons))
    timestamp = Column(DateTime, default=datetime.utcnow())

    def __str__(self):
        return f"{self.name} ({self.ip_address}): {self.reason}"


class MapInfo(Base):
    """Track mapping processes."""

    __tablename__ = "map_info"
    id = Column(Unicode(50), primary_key=True)
    script_name = Column(Unicode(50))
    last_ran = Column(DateTime)
    currently_running = Column(Boolean)


class NodeInfo(Base):
    """Information about a node in the mesh network.

    Using `NULL`/`None` to indicate missing values.

    """

    __tablename__ = "node_info"

    node_name = Column(Unicode(70), primary_key=True)
    polling_status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE)
    last_seen = Column(DateTime)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    grid_square = Column(String(20), nullable=True)

    wlan_ip = Column(String(50), nullable=True)
    wlan_mac_address = Column(String(50))
    lan_ip = Column(String(50), nullable=True)

    # default text or nullable?
    model = Column(Unicode(100), nullable=True)
    board_id = Column(Unicode(100), nullable=True)
    firmware_version = Column(Unicode(50), nullable=True)
    firmware_manufacturer = Column(Unicode(100), nullable=True)
    api_version = Column(Unicode(50))
    uptime = Column(Unicode(50), nullable=True)
    load_average = Column(JsonEncodedValue(128))
    services = Column(JsonEncodedValue(2048))

    ssid = Column(Unicode(100))
    channel = Column(String(25))
    frequency = Column(String(25))
    channel_bandwidth = Column(String(25))

    tunnel_installed = Column(Boolean)
    active_tunnel_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow())
    last_updated_at = Column(DateTime, onupdate=datetime.utcnow())

    def __str__(self):
        return f"{self.node_name} ({self.polling_status})"
