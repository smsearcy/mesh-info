from sqlalchemy import Boolean, Column, DateTime, Integer, Unicode

from .meta import Base


class Process(Base):
    """Track mapping processes."""

    __tablename__ = "process"
    id = Column(Integer, primary_key=True, autoincrement=True)
    script_name = Column(Unicode(50))
    last_ran = Column(DateTime)
    currently_running = Column(Boolean)
    # TODO: I identified more details that would be useful to track here
