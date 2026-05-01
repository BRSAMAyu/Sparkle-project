from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter

InferenceScope = Literal["exam_sprint", "long_term"]
InferenceStatus = Literal["observed", "candidate", "trial", "confirmed", "revoked"]

SELF_MODEL_KEY = "self_model"
KNOWN_ASSUMPTIONS_KEY = "known_assumptions"
INFERENCE_PIPELINE_KEY = "inference_write_pipeline"

TEMPORARY_STATE_TTL_SECONDS = 24 * 60 * 60
TRIAL_WINDOW_DAYS = 7
CANDIDATE_CONFIDENCE_THRESHOLD = 0.7
MIN_EXAM_SPRINT_EVIDENCE = 2
MAX_EVIDENCE_ITEMS = 5

TEMPORARY_STATE_KEY_TEMPLATE = "aurora:write-pipeline:temporary:{user_id}:{claim_id}"
EXAM_SPRINT_KEY_TEMPLATE = "aurora:write-pipeline:exam-sprint:{user_id}:{planning_session_id}"
AURORA_CLAIM_KEY_TEMPLATE = "aurora:claims:{user_id}:{domain}"
AURORA_CLAIM_TTL_SECONDS = 24 * 60 * 60
INFERENCE_CLAIM_KEY_TEMPLATE = AURORA_CLAIM_KEY_TEMPLATE
INFERENCE_CLAIM_TTL_SECONDS = AURORA_CLAIM_TTL_SECONDS


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return _strip(value).lower() in {"1", "true", "yes", "y"}


def _clamp_confidence(value: Any, *, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(max(0.0, min(1.0, numeric)), 4)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = _strip(value)
    return text or None


def _parse_iso(value: Any) -> datetime | None:
    text = _coerce_iso(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _claim_fingerprint(
    *,
    claim: str,
    scope: InferenceScope,
    claim_type: str,
    preference_key: str | None = None,
) -> str:
    payload = json.dumps(
        {
            "claim": _strip(claim).lower(),
            "scope": scope,
            "claim_type": _strip(claim_type).lower(),
            "preference_key": _strip(preference_key).lower() or None,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:24]


def _normalize_scope(value: Any) -> InferenceScope:
    return "exam_sprint" if _strip(value).lower() == "exam_sprint" else "long_term"


def _normalize_status(value: Any, *, needs_confirmation: bool = False) -> InferenceStatus:
    normalized = _strip(value).lower()
    if normalized in {"observed", "candidate", "trial", "confirmed", "revoked"}:
        return normalized  # type: ignore[return-value]
    if normalized in {"rejected", "suppressed", "dismissed", "archived"}:
        return "revoked"
    if needs_confirmation:
        return "candidate"
    return "observed"


def _merge_evidence(existing: Sequence[str], additions: Sequence[str]) -> list[str]:
    merged: list[str] = []
    for item in [*existing, *additions]:
        normalized = _strip(item)
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged[-MAX_EVIDENCE_ITEMS:]


def _extract_evidence(payload: Mapping[str, Any]) -> list[str]:
    evidence: list[str] = []
    for raw in _as_list(payload.get("evidence")):
        if isinstance(raw, Mapping):
            detail = _strip(raw.get("detail"))
            if detail:
                evidence.append(detail)
            continue
        detail = _strip(raw)
        if detail:
            evidence.append(detail)
    return evidence[-MAX_EVIDENCE_ITEMS:]


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _normalize_claim_domain(value: Any) -> str:
    return _strip(value).lower().replace(" ", "_")


@dataclass
class InferenceClaim:
    claim: str = ""
    scope: InferenceScope = "long_term"
    status: InferenceStatus = "observed"
    confidence: float = 0.0
    evidence_count: int = 0
    needs_confirmation: bool = False
    domain: str | None = None
    value: Any = None
    evidence_type: str | None = None
    user_id: str | None = None
    expires_at: str | None = None
    id: str | None = None
    claim_type: str = "general"
    fingerprint: str | None = None
    title: str | None = None
    statement: str | None = None
    evidence: list[str] = field(default_factory=list)
    source: str | None = None
    observed_at: str | None = None
    last_observed_at: str | None = None
    candidate_at: str | None = None
    trial_started_at: str | None = None
    trial_expires_at: str | None = None
    confirmed_at: str | None = None
    revoked_at: str | None = None
    updated_at: str | None = None
    plan_id: str | None = None
    planning_session_id: str | None = None
    preference_key: str | None = None
    preference_value: Any = None
    response_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now_iso = _utcnow_iso()
        self.domain = _normalize_claim_domain(self.domain) or None
        self.evidence_type = _strip(self.evidence_type) or None
        self.user_id = _strip(self.user_id) or None
        self.value = _json_safe(self.value)
        normalized_claim = _strip(self.claim)
        if not normalized_claim and self.domain:
            normalized_claim = f"{self.domain}={json.dumps(self.value, ensure_ascii=False, default=str)}"
        self.claim = normalized_claim
        self.scope = _normalize_scope(self.scope)
        self.claim_type = _strip(self.claim_type) or "general"
        if self.domain and self.claim_type == "general":
            self.claim_type = self.domain
        self.fingerprint = _strip(self.fingerprint) or _claim_fingerprint(
            claim=normalized_claim,
            scope=self.scope,
            claim_type=self.claim_type,
            preference_key=self.preference_key,
        )
        self.id = _strip(self.id) or f"claim-{self.fingerprint[:12]}"
        self.title = _strip(self.title) or normalized_claim
        self.statement = _strip(self.statement) or normalized_claim
        self.source = _strip(self.source) or None
        self.plan_id = _strip(self.plan_id) or None
        self.planning_session_id = _strip(self.planning_session_id) or None
        self.preference_key = _strip(self.preference_key) or None
        self.confidence = _clamp_confidence(self.confidence)
        self.evidence = _merge_evidence([], self.evidence)
        self.evidence_count = max(int(self.evidence_count or 0), len(self.evidence))
        self.observed_at = _coerce_iso(self.observed_at) or now_iso
        self.last_observed_at = _coerce_iso(self.last_observed_at) or self.observed_at
        self.candidate_at = _coerce_iso(self.candidate_at)
        self.trial_started_at = _coerce_iso(self.trial_started_at)
        self.trial_expires_at = _coerce_iso(self.trial_expires_at)
        self.confirmed_at = _coerce_iso(self.confirmed_at)
        self.revoked_at = _coerce_iso(self.revoked_at)
        self.expires_at = _coerce_iso(self.expires_at)
        self.updated_at = _coerce_iso(self.updated_at) or self.last_observed_at or now_iso
        self.response_history = [
            {
                "response": _strip(item.get("response")) or None,
                "reason": _strip(item.get("reason")) or None,
                "corrected_assumption": _strip(item.get("corrected_assumption")) or None,
                "responded_at": _coerce_iso(item.get("responded_at")),
            }
            for item in self.response_history
            if isinstance(item, Mapping)
        ][-10:]
        self.metadata = _as_dict(self.metadata)
        if self.domain:
            self.metadata.setdefault("domain", self.domain)
        if self.value is not None:
            self.metadata.setdefault("value", _json_safe(self.value))
        if self.evidence_type:
            self.metadata.setdefault("evidence_type", self.evidence_type)
        if self.user_id:
            self.metadata.setdefault("user_id", self.user_id)

    @classmethod
    def from_dict(cls, payload: Any) -> InferenceClaim:
        data = _as_dict(payload)
        evidence = _extract_evidence(data)
        needs_confirmation = _as_bool(data.get("needs_confirmation"))
        domain = _normalize_claim_domain(data.get("domain") or _as_dict(data.get("metadata")).get("domain")) or None
        value = _json_safe(data.get("value", _as_dict(data.get("metadata")).get("value")))
        claim = _strip(data.get("claim") or data.get("statement") or data.get("title"))
        if not claim and domain:
            claim = f"{domain}={json.dumps(value, ensure_ascii=False, default=str)}"
        claim_type = _strip(data.get("claim_type")) or "general"
        scope = _normalize_scope(data.get("scope"))
        fingerprint = _strip(data.get("fingerprint")) or _claim_fingerprint(
            claim=claim,
            scope=scope,
            claim_type=claim_type,
            preference_key=_strip(data.get("preference_key")) or None,
        )
        status = _normalize_status(
            data.get("status"),
            needs_confirmation=needs_confirmation,
        )
        return cls(
            id=_strip(data.get("id")) or _strip(data.get("assumption_id")) or None,
            fingerprint=fingerprint,
            claim=claim,
            title=_strip(data.get("title")) or None,
            statement=_strip(data.get("statement")) or None,
            scope=scope,
            status=status,
            confidence=_clamp_confidence(data.get("confidence")),
            evidence_count=max(_safe_int(data.get("evidence_count")), len(evidence)),
            needs_confirmation=needs_confirmation or status == "candidate",
            domain=domain,
            value=value,
            evidence_type=_strip(data.get("evidence_type") or _as_dict(data.get("metadata")).get("evidence_type"))
            or None,
            user_id=_strip(data.get("user_id") or _as_dict(data.get("metadata")).get("user_id")) or None,
            expires_at=_coerce_iso(data.get("expires_at")),
            claim_type=claim_type,
            evidence=evidence,
            source=_strip(data.get("source")) or None,
            observed_at=_coerce_iso(data.get("observed_at")),
            last_observed_at=_coerce_iso(data.get("last_observed_at") or data.get("updated_at")),
            candidate_at=_coerce_iso(data.get("candidate_at")),
            trial_started_at=_coerce_iso(data.get("trial_started_at")),
            trial_expires_at=_coerce_iso(data.get("trial_expires_at")),
            confirmed_at=_coerce_iso(data.get("confirmed_at")),
            revoked_at=_coerce_iso(data.get("revoked_at") or data.get("rejected_at") or data.get("suppressed_at")),
            updated_at=_coerce_iso(data.get("updated_at")),
            plan_id=_strip(data.get("plan_id")) or None,
            planning_session_id=_strip(data.get("planning_session_id")) or None,
            preference_key=_strip(data.get("preference_key")) or None,
            preference_value=_json_safe(data.get("preference_value")),
            response_history=[
                _as_dict(item) for item in _as_list(data.get("response_history")) if isinstance(item, Mapping)
            ],
            metadata=_as_dict(data.get("metadata")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = self.confidence
        payload["claim"] = self.claim
        payload["title"] = self.title or self.claim
        payload["statement"] = self.statement or self.claim
        payload["evidence"] = list(self.evidence)
        payload["evidence_count"] = max(self.evidence_count, len(self.evidence))
        payload["needs_confirmation"] = bool(self.needs_confirmation)
        payload["metadata"] = _json_safe(self.metadata)
        payload["preference_value"] = _json_safe(self.preference_value)
        payload["value"] = _json_safe(self.value)
        return payload


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class AuroraWritePipeline:
    """Redis-backed signal lane for cross-runtime Aurora claims."""

    def __init__(self, redis_client=None, *, ttl_seconds: int = AURORA_CLAIM_TTL_SECONDS) -> None:
        self.redis = redis_client
        self.ttl_seconds = max(1, int(ttl_seconds))

    @staticmethod
    def claim_key(*, user_id: UUID | str, domain: str) -> str:
        normalized_domain = _normalize_claim_domain(domain)
        if not _strip(user_id):
            raise ValueError("user_id required for Aurora claim")
        if not normalized_domain:
            raise ValueError("domain required for Aurora claim")
        return AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user_id), domain=normalized_domain)

    async def submit_claim(self, claim: InferenceClaim) -> InferenceClaim:
        if self.redis is None:
            raise RuntimeError("redis required for Aurora claim pipeline")
        if not claim.domain:
            raise ValueError("claim.domain required")
        if not claim.user_id:
            raise ValueError("claim.user_id required")

        key = self.claim_key(user_id=claim.user_id, domain=claim.domain)
        raw = await self._redis_get(key)
        payload = self._load_payload(raw)
        existing_claim = self._claim_from_payload(payload, domain=claim.domain)

        stored_claim = InferenceClaim(
            **{
                **claim.to_dict(),
                "user_id": claim.user_id,
                "domain": claim.domain,
                "updated_at": _utcnow_iso(),
            }
        )
        if existing_claim is not None:
            stored_claim = InferenceClaim(
                **{
                    **existing_claim.to_dict(),
                    **stored_claim.to_dict(),
                    "evidence": _merge_evidence(existing_claim.evidence, stored_claim.evidence),
                    "evidence_count": max(existing_claim.evidence_count, stored_claim.evidence_count),
                    "observed_at": existing_claim.observed_at,
                    "last_observed_at": stored_claim.updated_at,
                    "confidence": max(existing_claim.confidence, stored_claim.confidence),
                    "metadata": {**existing_claim.metadata, **stored_claim.metadata},
                }
            )

        updated_payload = {
            "user_id": claim.user_id,
            "domain": claim.domain,
            "value": _json_safe(stored_claim.value),
            "confidence": stored_claim.confidence,
            "claim": stored_claim.to_dict(),
            "values": [_json_safe(stored_claim.value)] if stored_claim.value is not None else [],
            "claims": [stored_claim.to_dict()],
            "updated_at": _utcnow_iso(),
        }
        await self._redis_set(key, json.dumps(updated_payload, ensure_ascii=False))
        return stored_claim

    async def get_claim(self, *, user_id: UUID | str, domain: str) -> InferenceClaim | None:
        if self.redis is None:
            return None
        key = self.claim_key(user_id=user_id, domain=domain)
        payload = self._load_payload(await self._redis_get(key))
        return self._claim_from_payload(payload, domain=domain)

    async def _redis_get(self, key: str) -> Any:
        getter = getattr(self.redis, "get", None)
        if getter is None:
            return None
        return await _maybe_await(getter(key))

    async def _redis_set(self, key: str, value: str) -> None:
        setex = getattr(self.redis, "setex", None)
        if setex is not None:
            await _maybe_await(setex(key, self.ttl_seconds, value))
            return
        setter = getattr(self.redis, "set", None)
        if setter is None:
            raise RuntimeError("redis client must support set or setex")
        try:
            await _maybe_await(setter(key, value, ex=self.ttl_seconds))
        except TypeError:
            await _maybe_await(setter(key, value))

    @staticmethod
    def _load_payload(raw: Any) -> dict[str, Any]:
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, Mapping):
            return _as_dict(raw)
        try:
            return _as_dict(json.loads(str(raw)))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _claim_from_payload(payload: Mapping[str, Any], *, domain: str) -> InferenceClaim | None:
        claims = [item for item in _as_list(payload.get("claims")) if isinstance(item, Mapping)]
        if claims:
            return InferenceClaim.from_dict(claims[-1])
        claim_payload = payload.get("claim")
        if isinstance(claim_payload, Mapping):
            return InferenceClaim.from_dict(claim_payload)
        if payload.get("domain") or payload.get("value") is not None:
            return InferenceClaim.from_dict({**dict(payload), "domain": payload.get("domain") or domain})
        return None


async def submit_claim(
    claim: InferenceClaim,
    redis,
    *,
    user_id: UUID | str | None = None,
) -> InferenceClaim:
    if user_id is not None and not claim.user_id:
        claim = InferenceClaim(**{**claim.to_dict(), "user_id": str(user_id)})
    return await AuroraWritePipeline(redis).submit_claim(claim)


async def get_claim(
    domain: str,
    redis,
    *,
    user_id: UUID | str,
) -> InferenceClaim | None:
    return await AuroraWritePipeline(redis).get_claim(user_id=user_id, domain=domain)


class InferenceWritePipeline:
    """Confidence-aware write lane for Aurora inference claims."""

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        *,
        pref_service: Any | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.pref_service = pref_service  # injected by caller outside aurora/ path

    async def _save_inferred_data(self, user_uuid: UUID, inferred: dict[str, Any]) -> Any:
        return await self._save_inferred_data(user_uuid, inferred)

    async def _read_user_preferences(self, user_uuid: UUID) -> Any:
        return await self._read_user_preferences(user_uuid)

    @staticmethod
    def temporary_state_key(*, user_id: UUID | str, claim_id: str) -> str:
        return TEMPORARY_STATE_KEY_TEMPLATE.format(user_id=str(user_id), claim_id=_strip(claim_id))

    @staticmethod
    def exam_sprint_key(*, user_id: UUID | str, planning_session_id: str) -> str:
        return EXAM_SPRINT_KEY_TEMPLATE.format(
            user_id=str(user_id),
            planning_session_id=_strip(planning_session_id),
        )

    async def ingest_claim(
        self,
        *,
        user_id: UUID | str,
        claim: str,
        claim_type: str,
        scope: InferenceScope,
        confidence: float,
        evidence: Sequence[str] | None = None,
        evidence_count: int | None = None,
        claim_id: str | None = None,
        title: str | None = None,
        statement: str | None = None,
        source: str | None = None,
        plan_id: str | None = None,
        planning_session_id: str | None = None,
        exam_ends_at: datetime | str | None = None,
        preference_key: str | None = None,
        preference_value: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> InferenceClaim:
        normalized_type = _strip(claim_type).lower()
        if normalized_type == "temporary_state":
            return await self._write_temporary_state(
                user_id=user_id,
                claim=claim,
                confidence=confidence,
                evidence=evidence,
                evidence_count=evidence_count,
                claim_id=claim_id,
                title=title,
                statement=statement,
                source=source,
                metadata=metadata,
            )
        if normalized_type == "exam_sprint":
            return await self._write_exam_sprint_claim(
                user_id=user_id,
                claim=claim,
                confidence=confidence,
                evidence=evidence,
                evidence_count=evidence_count,
                claim_id=claim_id,
                title=title,
                statement=statement,
                source=source,
                plan_id=plan_id,
                planning_session_id=planning_session_id,
                exam_ends_at=exam_ends_at,
                metadata=metadata,
            )
        return await self._upsert_long_term_claim(
            user_id=user_id,
            claim=claim,
            confidence=confidence,
            evidence=evidence,
            evidence_count=evidence_count,
            claim_id=claim_id,
            title=title,
            statement=statement,
            source=source,
            plan_id=plan_id,
            claim_type=normalized_type or "general",
            preference_key=preference_key,
            preference_value=preference_value,
            metadata=metadata,
        )

    async def respond_to_claim(
        self,
        *,
        user_id: UUID | str,
        claim_id: str,
        response: str,
        reason: str | None = None,
        corrected_assumption: str | None = None,
    ) -> tuple[UserPreferencesCenter, InferenceClaim]:
        normalized_response = _strip(response).lower()
        if normalized_response not in {"confirm", "incorrect", "mute"}:
            raise ValueError("unsupported response")

        user_uuid = _coerce_uuid(user_id)
        prefs = await self._read_user_preferences(user_uuid)
        inferred = dict(prefs.inferred or {})
        self_model = self._get_self_model(inferred)
        claims = self._load_claims_from_self_model(self_model)
        claims, _ = self._promote_due_trials_in_memory(claims, now=_utcnow())

        target_index = self._find_claim_index(claims, claim_id=claim_id)
        if target_index is None:
            raise LookupError("calibration card not found")

        now = _utcnow()
        updated_claim = self._apply_response(
            claim=claims[target_index],
            response=normalized_response,
            reason=reason,
            corrected_assumption=corrected_assumption,
            responded_at=now,
        )
        claims[target_index] = updated_claim
        durable_bucket = self._ensure_pipeline_bucket(inferred)
        self._sync_durable_bucket(durable_bucket, updated_claim)

        self._persist_claims_to_self_model(self_model, claims)
        inferred[SELF_MODEL_KEY] = self_model
        inferred[INFERENCE_PIPELINE_KEY] = durable_bucket
        updated_prefs = await self._save_inferred_data(user_uuid, inferred)
        return updated_prefs, updated_claim

    async def promote_due_trials(
        self,
        *,
        user_id: UUID | str,
    ) -> list[InferenceClaim]:
        user_uuid = _coerce_uuid(user_id)
        prefs = await self._read_user_preferences(user_uuid)
        inferred = dict(prefs.inferred or {})
        self_model = self._get_self_model(inferred)
        claims = self._load_claims_from_self_model(self_model)
        updated_claims, changed = self._promote_due_trials_in_memory(claims, now=_utcnow())
        if not changed:
            return updated_claims

        durable_bucket = self._ensure_pipeline_bucket(inferred)
        for claim in updated_claims:
            if claim.status in {"trial", "confirmed", "revoked"}:
                self._sync_durable_bucket(durable_bucket, claim)

        self._persist_claims_to_self_model(self_model, updated_claims)
        inferred[SELF_MODEL_KEY] = self_model
        inferred[INFERENCE_PIPELINE_KEY] = durable_bucket
        await self._save_inferred_data(user_uuid, inferred)
        return updated_claims

    async def get_temporary_state(
        self,
        *,
        user_id: UUID | str,
        claim_id: str,
    ) -> InferenceClaim | None:
        if self.redis is None:
            return None
        raw = await self.redis.get(self.temporary_state_key(user_id=user_id, claim_id=claim_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, Mapping):
            return InferenceClaim.from_dict(raw)
        return InferenceClaim.from_dict(json.loads(raw))

    async def get_exam_sprint_claims(
        self,
        *,
        user_id: UUID | str,
        planning_session_id: str,
    ) -> list[InferenceClaim]:
        if self.redis is None:
            return []
        raw = await self.redis.get(self.exam_sprint_key(user_id=user_id, planning_session_id=planning_session_id))
        if not raw:
            return []
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = _as_dict(raw if isinstance(raw, Mapping) else json.loads(raw))
        return [
            InferenceClaim.from_dict(item)
            for item in _as_list(payload.get("claims"))
            if isinstance(item, Mapping)
        ]

    async def _write_temporary_state(
        self,
        *,
        user_id: UUID | str,
        claim: str,
        confidence: float,
        evidence: Sequence[str] | None,
        evidence_count: int | None,
        claim_id: str | None,
        title: str | None,
        statement: str | None,
        source: str | None,
        metadata: dict[str, Any] | None,
    ) -> InferenceClaim:
        if self.redis is None:
            raise RuntimeError("redis required for temporary inference claims")
        now = _utcnow()
        expires_at = now + timedelta(seconds=TEMPORARY_STATE_TTL_SECONDS)
        claim_model = InferenceClaim(
            id=claim_id,
            claim=claim,
            title=title,
            statement=statement,
            scope="long_term",
            status="observed",
            confidence=confidence,
            evidence_count=max(evidence_count or 0, len(list(evidence or []))),
            needs_confirmation=False,
            expires_at=expires_at.isoformat(),
            claim_type="temporary_state",
            evidence=[_strip(item) for item in list(evidence or []) if _strip(item)],
            source=source,
            observed_at=now.isoformat(),
            last_observed_at=now.isoformat(),
            updated_at=now.isoformat(),
            metadata=dict(metadata or {}),
        )
        await self.redis.setex(
            self.temporary_state_key(user_id=user_id, claim_id=claim_model.id or ""),
            TEMPORARY_STATE_TTL_SECONDS,
            json.dumps(claim_model.to_dict(), ensure_ascii=False),
        )
        return claim_model

    async def _write_exam_sprint_claim(
        self,
        *,
        user_id: UUID | str,
        claim: str,
        confidence: float,
        evidence: Sequence[str] | None,
        evidence_count: int | None,
        claim_id: str | None,
        title: str | None,
        statement: str | None,
        source: str | None,
        plan_id: str | None,
        planning_session_id: str | None,
        exam_ends_at: datetime | str | None,
        metadata: dict[str, Any] | None,
    ) -> InferenceClaim:
        if self.redis is None:
            raise RuntimeError("redis required for exam sprint claims")
        normalized_session_id = _strip(planning_session_id)
        if not normalized_session_id:
            raise ValueError("planning_session_id required for exam_sprint claim")
        exam_end = _parse_iso(exam_ends_at)
        if exam_end is None:
            raise ValueError("exam_ends_at required for exam_sprint claim")

        evidence_lines = [_strip(item) for item in list(evidence or []) if _strip(item)]
        total_evidence = max(evidence_count or 0, len(evidence_lines))
        if total_evidence < MIN_EXAM_SPRINT_EVIDENCE:
            raise ValueError("exam_sprint claim requires evidence")

        raw = await self.redis.get(self.exam_sprint_key(user_id=user_id, planning_session_id=normalized_session_id))
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = _as_dict(raw if isinstance(raw, Mapping) else json.loads(raw)) if raw else {}
        claims = [
            InferenceClaim.from_dict(item)
            for item in _as_list(payload.get("claims"))
            if isinstance(item, Mapping)
        ]

        now = _utcnow()
        claim_model = InferenceClaim(
            id=claim_id,
            claim=claim,
            title=title,
            statement=statement,
            scope="exam_sprint",
            status="confirmed",
            confidence=confidence,
            evidence_count=total_evidence,
            needs_confirmation=False,
            expires_at=exam_end.isoformat(),
            claim_type="exam_sprint",
            evidence=evidence_lines,
            source=source,
            observed_at=now.isoformat(),
            last_observed_at=now.isoformat(),
            confirmed_at=now.isoformat(),
            updated_at=now.isoformat(),
            plan_id=plan_id,
            planning_session_id=normalized_session_id,
            metadata=dict(metadata or {}),
        )

        existing_index = self._find_claim_index(claims, claim_id=claim_model.id or "", fingerprint=claim_model.fingerprint)
        if existing_index is None:
            claims.append(claim_model)
        else:
            current = claims[existing_index]
            claim_model.evidence = _merge_evidence(current.evidence, claim_model.evidence)
            claim_model.evidence_count = max(current.evidence_count, claim_model.evidence_count, len(claim_model.evidence))
            claim_model.observed_at = current.observed_at
            claims[existing_index] = claim_model

        ttl_seconds = max(1, int((exam_end - now).total_seconds()))
        await self.redis.setex(
            self.exam_sprint_key(user_id=user_id, planning_session_id=normalized_session_id),
            ttl_seconds,
            json.dumps(
                {
                    "planning_session_id": normalized_session_id,
                    "expires_at": exam_end.isoformat(),
                    "updated_at": now.isoformat(),
                    "claims": [item.to_dict() for item in claims],
                },
                ensure_ascii=False,
            ),
        )
        return claim_model

    async def _upsert_long_term_claim(
        self,
        *,
        user_id: UUID | str,
        claim: str,
        confidence: float,
        evidence: Sequence[str] | None,
        evidence_count: int | None,
        claim_id: str | None,
        title: str | None,
        statement: str | None,
        source: str | None,
        plan_id: str | None,
        claim_type: str,
        preference_key: str | None,
        preference_value: Any,
        metadata: dict[str, Any] | None,
    ) -> InferenceClaim:
        user_uuid = _coerce_uuid(user_id)
        prefs = await self._read_user_preferences(user_uuid)
        inferred = dict(prefs.inferred or {})
        self_model = self._get_self_model(inferred)
        claims = self._load_claims_from_self_model(self_model)
        durable_bucket = self._ensure_pipeline_bucket(inferred)

        evidence_lines = [_strip(item) for item in list(evidence or []) if _strip(item)]
        fingerprint = _claim_fingerprint(
            claim=claim,
            scope="long_term",
            claim_type=claim_type,
            preference_key=preference_key,
        )
        revoked_claims = _as_dict(durable_bucket.get("revoked_claims"))
        if fingerprint in revoked_claims:
            return InferenceClaim.from_dict(revoked_claims[fingerprint])

        now = _utcnow()
        existing_index = self._find_claim_index(claims, claim_id=claim_id or "", fingerprint=fingerprint)
        if existing_index is None:
            merged_claim = InferenceClaim(
                id=claim_id,
                claim=claim,
                title=title,
                statement=statement,
                scope="long_term",
                status="candidate" if _clamp_confidence(confidence) >= CANDIDATE_CONFIDENCE_THRESHOLD else "observed",
                confidence=confidence,
                evidence_count=max(evidence_count or 0, len(evidence_lines)),
                needs_confirmation=_clamp_confidence(confidence) >= CANDIDATE_CONFIDENCE_THRESHOLD,
                claim_type=claim_type,
                evidence=evidence_lines,
                source=source,
                observed_at=now.isoformat(),
                last_observed_at=now.isoformat(),
                candidate_at=now.isoformat() if _clamp_confidence(confidence) >= CANDIDATE_CONFIDENCE_THRESHOLD else None,
                updated_at=now.isoformat(),
                plan_id=plan_id,
                preference_key=preference_key,
                preference_value=_json_safe(preference_value),
                metadata=dict(metadata or {}),
                fingerprint=fingerprint,
            )
            claims.append(merged_claim)
        else:
            current = claims[existing_index]
            if current.status == "revoked":
                return current
            merged_evidence = _merge_evidence(current.evidence, evidence_lines)
            merged_confidence = max(current.confidence, _clamp_confidence(confidence))
            merged_status: InferenceStatus = current.status
            if current.status in {"observed", "candidate"}:
                merged_status = "candidate" if merged_confidence >= CANDIDATE_CONFIDENCE_THRESHOLD else "observed"
            merged_claim = InferenceClaim(
                id=current.id or claim_id,
                fingerprint=current.fingerprint,
                claim=current.claim or claim,
                title=title or current.title,
                statement=statement or current.statement,
                scope="long_term",
                status=merged_status,
                confidence=merged_confidence,
                evidence_count=max(current.evidence_count, evidence_count or 0, len(merged_evidence)),
                needs_confirmation=merged_status == "candidate",
                expires_at=current.expires_at,
                claim_type=current.claim_type or claim_type,
                evidence=merged_evidence,
                source=source or current.source,
                observed_at=current.observed_at,
                last_observed_at=now.isoformat(),
                candidate_at=current.candidate_at
                or (now.isoformat() if merged_status == "candidate" else None),
                trial_started_at=current.trial_started_at,
                trial_expires_at=current.trial_expires_at,
                confirmed_at=current.confirmed_at,
                revoked_at=current.revoked_at,
                updated_at=now.isoformat(),
                plan_id=plan_id or current.plan_id,
                planning_session_id=current.planning_session_id,
                preference_key=preference_key or current.preference_key,
                preference_value=_json_safe(preference_value if preference_value is not None else current.preference_value),
                response_history=current.response_history,
                metadata={**current.metadata, **dict(metadata or {})},
            )
            claims[existing_index] = merged_claim

        self._persist_claims_to_self_model(self_model, claims)
        inferred[SELF_MODEL_KEY] = self_model
        await self._save_inferred_data(user_uuid, inferred)
        return merged_claim

    @staticmethod
    def _get_self_model(inferred: dict[str, Any]) -> dict[str, Any]:
        model = _as_dict(inferred.get(SELF_MODEL_KEY))
        assumptions = [
            _as_dict(item)
            for item in _as_list(model.get(KNOWN_ASSUMPTIONS_KEY))
            if isinstance(item, Mapping) and _strip(_as_dict(item).get("id"))
        ]
        model[KNOWN_ASSUMPTIONS_KEY] = assumptions
        return model

    @staticmethod
    def _load_claims_from_self_model(self_model: Mapping[str, Any]) -> list[InferenceClaim]:
        return [
            InferenceClaim.from_dict(item)
            for item in _as_list(self_model.get(KNOWN_ASSUMPTIONS_KEY))
            if isinstance(item, Mapping) and _strip(_as_dict(item).get("id"))
        ]

    @staticmethod
    def _persist_claims_to_self_model(self_model: dict[str, Any], claims: Sequence[InferenceClaim]) -> None:
        self_model[KNOWN_ASSUMPTIONS_KEY] = [item.to_dict() for item in claims]
        self_model["updated_at"] = _utcnow_iso()

    @staticmethod
    def _ensure_pipeline_bucket(inferred: dict[str, Any]) -> dict[str, Any]:
        bucket = _as_dict(inferred.get(INFERENCE_PIPELINE_KEY))
        bucket["claims"] = _as_dict(bucket.get("claims"))
        bucket["revoked_claims"] = _as_dict(bucket.get("revoked_claims"))
        bucket["updated_at"] = _coerce_iso(bucket.get("updated_at")) or _utcnow_iso()
        return bucket

    @staticmethod
    def _sync_durable_bucket(bucket: dict[str, Any], claim: InferenceClaim) -> None:
        durable_claims = _as_dict(bucket.get("claims"))
        revoked_claims = _as_dict(bucket.get("revoked_claims"))
        if claim.status == "revoked":
            durable_claims.pop(claim.id or "", None)
            revoked_claims[claim.fingerprint or ""] = claim.to_dict()
        elif claim.scope == "long_term" and claim.status in {"trial", "confirmed"}:
            durable_claims[claim.id or ""] = claim.to_dict()
            revoked_claims.pop(claim.fingerprint or "", None)
        bucket["claims"] = durable_claims
        bucket["revoked_claims"] = revoked_claims
        bucket["updated_at"] = _utcnow_iso()

    @staticmethod
    def _find_claim_index(
        claims: Sequence[InferenceClaim],
        *,
        claim_id: str | None = None,
        fingerprint: str | None = None,
    ) -> int | None:
        normalized_id = _strip(claim_id)
        normalized_fingerprint = _strip(fingerprint)
        for index, item in enumerate(claims):
            if normalized_id and _strip(item.id) == normalized_id:
                return index
            if normalized_fingerprint and _strip(item.fingerprint) == normalized_fingerprint:
                return index
        return None

    @staticmethod
    def _apply_response(
        *,
        claim: InferenceClaim,
        response: str,
        reason: str | None,
        corrected_assumption: str | None,
        responded_at: datetime,
    ) -> InferenceClaim:
        responded_at_iso = responded_at.isoformat()
        history = list(claim.response_history)
        history.append(
            {
                "response": response,
                "reason": _strip(reason) or None,
                "corrected_assumption": _strip(corrected_assumption) or None,
                "responded_at": responded_at_iso,
            }
        )
        if response == "confirm":
            return InferenceClaim(
                **{
                    **claim.to_dict(),
                    "status": "trial",
                    "needs_confirmation": False,
                    "confidence": max(claim.confidence, 0.85),
                    "trial_started_at": claim.trial_started_at or responded_at_iso,
                    "trial_expires_at": claim.trial_expires_at
                    or (responded_at + timedelta(days=TRIAL_WINDOW_DAYS)).isoformat(),
                    "expires_at": claim.trial_expires_at
                    or (responded_at + timedelta(days=TRIAL_WINDOW_DAYS)).isoformat(),
                    "updated_at": responded_at_iso,
                    "response_history": history[-10:],
                }
            )
        updated_metadata = dict(claim.metadata or {})
        if _strip(corrected_assumption):
            updated_metadata["user_correction"] = _strip(corrected_assumption)
        return InferenceClaim(
            **{
                **claim.to_dict(),
                "status": "revoked",
                "needs_confirmation": False,
                "confidence": min(claim.confidence, 0.25 if response == "incorrect" else 0.2),
                "revoked_at": responded_at_iso,
                "expires_at": None,
                "trial_expires_at": claim.trial_expires_at,
                "updated_at": responded_at_iso,
                "response_history": history[-10:],
                "metadata": updated_metadata,
            }
        )

    @staticmethod
    def _promote_due_trials_in_memory(
        claims: Sequence[InferenceClaim],
        *,
        now: datetime,
    ) -> tuple[list[InferenceClaim], bool]:
        updated: list[InferenceClaim] = []
        changed = False
        for claim in claims:
            if claim.status != "trial":
                updated.append(claim)
                continue

            trial_end = _parse_iso(claim.trial_expires_at) or (
                (_parse_iso(claim.trial_started_at) or now) + timedelta(days=TRIAL_WINDOW_DAYS)
            )
            if trial_end > now:
                updated.append(claim)
                continue

            changed = True
            updated.append(
                InferenceClaim(
                    **{
                        **claim.to_dict(),
                        "status": "confirmed",
                        "needs_confirmation": False,
                        "confidence": max(claim.confidence, 0.9),
                        "confirmed_at": now.isoformat(),
                        "expires_at": None,
                        "updated_at": now.isoformat(),
                    }
                )
            )
        return updated, changed
