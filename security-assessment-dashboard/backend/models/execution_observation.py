"""The ``ExecutionObservation`` model: which execution (re-)observed which observation.

Mirrors ``ExecutionHost`` exactly, for the same reason: an ``Observation``
is deduplicated across scans (see ``backend.models.observation``), so this
join table is the only durable record of every execution that (re-)observed it.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.models.observation import Observation
    from backend.models.tool_execution import ToolExecution


class ExecutionObservation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One record of one execution (re-)observing one observation."""

    __tablename__ = "execution_observations"
    __table_args__ = (
        Index("uq_execution_observations_execution_id_observation_id", "execution_id", "observation_id", unique=True),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, doc="Did this execution create the observation, or just re-observe it?")

    execution: Mapped["ToolExecution"] = relationship(back_populates="execution_observations")
    observation: Mapped["Observation"] = relationship()
