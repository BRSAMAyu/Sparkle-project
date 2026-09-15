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
