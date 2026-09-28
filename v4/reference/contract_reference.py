"""Offline semantic reference, not Sparkle production code or an ML utility model.
No network, database, model, audio or haptic calls are made.
The caller provides trusted receipt snapshots; real authentication is out of scope.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class Candidate:
    ref: str
    owner: str
    goal: str | None
    task_type: str | None
    relevance: float
    decision_relevance: float
    negative_transfer: float = 0.0
    conflict: bool = False
    confirmed: bool = False
    revoked: bool = False
    source_alive: bool = True
    global_consent: bool = False
    source_kind: str = 'explicit_user'
    tokens: int = 100
    expires_at: datetime | None = None

@dataclass(frozen=True)
class Context:
    owner: str
    goal: str
    task_type: str
    now: datetime
    token_budget: int = 600
    top_k: int = 6


def select_optional(candidates: Sequence[Candidate], context: Context) -> tuple[list[str], dict[str, str]]:
    """Demonstrates hard filtering before illustrative utility ranking.
    Current constraints are NOT optional candidates and must be supplied separately.
    Scores are not probabilities. Constants are uncalibrated demonstration values.
    """
    if context.now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    if context.token_budget < 0 or context.top_k < 0:
        raise ValueError('negative budget')
    rejected: dict[str,str] = {}; eligible=[]; ids=set()
    for c in candidates:
        if not c.ref or c.ref in ids:
            raise ValueError('empty or duplicate reference')
        ids.add(c.ref)
        for v in (c.relevance,c.decision_relevance,c.negative_transfer):
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError('scores must be finite within [0,1]')
        if c.tokens <= 0:
            raise ValueError('tokens must be positive')
        if c.expires_at is not None and c.expires_at.tzinfo is None:
            raise ValueError('expiry must be timezone-aware')
        reason=None
        if c.owner != context.owner: reason='owner'
        elif c.revoked or not c.source_alive: reason='source_invalid'
        elif c.expires_at is not None and c.expires_at <= context.now: reason='expired'
        elif c.source_kind == 'external_material': reason='external_not_user_memory'
        elif c.source_kind not in {'explicit_user','observed','inferred'}: reason='unknown_source_kind'
        elif c.goal is None and not c.global_consent: reason='global_not_consented'
        elif c.goal is not None and c.goal != context.goal: reason='scope'
        elif c.task_type is not None and c.task_type != context.task_type: reason='task_type'
        elif c.conflict: reason='conflict_requires_resolution'
        if reason:
            rejected[c.ref]=reason; continue
        score=(c.relevance+c.decision_relevance+0.2*int(c.confirmed)
               -1.5*c.negative_transfer-0.0001*c.tokens)
        if score <= 0.5:
            rejected[c.ref]='low_expected_utility'; continue
        eligible.append((score,c.ref,c))
    chosen=[]; remaining=context.token_budget
    for _,ref,c in sorted(eligible,key=lambda x:(-x[0],x[1])):
        if len(chosen)>=context.top_k: rejected[ref]='top_k'
        elif c.tokens>remaining: rejected[ref]='budget'
        else: chosen.append(ref);remaining-=c.tokens
    return chosen,rejected

@dataclass(frozen=True)
class Receipt:
    ref: str
    owner: str
    object_ref: str
    version: int
    status: str

@dataclass(frozen=True)
class PresentationEvent:
    event_id: str
    owner: str
    object_ref: str
    version: int
    kind: str
    receipt_ref: str | None = None
    replay: bool = False

@dataclass(frozen=True)
class Preferences:
    audio: bool = False
    haptic: bool = False
    reduced_motion: bool = False
    foreground: bool = True
    haptic_supported: bool = True

class FeedbackPolicy:
    """In-memory example only. Product dedupe belongs to existing persisted runtime."""
    def __init__(self) -> None:
        self.seen: set[tuple[str,str,str]] = set()

    def project(self, event: PresentationEvent, receipts: Mapping[str,Receipt], pref: Preferences) -> dict:
        if event.kind not in {'action_committed','proposal','unknown','failed','memory_saved'}:
            raise ValueError('unknown event kind')
        trusted_success=False
        if event.kind=='action_committed':
            r=receipts.get(event.receipt_ref or '')
            trusted_success=bool(r and r.status=='committed' and r.owner==event.owner
                and r.object_ref==event.object_ref and r.version==event.version)
            if not trusted_success:
                return {'visual':'unverified','audio':False,'haptic':False,'motion':False}
        key=(event.owner,event.kind,event.receipt_ref or event.event_id)
        duplicate=key in self.seen
        self.seen.add(key)
        emit=trusted_success and not duplicate and not event.replay and pref.foreground
        visual='committed' if trusted_success else event.kind
        return {'visual':visual,'audio':bool(emit and pref.audio),
                'haptic':bool(emit and pref.haptic and pref.haptic_supported),
                'motion':bool(emit and not pref.reduced_motion)}


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator < 0 or numerator < 0 or numerator > denominator:
        raise ValueError('invalid denominator or numerator')
    return numerator / denominator if denominator else None
