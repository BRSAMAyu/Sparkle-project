from __future__ import annotations

from typing import Any

from app.core.time_utils import utcnow


def append_graph_event_source(
    status: object,
    *,
    event_type: str,
    source_type: str,
    reference_id: object | None = None,
    label: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Stamp why a user-owned Galaxy node exists or changed.

    Stored in UserNodeStatus.learning_path_snapshot so graph clients can explain
    document/translation/error/task origins without adding a new table.
    """
    snapshot = getattr(status, "learning_path_snapshot", None)
    if not isinstance(snapshot, dict):
        snapshot = {}

    sources = snapshot.get("graph_event_sources")
    if not isinstance(sources, list):
        sources = []

    entry = {
        "event_type": event_type,
        "source_type": source_type,
        "reference_id": str(reference_id) if reference_id is not None else None,
        "label": label,
        "payload": payload or {},
        "recorded_at": utcnow().isoformat(),
    }
    dedupe_key = (
        entry["event_type"],
        entry["source_type"],
        entry["reference_id"],
    )

    kept = [
        item
        for item in sources
        if not (
            isinstance(item, dict)
            and (item.get("event_type"), item.get("source_type"), item.get("reference_id")) == dedupe_key
        )
    ]
    snapshot["graph_event_sources"] = [entry, *kept][:8]
    status.learning_path_snapshot = snapshot


#: 读面单点：星图（``NodeWithStatus._graph_event_sources``）与 Goal 轨迹面
#: （J-08 ``goal_trajectory_service``）都经本函数读同一批 provenance 行——
#: 同一函数 = 同一数据，「Goal 页面/星图一致」是结构性保证而非口径约定。
#: 截断上限与星图历史行为一致（最近 5 条）。
PROVENANCE_READ_LIMIT = 5


def read_graph_event_sources(status: object, *, limit: int = PROVENANCE_READ_LIMIT) -> list[dict[str, Any]]:
    """读取节点溯源行（与写入端同构的只读投影；缺列/非 dict 条目诚实剔除）。"""
    snapshot = getattr(status, "learning_path_snapshot", None)
    if not isinstance(snapshot, dict):
        return []
    raw_sources = snapshot.get("graph_event_sources")
    if not isinstance(raw_sources, list):
        return []
    bounded = max(0, int(limit))
    sources: list[dict[str, Any]] = []
    for item in raw_sources[:bounded]:
        if isinstance(item, dict):
            sources.append({str(key): value for key, value in item.items() if value is not None})
    return sources
