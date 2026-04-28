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
from datetime import datetime, timezone
from typing import Any


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                days_stale = (datetime.now(timezone.utc) - last).days
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
                if (datetime.now(timezone.utc) - datetime.fromisoformat(
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
