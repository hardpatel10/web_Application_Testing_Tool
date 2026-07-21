"""The ``OperatingSystem`` model: one OS candidate match for an asset.

Phase 7's normalizer kept only Nmap's single best-accuracy OS guess,
discarding every other candidate. This table keeps all of them -- an asset
can have several ``OperatingSystem`` rows, ranked by ``accuracy``.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.tool_execution import ToolExecution


class OperatingSystem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One OS candidate match reported for a host."""

    __tablename__ = "operating_systems"
    __table_args__ = (
        Index("uq_operating_systems_host_id_name_version", "host_id", "name", "version", unique=True),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    family: Mapped[str | None] = mapped_column(String(255), nullable=True, doc="e.g. 'Windows', vs. the more specific `name`.")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, doc="e.g. 'nmap-os-detection'.")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    host: Mapped["DiscoveredHost"] = relationship(back_populates="operating_systems")
    source_execution: Mapped["ToolExecution | None"] = relationship()
