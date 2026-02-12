from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.orchestration.schemas import ToolCallSpec


@dataclass
class DependencyResolutionResult:
    total_dependencies: int
    resolved_by_reference: int
    resolved_by_semantic: int


class PlanDependencyResolver:
    """Resolve explicit and semantic dependencies between tool calls."""

    _REF_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\-:]+)(?:\.[a-zA-Z0-9_\-:]+)?\s*\}\}")
    _CREATOR_NAME_BY_PARAM = {
        "plan_id": ("create_plan",),
        "task_id": ("create_task", "batch_create_tasks", "generate_tasks_for_plan"),
        "parent_id": ("create_task", "batch_create_tasks"),
        "node_id": ("create_knowledge_node",),
    }

    def resolve(self, tool_calls: list[ToolCallSpec]) -> DependencyResolutionResult:
        id_map = {tc.id: tc for tc in tool_calls}
        latest_creator: dict[str, str] = {}
        resolved_by_reference = 0
        resolved_by_semantic = 0

        for tc in tool_calls:
            if tc.name in {"create_plan", "create_task", "batch_create_tasks", "create_knowledge_node"} and not tc.output_key:
                tc.output_key = f"{tc.name}_result_{tc.id[-8:]}"
            latest_creator[tc.name] = tc.id

        for index, tc in enumerate(tool_calls):
            refs = self._extract_step_refs(tc.params)
            for step_id in refs:
                if step_id in id_map and step_id != tc.id and step_id not in tc.depends_on:
                    tc.depends_on.append(step_id)
                    resolved_by_reference += 1

            for param_name in tc.params.keys():
                creator_names = self._CREATOR_NAME_BY_PARAM.get(str(param_name))
                if not creator_names:
                    continue
                dependency_id = self._find_latest_creator(tool_calls[:index], creator_names)
                if dependency_id and dependency_id not in tc.depends_on:
                    tc.depends_on.append(dependency_id)
                    resolved_by_semantic += 1

        total = sum(len(tc.depends_on) for tc in tool_calls)
        return DependencyResolutionResult(
            total_dependencies=total,
            resolved_by_reference=resolved_by_reference,
            resolved_by_semantic=resolved_by_semantic,
        )

    def _find_latest_creator(
        self,
        calls: Iterable[ToolCallSpec],
        creator_names: tuple[str, ...],
    ) -> str | None:
        for item in reversed(list(calls)):
            if item.name in creator_names:
                return item.id
        return None

    def _extract_step_refs(self, params: dict) -> set[str]:
        refs: set[str] = set()

        def _walk(value):
            if isinstance(value, dict):
                from_step = value.get("$from_step")
                if isinstance(from_step, str) and from_step.strip():
                    refs.add(from_step.strip())
                for sub in value.values():
                    _walk(sub)
                return
            if isinstance(value, list):
                for sub in value:
                    _walk(sub)
                return
            if isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith("ref:"):
                    refs.add(stripped.removeprefix("ref:").strip())
                for matched in self._REF_PATTERN.findall(stripped):
                    refs.add(matched.strip())

        _walk(params or {})
        return refs
