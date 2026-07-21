"""ExecutionPlanner: turns (assessment, targets, tools) into planned jobs.

One job is one ``ToolExecution`` row: one (target, tool) pair. The planner
has zero tool-specific logic and zero queuing/dispatch logic -- it only
decides *what* should run, via each plugin's own declared
``validate_target()``, and records a ``SKIPPED`` job (never a runnable
one) for a pairing a tool cannot or should not run: not currently
registered, disabled, not installed/healthy, or incompatible with the
target. Per ``.claude/CLAUDE.md``'s plugin philosophy, the planner never
knows what "nmap" or "nuclei" means -- only that a registered plugin
either accepts a target or doesn't, and either is or isn't actually
runnable right now.

The installation/health check (``registered.instance.health()``) is run at
most once per tool per ``plan()`` call, not once per (target, tool)
pairing -- it shells out to run the tool's own version command, and
planning N targets against one uninstalled tool must not spawn N
redundant subprocesses just to reach the same "not installed" answer.

Phase 7 adds optional, per-tool ``ToolExecutionOptions`` (a Scan Profile
id and advanced-option overrides), stored on the planned job so the
execution engine can pass them into that job's ``PluginExecutionContext``.
This is a plain dataclass, not the API's Pydantic schema, so ``workers``
(execution-engine internals) stays decoupled from ``schemas`` (the API
layer) -- ``ExecutionService`` is what translates between the two.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import InvalidInputError, NotFoundError
from backend.models.enums import ToolExecutionStatus
from backend.models.target import Target
from backend.models.tool import Tool
from backend.models.tool_execution import ToolExecution
from backend.plugins.exceptions import PluginNotFoundError
from backend.plugins.manager.plugin_manager import PluginManager
from backend.plugins.models.enums import PluginHealthStatus
from backend.plugins.models.health import PluginHealth


@dataclass(frozen=True)
class ToolExecutionOptions:
    """Per-tool planning options for one ``execute()`` call: a Scan Profile id and its overrides.

    Only meaningful for a plugin with a profile system (``registered.instance.profile_manager``,
    Nmap being the reference implementation) -- specifying ``profile_id`` for a
    plugin without one is a request-shape error, not a silent no-op.
    """

    profile_id: str | None = None
    advanced_options: dict | None = None


class ExecutionPlanner:
    """Creates one ``ToolExecution`` (job) row per (enabled target, requested tool) pair."""

    def __init__(self, session: AsyncSession, plugin_manager: PluginManager) -> None:
        self._session = session
        self._manager = plugin_manager

    async def plan(
        self,
        assessment_id: uuid.UUID,
        tool_names: list[str],
        target_ids: list[uuid.UUID] | None,
        tool_options: dict[str, ToolExecutionOptions] | None = None,
    ) -> list[ToolExecution]:
        """Plan jobs for every (selected target) x (selected tool) pair.

        ``target_ids=None`` selects every enabled target on the
        assessment. Raises if a named tool has no ``Tool`` catalog row
        (run tool discovery first), if any explicitly named target id
        doesn't resolve to an enabled target on this assessment, or if
        ``tool_options`` names a profile a tool doesn't have or doesn't
        support -- those are request-shape problems, not per-pairing skip
        reasons.
        """
        if not tool_names:
            raise InvalidInputError("At least one tool must be selected.")

        tools = await self._resolve_tools(tool_names)
        targets = await self._resolve_targets(assessment_id, target_ids)
        if not targets:
            raise InvalidInputError("No enabled targets available to plan jobs for.")

        tool_options = tool_options or {}
        self._validate_tool_options(tools, tool_options)

        health_cache: dict[str, PluginHealth] = {}
        jobs = [
            await self._plan_one(assessment_id, target, tool, tool_options.get(tool.name), health_cache)
            for target in targets
            for tool in tools
        ]

        self._session.add_all(jobs)
        await self._session.flush()
        return jobs

    def _validate_tool_options(self, tools: list[Tool], tool_options: dict[str, ToolExecutionOptions]) -> None:
        by_name = {tool.name: tool for tool in tools}
        for tool_name, options in tool_options.items():
            if options.profile_id is None:
                continue
            if tool_name not in by_name:
                raise InvalidInputError(f"tool_options names '{tool_name}', which was not selected to run.")
            try:
                registered = self._manager.get_plugin(tool_name)
            except PluginNotFoundError as exc:
                raise NotFoundError(f"Plugin '{tool_name}' is not currently registered.") from exc
            profile_manager = getattr(registered.instance, "profile_manager", None)
            if profile_manager is None:
                raise InvalidInputError(f"'{tool_name}' does not support Scan Profiles.")
            if not any(profile.id == options.profile_id for profile in profile_manager.list_profiles()):
                raise NotFoundError(f"'{tool_name}' has no Scan Profile '{options.profile_id}'.")

    async def _plan_one(
        self,
        assessment_id: uuid.UUID,
        target: Target,
        tool: Tool,
        options: ToolExecutionOptions | None,
        health_cache: dict[str, PluginHealth],
    ) -> ToolExecution:
        try:
            registered = self._manager.get_plugin(tool.name)
        except PluginNotFoundError:
            return self._skipped(assessment_id, target, tool, f"Plugin '{tool.name}' is not currently registered.")

        if not registered.config.enabled:
            return self._skipped(assessment_id, target, tool, f"Tool '{tool.name}' is disabled.")

        health = health_cache.get(tool.name)
        if health is None:
            health = registered.instance.health()
            health_cache[tool.name] = health
        if health.status != PluginHealthStatus.HEALTHY:
            return self._skipped(assessment_id, target, tool, f"'{tool.name}' is unavailable: {health.message}")

        if not registered.instance.validate_target(target.target_type, target.target_value):
            return self._skipped(
                assessment_id,
                target,
                tool,
                f"'{tool.name}' cannot run against {target.target_type.value} target '{target.target_value}'.",
            )

        return ToolExecution(
            assessment_id=assessment_id,
            target_id=target.id,
            tool_id=tool.id,
            status=ToolExecutionStatus.PENDING,
            profile_id=options.profile_id if options else None,
            advanced_options=options.advanced_options if options else None,
        )

    @staticmethod
    def _skipped(assessment_id: uuid.UUID, target: Target, tool: Tool, reason: str) -> ToolExecution:
        return ToolExecution(
            assessment_id=assessment_id,
            target_id=target.id,
            tool_id=tool.id,
            status=ToolExecutionStatus.SKIPPED,
            status_message=reason,
        )

    async def _resolve_tools(self, tool_names: list[str]) -> list[Tool]:
        stmt = select(Tool).where(Tool.name.in_(tool_names))
        by_name = {tool.name: tool for tool in (await self._session.execute(stmt)).scalars().all()}
        missing = [name for name in tool_names if name not in by_name]
        if missing:
            raise NotFoundError(f"Unknown tool(s): {', '.join(missing)}. Run tool discovery first.")
        return [by_name[name] for name in tool_names]

    async def _resolve_targets(self, assessment_id: uuid.UUID, target_ids: list[uuid.UUID] | None) -> list[Target]:
        conditions = [Target.assessment_id == assessment_id, Target.enabled.is_(True)]
        if target_ids:
            conditions.append(Target.id.in_(target_ids))
        stmt = select(Target).where(*conditions)
        targets = list((await self._session.execute(stmt)).scalars().all())
        if target_ids:
            found_ids = {target.id for target in targets}
            missing = [str(target_id) for target_id in target_ids if target_id not in found_ids]
            if missing:
                raise NotFoundError(f"Target(s) not found or not enabled: {', '.join(missing)}.")
        return targets
