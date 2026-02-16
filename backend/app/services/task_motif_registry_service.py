from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.core.cache import cache_service

_MEM_RULES: dict[str, dict[str, Any]] = {}
_MEM_GRAPHS: dict[str, dict[str, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TaskMotifRegistryService:
    """Registry for cognitive rules and task motif graphs."""

    RULES_KEY = "meta_learning:cognitive_rules:v1"
    GRAPHS_KEY = "meta_learning:task_motif_graphs:v1"
    RULE_STATUS_FLOW = {
        "draft": {"validated", "deprecated"},
        "validated": {"approved", "deprecated"},
        "approved": {"active", "deprecated"},
        "active": {"deprecated"},
        "deprecated": set(),
    }

    async def list_rules(
        self,
        *,
        status: str | None = None,
        domain: str | None = None,
        task_type: str | None = None,
        redis_client=None,
    ) -> list[dict[str, Any]]:
        rows = list((await self._load_rules(redis_client=redis_client)).values())
        if status:
            rows = [row for row in rows if str(row.get("status", "")) == status]
        if domain:
            rows = [row for row in rows if str(row.get("domain", "")) == domain]
        if task_type:
            rows = [row for row in rows if str(row.get("task_type", "")) == task_type]
        rows.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return rows

    async def get_rule(self, rule_id: str, *, redis_client=None) -> dict[str, Any] | None:
        return (await self._load_rules(redis_client=redis_client)).get(rule_id)

    async def upsert_rule(self, payload: dict[str, Any], *, redis_client=None) -> dict[str, Any]:
        rule_id = str(payload.get("rule_id", "")).strip()
        if not rule_id:
            raise ValueError("rule_id_required")
        rows = await self._load_rules(redis_client=redis_client)
        merged = dict(rows.get(rule_id, {}))
        merged.update(payload)
        merged.setdefault("status", "draft")
        merged.setdefault("version", "v1")
        merged.setdefault("created_at", _utcnow().isoformat())
        merged["updated_at"] = _utcnow().isoformat()
        rows[rule_id] = merged
        await self._save_rules(rows, redis_client=redis_client)
        return merged

    async def register_rule_candidate(
        self,
        *,
        rule: dict[str, Any],
        motif_graph: dict[str, Any] | None = None,
        redis_client=None,
    ) -> dict[str, Any]:
        payload = dict(rule)
        payload.setdefault("status", "draft")
        saved_rule = await self.upsert_rule(payload, redis_client=redis_client)
        if motif_graph:
            await self.upsert_graph(motif_graph, redis_client=redis_client)
        return saved_rule

    async def validate_rule(
        self,
        *,
        rule_id: str,
        reviewer: str,
        note: str = "",
        redis_client=None,
    ) -> dict[str, Any]:
        return await self._transition_rule_status(
            rule_id=rule_id,
            target_status="validated",
            reviewer=reviewer,
            note=note,
            action="validated",
            redis_client=redis_client,
        )

    async def approve_rule(
        self,
        *,
        rule_id: str,
        reviewer: str,
        note: str = "",
        activate: bool = False,
        redis_client=None,
    ) -> dict[str, Any]:
        approved = await self._transition_rule_status(
            rule_id=rule_id,
            target_status="approved",
            reviewer=reviewer,
            note=note,
            action="approved",
            redis_client=redis_client,
        )
        if activate:
            return await self.activate_rule(
                rule_id=rule_id,
                reviewer=reviewer,
                note=note,
                redis_client=redis_client,
            )
        return approved

    async def activate_rule(
        self,
        *,
        rule_id: str,
        reviewer: str,
        note: str = "",
        redis_client=None,
    ) -> dict[str, Any]:
        return await self._transition_rule_status(
            rule_id=rule_id,
            target_status="active",
            reviewer=reviewer,
            note=note,
            action="activated",
            redis_client=redis_client,
        )

    async def reject_rule(
        self,
        *,
        rule_id: str,
        reviewer: str,
        note: str = "",
        redis_client=None,
    ) -> dict[str, Any]:
        return await self._transition_rule_status(
            rule_id=rule_id,
            target_status="deprecated",
            reviewer=reviewer,
            note=note,
            action="rejected",
            redis_client=redis_client,
        )

    async def list_active_rules(
        self,
        *,
        domain: str | None = None,
        task_type: str | None = None,
        redis_client=None,
    ) -> list[dict[str, Any]]:
        return await self.list_rules(
            status="active",
            domain=domain,
            task_type=task_type,
            redis_client=redis_client,
        )

    async def _transition_rule_status(
        self,
        *,
        rule_id: str,
        target_status: str,
        reviewer: str,
        note: str,
        action: str,
        redis_client=None,
    ) -> dict[str, Any]:
        rows = await self._load_rules(redis_client=redis_client)
        row = rows.get(rule_id)
        if not row:
            raise ValueError("rule_not_found")
        current_status = str(row.get("status", "draft"))
        if current_status == target_status:
            return row
        if current_status == "deprecated":
            raise ValueError("rule_deprecated")
        allowed = self.RULE_STATUS_FLOW.get(current_status, set())
        if target_status not in allowed:
            raise ValueError(f"invalid_status_transition:{current_status}->{target_status}")

        now = _utcnow().isoformat()
        row["status"] = target_status
        row["updated_at"] = now
        row.setdefault("status_history", [])
        if isinstance(row["status_history"], list):
            row["status_history"].append(
                {
                    "from": current_status,
                    "to": target_status,
                    "action": action,
                    "reviewer": reviewer,
                    "note": note,
                    "at": now,
                }
            )
        if target_status == "validated":
            row["validated_by"] = reviewer
            row["validated_at"] = now
            if note:
                row["validation_note"] = note
        elif target_status == "approved":
            row["approved_by"] = reviewer
            row["approved_at"] = now
            if note:
                row["approval_note"] = note
        elif target_status == "active":
            row["activated_by"] = reviewer
            row["activated_at"] = now
            if note:
                row["activation_note"] = note
        elif target_status == "deprecated":
            row["rejected_by"] = reviewer
            row["rejected_at"] = now
            if note:
                row["rejection_note"] = note

        rows[rule_id] = row
        await self._save_rules(rows, redis_client=redis_client)
        return row

    async def upsert_graph(self, payload: dict[str, Any], *, redis_client=None) -> dict[str, Any]:
        graph_id = str(payload.get("graph_id", "")).strip()
        if not graph_id:
            raise ValueError("graph_id_required")
        rows = await self._load_graphs(redis_client=redis_client)
        merged = dict(rows.get(graph_id, {}))
        merged.update(payload)
        merged.setdefault("created_at", _utcnow().isoformat())
        merged["updated_at"] = _utcnow().isoformat()
        rows[graph_id] = merged
        await self._save_graphs(rows, redis_client=redis_client)
        return merged

    async def get_graph(self, graph_id: str, *, redis_client=None) -> dict[str, Any] | None:
        return (await self._load_graphs(redis_client=redis_client)).get(graph_id)

    async def list_graphs(self, *, redis_client=None) -> list[dict[str, Any]]:
        rows = list((await self._load_graphs(redis_client=redis_client)).values())
        rows.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return rows

    async def _load_rules(self, *, redis_client=None) -> dict[str, dict[str, Any]]:
        redis = redis_client or cache_service.redis
        if redis is None:
            return dict(_MEM_RULES)
        data = await self._load_json(self.RULES_KEY, default={}, redis=redis)
        if not isinstance(data, dict):
            return {}
        return data

    async def _save_rules(self, payload: dict[str, dict[str, Any]], *, redis_client=None) -> None:
        redis = redis_client or cache_service.redis
        if redis is None:
            _MEM_RULES.clear()
            _MEM_RULES.update(payload)
            return
        await self._save_json(self.RULES_KEY, payload, redis=redis)

    async def _load_graphs(self, *, redis_client=None) -> dict[str, dict[str, Any]]:
        redis = redis_client or cache_service.redis
        if redis is None:
            return dict(_MEM_GRAPHS)
        data = await self._load_json(self.GRAPHS_KEY, default={}, redis=redis)
        if not isinstance(data, dict):
            return {}
        return data

    async def _save_graphs(self, payload: dict[str, dict[str, Any]], *, redis_client=None) -> None:
        redis = redis_client or cache_service.redis
        if redis is None:
            _MEM_GRAPHS.clear()
            _MEM_GRAPHS.update(payload)
            return
        await self._save_json(self.GRAPHS_KEY, payload, redis=redis)

    @staticmethod
    async def _load_json(key: str, *, default: Any, redis) -> Any:
        try:
            raw = await redis.get(key)
        except Exception as exc:
            logger.warning("TaskMotifRegistry load failed {}: {}", key, exc)
            return default
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    @staticmethod
    async def _save_json(key: str, payload: Any, *, redis) -> None:
        try:
            await redis.set(key, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.warning("TaskMotifRegistry save failed {}: {}", key, exc)
