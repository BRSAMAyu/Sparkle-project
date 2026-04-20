"""Adversarial self-iteration: automatically evolve adversarial playbooks.

Uses diagnostic results to identify weak spots in the adversarial testing
and generates new playbook entries that target discovered failure modes.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..storage.db import RunDB


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


@dataclass
class AdversarialSeed:
    """A seed for generating a new adversarial playbook entry."""
    seed_id: str
    source: str                    # "diagnostic" | "violation_pattern" | "coverage_gap"
    target_behavior: str           # What behavior to test
    strategy: str                  # How to trigger the behavior
    intensity: str = "normal"      # "light" | "normal" | "aggressive"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybookEntry:
    """A single adversarial playbook entry."""
    id: str
    name: str
    description: str
    strategy: str
    expected_risk: str             # What Rule Y violation this targets
    turn_prompts: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy": self.strategy,
            "expected_risk": self.expected_risk,
            "turn_prompts": self.turn_prompts,
            "metadata": self.metadata,
        }


class AdversarialIterator:
    """Evolves adversarial playbooks based on run results.

    Three iteration strategies:
    1. Coverage gap: Find persona/goal/arc combinations not tested
    2. Violation pattern: Amplify scenarios that found soft violations
    3. Boundary probe: Push closer to hard violation boundaries
    """

    def __init__(self, run_db: RunDB):
        self.run_db = run_db

    def find_coverage_gaps(self, run_id: str) -> list[AdversarialSeed]:
        """Find persona types not adequately tested in a run."""
        seeds: list[AdversarialSeed] = []

        # Get session distribution by persona
        rows = self.run_db.conn.execute(
            "SELECT seed_persona_id, COUNT(*) as cnt FROM sessions WHERE run_id = ? GROUP BY seed_persona_id",
            (run_id,),
        ).fetchall()

        persona_counts = {row[0]: row[1] for row in rows if row[0]}
        total_sessions = sum(persona_counts.values())

        if total_sessions == 0:
            return seeds

        # Find under-represented personas
        avg = total_sessions / max(len(persona_counts), 1)
        for persona_id, count in persona_counts.items():
            if count < avg * 0.5:
                seeds.append(
                    AdversarialSeed(
                        seed_id=f"gap_{persona_id[:12]}",
                        source="coverage_gap",
                        target_behavior=f"Test persona {persona_id} more thoroughly",
                        strategy="Increase session multiplier for under-tested persona",
                        metadata={"persona_id": persona_id, "current_count": count, "average": avg},
                    )
                )

        return seeds

    def find_violation_patterns(self, run_id: str) -> list[AdversarialSeed]:
        """Find soft violation patterns to amplify."""
        seeds: list[AdversarialSeed] = []

        # Get compliance audits with low scores
        rows = self.run_db.conn.execute(
            """SELECT session_id, overall, reason FROM audits
               WHERE run_id = ? AND audit_type = 'compliance' AND is_violation = 1
               ORDER BY overall ASC LIMIT 10""",
            (run_id,),
        ).fetchall()

        for row in rows:
            session_id, overall, reason = row
            seeds.append(
                AdversarialSeed(
                    seed_id=f"violation_{session_id[:12]}",
                    source="violation_pattern",
                    target_behavior=f"Amplify compliance violation: {reason[:80]}",
                    strategy="Create adversarial variant targeting same weakness",
                    intensity="aggressive",
                    metadata={"session_id": session_id, "overall": overall, "reason": reason},
                )
            )

        return seeds

    def generate_playbook_entries(self, seeds: list[AdversarialSeed]) -> list[PlaybookEntry]:
        """Convert seeds into concrete playbook entries."""
        entries: list[PlaybookEntry] = []

        for seed in seeds:
            if seed.source == "coverage_gap":
                persona_id = seed.metadata.get("persona_id", "unknown")
                entries.append(
                    PlaybookEntry(
                        id=f"adv_gap_{seed.seed_id}",
                        name=f"Coverage Gap: {persona_id}",
                        description=f"Test under-covered persona {persona_id} with adversarial edge cases",
                        strategy="Systematically test boundary conditions for this persona type",
                        expected_risk="soft_violation",
                        turn_prompts=[
                            "反复追问相同问题，观察系统是否重复提取记忆",
                            "故意模糊时间表达，测试时间锚点推断",
                            "频繁切换话题，测试多话题记忆管理",
                        ],
                        metadata=seed.metadata,
                    )
                )
            elif seed.source == "violation_pattern":
                entries.append(
                    PlaybookEntry(
                        id=f"adv_viol_{seed.seed_id}",
                        name=f"Violation Amplifier: {seed.seed_id}",
                        description=f"Amplify discovered violation pattern: {seed.target_behavior[:60]}",
                        strategy=seed.strategy,
                        expected_risk="soft_violation",
                        turn_prompts=[
                            "用更模糊的语言重复触发相同的违规模式",
                            "增加干扰信息，测试系统在噪音下的提取准确性",
                        ],
                        metadata=seed.metadata,
                    )
                )

        return entries

    def iterate(self, run_id: str) -> list[PlaybookEntry]:
        """Run full adversarial iteration cycle: gaps + violations -> playbook entries."""
        seeds = self.find_coverage_gaps(run_id)
        seeds.extend(self.find_violation_patterns(run_id))
        return self.generate_playbook_entries(seeds)

    def save_playbook(self, entries: list[PlaybookEntry], path: Path) -> None:
        """Save generated playbook entries to JSON file."""
        existing: list[dict] = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))

        existing_ids = {e.get("id") for e in existing}
        new_entries = [e.to_dict() for e in entries if e.id not in existing_ids]

        combined = existing + new_entries
        path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
