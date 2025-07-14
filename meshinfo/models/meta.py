from __future__ import annotations

import pendulum
from sqlalchemy.orm import declarative_base
from sqlalchemy.schema import MetaData
from sqlalchemy.types import TIMESTAMP, TypeDecorator

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


# Necessary for 2.0 migration:
# https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-to-2-0-step-six-add-allow-unmapped-to-explicitly-typed-orm-models
class _Base:
    __allow_unmapped__ = True


metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata, cls=_Base)


class PDateTime(TypeDecorator):
    """SQLAlchemy type to wrap `pendulum.datetime` instead of `datetime.datetime`."""

    impl = TIMESTAMP(timezone=True)
    cache_ok = False

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, pendulum.DateTime):
                # Pendulum enforces non-naive datetime objects
                raise TypeError(f"Expected pendulum.datetime, not {value!r}")
            value = value.in_tz("UTC")
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = pendulum.instance(value)

        return value
