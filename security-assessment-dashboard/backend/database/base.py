"""SQLAlchemy declarative base.

All ORM models inherit from ``Base``. Kept in its own module so Alembic's
migration environment can import metadata without importing the full
application.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Explicit naming convention for constraints/indexes. Without this,
# SQLAlchemy leaves auto-generated constraints unnamed, which breaks
# Alembic's SQLite "batch" migration mode (used for ALTER TABLE) once
# later phases need to rename or drop a constraint.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
