from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.agent_profiles import agent_profile_registry
from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_STANDARD,
    CHAT_MODE_STUDY_PLAN,
)
from app.orchestration.mode_workflow_config import MODE_WORKFLOWS

# Presentation metadata for user-visible mode entries.
_MODE_META: dict[str, dict[str, Any]] = {
    CHAT_MODE_STANDARD: {
        "label": "标准对话",
        "description": "通用对话与任务处理",
        "rank": 0,
        "tags": ["general", "chat"],
        "enabled": True,
    },
    CHAT_MODE_DEEP_ANALYSIS: {
        "label": "深度解析",
        "description": "多专家协作深度解析问题",
        "rank": 10,
        "tags": ["analysis", "reasoning", "evidence"],
        "enabled": True,
    },
    CHAT_MODE_STUDY_PLAN: {
        "label": "学习计划",
        "description": "任务分解与学习计划协作",
        "rank": 20,
        "tags": ["planning", "schedule", "milestones"],
        "enabled": True,
    },
    CHAT_MODE_ERROR_DIAGNOSIS: {
        "label": "错题分析",
        "description": "错题诊断与补救策略",
        "rank": 30,
        "tags": ["diagnosis", "remediation", "root-cause"],
        "enabled": True,
    },
    CHAT_MODE_EXPERT_AUTO: {
        "label": "专家自动",
        "description": "自动选择最合适专家组合",
        "rank": 40,
        "tags": ["auto-routing", "experts", "adaptive"],
        "enabled": True,
    },
}


@lru_cache(maxsize=1)
def get_mode_capability_catalog() -> tuple[dict[str, Any], ...]:
    """Return public mode catalog for product entry surfaces."""
    modes: dict[str, dict[str, Any]] = {}

    # Include workflow-driven multi-agent modes.
    for mode_id, config in MODE_WORKFLOWS.items():
        meta = _MODE_META.get(mode_id, {})
        tier = "advanced"
        if mode_id == CHAT_MODE_STUDY_PLAN:
            tier = "expert"
        elif mode_id == CHAT_MODE_ERROR_DIAGNOSIS:
            tier = "expert"
        elif mode_id == CHAT_MODE_DEEP_ANALYSIS:
            tier = "advanced"
        modes[mode_id] = {
            "id": mode_id,
            "label": str(meta.get("label", mode_id)),
            "description": str(meta.get("description", "")),
            "entry_chat_mode": mode_id,
            "enabled": bool(meta.get("enabled", True)),
            "rank": int(meta.get("rank", 999)),
            "tags": list(meta.get("tags", [])),
            "collaboration_mode": config.collaboration_mode,
            "decomposition_capability_tier": tier,
        }

    # Add stable entries that are not necessarily present in MODE_WORKFLOWS.
    for mode_id in (CHAT_MODE_STANDARD, CHAT_MODE_EXPERT_AUTO):
        if mode_id in modes:
            continue
        meta = _MODE_META.get(mode_id, {})
        modes[mode_id] = {
            "id": mode_id,
            "label": str(meta.get("label", mode_id)),
            "description": str(meta.get("description", "")),
            "entry_chat_mode": mode_id,
            "enabled": bool(meta.get("enabled", True)),
            "rank": int(meta.get("rank", 999)),
            "tags": list(meta.get("tags", [])),
            "collaboration_mode": "single" if mode_id == CHAT_MODE_STANDARD else "sequential",
            "decomposition_capability_tier": "basic" if mode_id == CHAT_MODE_STANDARD else "advanced",
        }

    ordered = sorted(modes.values(), key=lambda item: (item.get("rank", 999), item.get("id", "")))
    return tuple(ordered)


@lru_cache(maxsize=1)
def get_expert_capability_catalog() -> tuple[dict[str, Any], ...]:
    """Return public expert catalog backed by agent_profiles single source."""
    experts: list[dict[str, Any]] = []
    for role, profile in agent_profile_registry.list_public_entry_profiles():
        expert_id = role.value
        experts.append(
            {
                "id": expert_id,
                "display_name": profile.display_name,
                "description": profile.description,
                "tags": list(profile.entry_tags),
                "entry_chat_mode": f"expert::{expert_id}",
                "recommended_scenarios": list(profile.entry_tags[:3]),
                "enabled": bool(profile.entry_enabled),
                "rank": int(profile.entry_rank),
            }
        )
    ordered = sorted(experts, key=lambda item: (item["rank"], item["display_name"]))
    return tuple(ordered)


def get_enabled_expert_ids() -> list[str]:
    return [expert["id"] for expert in get_expert_capability_catalog() if expert.get("enabled")]


def get_expert_catalog_map() -> dict[str, dict[str, Any]]:
    return {expert["id"]: dict(expert) for expert in get_expert_capability_catalog()}


def get_capability_catalog() -> dict[str, Any]:
    experts = [dict(item) for item in get_expert_capability_catalog()]
    modes = [dict(item) for item in get_mode_capability_catalog()]
    return {
        "modes": modes,
        "experts": experts,
        "total_experts": len(experts),
    }


def reset_capability_registry_cache() -> None:
    """Used by tests when agent profile flags are patched."""
    get_expert_capability_catalog.cache_clear()
    get_mode_capability_catalog.cache_clear()
