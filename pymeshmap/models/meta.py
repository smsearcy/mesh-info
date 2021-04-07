import enum

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import expression
from sqlalchemy.types import DateTime

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

metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)


class NodeStatus(enum.Enum):
    """Enumerate possible polling statuses for nodes."""

    ACTIVE = enum.auto()
    INACTIVE = enum.auto()

    def __str__(self):
        return self.name.title()


class LinkStatus(enum.Enum):
    """Enumerate possible statuses for links."""

    CURRENT = enum.auto()
    RECENT = enum.auto()
    INACTIVE = enum.auto()

    def __str__(self):
        return self.name.title()


class utcnow(expression.FunctionElement):
    type = DateTime()


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"
