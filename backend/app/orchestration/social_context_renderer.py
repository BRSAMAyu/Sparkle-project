from __future__ import annotations

from typing import Any


def render_social_context_lines(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict) or not payload:
        return []

    lines = ["【社交上下文】"]

    recent_mentions = payload.get("recent_person_mentions") or []
    mention_count = min(len(recent_mentions), 3)
    if mention_count:
        lines.append(f"- 你最近提到过 {mention_count} 位学习相关人物。")

    relationship_count = int(payload.get("relationship_count") or 0)
    if relationship_count > 0:
        lines.append(f"- 你当前有 {relationship_count} 条关系型背景可供理解。")

    pending_commitments_count = int(payload.get("pending_commitments_count") or 0)
    if pending_commitments_count > 0:
        lines.append(f"- 你有 {pending_commitments_count} 条到期承诺待跟进。")

    return lines if len(lines) > 1 else []
