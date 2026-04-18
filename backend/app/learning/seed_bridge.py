"""Bridge legacy seed-library content into Aurora distilled strategies."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timezone, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid5

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle, ProjectionPolicy, Shareability
from app.data.seed_content_initial import OFFICIAL_LIBRARIES
from app.models.seed_content import SeedItem, SeedLibrary

SEED_BRIDGE_NAMESPACE = UUID("9eb4b11b-f9f8-4a5f-9c2f-3b4cb6c03db7")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _coerce_library_payload(library: dict[str, Any] | SeedLibrary) -> dict[str, Any]:
    if isinstance(library, dict):
        return library
    return {
        "name": library.name,
        "description": library.description,
        "category": library.category,
        "language": library.language,
        "tags": list(library.tags or []),
        "quality_score": library.quality_score,
        "items": list(getattr(library, "items", []) or []),
    }


def _coerce_item_payload(item: dict[str, Any] | SeedItem) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    return {
        "item_type": item.item_type,
        "title": item.title,
        "content": item.content,
        "content_data": item.content_data,
        "subject": item.subject,
        "difficulty_level": item.difficulty_level,
        "tags": list(item.tags or []),
        "order_index": item.order_index,
    }


def _enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw).strip()


def _item_description(item: dict[str, Any]) -> str:
    candidates: list[str] = []
    title = str(item.get("title") or "").strip()
    if title:
        candidates.append(title)
    content = str(item.get("content") or "").strip()
    if content:
        candidates.append(content)
    content_data = item.get("content_data")
    if isinstance(content_data, dict):
        for key in ("explanation", "summary", "output"):
            value = content_data.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
                break
    return "\n\n".join(candidates) if candidates else "Human-authored seed content imported from the seed library."


def _strategy_scope(library: dict[str, Any], item: dict[str, Any]) -> str:
    subject = str(item.get("subject") or "").strip()
    category = _enum_value(library.get("category"))
    tags = [str(tag).strip() for tag in list(item.get("tags") or []) if str(tag).strip()]
    parts = [part for part in [category, subject, ",".join(tags[:3])] if part]
    return " / ".join(parts) if parts else "general"


def _evidence_strength(library: dict[str, Any], item: dict[str, Any]) -> float:
    quality = library.get("quality_score")
    base = float(quality) / 10.0 if isinstance(quality, (int, float)) else 0.72
    text_length = len(_item_description(item))
    length_boost = min(0.15, text_length / 6000.0)
    return round(min(0.98, base + length_boost), 3)


def _diversity_score(item: dict[str, Any]) -> float:
    tags = {str(tag).strip().casefold() for tag in list(item.get("tags") or []) if str(tag).strip()}
    return round(min(1.0, 0.25 + (len(tags) * 0.08)), 3)


def _strategy_id(library: dict[str, Any], item: dict[str, Any]) -> UUID:
    digest_source = "|".join(
        [
            str(library.get("name") or "").strip(),
            str(item.get("title") or "").strip(),
            str(item.get("subject") or "").strip(),
            str(item.get("item_type") or "").strip(),
            str(item.get("order_index") or 0),
        ]
    )
    digest = sha256(digest_source.encode("utf-8")).hexdigest()
    return uuid5(SEED_BRIDGE_NAMESPACE, digest)


def build_distilled_strategy_from_seed(
    *,
    library: dict[str, Any] | SeedLibrary,
    item: dict[str, Any] | SeedItem,
    imported_at: datetime | None = None,
) -> DistilledStrategy:
    """Convert a single seed-library item into a distilled strategy record."""

    library_payload = _coerce_library_payload(library)
    item_payload = _coerce_item_payload(item)
    now = imported_at or _utcnow()
    item_type = _enum_value(item_payload.get("item_type") or "example")
    title = str(item_payload.get("title") or library_payload.get("name") or "Seed strategy").strip()

    return DistilledStrategy(
        id=_strategy_id(library_payload, item_payload),
        created_at=now,
        updated_at=now,
        title=title,
        description=_item_description(item_payload),
        strategy_type=f"{_enum_value(library_payload.get('category') or 'seed')}::{item_type}",
        status=DistilledStrategyLifecycle.USER_REVIEWED,
        applicability_scope=_strategy_scope(library_payload, item_payload),
        contraindications=[f"avoid:{tag}" for tag in list(item_payload.get("tags") or [])[:3]],
        evidence_strength=_evidence_strength(library_payload, item_payload),
        diversity_score=_diversity_score(item_payload),
        safety_audit={
            "human_authored": True,
            "deidentified": True,
            "reviewed": True,
            "safe": True,
        },
        source_trajectory_type="human_authored",
        attribution_count=1,
        deidentification_verified=True,
        user_authorization=True,
        projection_policy=ProjectionPolicy.SENSITIVE_MEDIATED,
        shareability=Shareability.PUBLIC_SEED_CANDIDATE,
    )


def import_seed_library_content(
    libraries: Iterable[dict[str, Any] | SeedLibrary] | None = None,
    *,
    imported_at: datetime | None = None,
) -> list[DistilledStrategy]:
    """Import all seed-library items as DistilledStrategy records."""

    source_libraries = list(libraries or OFFICIAL_LIBRARIES)
    imported: list[DistilledStrategy] = []
    for library in source_libraries:
        library_payload = _coerce_library_payload(library)
        for item in list(library_payload.get("items") or []):
            imported.append(
                build_distilled_strategy_from_seed(
                    library=library_payload,
                    item=item,
                    imported_at=imported_at,
                )
            )
    return imported


def export_seed_bridge_fingerprint(strategies: Iterable[DistilledStrategy]) -> str:
    """Return a stable fingerprint for a batch of imported strategies."""

    payload = "|".join(
        f"{strategy.id}:{strategy.title}:{strategy.strategy_type}:{strategy.source_trajectory_type}"
        for strategy in strategies
    )
    return sha256(payload.encode("utf-8")).hexdigest()
