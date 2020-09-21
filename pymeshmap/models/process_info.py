import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer

from .meta import Base


class ProcessType(enum.Enum):
    NODES = "NODEINFO"
    LINKS = "LINKINFO"


class ProcessInfo(Base):
    """Track mapping processes, aiming for necessary compatibility with MeshMap."""

    __tablename__ = "map_info"

    type = Column("id", Enum(ProcessType), primary_key=True)
    record_count = Column("table_records_num", Integer)
    table_last_update = Column(DateTime)
    last_ran = Column("script_last_run", DateTime)
    currently_running = Column(Boolean)
    # TODO: I identified more details that would be useful to track here
