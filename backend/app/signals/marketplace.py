"""
Core: execution / research
Phase: adapt
Stage: P4-4 — Skill & DomainPack Marketplace v2

Research-grade knowledge asset marketplace with:
  1. SkillCard v2 — evidence-backed, effectiveness-tracked skill cards
  2. DomainPack v2 — community-contributed strategy packs with reviews
  3. 10 marketplace iron laws — quality floors, provenance, evidence
  4. Adoption tracking + effectiveness decay monitoring

Every listed asset must prove it works before it can be recommended.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.privacy import redact_pii_with_report
from app.models.marketplace import (
    MarketplacePack,
    MarketplaceSkill,
    PackAdoptionHistory,
    UserSkillAdoption,
)
from app.signals.types import SkillEntry


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. SkillCard v2
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SkillCard:
    """Research-grade skill card v2.

    Each card carries evidence of effectiveness, not just a description.
    Iron law: no skill can be recommended without at least Grade 2 evidence.
    """
    card_id: str = ""
    name: str = ""
    description: str = ""
    goal_type: str = ""                    # "exam" | "project" | "job_search" | "fitness" | ...
    domain: str = ""                       # "computer_science" | "mathematics" | ...
    author_id: str = ""
    version: int = 1

    # Core behavior
    trigger_condition: str = ""            # When this skill should be suggested
    action_template: str = ""              # What the AI should do/say
    expected_outcome: str = ""             # What should happen if it works
    prerequisites: list[str] = field(default_factory=list)  # Skill IDs that must be adopted first

    # Evidence
    evidence_grade: int = 0               # 0-5, minimum 2 to list
    evidence_summary: str = ""             # Human-readable summary of evidence
    episode_count: int = 0                 # How many episodes support this skill
    success_rate: float = 0.0             # Proportion of positive outcomes
    context_signatures: list[dict[str, Any]] = field(default_factory=list)

    # Marketplace
    status: str = "draft"                  # draft | under_review | active | deprecated | retired
    rating: float = 0.0                    # Average user rating (1-5)
    review_count: int = 0
    adoption_count: int = 0
    effectiveness_decay: float = 1.0       # 1.0 = fully effective, decays if success_rate drops
    last_validated_at: str = ""
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.card_id:
            self.card_id = _uid("sk")

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "goal_type": self.goal_type,
            "domain": self.domain,
            "author_id": self.author_id,
            "version": self.version,
            "trigger_condition": self.trigger_condition,
            "action_template": self.action_template,
            "expected_outcome": self.expected_outcome,
            "prerequisites": self.prerequisites,
            "evidence_grade": self.evidence_grade,
            "evidence_summary": self.evidence_summary,
            "episode_count": self.episode_count,
            "success_rate": self.success_rate,
            "context_signatures": self.context_signatures,
            "status": self.status,
            "rating": self.rating,
            "review_count": self.review_count,
            "adoption_count": self.adoption_count,
            "effectiveness_decay": self.effectiveness_decay,
            "last_validated_at": self.last_validated_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillCard:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════
# 1b. DomainPack v2
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DomainPack:
    """Versioned domain pack that can be previewed, adopted, and rolled back."""

    pack_id: str = ""
    name: str = ""
    description: str = ""
    domain: str = ""
    version: int = 1
    source: str = "system"
    status: str = "draft"
    node_schema: dict[str, Any] = field(default_factory=dict)
    task_templates: list[dict[str, Any]] = field(default_factory=list)
    risk_rules: list[dict[str, Any]] = field(default_factory=list)
    skill_ids: list[str] = field(default_factory=list)
    quality_evidence: dict[str, Any] = field(default_factory=dict)
    privacy_report: dict[str, Any] = field(default_factory=dict)
    governance: dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    adoption_count: int = 0
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.pack_id:
            self.pack_id = _uid("pack")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "version": self.version,
            "source": self.source,
            "status": self.status,
            "node_schema": self.node_schema,
            "task_templates": self.task_templates,
            "risk_rules": self.risk_rules,
            "skill_ids": self.skill_ids,
            "quality_evidence": self.quality_evidence,
            "privacy_report": self.privacy_report,
            "governance": self.governance,
            "quality_score": self.quality_score,
            "adoption_count": self.adoption_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DomainPack:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════
# 2. DomainPackReview
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DomainPackReview:
    """User-contributed review for a DomainPack or SkillCard."""
    review_id: str = ""
    asset_id: str = ""                     # The pack or card being reviewed
    user_id: str = ""
    rating: float = 0.0                    # 1-5
    title: str = ""
    body: str = ""
    used_in_production: bool = False       # Did the reviewer actually use it?
    outcome_summary: str = ""              # What happened when they used it
    helpfulness_votes: int = 0
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.review_id:
            self.review_id = _uid("rev")

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "asset_id": self.asset_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "used_in_production": self.used_in_production,
            "outcome_summary": self.outcome_summary,
            "helpfulness_votes": self.helpfulness_votes,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. Marketplace Iron Laws
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class IronLawViolation:
    law_id: str
    law_name: str
    description: str
    asset_id: str
    severity: str  # "blocking" | "warning"


class MarketplaceIronLaws:
    """Enforce 10 marketplace iron laws.

    Iron Laws:
      1. No listing without evidence (min Grade 2)
      2. No recommendation without adoption data (min 5 adoptions)
      3. Effectiveness must be periodically re-validated (max 90-day stale)
      4. Deprecated assets cannot be listed or recommended
      5. Provenance must be traceable (author_id required)
      6. Claims must be evidence-backed (no "revolutionary" without data)
      7. Rating manipulation prevention (min 3 reviews to show rating)
      8. Prerequisite skills must themselves be active
      9. Cross-domain claims need cross-domain evidence
      10. High-risk domains require safety review
    """

    LAW_MIN_EVIDENCE_GRADE = 2
    LAW_MIN_ADOPTIONS = 5
    LAW_MAX_STALE_DAYS = 90
    LAW_MIN_REVIEWS_FOR_RATING = 3
    LAW_HIGH_RISK_DOMAINS = {"mental_health", "finance", "legal", "medical"}

    @classmethod
    def validate_listing(cls, card: SkillCard) -> list[IronLawViolation]:
        """Check a skill card against all listing iron laws."""
        violations: list[IronLawViolation] = []

        # Law 1: Minimum evidence grade
        if card.evidence_grade < cls.LAW_MIN_EVIDENCE_GRADE:
            violations.append(IronLawViolation(
                law_id="ML-1", law_name="evidence_floor",
                description=f"Evidence grade {card.evidence_grade} < minimum {cls.LAW_MIN_EVIDENCE_GRADE}",
                asset_id=card.card_id, severity="blocking",
            ))

        # Law 2: Minimum adoptions for recommendation
        if card.adoption_count < cls.LAW_MIN_ADOPTIONS:
            violations.append(IronLawViolation(
                law_id="ML-2", law_name="adoption_floor",
                description=f"Adoption count {card.adoption_count} < minimum {cls.LAW_MIN_ADOPTIONS}",
                asset_id=card.card_id, severity="warning",
            ))

        # Law 3: Staleness check
        if card.last_validated_at:
            try:
                last = datetime.fromisoformat(card.last_validated_at.replace("Z", "+00:00"))
                days_stale = (datetime.now(UTC) - last).days
                if days_stale > cls.LAW_MAX_STALE_DAYS:
                    violations.append(IronLawViolation(
                        law_id="ML-3", law_name="staleness",
                        description=f"Last validated {days_stale} days ago > max {cls.LAW_MAX_STALE_DAYS}",
                        asset_id=card.card_id, severity="warning",
                    ))
            except (ValueError, TypeError):
                pass

        # Law 4: Deprecated/retired cannot list
        if card.status in ("deprecated", "retired"):
            violations.append(IronLawViolation(
                law_id="ML-4", law_name="no_deprecated_listing",
                description=f"Asset status '{card.status}' not allowed for listing",
                asset_id=card.card_id, severity="blocking",
            ))

        # Law 5: Provenance
        if not card.author_id:
            violations.append(IronLawViolation(
                law_id="ML-5", law_name="provenance_required",
                description="No author_id — provenance untraceable",
                asset_id=card.card_id, severity="blocking",
            ))

        # Law 6: Evidence-backed claims
        banned_claim_words = ["revolutionary", "guaranteed", "magic", "perfect", "foolproof"]
        for word in banned_claim_words:
            if word in card.description.lower() or word in card.expected_outcome.lower():
                violations.append(IronLawViolation(
                    law_id="ML-6", law_name="evidence_backed_claims",
                    description=f"Unsubstantiated claim word '{word}' without supporting evidence",
                    asset_id=card.card_id, severity="blocking",
                ))
                break

        # Law 7: Minimum reviews for rating display
        if card.rating > 0 and card.review_count < cls.LAW_MIN_REVIEWS_FOR_RATING:
            violations.append(IronLawViolation(
                law_id="ML-7", law_name="rating_integrity",
                description=f"Rating {card.rating} with only {card.review_count} reviews (min {cls.LAW_MIN_REVIEWS_FOR_RATING})",
                asset_id=card.card_id, severity="warning",
            ))

        # Law 10: High-risk domain safety review
        if card.domain in cls.LAW_HIGH_RISK_DOMAINS and card.status != "under_review":
            violations.append(IronLawViolation(
                law_id="ML-10", law_name="high_risk_safety_review",
                description=f"Domain '{card.domain}' requires safety review before listing",
                asset_id=card.card_id, severity="blocking",
            ))

        return violations

    @classmethod
    def is_listable(cls, card: SkillCard) -> dict[str, Any]:
        """Check if a skill card can be listed (no blocking violations)."""
        violations = cls.validate_listing(card)
        blocking = [v for v in violations if v.severity == "blocking"]
        warnings = [v for v in violations if v.severity == "warning"]
        return {
            "listable": len(blocking) == 0,
            "blocking_violations": [v.__dict__ for v in blocking],
            "warnings": [v.__dict__ for v in warnings],
            "total_violations": len(violations),
        }

    @classmethod
    def validate_prerequisites(cls, card: SkillCard, active_cards: dict[str, SkillCard]) -> list[IronLawViolation]:
        """Law 8: All prerequisite skills must be active."""
        violations: list[IronLawViolation] = []
        for prereq_id in card.prerequisites:
            prereq = active_cards.get(prereq_id)
            if prereq is None:
                violations.append(IronLawViolation(
                    law_id="ML-8", law_name="prerequisite_exists",
                    description=f"Prerequisite skill '{prereq_id}' not found",
                    asset_id=card.card_id, severity="blocking",
                ))
            elif prereq.status not in ("active",):
                violations.append(IronLawViolation(
                    law_id="ML-8", law_name="prerequisite_active",
                    description=f"Prerequisite skill '{prereq_id}' is '{prereq.status}', not active",
                    asset_id=card.card_id, severity="blocking",
                ))
        return violations

    @classmethod
    def validate_cross_domain_evidence(
        cls, card: SkillCard, contexts: list[dict[str, Any]],
    ) -> list[IronLawViolation]:
        """Law 9: Cross-domain claims need cross-domain evidence."""
        violations: list[IronLawViolation] = []
        unique_domains = {ctx.get("domain", "") for ctx in contexts if ctx.get("domain")}
        if card.domain and len(unique_domains) > 1:
            # Card claims a specific domain but has evidence from multiple
            if card.domain not in unique_domains:
                violations.append(IronLawViolation(
                    law_id="ML-9", law_name="cross_domain_evidence",
                    description=f"Card domain '{card.domain}' but evidence from {unique_domains}",
                    asset_id=card.card_id, severity="warning",
                ))
        return violations


# ═══════════════════════════════════════════════════════════════════════
# 4. Marketplace Registry
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AdoptionRecord:
    """Record of a user adopting a marketplace asset."""
    record_id: str = ""
    user_id: str = ""
    asset_id: str = ""
    asset_type: str = ""                   # "skill_card" | "domain_pack"
    context_signature: dict[str, Any] = field(default_factory=dict)
    outcome: str = "pending"               # "pending" | "success" | "failure" | "abandoned"
    outcome_detail: str = ""
    adopted_at: str = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.record_id:
            self.record_id = _uid("adopt")


class MarketplaceRegistry:
    """Manage marketplace listings, reviews, adoptions, and effectiveness tracking."""

    def __init__(self):
        self._cards: dict[str, SkillCard] = {}
        self._reviews: dict[str, list[DomainPackReview]] = {}  # asset_id → reviews
        self._adoptions: dict[str, list[AdoptionRecord]] = {}  # asset_id → records

    # ── Card management ──

    def register_card(self, card: SkillCard) -> dict[str, Any]:
        """Register a skill card in the marketplace. Validates iron laws first."""
        check = MarketplaceIronLaws.is_listable(card)
        if not check["listable"]:
            return {"registered": False, "reason": "iron_law_violations", **check}

        self._cards[card.card_id] = card
        return {"registered": True, "card_id": card.card_id}

    def get_card(self, card_id: str) -> SkillCard | None:
        return self._cards.get(card_id)

    def list_cards(
        self,
        *,
        goal_type: str | None = None,
        domain: str | None = None,
        min_evidence_grade: int = 0,
        include_drafts: bool = False,
    ) -> list[SkillCard]:
        """List cards with optional filters. Only active cards by default."""
        cards = list(self._cards.values())
        if not include_drafts:
            cards = [c for c in cards if c.status == "active"]
        if goal_type:
            cards = [c for c in cards if c.goal_type == goal_type]
        if domain:
            cards = [c for c in cards if c.domain == domain]
        if min_evidence_grade:
            cards = [c for c in cards if c.evidence_grade >= min_evidence_grade]
        return cards

    def list_recommendable(
        self,
        *,
        goal_type: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """List cards that pass all iron laws for recommendation."""
        cards = self.list_cards(goal_type=goal_type, domain=domain)
        results = []
        for card in cards:
            check = MarketplaceIronLaws.is_listable(card)
            prereq_check = MarketplaceIronLaws.validate_prerequisites(card, self._cards)
            all_ok = check["listable"] and len(prereq_check) == 0
            results.append({
                "card": card.to_dict(),
                "recommendable": all_ok,
                "iron_law_check": check,
                "prerequisite_check": [v.__dict__ for v in prereq_check],
            })
        return sorted(
            results,
            key=lambda r: (
                r["recommendable"],
                r["card"]["evidence_grade"],
                r["card"]["success_rate"],
                r["card"]["rating"],
            ),
            reverse=True,
        )

    def update_effectiveness(self, card_id: str, new_success_rate: float) -> dict[str, Any]:
        """Update a card's effectiveness tracking. Triggers decay calculation."""
        card = self._cards.get(card_id)
        if not card:
            return {"updated": False, "reason": "not_found"}

        old_rate = card.success_rate
        card.success_rate = new_success_rate
        card.last_validated_at = _utcnow()

        # Decay: if success drops >20% from peak, decay factor decreases
        if new_success_rate < old_rate * 0.8:
            card.effectiveness_decay = round(max(0.1, card.effectiveness_decay - 0.2), 2)
            if card.effectiveness_decay < 0.5:
                card.status = "under_review"

        return {
            "updated": True,
            "card_id": card_id,
            "old_rate": old_rate,
            "new_rate": new_success_rate,
            "effectiveness_decay": card.effectiveness_decay,
            "status": card.status,
        }

    # ── Review management ──

    def add_review(self, review: DomainPackReview) -> dict[str, Any]:
        """Add a review and recalculate the asset's rating."""
        if review.asset_id not in self._reviews:
            self._reviews[review.asset_id] = []

        # Check for duplicate review by same user
        existing = [r for r in self._reviews[review.asset_id] if r.user_id == review.user_id]
        if existing:
            return {"added": False, "reason": "duplicate_user"}

        self._reviews[review.asset_id].append(review)

        # Recalculate rating for the card
        card = self._cards.get(review.asset_id)
        if card:
            card.review_count = len(self._reviews[review.asset_id])
            card.rating = round(
                sum(r.rating for r in self._reviews[review.asset_id]) / card.review_count, 2,
            )

        return {"added": True, "review_id": review.review_id}

    def get_reviews(self, asset_id: str) -> list[DomainPackReview]:
        return self._reviews.get(asset_id, [])

    def get_review_summary(self, asset_id: str) -> dict[str, Any]:
        """Aggregated review summary for an asset."""
        reviews = self._reviews.get(asset_id, [])
        if not reviews:
            return {"asset_id": asset_id, "review_count": 0, "rating": None}

        production_reviews = [r for r in reviews if r.used_in_production]
        return {
            "asset_id": asset_id,
            "review_count": len(reviews),
            "rating": round(sum(r.rating for r in reviews) / len(reviews), 2),
            "production_review_count": len(production_reviews),
            "production_rating": (
                round(sum(r.rating for r in production_reviews) / len(production_reviews), 2)
                if production_reviews else None
            ),
            "helpfulness_total": sum(r.helpfulness_votes for r in reviews),
            "rating_display_allowed": len(reviews) >= MarketplaceIronLaws.LAW_MIN_REVIEWS_FOR_RATING,
        }

    # ── Adoption tracking ──

    def record_adoption(
        self, user_id: str, asset_id: str, asset_type: str,
        context_signature: dict[str, Any] | None = None,
    ) -> AdoptionRecord:
        """Record an adoption event."""
        record = AdoptionRecord(
            user_id=user_id, asset_id=asset_id, asset_type=asset_type,
            context_signature=context_signature or {},
        )
        if asset_id not in self._adoptions:
            self._adoptions[asset_id] = []
        self._adoptions[asset_id].append(record)

        # Update card adoption count
        card = self._cards.get(asset_id)
        if card:
            card.adoption_count = len(self._adoptions[asset_id])

        return record

    def record_adoption_outcome(
        self, record_id: str, outcome: str, outcome_detail: str = "",
    ) -> dict[str, Any]:
        """Record the outcome of an adoption."""
        for records in self._adoptions.values():
            for rec in records:
                if rec.record_id == record_id:
                    rec.outcome = outcome
                    rec.outcome_detail = outcome_detail
                    return {"updated": True, "record_id": record_id}
        return {"updated": False, "reason": "not_found"}

    def get_adoption_stats(self, asset_id: str) -> dict[str, Any]:
        """Adoption statistics for an asset."""
        records = self._adoptions.get(asset_id, [])
        if not records:
            return {"asset_id": asset_id, "total_adoptions": 0}

        successful = sum(1 for r in records if r.outcome == "success")
        failed = sum(1 for r in records if r.outcome == "failure")
        abandoned = sum(1 for r in records if r.outcome == "abandoned")
        return {
            "asset_id": asset_id,
            "total_adoptions": len(records),
            "successful": successful,
            "failed": failed,
            "abandoned": abandoned,
            "success_rate": round(successful / max(len(records), 1), 3),
            "recent_adoptions": len([r for r in records
                if (datetime.now(UTC) - datetime.fromisoformat(
                    r.adopted_at.replace("Z", "+00:00"))).days < 30]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cards": len(self._cards),
            "active_cards": sum(1 for c in self._cards.values() if c.status == "active"),
            "total_reviews": sum(len(r) for r in self._reviews.values()),
            "total_adoptions": sum(len(a) for a in self._adoptions.values()),
            "cards": [c.to_dict() for c in self._cards.values()],
        }


# ═══════════════════════════════════════════════════════════════════════
# 5. Production persistence and governance helpers
# ═══════════════════════════════════════════════════════════════════════


NEGATIVE_FEEDBACK_DEPRECATION_THRESHOLD = 0.30
REVOKE_RATE_DEPRECATION_THRESHOLD = 0.50
MIN_SYSTEM_SKILL_EVIDENCE_GRADE = 2


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _asset_text_payload(asset: SkillCard | DomainPack) -> str:
    if isinstance(asset, SkillCard):
        pieces: list[Any] = [
            asset.name,
            asset.description,
            asset.trigger_condition,
            asset.action_template,
            asset.expected_outcome,
            asset.evidence_summary,
            asset.context_signatures,
        ]
    else:
        pieces = [
            asset.name,
            asset.description,
            asset.node_schema,
            asset.task_templates,
            asset.risk_rules,
            asset.quality_evidence,
        ]
    return "\n".join(str(piece) for piece in pieces if piece)


def scan_marketplace_asset_privacy(asset: SkillCard | DomainPack) -> dict[str, Any]:
    """Return a privacy report; assets with detected PII must not be listed."""

    report = redact_pii_with_report(_asset_text_payload(asset))
    return {
        "passed": not report.redacted,
        "redacted": report.redacted,
        "categories": list(report.categories),
        "mode": report.mode,
        "source_sha256": report.source_sha256,
    }


def compute_marketplace_quality_score(
    *,
    success_rate: float,
    evidence_grade: int,
    negative_feedback_rate: float,
    applicability_score: float,
    revoke_rate: float = 0.0,
) -> float:
    """Outcome-weighted quality score. Adoption/download volume is intentionally excluded."""

    evidence_component = _clamp(float(evidence_grade) / 5.0)
    score = (
        _clamp(success_rate) * 0.50
        + evidence_component * 0.22
        + _clamp(applicability_score) * 0.18
        + (1.0 - _clamp(negative_feedback_rate)) * 0.07
        + (1.0 - _clamp(revoke_rate)) * 0.03
    )
    return round(score, 3)


def deprecation_reason(
    *,
    negative_feedback_rate: float,
    revoke_rate: float,
    privacy_report: dict[str, Any],
) -> str | None:
    if privacy_report and privacy_report.get("passed") is False:
        return "privacy_alert"
    if negative_feedback_rate > NEGATIVE_FEEDBACK_DEPRECATION_THRESHOLD:
        return "negative_feedback_rate"
    if revoke_rate > REVOKE_RATE_DEPRECATION_THRESHOLD:
        return "user_revoke_rate"
    return None


def skill_card_from_entry(skill: SkillEntry, *, author_id: str | None = None) -> SkillCard:
    """Convert a promoted system SkillEntry into a marketplace SkillCard."""

    evidence = skill.evidence or {}
    strategy = skill.strategy or {}
    applicable_when = skill.applicable_when or {}
    sample_size = max(int(skill.sample_size or 0), int(skill.effective_count or 0), 1)
    success_rate = _clamp(float(skill.effective_count or 0) / sample_size)
    evidence_grade = int(evidence.get("evidence_grade", MIN_SYSTEM_SKILL_EVIDENCE_GRADE))
    context_signatures = evidence.get("context_signatures") or [applicable_when]
    if not isinstance(context_signatures, list):
        context_signatures = [context_signatures]

    return SkillCard(
        card_id=skill.skill_id if skill.skill_id.startswith("sk") else _uid("sk"),
        name=str(strategy.get("name") or strategy.get("title") or skill.source_policy_key or "System skill"),
        description=str(strategy.get("description") or strategy.get("intervention_summary") or ""),
        goal_type=str(applicable_when.get("goal_type") or applicable_when.get("mode") or ""),
        domain=str(applicable_when.get("domain") or applicable_when.get("subject") or ""),
        author_id=str(author_id or ""),
        version=int(evidence.get("version", 1) or 1),
        trigger_condition=str(applicable_when.get("state_key") or applicable_when.get("trigger") or ""),
        action_template=str(strategy.get("action_template") or strategy.get("intervention_summary") or ""),
        expected_outcome=str(strategy.get("expected_outcome") or evidence.get("expected_outcome") or "effective"),
        prerequisites=list(strategy.get("prerequisites") or []),
        evidence_grade=evidence_grade,
        evidence_summary=str(evidence.get("summary") or evidence.get("evidence_summary") or ""),
        episode_count=sample_size,
        success_rate=success_rate,
        context_signatures=context_signatures,
        status="active" if evidence_grade >= MIN_SYSTEM_SKILL_EVIDENCE_GRADE else "under_review",
        effectiveness_decay=1.0,
        last_validated_at=str(evidence.get("last_validated_at") or _utcnow()),
    )


class MarketplacePersistenceService:
    """DB-backed marketplace operations used by API and lifecycle promotion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_skills(
        self,
        *,
        domain: str | None = None,
        goal_type: str | None = None,
        include_deprecated: bool = False,
    ) -> list[MarketplaceSkill]:
        stmt = select(MarketplaceSkill).where(MarketplaceSkill.deleted_at.is_(None))
        if not include_deprecated:
            stmt = stmt.where(MarketplaceSkill.status == "active")
        if domain:
            stmt = stmt.where(MarketplaceSkill.domain == domain)
        if goal_type:
            stmt = stmt.where(MarketplaceSkill.goal_type == goal_type)
        stmt = stmt.order_by(MarketplaceSkill.quality_score.desc(), MarketplaceSkill.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_packs(
        self,
        *,
        domain: str | None = None,
        include_deprecated: bool = False,
    ) -> list[MarketplacePack]:
        stmt = select(MarketplacePack).where(MarketplacePack.deleted_at.is_(None))
        if not include_deprecated:
            stmt = stmt.where(MarketplacePack.status == "active")
        if domain:
            stmt = stmt.where(MarketplacePack.domain == domain)
        stmt = stmt.order_by(MarketplacePack.quality_score.desc(), MarketplacePack.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_skill(self, skill_id: str) -> MarketplaceSkill | None:
        result = await self.db.execute(
            select(MarketplaceSkill).where(
                MarketplaceSkill.skill_id == skill_id,
                MarketplaceSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_pack(self, pack_id: str) -> MarketplacePack | None:
        result = await self.db.execute(
            select(MarketplacePack).where(
                MarketplacePack.pack_id == pack_id,
                MarketplacePack.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def register_skill_card(
        self,
        card: SkillCard,
        *,
        source_skill_id: str | None = None,
        contraindications: list[str] | None = None,
        governance: dict[str, Any] | None = None,
    ) -> MarketplaceSkill:
        privacy_report = scan_marketplace_asset_privacy(card)
        if not privacy_report["passed"]:
            raise ValueError(f"pii_detected:{','.join(privacy_report['categories'])}")

        listing_check = MarketplaceIronLaws.is_listable(card)
        if not listing_check["listable"]:
            raise ValueError("iron_law_violations")

        quality_score = compute_marketplace_quality_score(
            success_rate=card.success_rate,
            evidence_grade=card.evidence_grade,
            negative_feedback_rate=0.0,
            applicability_score=self._applicability_score(card.context_signatures),
        )
        existing = await self.get_skill(card.card_id)
        if existing:
            existing.previous_versions = [
                *(existing.previous_versions or []),
                self.serialize_skill(existing),
            ]
            existing.version = card.version
            existing.name = card.name
            existing.description = card.description
            existing.goal_type = card.goal_type
            existing.domain = card.domain
            existing.status = card.status
            existing.trigger_condition = card.trigger_condition
            existing.action_template = card.action_template
            existing.expected_outcome = card.expected_outcome
            existing.prerequisites = card.prerequisites
            existing.contraindications = contraindications or []
            existing.evidence_grade = card.evidence_grade
            existing.evidence_summary = card.evidence_summary
            existing.episode_count = card.episode_count
            existing.success_rate = card.success_rate
            existing.context_signatures = card.context_signatures
            existing.quality_score = quality_score
            existing.privacy_report = privacy_report
            existing.governance = governance or {"registered_by": "skill_lifecycle", "iron_law_check": listing_check}
            existing.listed_at = existing.listed_at or datetime.now(UTC).replace(tzinfo=None)
            await self.db.flush()
            return existing

        record = MarketplaceSkill(
            skill_id=card.card_id,
            source_skill_id=source_skill_id,
            name=card.name,
            description=card.description,
            goal_type=card.goal_type,
            domain=card.domain,
            author_id=card.author_id or None,
            version=card.version,
            status=card.status,
            trigger_condition=card.trigger_condition,
            action_template=card.action_template,
            expected_outcome=card.expected_outcome,
            prerequisites=card.prerequisites,
            contraindications=contraindications or [],
            context_signatures=card.context_signatures,
            evidence_grade=card.evidence_grade,
            evidence_summary=card.evidence_summary,
            episode_count=card.episode_count,
            success_rate=card.success_rate,
            quality_score=quality_score,
            privacy_report=privacy_report,
            governance=governance or {"registered_by": "skill_lifecycle", "iron_law_check": listing_check},
            listed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def register_system_skill(
        self,
        skill: SkillEntry,
        *,
        user_id: str | None = None,
    ) -> MarketplaceSkill:
        if skill.scope != "system":
            raise ValueError("only_system_skill_can_be_listed")
        if skill.privacy and skill.privacy.get("contains_personal_data"):
            raise ValueError("personal_data_skill_cannot_be_listed")
        card = skill_card_from_entry(skill, author_id=user_id)
        return await self.register_skill_card(
            card,
            source_skill_id=skill.skill_id,
            contraindications=skill.contraindications,
            governance={
                "registered_by": "skill_lifecycle",
                "promotion_history": (skill.evidence or {}).get("promotion_history", []),
                "requires_approval": card.domain in MarketplaceIronLaws.LAW_HIGH_RISK_DOMAINS,
            },
        )

    async def adopt_asset(
        self,
        *,
        user_id: Any,
        asset_id: str,
        asset_type: str,
        confirm: bool,
        context_signature: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> UserSkillAdoption:
        if not confirm:
            raise ValueError("explicit_confirmation_required")
        asset = await self._get_asset(asset_type, asset_id)
        if asset is None or asset.status != "active":
            raise ValueError("asset_not_available")

        existing = await self._get_adoption(user_id=user_id, asset_type=asset_type, asset_id=asset_id)
        if existing:
            existing.status = "active"
            existing.revoked_at = None
            existing.revoked_reason = None
            existing.explicit_confirm = True
            existing.context_signature = context_signature or {}
            existing.preview_snapshot = self.preview_asset(asset)
            existing.trace_id = trace_id
            await self.db.flush()
            await self._refresh_asset_adoption_stats(asset_type, asset_id)
            return existing

        adoption = UserSkillAdoption(
            user_id=user_id,
            asset_id=asset_id,
            asset_type=asset_type,
            asset_version=int(asset.version),
            status="active",
            explicit_confirm=True,
            context_signature=context_signature or {},
            preview_snapshot=self.preview_asset(asset),
            trace_id=trace_id,
        )
        self.db.add(adoption)
        await self.db.flush()
        await self._refresh_asset_adoption_stats(asset_type, asset_id)
        return adoption

    async def revoke_adoption(self, *, user_id: Any, adoption_id: Any, reason: str = "") -> UserSkillAdoption:
        result = await self.db.execute(
            select(UserSkillAdoption).where(
                UserSkillAdoption.id == adoption_id,
                UserSkillAdoption.user_id == user_id,
                UserSkillAdoption.deleted_at.is_(None),
            )
        )
        adoption = result.scalar_one_or_none()
        if adoption is None:
            raise ValueError("adoption_not_found")
        adoption.status = "revoked"
        adoption.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        adoption.revoked_reason = reason[:256] if reason else None
        await self.db.flush()
        await self._refresh_asset_adoption_stats(adoption.asset_type, adoption.asset_id)
        return adoption

    async def record_impact(
        self,
        *,
        user_id: Any,
        adoption_id: Any,
        trace_id: str,
        impact_type: str,
        impact_summary: str,
        target_id: str | None = None,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
        outcome: str = "pending",
        metadata: dict[str, Any] | None = None,
    ) -> PackAdoptionHistory:
        result = await self.db.execute(
            select(UserSkillAdoption).where(
                UserSkillAdoption.id == adoption_id,
                UserSkillAdoption.user_id == user_id,
                UserSkillAdoption.deleted_at.is_(None),
            )
        )
        adoption = result.scalar_one_or_none()
        if adoption is None:
            raise ValueError("adoption_not_found")

        history = PackAdoptionHistory(
            adoption_id=adoption.id,
            user_id=user_id,
            asset_id=adoption.asset_id,
            asset_type=adoption.asset_type,
            trace_id=trace_id,
            impact_type=impact_type,
            impact_summary=impact_summary,
            target_id=target_id,
            before_snapshot=before_snapshot or {},
            after_snapshot=after_snapshot or {},
            outcome=outcome,
            metadata_json=metadata or {},
        )
        self.db.add(history)
        await self.db.flush()
        await self._refresh_asset_adoption_stats(adoption.asset_type, adoption.asset_id)
        return history

    async def rollback_skill(self, skill_id: str) -> MarketplaceSkill:
        skill = await self.get_skill(skill_id)
        if skill is None:
            raise ValueError("skill_not_found")
        versions = list(skill.previous_versions or [])
        if not versions:
            raise ValueError("no_previous_version")
        previous = versions.pop()
        skill.previous_versions = versions
        for key in (
            "name",
            "description",
            "goal_type",
            "domain",
            "version",
            "status",
            "trigger_condition",
            "action_template",
            "expected_outcome",
            "prerequisites",
            "contraindications",
            "context_signatures",
            "evidence_grade",
            "evidence_summary",
            "episode_count",
            "success_rate",
            "quality_score",
            "privacy_report",
            "governance",
        ):
            if key in previous:
                setattr(skill, key, previous[key])
        await self.db.flush()
        return skill

    async def rollback_pack(self, pack_id: str) -> MarketplacePack:
        pack = await self.get_pack(pack_id)
        if pack is None:
            raise ValueError("pack_not_found")
        versions = list(pack.previous_versions or [])
        if not versions:
            raise ValueError("no_previous_version")
        previous = versions.pop()
        pack.previous_versions = versions
        for key in (
            "name",
            "description",
            "domain",
            "version",
            "source",
            "status",
            "node_schema",
            "task_templates",
            "risk_rules",
            "skill_ids",
            "quality_evidence",
            "quality_score",
            "privacy_report",
            "governance",
        ):
            if key in previous:
                setattr(pack, key, previous[key])
        await self.db.flush()
        return pack

    def preview_asset(self, asset: MarketplaceSkill | MarketplacePack) -> dict[str, Any]:
        if isinstance(asset, MarketplaceSkill):
            return {
                "asset_id": asset.skill_id,
                "asset_type": "skill",
                "version": asset.version,
                "will_affect": ["task", "plan", "source", "recall"],
                "trigger_condition": asset.trigger_condition,
                "expected_outcome": asset.expected_outcome,
                "contraindications": asset.contraindications or [],
                "evidence": {
                    "grade": asset.evidence_grade,
                    "summary": asset.evidence_summary,
                    "episode_count": asset.episode_count,
                    "success_rate": asset.success_rate,
                },
                "quality_score": asset.quality_score,
                "privacy": asset.privacy_report,
                "requires_explicit_confirm": True,
                "trace_policy": "every task/plan/source impact must write pack_adoption_history.trace_id",
            }
        return {
            "asset_id": asset.pack_id,
            "asset_type": "pack",
            "version": asset.version,
            "will_affect": ["goal_graph", "task_templates", "risk_rules", "skills"],
            "node_schema": asset.node_schema,
            "task_template_count": len(asset.task_templates or []),
            "risk_rule_count": len(asset.risk_rules or []),
            "skill_ids": asset.skill_ids or [],
            "quality_evidence": asset.quality_evidence,
            "quality_score": asset.quality_score,
            "privacy": asset.privacy_report,
            "requires_explicit_confirm": True,
            "trace_policy": "every task/plan/source impact must write pack_adoption_history.trace_id",
        }

    @staticmethod
    def serialize_skill(skill: MarketplaceSkill) -> dict[str, Any]:
        return {
            "skill_id": skill.skill_id,
            "source_skill_id": skill.source_skill_id,
            "name": skill.name,
            "description": skill.description,
            "goal_type": skill.goal_type,
            "domain": skill.domain,
            "version": skill.version,
            "status": skill.status,
            "trigger_condition": skill.trigger_condition,
            "action_template": skill.action_template,
            "expected_outcome": skill.expected_outcome,
            "prerequisites": skill.prerequisites or [],
            "contraindications": skill.contraindications or [],
            "context_signatures": skill.context_signatures or [],
            "evidence_grade": skill.evidence_grade,
            "evidence_summary": skill.evidence_summary,
            "episode_count": skill.episode_count,
            "success_rate": skill.success_rate,
            "quality_score": skill.quality_score,
            "negative_feedback_rate": skill.negative_feedback_rate,
            "revoke_rate": skill.revoke_rate,
            "adoption_count": skill.adoption_count,
            "privacy_report": skill.privacy_report or {},
            "governance": skill.governance or {},
            "created_at": _json_safe(skill.created_at),
            "updated_at": _json_safe(skill.updated_at),
        }

    @staticmethod
    def serialize_pack(pack: MarketplacePack) -> dict[str, Any]:
        return {
            "pack_id": pack.pack_id,
            "name": pack.name,
            "description": pack.description,
            "domain": pack.domain,
            "version": pack.version,
            "source": pack.source,
            "status": pack.status,
            "node_schema": pack.node_schema or {},
            "task_templates": pack.task_templates or [],
            "risk_rules": pack.risk_rules or [],
            "skill_ids": pack.skill_ids or [],
            "quality_evidence": pack.quality_evidence or {},
            "quality_score": pack.quality_score,
            "negative_feedback_rate": pack.negative_feedback_rate,
            "revoke_rate": pack.revoke_rate,
            "adoption_count": pack.adoption_count,
            "privacy_report": pack.privacy_report or {},
            "governance": pack.governance or {},
            "created_at": _json_safe(pack.created_at),
            "updated_at": _json_safe(pack.updated_at),
        }

    @staticmethod
    def serialize_adoption(adoption: UserSkillAdoption) -> dict[str, Any]:
        return {
            "id": str(adoption.id),
            "user_id": str(adoption.user_id),
            "asset_id": adoption.asset_id,
            "asset_type": adoption.asset_type,
            "asset_version": adoption.asset_version,
            "status": adoption.status,
            "explicit_confirm": adoption.explicit_confirm,
            "context_signature": adoption.context_signature or {},
            "preview_snapshot": adoption.preview_snapshot or {},
            "trace_id": adoption.trace_id,
            "revoked_at": _json_safe(adoption.revoked_at),
            "created_at": _json_safe(adoption.created_at),
            "updated_at": _json_safe(adoption.updated_at),
        }

    @staticmethod
    def serialize_history(history: PackAdoptionHistory) -> dict[str, Any]:
        return {
            "id": str(history.id),
            "adoption_id": str(history.adoption_id),
            "asset_id": history.asset_id,
            "asset_type": history.asset_type,
            "trace_id": history.trace_id,
            "impact_type": history.impact_type,
            "impact_summary": history.impact_summary,
            "target_id": history.target_id,
            "before_snapshot": history.before_snapshot or {},
            "after_snapshot": history.after_snapshot or {},
            "outcome": history.outcome,
            "metadata": history.metadata_json or {},
            "created_at": _json_safe(history.created_at),
        }

    async def _get_asset(self, asset_type: str, asset_id: str) -> MarketplaceSkill | MarketplacePack | None:
        if asset_type == "skill":
            return await self.get_skill(asset_id)
        if asset_type == "pack":
            return await self.get_pack(asset_id)
        raise ValueError("invalid_asset_type")

    async def _get_adoption(self, *, user_id: Any, asset_type: str, asset_id: str) -> UserSkillAdoption | None:
        result = await self.db.execute(
            select(UserSkillAdoption).where(
                UserSkillAdoption.user_id == user_id,
                UserSkillAdoption.asset_type == asset_type,
                UserSkillAdoption.asset_id == asset_id,
                UserSkillAdoption.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _refresh_asset_adoption_stats(self, asset_type: str, asset_id: str) -> None:
        asset = await self._get_asset(asset_type, asset_id)
        if asset is None:
            return

        adoption_counts = await self.db.execute(
            select(
                func.count(UserSkillAdoption.id),
                func.sum((UserSkillAdoption.status == "revoked").cast(Integer)),
            ).where(
                UserSkillAdoption.asset_type == asset_type,
                UserSkillAdoption.asset_id == asset_id,
                UserSkillAdoption.deleted_at.is_(None),
            )
        )
        total, revoked = adoption_counts.one()
        total_count = int(total or 0)
        revoked_count = int(revoked or 0)
        asset.adoption_count = total_count
        asset.revoke_rate = round(revoked_count / max(total_count, 1), 3)

        impact_counts = await self.db.execute(
            select(
                func.count(PackAdoptionHistory.id),
                func.sum((PackAdoptionHistory.outcome.in_(["negative", "failure", "harmful"])).cast(Integer)),
                func.sum((PackAdoptionHistory.outcome.in_(["success", "effective"])).cast(Integer)),
            ).where(
                PackAdoptionHistory.asset_type == asset_type,
                PackAdoptionHistory.asset_id == asset_id,
                PackAdoptionHistory.deleted_at.is_(None),
            )
        )
        impact_total, negative, positive = impact_counts.one()
        impact_total_count = int(impact_total or 0)
        negative_count = int(negative or 0)
        positive_count = int(positive or 0)
        asset.negative_feedback_rate = round(negative_count / max(impact_total_count, 1), 3)
        if impact_total_count:
            success_rate = positive_count / max(impact_total_count, 1)
        else:
            success_rate = float(getattr(asset, "success_rate", 0.0) or 0.0)
        if isinstance(asset, MarketplaceSkill):
            asset.success_rate = round(success_rate, 3)
            evidence_grade = int(asset.evidence_grade or 0)
            applicability_score = self._applicability_score(asset.context_signatures or [])
        else:
            evidence_grade = int((asset.quality_evidence or {}).get("evidence_grade", 0))
            applicability_score = self._applicability_score(asset.task_templates or [])

        asset.quality_score = compute_marketplace_quality_score(
            success_rate=success_rate,
            evidence_grade=evidence_grade,
            negative_feedback_rate=asset.negative_feedback_rate,
            applicability_score=applicability_score,
            revoke_rate=asset.revoke_rate,
        )
        reason = deprecation_reason(
            negative_feedback_rate=asset.negative_feedback_rate,
            revoke_rate=asset.revoke_rate,
            privacy_report=asset.privacy_report or {},
        )
        if reason and asset.status == "active":
            asset.status = "deprecated"
            asset.auto_deprecation_reason = reason
            asset.deprecated_at = datetime.now(UTC).replace(tzinfo=None)
            try:
                from app.core.metrics import MARKETPLACE_AUTO_DEPRECATIONS_TOTAL

                MARKETPLACE_AUTO_DEPRECATIONS_TOTAL.labels(asset_type=asset_type, reason=reason).inc()
            except Exception:
                pass
        try:
            from app.core.metrics import MARKETPLACE_QUALITY_SCORE

            MARKETPLACE_QUALITY_SCORE.labels(
                asset_type=asset_type,
                domain=str(getattr(asset, "domain", "") or "unknown"),
                status=str(getattr(asset, "status", "") or "unknown"),
            ).set(asset.quality_score)
        except Exception:
            pass
        await self.db.flush()

    @staticmethod
    def _applicability_score(scopes: Any) -> float:
        if isinstance(scopes, dict):
            return 0.75 if scopes else 0.35
        if isinstance(scopes, list):
            return _clamp(0.35 + min(len(scopes), 5) * 0.1)
        return 0.35
