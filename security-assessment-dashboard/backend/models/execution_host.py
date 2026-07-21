"""The ``ExecutionHost`` model: which execution touched which discovered host.

The execution-history join table -- a ``DiscoveredHost`` no longer belongs to
one execution (see ``backend.models.discovered_host``), so this is the only
durable record of "job X discovered/re-confirmed host Y," with ``is_new``
distinguishing first discovery from a later re-confirmation.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.models.discovered_host import DiscoveredHost
    from backend.models.tool_execution import ToolExecution


class ExecutionHost(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One record of one execution touching one discovered host."""

    __tablename__ = "execution_hosts"
    __table_args__ = (
        Index("uq_execution_hosts_execution_id_host_id", "execution_id", "host_id", unique=True),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovered_hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, doc="Did this execution create the host, or just re-confirm it?")

    execution: Mapped["ToolExecution"] = relationship(back_populates="execution_hosts")
    host: Mapped["DiscoveredHost"] = relationship(back_populates="execution_links")
