"""Sprint Pack loader — loads structured subject strategy assets for exam sprint mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

_PACKS_DIR = Path(__file__).resolve().parent

_SUBJECT_ALIASES: dict[str, str] = {
    "计算机网络": "computer_networks",
    "计网": "computer_networks",
    "computer_networks": "computer_networks",
    "computer networks": "computer_networks",
}


def _normalize_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    return _SUBJECT_ALIASES.get(subject.strip().lower(), subject.strip().lower().replace(" ", "_"))


def load_pack(subject: str, version: str = "v1") -> dict[str, Any] | None:
    """Load a Sprint Pack JSON file by subject and version.

    Returns the parsed JSON dict, or None if no matching pack exists.
    """
    normalized = _normalize_subject(subject)
    if not normalized:
        return None

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

    logger.debug("Loaded Sprint Pack: {} ({} nodes)", filename, len(data.get("knowledge_nodes", [])))
    return data


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


def get_task_template(pack: dict[str, Any], scenario: str) -> dict[str, Any] | None:
    """Find a task card template by scenario name."""
    for template in pack.get("task_card_templates", []):
        if template.get("scenario", "").lower() == scenario.lower():
            return template
    return None
