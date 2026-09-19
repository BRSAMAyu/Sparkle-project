#!/usr/bin/env python3
"""C-03: Hard-filter → rerank pipeline delay profile (candidate scale × latency, standalone rerunnable version).

Usage (repo root):
    SECRET_KEY=<test-value> python scripts/devtools/c03_pipeline_perf_profile.py [--scales 100,250,500,1000,2000]

Same synthetic factory as tests/unit/test_context_retrieval_pipeline_perf.py (shared seed):
memory (real M-03 prefiltering, four kinds of illegal) + knowledge (three kinds of illegal + lifecycle),
rerank is synthetic vector cosine (real LLM/embedding 0 times). Prints the profile table,
the assertions in the test version are not enforced here (for observation only).
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scales", default="100,250,500,1000,2000", help="Comma-separated candidate scales")
    args = parser.parse_args()
    scales = [int(s) for s in args.scales.split(",") if s.strip()]

    from app.core.time_utils import utcnow
    from app.models.memory import EpisodicMemory
    from app.services.context_retrieval_pipeline import (
        KnowledgeAccessContext,
        run_hard_filter_pipeline,
    )
    from app.services.memory_retrieval_prefilter import PURPOSE_LLM_CONTEXT, RetrievalContext

    seed = 20260919
    user_id = uuid4()
    now = utcnow()

    def memory_candidates(n: int, rng: random.Random) -> list[EpisodicMemory]:
        rows = []
        for i in range(n):
            kind = i % 10
            row = EpisodicMemory(
                id=uuid4(),
                user_id=user_id,
                summary=f"synthetic episodic {i}",
                source_type="chat_turn",
                source_lane="direct_capture",
                subject_type="self",
                occurred_at=now - timedelta(hours=rng.randint(1, 48)),
                created_at=now - timedelta(hours=rng.randint(1, 48)),
                importance_score=0.5,
                evidence_refs=[{"type": "user_state", "id": "t"}],
            )
            if kind == 0:
                row.user_id = uuid4()
            elif kind == 1:
                row.revoked_at = now
            elif kind == 2:
                row.superseded_by_id = uuid4()
            elif kind == 3:
                row.subject_type = "commitment"
                row.decay_policy = "due_at+7d"
                row.due_at = now - timedelta(days=30)
            rows.append(row)
        return rows

    def knowledge_candidates(n: int, rng: random.Random) -> list[SimpleNamespace]:
        docs = []
        for i in range(n):
            kind = i % 10
            doc = SimpleNamespace(
                id=f"synthetic-doc-{i}",
                parent_id=f"parent-{i}",
                content=" ".join(f"token{rng.randint(0, 999)}" for _ in range(24)),
                source_type="document_chunk",
                user_id=str(user_id),
                vector=[rng.random() for _ in range(16)],
            )
            if kind == 0:
                doc.user_id = f"other-user-{i}"
            elif kind == 1:
                doc.group_id = f"group-blocked-{i}"
                doc.user_id = ""
            elif kind == 2:
                doc.user_id = ""
            elif kind == 3:
                doc.lifecycle_status = "archived"
            docs.append(doc)
        return docs

    query_vector = [0.5] * 16

    def rerank(candidates: list) -> list:
        def score(candidate):
            vector = getattr(candidate, "vector", None)
            if not vector:
                return 0.0
            dot = sum(a * b for a, b in zip(query_vector, vector, strict=False))
            norm = sum(v * v for v in vector) ** 0.5
            return dot / norm if norm else 0.0

        return sorted(candidates, key=score, reverse=True)[:50]

    retrieval_ctx = RetrievalContext(user_id=str(user_id), purpose=PURPOSE_LLM_CONTEXT, now=now)
    knowledge_ctx = KnowledgeAccessContext(user_id=str(user_id), allowed_group_ids=frozenset({"group-0"}))

    header = f"{'candidates':>10} {'filter_ms':>10} {'rerank_ms':>10} {'total_ms':>10} {'per_cand_us':>12}"
    print(header)
    print("-" * len(header))
    for scale in scales:
        rng = random.Random(seed + scale)
        memory = memory_candidates(scale, rng)
        knowledge = knowledge_candidates(scale, rng)

        import time

        best_ms, report = None, None
        for _ in range(3):
            start = time.perf_counter()
            result = run_hard_filter_pipeline(
                memory_candidates=memory,
                retrieval_ctx=retrieval_ctx,
                knowledge_candidates=knowledge,
                knowledge_ctx=knowledge_ctx,
                rerank_fn=rerank,
            )
            elapsed = (time.perf_counter() - start) * 1000.0
            if best_ms is None or elapsed < best_ms:
                best_ms, report = elapsed, result.report
        channels = report["channels"]
        filter_ms = sum(ch["latency_ms"] for ch in channels.values())
        print(
            f"{2 * scale:>10} {filter_ms:>10.3f} {report['rerank']['latency_ms']:>10.3f} "
            f"{best_ms:>10.3f} {best_ms * 1000.0 / (2 * scale):>12.2f}"
        )


if __name__ == "__main__":
    main()
