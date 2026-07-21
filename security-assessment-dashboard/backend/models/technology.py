"""The ``Technology`` model: a normalized software/product signature.

Extracted from a ``Service``'s ``product``/``version`` at persistence time
(see ``backend.services.host_inventory_service``) rather than left as flat
strings only -- this is what lets "every service running Apache 2.4.49
across this assessment" be a real query instead of a string search.
``service_id`` is nullable because some technology signals are host-level
(e.g. an OS-implied stack) rather than tied to one specific service.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import TechnologyCategory

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.service import Service
    from backend.models.tool_execution import ToolExecution


class Technology(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One detected software/product on a host, optionally scoped to a service."""

    __tablename__ = "technologies"
    __table_args__ = (
        Index("uq_technologies_host_id_service_id_name", "host_id", "service_id", "name", unique=True),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[TechnologyCategory] = mapped_column(
        Enum(TechnologyCategory, native_enum=False, validate_strings=True, create_constraint=True, length=24),
        nullable=False,
        default=TechnologyCategory.OTHER,
    )
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    host: Mapped["DiscoveredHost"] = relationship(back_populates="technologies")
    service: Mapped["Service | None"] = relationship(back_populates="technologies")
    source_execution: Mapped["ToolExecution | None"] = relationship()
