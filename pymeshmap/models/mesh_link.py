from sqlalchemy import Column, DateTime, Float, String

from .meta import Base


class MeshLink(Base):
    """Represents a link between two nodes."""

    __tablename__ = "topology"

    source = Column("node", String(70), primary_key=True)
    source_latitude = Column("nodelat", Float)
    source_longitude = Column("nodelon", Float)
    destination = Column("linkto", String(70))
    destination_latitude = Column("linklat", Float)
    destination_longitude = Column("linklon", Float, primary_key=True)
    cost = Column(Float)
    distance = Column(Float)
    bearing = Column(Float)
    last_updated = Column("lastupd", DateTime)

    # TODO: update and add relationships once the nodes are keyed by IP

    def __repr__(self):
        return f"<MeshLink(source={self.source!r}, destination={self.destination!r})>"
