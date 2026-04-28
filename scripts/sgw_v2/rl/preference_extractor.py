"""Preference pair extraction for DPO training.

Extracts (context, chosen_response, rejected_response) triplets from completed
SGw v2 sessions. Pairs high-quality vs low-quality turns within the same session
or across sessions with the same persona.
"""
from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..sim.ai_behavior_classifier import AIBehaviorClass, classify_ai_response
from .response_evaluator import ResponseEvaluator, ResponseQuality

BEHAVIOR_ONEHOT_DIM = 8
_BEHAVIOR_ORDER = [e.value for e in AIBehaviorClass]


@dataclass
class PreferencePair:
    """A single (context, chosen, rejected) triplet for DPO training."""

    pair_id: str
    context_vector: list[float]
    chosen_response: str
    rejected_response: str
    chosen_score: float
    rejected_score: float
    chosen_behavior: str
    rejected_behavior: str
    margin: float
    session_id: str = ""
    run_id: str = ""
    chosen_turn_id: str = ""
    rejected_turn_id: str = ""
    persona_id: str = ""


@dataclass
class ExtractionResult:
    """Result of running preference extraction on a run."""

    run_id: str
    pairs: list[PreferencePair]
    sessions_scanned: int
    turns_evaluated: int
    pairs_created: int
    pairs_skipped_low_margin: int = 0
    pairs_skipped_insufficient_turns: int = 0

    @property
    def total_attempted(self) -> int:
        return self.pairs_created + self.pairs_skipped_low_margin + self.pairs_skipped_insufficient_turns


class PreferenceExtractor:
    """Extracts preference pairs from completed SGW v2 sessions.

    Pairing strategy (priority order):
      1. Within-session: highest-quality turn vs lowest-quality turn (min margin 0.15)
      2. Within-session: adjacent turns with significant quality difference
      3. Cross-session same-persona: best turn from session A vs worst from session B

    Context vector encodes turn position, message features, AI behavior, session
    progress, and persona identity into a ~25-dim float vector.
    """

    def __init__(
        self,
        evaluator: ResponseEvaluator | None = None,
        min_margin: float = 0.15,
        min_turns_per_session: int = 3,
        max_pairs_per_session: int = 5,
        cross_session_pairing: bool = True,
    ):
        self.evaluator = evaluator or ResponseEvaluator()
        self.min_margin = min_margin
        self.min_turns_per_session = min_turns_per_session
        self.max_pairs_per_session = max_pairs_per_session
        self.cross_session_pairing = cross_session_pairing

    # ── Public API ──────────────────────────────────────

    def extract_from_run(
        self,
        run_id: str,
        sessions: list[dict[str, Any]],
        turns_by_session: dict[str, list[dict[str, Any]]],
    ) -> ExtractionResult:
        """Extract preference pairs from all sessions in a run."""
        all_pairs: list[PreferencePair] = []
        sessions_scanned = 0
        turns_evaluated = 0
        skipped_low_margin = 0
        skipped_insufficient = 0

        # Build quality scores for every turn
        session_qualities: dict[str, list[tuple[dict[str, Any], ResponseQuality]]] = {}
        for sess in sessions:
            sid = sess.get("session_id", "")
            turns = turns_by_session.get(sid, [])
            if len(turns) < self.min_turns_per_session:
                skipped_insufficient += 1
                continue

            sessions_scanned += 1
            scored: list[tuple[dict[str, Any], ResponseQuality]] = []
            for turn in turns:
                quality = self.evaluator.evaluate(turn)
                turns_evaluated += 1
                scored.append((turn, quality))
            session_qualities[sid] = scored

        # Within-session pairing
        for sess in sessions:
            sid = sess.get("session_id", "")
            scored = session_qualities.get(sid, [])
            if not scored:
                continue

            persona_id = sess.get("seed_persona_id", "")
            within_pairs, within_skipped = self._pair_within_session(
                run_id, sid, scored, persona_id
            )
            all_pairs.extend(within_pairs)
            skipped_low_margin += within_skipped

        # Cross-session same-persona pairing
        if self.cross_session_pairing:
            cross_pairs, cross_skipped = self._pair_cross_session(
                run_id, sessions, session_qualities
            )
            all_pairs.extend(cross_pairs)
            skipped_low_margin += cross_skipped

        return ExtractionResult(
            run_id=run_id,
            pairs=all_pairs,
            sessions_scanned=sessions_scanned,
            turns_evaluated=turns_evaluated,
            pairs_created=len(all_pairs),
            pairs_skipped_low_margin=skipped_low_margin,
            pairs_skipped_insufficient_turns=skipped_insufficient,
        )

    def build_context_vector(
        self,
        turn: dict[str, Any],
        session: dict[str, Any] | None = None,
    ) -> list[float]:
        """Build a ~25-dim context feature vector for a single turn."""
        vec: list[float] = []

        # ── Turn position (5 dims) ──
        turn_index = turn.get("turn_index", 0)
        max_turns = (session or {}).get("target_turns", 12) if session else 12
        max_turns = max(max_turns, 1)
        remaining = max(0, max_turns - turn_index)

        vec.append(min(1.0, turn_index / max_turns))            # normalized position
        vec.append(1.0 if turn_index <= 3 else 0.0)             # opening phase
        vec.append(1.0 if remaining <= 3 and remaining >= 0 else 0.0)  # closing phase
        vec.append(min(1.0, remaining / max_turns))             # remaining ratio
        vec.append(1.0 if turn_index == 1 else 0.0)             # is first turn

        # ── Message features (5 dims) ──
        user_msg = turn.get("user_message", "") or ""
        ai_resp = turn.get("ai_response", "") or ""
        user_len = len(user_msg)
        ai_len = len(ai_resp)

        vec.append(min(1.0, math.log(1 + user_len) / math.log(1 + 500)))
        vec.append(min(1.0, math.log(1 + ai_len) / math.log(1 + 2000)))
        has_q = any(q in user_msg for q in ("?", "？", "吗", "呢", "什么", "怎么", "为什么"))
        vec.append(1.0 if has_q else 0.0)
        digit_count = sum(1 for c in user_msg if c.isdigit())
        vec.append(min(1.0, digit_count / 50.0))
        word_count = len(user_msg.replace(" ", ""))
        vec.append(min(1.0, word_count / 200.0))

        # ── AI behavior one-hot (8 dims) ──
        behavior = turn.get("ai_behavior_class", "") or classify_ai_response(ai_resp).value
        for bv in _BEHAVIOR_ORDER:
            vec.append(1.0 if behavior == bv else 0.0)

        # ── Session features (4 dims) ──
        if session:
            target = max(session.get("target_turns", 12), 1)
            completed = session.get("turns_completed", 0)
            vec.append(min(1.0, target / 20.0))
            vec.append(min(1.0, completed / target))
            vec.append(min(1.0, turn_index / target))
            vec.append(1.0 if session.get("status") == "completed" else 0.0)
        else:
            vec.extend([0.6, 0.5, 0.5, 0.0])

        # ── Persona features (3 dims) ──
        persona_id = (session or {}).get("seed_persona_id", "") if session else ""
        arc_id = (session or {}).get("arc_id", "") if session else ""
        role = (session or {}).get("role", "") if session else ""

        if persona_id:
            h = int(hashlib.sha256(persona_id.encode()).hexdigest()[:8], 16)
            vec.append((h % 100) / 100.0)
        else:
            vec.append(0.0)

        if arc_id:
            h = int(hashlib.sha256(arc_id.encode()).hexdigest()[:8], 16)
            vec.append((h % 100) / 100.0)
        else:
            vec.append(0.0)

        vec.append(min(1.0, len(role) / 20.0))

        return vec

    # ── Pairing strategies ──────────────────────────────

    def _pair_within_session(
        self,
        run_id: str,
        session_id: str,
        scored: list[tuple[dict[str, Any], ResponseQuality]],
        persona_id: str,
    ) -> tuple[list[PreferencePair], int]:
        """Pair highest vs lowest quality turns within a session."""
        pairs: list[PreferencePair] = []
        skipped = 0

        # Sort by overall_score descending
        ranked = sorted(scored, key=lambda x: x[1].overall_score, reverse=True)
        n = len(ranked)

        # Take top-N and bottom-N pairs
        for i in range(min(self.max_pairs_per_session, n // 2)):
            best_turn, best_q = ranked[i]
            worst_turn, worst_q = ranked[-(i + 1)]

            margin = best_q.overall_score - worst_q.overall_score
            if margin < self.min_margin:
                skipped += 1
                continue

            pair = PreferencePair(
                pair_id=str(uuid.uuid4()),
                context_vector=self.build_context_vector(best_turn),
                chosen_response=best_turn.get("ai_response", ""),
                rejected_response=worst_turn.get("ai_response", ""),
                chosen_score=best_q.overall_score,
                rejected_score=worst_q.overall_score,
                chosen_behavior=best_q.ai_behavior,
                rejected_behavior=worst_q.ai_behavior,
                margin=round(margin, 4),
                session_id=session_id,
                run_id=run_id,
                chosen_turn_id=best_turn.get("turn_id", ""),
                rejected_turn_id=worst_turn.get("turn_id", ""),
                persona_id=persona_id,
            )
            pairs.append(pair)

        return pairs, skipped

    def _pair_cross_session(
        self,
        run_id: str,
        sessions: list[dict[str, Any]],
        session_qualities: dict[str, list[tuple[dict[str, Any], ResponseQuality]]],
    ) -> tuple[list[PreferencePair], int]:
        """Pair best turn of one session vs worst turn of another, same persona."""
        pairs: list[PreferencePair] = []
        skipped = 0

        # Group sessions by persona
        persona_sessions: dict[str, list[str]] = {}
        for sess in sessions:
            pid = sess.get("seed_persona_id", "")
            if pid:
                persona_sessions.setdefault(pid, []).append(sess.get("session_id", ""))

        for persona_id, sid_list in persona_sessions.items():
            if len(sid_list) < 2:
                continue

            # For each pair of sessions, compare best of A vs worst of B
            for i in range(len(sid_list)):
                for j in range(i + 1, len(sid_list)):
                    scored_a = session_qualities.get(sid_list[i], [])
                    scored_b = session_qualities.get(sid_list[j], [])
                    if len(scored_a) < 2 or len(scored_b) < 2:
                        continue

                    ranked_a = sorted(scored_a, key=lambda x: x[1].overall_score, reverse=True)
                    ranked_b = sorted(scored_b, key=lambda x: x[1].overall_score, reverse=True)

                    # A's best vs B's worst
                    best_a_t, best_a_q = ranked_a[0]
                    worst_b_t, worst_b_q = ranked_b[-1]
                    margin = best_a_q.overall_score - worst_b_q.overall_score
                    if margin >= self.min_margin:
                        pairs.append(PreferencePair(
                            pair_id=str(uuid.uuid4()),
                            context_vector=self.build_context_vector(best_a_t),
                            chosen_response=best_a_t.get("ai_response", ""),
                            rejected_response=worst_b_t.get("ai_response", ""),
                            chosen_score=best_a_q.overall_score,
                            rejected_score=worst_b_q.overall_score,
                            chosen_behavior=best_a_q.ai_behavior,
                            rejected_behavior=worst_b_q.ai_behavior,
                            margin=round(margin, 4),
                            session_id=sid_list[i],
                            run_id=run_id,
                            chosen_turn_id=best_a_t.get("turn_id", ""),
                            rejected_turn_id=worst_b_t.get("turn_id", ""),
                            persona_id=persona_id,
                        ))
                    else:
                        skipped += 1

                    # B's best vs A's worst
                    best_b_t, best_b_q = ranked_b[0]
                    worst_a_t, worst_a_q = ranked_a[-1]
                    margin = best_b_q.overall_score - worst_a_q.overall_score
                    if margin >= self.min_margin:
                        pairs.append(PreferencePair(
                            pair_id=str(uuid.uuid4()),
                            context_vector=self.build_context_vector(best_b_t),
                            chosen_response=best_b_t.get("ai_response", ""),
                            rejected_response=worst_a_t.get("ai_response", ""),
                            chosen_score=best_b_q.overall_score,
                            rejected_score=worst_a_q.overall_score,
                            chosen_behavior=best_b_q.ai_behavior,
                            rejected_behavior=worst_a_q.ai_behavior,
                            margin=round(margin, 4),
                            session_id=sid_list[j],
                            run_id=run_id,
                            chosen_turn_id=best_b_t.get("turn_id", ""),
                            rejected_turn_id=worst_a_t.get("turn_id", ""),
                            persona_id=persona_id,
                        ))
                    else:
                        skipped += 1

        return pairs, skipped

    # ── Persistence ─────────────────────────────────────

    def persist_pairs(
        self,
        pairs: list[PreferencePair],
        db: Any,  # RunDB
    ) -> int:
        """Write preference pairs to RunDB. Returns count persisted."""
        count = 0
        for pair in pairs:
            try:
                db.insert_preference_pair(
                    pair_id=pair.pair_id,
                    run_id=pair.run_id,
                    context_vector=pair.context_vector,
                    chosen_response=pair.chosen_response,
                    rejected_response=pair.rejected_response,
                    chosen_score=pair.chosen_score,
                    rejected_score=pair.rejected_score,
                    session_id=pair.session_id,
                    chosen_behavior=pair.chosen_behavior,
                    rejected_behavior=pair.rejected_behavior,
                    chosen_turn_id=pair.chosen_turn_id,
                    rejected_turn_id=pair.rejected_turn_id,
                    persona_id=pair.persona_id,
                )
                count += 1
            except Exception:
                continue
        return count
