"""Sprint Pack loader — loads structured subject strategy assets for exam sprint mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.sprint_packs.sprint_pack_schema import SprintPackV1

try:
    from loguru import logger
except ModuleNotFoundError:
    import logging

    class _FallbackLogger:
        def __init__(self) -> None:
            self._logger = logging.getLogger(__name__)

        def debug(self, message: str, *args: Any) -> None:
            self._logger.debug(message.format(*args))

        def warning(self, message: str, *args: Any) -> None:
            self._logger.warning(message.format(*args))

    logger = _FallbackLogger()

_PACKS_DIR = Path(__file__).resolve().parent

_SUBJECT_ALIASES: dict[str, str] = {
    "计算机网络": "computer_networks",
    "计网": "computer_networks",
    "网络": "computer_networks",
    "computer_networks": "computer_networks",
    "computer network": "computer_networks",
    "computer networks": "computer_networks",
    "操作系统": "operating_systems",
    "计算机操作系统": "operating_systems",
    "操作系统原理": "operating_systems",
    "operating_systems": "operating_systems",
    "operating system": "operating_systems",
    "operating systems": "operating_systems",
    "os": "operating_systems",
    "操系": "operating_systems",
    "高数": "mathematics",
    "高等数学": "mathematics",
    "线代": "mathematics",
    "线性代数": "mathematics",
    "数学": "mathematics",
    "math": "mathematics",
    "mathematics": "mathematics",
    "数据结构": "data_structures_algorithms",
    "数据结构与算法": "data_structures_algorithms",
    "数据结构和算法": "data_structures_algorithms",
    "数结": "data_structures_algorithms",
    "ds": "data_structures_algorithms",
    "算法": "data_structures_algorithms",
    "算法设计": "data_structures_algorithms",
    "algo": "data_structures_algorithms",
    "algorithm": "data_structures_algorithms",
    "algorithms": "data_structures_algorithms",
    "data_structures_algorithms": "data_structures_algorithms",
    "data structures and algorithms": "data_structures_algorithms",
    "data structures algorithms": "data_structures_algorithms",
    "data structures": "data_structures_algorithms",
    "dsa": "data_structures_algorithms",
}


def _alias_match(subject: str | None) -> str | None:
    if not subject:
        return None
    return _SUBJECT_ALIASES.get(subject.strip().lower())


def _normalize_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    return _alias_match(subject) or subject.strip().lower().replace(" ", "_")


def auto_detect_subject(user_input: str) -> str | None:
    """Detect the Sprint Pack subject from free-form user input."""

    from app.sprint_packs.sprint_pack_registry import SprintPackRegistry

    return SprintPackRegistry().match_subject(user_input)


def _load_pack_file(normalized: str, version: str) -> dict[str, Any] | None:
    filename = f"{normalized}_{version}.json"
    path = _PACKS_DIR / filename
    if not path.exists():
        logger.debug("Sprint Pack not found: {}", path)
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load Sprint Pack {}: {}", path, exc)
        return None

    try:
        pack = SprintPackV1.model_validate(data)
    except ValidationError as exc:
        logger.warning("Invalid Sprint Pack {}: {}", path, exc.errors()[0] if exc.errors() else exc)
        return None

    data = pack.model_dump()
    logger.debug("Loaded Sprint Pack: {} ({} nodes)", filename, len(data.get("knowledge_nodes", [])))
    return data


def load_pack(subject: str, version: str = "v1") -> dict[str, Any] | None:
    """Load a Sprint Pack JSON file by subject and version.

    Returns the parsed JSON dict, or None if no matching pack exists.
    """
    subject_text = str(subject or "").strip()
    if not subject_text:
        return None

    candidates: list[str] = []
    alias = _alias_match(subject_text)
    if alias:
        candidates.append(alias)
    else:
        detected = auto_detect_subject(subject_text)
        if detected:
            candidates.append(detected)

    normalized = _normalize_subject(subject_text)
    if normalized and normalized not in candidates:
        candidates.append(normalized)

    for candidate in candidates:
        pack = _load_pack_file(candidate, version)
        if pack is not None:
            return pack

    if alias:
        detected = auto_detect_subject(subject_text)
        if detected and detected not in candidates:
            return _load_pack_file(detected, version)
    return None


def query_nodes_by_priority(
    pack: dict[str, Any],
    current_mastery: dict[str, float] | None = None,
    days_left: int | None = None,
    *,
    path_mode: str = "minimum_pass",
) -> list[dict[str, Any]]:
    """Return pack nodes sorted by priority using the priority formula.

    Priority = exam_weight * frequency * gap * trainability / (time_cost * difficulty)
    where gap = 1.0 - current_mastery (default 1.0 if unknown).
    """
    current_mastery = dict(current_mastery or {})
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in pack.get("knowledge_nodes", []):
        nodes_by_id[node.get("node_id", "")] = node

    # Determine which nodes to include based on path_mode
    paths = pack.get("paths", {})
    if path_mode == "minimum_pass":
        path_data = paths.get("minimum_pass", {})
        allowed_ids = set(path_data.get("ordered_nodes", []))
    elif path_mode == "score_max":
        path_data = paths.get("score_max", {})
        allowed_ids = set(path_data.get("ordered_nodes", []))
    else:
        allowed_ids = set(nodes_by_id.keys())

    if not allowed_ids:
        allowed_ids = set(nodes_by_id.keys())

    # Time pressure: if days_left is low, boost high-weight nodes
    time_pressure_boost = 1.0
    if days_left is not None and days_left <= 3:
        time_pressure_boost = 1.3
    elif days_left is not None and days_left <= 7:
        time_pressure_boost = 1.1

    scored: list[tuple[float, dict[str, Any]]] = []
    for node_id in allowed_ids:
        node = nodes_by_id.get(node_id)
        if not node:
            continue

        exam_weight = float(node.get("exam_weight", 0.5))
        frequency = float(node.get("frequency", 0.5))
        mastery = float(current_mastery.get(node_id, 0.0))
        gap = max(0.0, 1.0 - mastery)
        trainability = float(node.get("trainability", 0.5))
        time_cost = max(1.0, float(node.get("time_cost", 30)))
        difficulty = max(1.0, float(node.get("difficulty", 3)))

        # Minimum-pass-required nodes get a boost
        mp_boost = 1.2 if node.get("minimum_pass_required") else 1.0

        priority = (
            exam_weight
            * frequency
            * gap
            * trainability
            * mp_boost
            * time_pressure_boost
            / (time_cost * difficulty)
        )
        scored.append((priority, node))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [node for _, node in scored]


def get_mistake_by_nodes(pack: dict[str, Any], node_ids: list[str]) -> list[dict[str, Any]]:
    """Find mistake types that relate to any of the given node IDs."""
    node_set = set(node_ids)
    matches: list[dict[str, Any]] = []
    for mistake in pack.get("mistake_types", []):
        related = set(mistake.get("related_nodes", []))
        if related & node_set:
            matches.append(mistake)
    return matches


def get_archetypes_by_nodes(pack: dict[str, Any], node_ids: list[str]) -> list[dict[str, Any]]:
    """Find question archetypes that test any of the given node IDs."""
    node_set = set(node_ids)
    matches: list[dict[str, Any]] = []
    for archetype in pack.get("question_archetypes", []):
        tested = set(archetype.get("knowledge_nodes", []))
        if tested & node_set:
            matches.append(archetype)
    return matches


def get_task_template(pack: dict[str, Any], template_id: str) -> dict[str, Any] | None:
    """Find a task card template by template_id or label (case-insensitive)."""
    needle = template_id.lower()
    for template in pack.get("task_card_templates", []):
        if template.get("template_id", "").lower() == needle:
            return template
        if template.get("label", "").lower() == needle:
            return template
    return None
