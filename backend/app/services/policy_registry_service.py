from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config import settings
from app.core.cache import cache_service
from app.services.meta_policy_composer_service import MetaPolicyComposerService

_MEM_POLICIES: dict[str, dict[str, Any]] = {}
_MEM_CANDIDATES: dict[str, dict[str, Any]] = {}
_MEM_JOB_HISTORY: list[dict[str, Any]] = []
_MEM_WEEKLY_REPORTS: list[dict[str, Any]] = []


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PolicyRegistryService:
    """Policy/candidate state store with auditable lifecycle for manual governance."""

    POLICY_REGISTRY_KEY = "learning:policy_registry:v1"
    POLICY_CANDIDATE_KEY = "learning:policy_candidates:v1"
    POLICY_JOB_HISTORY_KEY = "learning:policy_jobs:v1"
    POLICY_WEEKLY_REPORTS_KEY = "learning:policy_weekly_reports:v1"

    def __init__(self, redis_client=None):
        self.redis = redis_client or cache_service.redis

    async def list_candidates(self, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = list((await self._load_candidates()).values())
        if status:
            rows = [row for row in rows if str(row.get("status", "")) == status]
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows

    async def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        return (await self._load_candidates()).get(candidate_id)

    async def create_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id:
            raise ValueError("candidate id is required")
        all_candidates = await self._load_candidates()
        if candidate_id in all_candidates:
            return all_candidates[candidate_id]
        payload = dict(candidate)
        payload.setdefault("channel", "routing")
        research_candidate = bool(payload.get("research_track", False) or payload.get("is_research", False))
        payload.setdefault("status", "research_pending" if research_candidate else "pending")
        payload.setdefault("created_at", _utcnow().isoformat())
        all_candidates[candidate_id] = payload
        await self._save_candidates(all_candidates)
        return payload

    async def approve_candidate(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        note: str = "",
    ) -> dict[str, Any]:
        all_candidates = await self._load_candidates()
        candidate = all_candidates.get(candidate_id)
        if not candidate:
            raise ValueError("candidate_not_found")
        if candidate.get("status") not in {"pending", "rejected", "research_passed"}:
            raise ValueError("candidate_not_pending")

        candidate["status"] = "approved"
        candidate["approved_at"] = _utcnow().isoformat()
        candidate["approved_by"] = reviewer
        if note:
            candidate["approval_note"] = note
        all_candidates[candidate_id] = candidate
        await self._save_candidates(all_candidates)

        policy_payload = {
            "policy_id": str(candidate.get("policy_id", "")),
            "base_policy": str(candidate.get("base_policy", "")),
            "strategy_pack": str(candidate.get("strategy_pack", "default")),
            "channel": str(candidate.get("channel", "routing")),
            "scope_type": str(candidate.get("scope_type", "global")),
            "scope_key": str(candidate.get("scope_key", "all")),
            "support_size": int(candidate.get("support_size", 0)),
            "weights": candidate.get("weights") or {},
            "thresholds": candidate.get("thresholds") or {},
            "params": candidate.get("params") or {},
            "arm_weights": candidate.get("arm_weights") or {},
            "created_from_window": str(candidate.get("created_from_window", "")),
            "expected_delta": float(candidate.get("expected_delta", 0.0) or 0.0),
            "risk_level": str(candidate.get("risk_level", "medium")),
            "status": "canary" if getattr(settings, "ENABLE_POLICY_CANARY_ROLLOUT", False) else "active",
            "lifecycle_state": "canary" if getattr(settings, "ENABLE_POLICY_CANARY_ROLLOUT", False) else "active",
            "rollout_percent": int(candidate.get("rollout_percent", 10)),
            "created_at": candidate.get("created_at"),
            "approved_at": candidate["approved_at"],
            "approved_by": reviewer,
            "source_candidate_id": candidate_id,
        }
        await self.upsert_policy(policy_payload)
        return candidate

    async def mark_research_passed(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        note: str = "",
    ) -> dict[str, Any]:
        all_candidates = await self._load_candidates()
        candidate = all_candidates.get(candidate_id)
        if not candidate:
            raise ValueError("candidate_not_found")
        if candidate.get("status") == "research_passed":
            return candidate
        if candidate.get("status") not in {"research_pending", "pending"}:
            raise ValueError("candidate_not_research_pending")
        candidate["status"] = "research_passed"
        candidate["research_passed_at"] = _utcnow().isoformat()
        candidate["research_reviewer"] = reviewer
        if note:
            candidate["research_note"] = note
        all_candidates[candidate_id] = candidate
        await self._save_candidates(all_candidates)
        return candidate

    async def approve_research_promotion(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        note: str = "",
    ) -> dict[str, Any]:
        candidate = await self.mark_research_passed(
            candidate_id=candidate_id,
            reviewer=reviewer,
            note=note,
        )
        approved = await self.approve_candidate(
            candidate_id=candidate_id,
            reviewer=reviewer,
            note=f"research_promotion:{note}" if note else "research_promotion",
        )
        return {
            "candidate": approved,
            "promotion_state": "canary" if getattr(settings, "ENABLE_POLICY_CANARY_ROLLOUT", False) else "active",
            "research_passed_at": candidate.get("research_passed_at", ""),
        }

    async def reject_candidate(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        note: str = "",
    ) -> dict[str, Any]:
        all_candidates = await self._load_candidates()
        candidate = all_candidates.get(candidate_id)
        if not candidate:
            raise ValueError("candidate_not_found")

        candidate["status"] = "rejected"
        candidate["rejected_at"] = _utcnow().isoformat()
        candidate["rejected_by"] = reviewer
        if note:
            candidate["rejection_note"] = note
        all_candidates[candidate_id] = candidate
        await self._save_candidates(all_candidates)
        return candidate

    async def upsert_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        policy_id = str(payload.get("policy_id", "")).strip()
        if not policy_id:
            raise ValueError("policy_id_required")
        policies = await self._load_policies()
        merged = dict(policies.get(policy_id, {}))
        merged.update(payload)
        merged.setdefault("created_at", _utcnow().isoformat())
        merged.setdefault("channel", "routing")
        merged.setdefault("scope_type", "global")
        merged.setdefault("scope_key", "all")
        merged["updated_at"] = _utcnow().isoformat()
        policies[policy_id] = merged
        await self._save_policies(policies)
        return merged

    async def list_policies(
        self,
        *,
        strategy_pack: str | None = None,
        statuses: set[str] | None = None,
        channel: str | None = None,
        scope_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list((await self._load_policies()).values())
        if strategy_pack:
            rows = [row for row in rows if str(row.get("strategy_pack", "")) == strategy_pack]
        if statuses:
            rows = [row for row in rows if str(row.get("status", "")) in statuses]
        if channel:
            rows = [row for row in rows if str(row.get("channel", "routing")) == channel]
        if scope_type:
            rows = [row for row in rows if str(row.get("scope_type", "global")) == scope_type]
        if scope_key:
            rows = [row for row in rows if str(row.get("scope_key", "all")) == scope_key]
        rows.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return rows

    async def get_policy(self, policy_id: str) -> dict[str, Any] | None:
        return (await self._load_policies()).get(policy_id)

    async def rollback_policy(self, *, policy_id: str, reason: str) -> dict[str, Any] | None:
        policies = await self._load_policies()
        row = policies.get(policy_id)
        if not row:
            return None
        row["status"] = "rolled_back"
        row["rollback_reason"] = reason
        row["rolled_back_at"] = _utcnow().isoformat()
        row["updated_at"] = _utcnow().isoformat()
        policies[policy_id] = row

        base_policy_id = str(row.get("base_policy", ""))
        if base_policy_id and base_policy_id in policies:
            base_policy = policies[base_policy_id]
            base_policy["status"] = "active"
            base_policy["updated_at"] = _utcnow().isoformat()
            policies[base_policy_id] = base_policy

        await self._save_policies(policies)
        return row

    async def resolve_runtime_policy(
        self,
        *,
        strategy_pack: str,
        user_id: str,
        session_id: str,
        channel: str = "routing",
        cohort_id: str = "",
        user_scope: str = "",
        disable_personal: bool = False,
    ) -> dict[str, Any] | None:
        if not getattr(settings, "ENABLE_POLICY_CANDIDATE_PIPELINE", False):
            return None

        resolved_user_scope = str(user_scope or "")
        if not resolved_user_scope:
            from app.services.learning_cohort_service import LearningCohortService

            resolved_user_scope = LearningCohortService.user_scope_key(user_id)

        global_policy = await self._resolve_scope_policy(
            strategy_pack=strategy_pack,
            channel=channel,
            scope_type="global",
            scope_key="all",
            user_id=user_id,
            session_id=session_id,
        )
        cohort_policy = await self._resolve_scope_policy(
            strategy_pack=strategy_pack,
            channel=channel,
            scope_type="cohort",
            scope_key=str(cohort_id or ""),
            user_id=user_id,
            session_id=session_id,
        )
        personal_policy = None
        if not disable_personal:
            personal_policy = await self._resolve_scope_policy(
                strategy_pack=strategy_pack,
                channel=channel,
                scope_type="personal",
                scope_key=resolved_user_scope,
                user_id=user_id,
                session_id=session_id,
            )

        layers: list[dict[str, Any]] = []
        if global_policy is not None:
            layers.append(global_policy)
        if cohort_policy is not None and int(cohort_policy.get("support_size", 0)) >= int(
            getattr(settings, "COHORT_POLICY_MIN_SUPPORT", 80)
        ):
            layers.append(cohort_policy)
        if personal_policy is not None and int(personal_policy.get("support_size", 0)) >= int(
            getattr(settings, "PERSONAL_POLICY_MIN_SUPPORT", 30)
        ):
            layers.append(personal_policy)

        if not layers:
            return None

        composed = self._compose_layered_policy(
            strategy_pack=strategy_pack,
            channel=channel,
            layers=layers,
            cohort_id=str(cohort_id or ""),
            user_scope=resolved_user_scope,
        )
        return composed

    async def resolve_runtime_policies(
        self,
        *,
        strategy_pack: str,
        user_id: str,
        session_id: str,
        cohort_id: str = "",
        user_scope: str = "",
        disable_personal: bool = False,
        channels: tuple[str, ...] = ("routing", "prompt", "toolchain"),
    ) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for channel in channels:
            resolved = await self.resolve_runtime_policy(
                strategy_pack=strategy_pack,
                user_id=user_id,
                session_id=session_id,
                channel=channel,
                cohort_id=cohort_id,
                user_scope=user_scope,
                disable_personal=disable_personal,
            )
            if resolved:
                out[channel] = resolved
        return out

    async def save_weekly_report(self, report: dict[str, Any]) -> None:
        payload = dict(report)
        payload.setdefault("generated_at", _utcnow().isoformat())
        if self.redis is None:
            _MEM_WEEKLY_REPORTS.append(payload)
            if len(_MEM_WEEKLY_REPORTS) > 52:
                del _MEM_WEEKLY_REPORTS[: len(_MEM_WEEKLY_REPORTS) - 52]
            return
        reports = await self._load_json(self.POLICY_WEEKLY_REPORTS_KEY, default=[])
        reports.append(payload)
        reports = reports[-52:]
        await self._save_json(self.POLICY_WEEKLY_REPORTS_KEY, reports)

    async def get_latest_weekly_report(self) -> dict[str, Any] | None:
        if self.redis is None:
            return _MEM_WEEKLY_REPORTS[-1] if _MEM_WEEKLY_REPORTS else None
        reports = await self._load_json(self.POLICY_WEEKLY_REPORTS_KEY, default=[])
        if not isinstance(reports, list) or not reports:
            return None
        return reports[-1]

    async def record_job_run(self, *, job: str, status: str, detail: dict[str, Any]) -> None:
        record = {
            "job": job,
            "status": status,
            "detail": detail,
            "updated_at": _utcnow().isoformat(),
        }
        if self.redis is None:
            _MEM_JOB_HISTORY.append(record)
            if len(_MEM_JOB_HISTORY) > 500:
                del _MEM_JOB_HISTORY[: len(_MEM_JOB_HISTORY) - 500]
            return
        rows = await self._load_json(self.POLICY_JOB_HISTORY_KEY, default=[])
        rows.append(record)
        rows = rows[-500:]
        await self._save_json(self.POLICY_JOB_HISTORY_KEY, rows)

    async def list_job_history(self, *, limit: int = 200) -> list[dict[str, Any]]:
        if self.redis is None:
            return _MEM_JOB_HISTORY[-limit:]
        rows = await self._load_json(self.POLICY_JOB_HISTORY_KEY, default=[])
        if not isinstance(rows, list):
            return []
        return rows[-max(1, limit):]

    async def _resolve_scope_policy(
        self,
        *,
        strategy_pack: str,
        channel: str,
        scope_type: str,
        scope_key: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        if not scope_key:
            return None
        policies = await self.list_policies(
            strategy_pack=strategy_pack,
            statuses={"canary", "active"},
            channel=channel,
            scope_type=scope_type,
            scope_key=scope_key,
        )
        if not policies:
            return None

        active_policy: dict[str, Any] | None = None
        canary_policy: dict[str, Any] | None = None
        for item in policies:
            status = str(item.get("status", ""))
            if status == "canary" and canary_policy is None:
                canary_policy = item
            elif status == "active" and active_policy is None:
                active_policy = item

        selected = active_policy or canary_policy
        if canary_policy and getattr(settings, "ENABLE_POLICY_CANARY_ROLLOUT", False):
            bucket = self._session_bucket(
                user_id=user_id,
                session_id=f"{session_id}:{scope_type}:{scope_key}",
            )
            canary_percent = max(0, min(int(canary_policy.get("rollout_percent", 10)), 100))
            if bucket < canary_percent:
                selected = canary_policy
            elif active_policy:
                selected = active_policy
        return selected

    def _compose_layered_policy(
        self,
        *,
        strategy_pack: str,
        channel: str,
        layers: list[dict[str, Any]],
        cohort_id: str,
        user_scope: str,
    ) -> dict[str, Any]:
        return MetaPolicyComposerService.compose(
            strategy_pack=strategy_pack,
            channel=channel,
            layers=layers,
            cohort_id=cohort_id,
            user_scope=user_scope,
        )

    @staticmethod
    def _session_bucket(*, user_id: str, session_id: str) -> int:
        seed = f"{user_id}:{session_id}".encode("utf-8", errors="ignore")
        digest = hashlib.sha1(seed).hexdigest()[:8]
        return int(digest, 16) % 100

    async def _load_candidates(self) -> dict[str, dict[str, Any]]:
        if self.redis is None:
            return dict(_MEM_CANDIDATES)
        data = await self._load_json(self.POLICY_CANDIDATE_KEY, default={})
        if not isinstance(data, dict):
            return {}
        return data

    async def _save_candidates(self, payload: dict[str, dict[str, Any]]) -> None:
        if self.redis is None:
            _MEM_CANDIDATES.clear()
            _MEM_CANDIDATES.update(payload)
            return
        await self._save_json(self.POLICY_CANDIDATE_KEY, payload)

    async def _load_policies(self) -> dict[str, dict[str, Any]]:
        if self.redis is None:
            return dict(_MEM_POLICIES)
        data = await self._load_json(self.POLICY_REGISTRY_KEY, default={})
        if not isinstance(data, dict):
            return {}
        return data

    async def _save_policies(self, payload: dict[str, dict[str, Any]]) -> None:
        if self.redis is None:
            _MEM_POLICIES.clear()
            _MEM_POLICIES.update(payload)
            return
        await self._save_json(self.POLICY_REGISTRY_KEY, payload)

    async def _load_json(self, key: str, *, default: Any) -> Any:
        if self.redis is None:
            return default
        try:
            raw = await self.redis.get(key)
        except Exception as exc:
            logger.warning("PolicyRegistry load failed {}: {}", key, exc)
            return default
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    async def _save_json(self, key: str, payload: Any) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.set(key, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.warning("PolicyRegistry save failed {}: {}", key, exc)
