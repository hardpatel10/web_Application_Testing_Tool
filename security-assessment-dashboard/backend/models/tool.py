"""The ``Tool`` and ``ToolConfiguration`` models.

``Tool`` is the catalog row for one installed (or installable) security
tool plugin. ``ToolConfiguration`` stores that tool's execution defaults
in a strict one-to-one relationship.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.models.enums import ToolHealthStatus, ToolStatus

if TYPE_CHECKING:
    from backend.models.assessment_tool import AssessmentTool
    from backend.models.tool_execution import ToolExecution


class Tool(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Catalog entry for one security tool plugin.

    Populated and kept in sync by the plugin subsystem via its
    installation-detection step (``ToolService.sync_catalog``). Never holds
    scan results itself. ``name`` is the plugin framework's manifest id
    (e.g. ``"nmap"``) — deliberately not a separate ``plugin_id`` column,
    since a unique, indexed technical identifier is exactly what ``name``
    already is; ``display_name`` is the human-readable label (e.g. "Nmap").
    """

    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    installation_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_installed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    status: Mapped[ToolStatus] = mapped_column(
        Enum(ToolStatus, native_enum=False, validate_strings=True, create_constraint=True, length=32),
        nullable=False,
        default=ToolStatus.MISSING,
        index=True,
    )
    health_status: Mapped[ToolHealthStatus | None] = mapped_column(
        Enum(ToolHealthStatus, native_enum=False, validate_strings=True, create_constraint=True, length=16),
        nullable=True,
    )
    health_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When POST /tools/{name}/validate (or the bulk /tools/validate) last ran for this tool. "
        "Distinct from last_checked_at: validation additionally checks version support, permissions, "
        "and dependencies, not just installation/health.",
    )

    configuration: Mapped["ToolConfiguration | None"] = relationship(
        back_populates="tool", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    assessment_tools: Mapped[list["AssessmentTool"]] = relationship(
        back_populates="tool", cascade="all, delete-orphan", passive_deletes=True
    )
    executions: Mapped[list["ToolExecution"]] = relationship(back_populates="tool")


class ToolConfiguration(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Execution configuration for one tool.

    One-to-one with :class:`Tool` (enforced by the unique ``tool_id``
    column): a single set of defaults per tool, since this is a
    single-user, single-machine application. This is the persistent
    counterpart of the plugin framework's in-memory
    ``backend.plugins.models.config.PluginConfiguration`` — ``ToolService``
    is the only place that translates between the two.
    """

    __tablename__ = "tool_configurations"

    tool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    timeout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    working_directory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    custom_executable_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    http_proxy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    https_proxy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    socks_proxy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_directory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    temp_directory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    headers_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    environment_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    arguments_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    wordlists_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    disabled_profiles_json: Mapped[list | None] = mapped_column(
        JSON, nullable=True, doc="Scan Profile ids disabled for this tool. See PluginConfiguration.disabled_profile_ids."
    )

    tool: Mapped["Tool"] = relationship(back_populates="configuration")
