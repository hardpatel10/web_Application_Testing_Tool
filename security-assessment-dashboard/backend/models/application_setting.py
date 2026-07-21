"""The ``ApplicationSetting`` model: a global key/value settings store."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base
from backend.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single global application setting, stored as a key/value pair.

    Examples: theme, report defaults, export directory, temp directory,
    default tool timeout. ``value`` holds a JSON-encoded string so a single
    table can hold settings of any shape.
    """

    __tablename__ = "application_settings"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
