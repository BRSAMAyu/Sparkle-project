#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.context_pack import DEFAULT_SEMANTIC_GATING_RULES  # noqa: E402
from app.orchestration.context_focus import cosine_similarity  # noqa: E402
from app.services.embedding_service import embedding_service  # noqa: E402


def _load_samples(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def _f1_score(precision: float, recall: float) -> float:
    if precision <= 0.0 or recall <= 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


async def _score_sample(sample: dict[str, Any]) -> list[dict[str, Any]]:
    query = str(sample.get("query") or "").strip()
    candidates = sample.get("candidate_items") or []
    if not query or not isinstance(candidates, list):
        return []
    candidate_texts = [str(item.get("text") or "").strip() for item in candidates if isinstance(item, dict)]
    if not candidate_texts:
        return []
    embeddings = await embedding_service.batch_embeddings([query, *candidate_texts], text_type="query")
    query_embedding = embeddings[0]
    scored: list[dict[str, Any]] = []
    for idx, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        semantic_score = cosine_similarity(query_embedding, embeddings[idx])
        evidence_score = float(item.get("evidence_score") or 0.0)
        final_score = evidence_score * 0.6 + semantic_score * 0.4
        scored.append(
            {
                "id": str(item.get("id") or ""),
                "section": str(item.get("section") or ""),
                "semantic_score": semantic_score,
                "evidence_score": evidence_score,
                "final_score": final_score,
            }
        )
    return scored


async def calibrate(dataset_path: Path) -> dict[str, Any]:
    samples = _load_samples(dataset_path)
    scored_samples: list[dict[str, Any]] = []
    for sample in samples:
        scored_samples.append(
            {
                "intent_type": str(sample.get("intent_type") or "unknown"),
                "query": str(sample.get("query") or ""),
                "expected_keep_ids": {str(item) for item in (sample.get("expected_keep_ids") or [])},
                "scored_candidates": await _score_sample(sample),
            }
        )

    sections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in scored_samples:
        for candidate in sample["scored_candidates"]:
            sections[candidate["section"]].append(sample)
            break

    recommendations: dict[str, dict[str, Any]] = {}
    for section, section_samples in sections.items():
        base = DEFAULT_SEMANTIC_GATING_RULES.get(section, {})
        best: dict[str, Any] | None = None
        candidate_limits = {int(base.get("candidate_limit", 10)), 8, 10, 12}
        top_ks = {int(base.get("top_k", 4)), 3, 4, 5}
        thresholds = [round(item, 2) for item in [0.4, 0.45, 0.5, 0.52, 0.55, 0.6, 0.65]]
        for candidate_limit in sorted(candidate_limits):
            for top_k in sorted(top_ks):
                for threshold in thresholds:
                    tp = fp = fn = 0
                    for sample in section_samples:
                        ranked = sorted(
                            [item for item in sample["scored_candidates"] if item["section"] == section],
                            key=lambda item: item["final_score"],
                            reverse=True,
                        )[:candidate_limit]
                        kept = {
                            item["id"]
                            for item in ranked
                            if item["semantic_score"] >= threshold
                        }
                        if len(kept) < top_k:
                            for item in ranked:
                                kept.add(item["id"])
                                if len(kept) >= top_k:
                                    break
                        expected = sample["expected_keep_ids"]
                        tp += len(kept & expected)
                        fp += len(kept - expected)
                        fn += len(expected - kept)
                    precision = tp / (tp + fp) if (tp + fp) else 0.0
                    recall = tp / (tp + fn) if (tp + fn) else 0.0
                    candidate = {
                        "candidate_limit": candidate_limit,
                        "top_k": top_k,
                        "threshold": threshold,
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                        "f1": round(_f1_score(precision, recall), 4),
                        "false_positive": fp,
                        "false_negative": fn,
                    }
                    if best is None or candidate["f1"] > best["f1"]:
                        best = candidate
        if best:
            recommendations[section] = best

    return {
        "dataset": str(dataset_path),
        "sample_count": len(samples),
        "recommended_rules": {
            section: {
                "candidate_limit": result["candidate_limit"],
                "top_k": result["top_k"],
                "threshold": result["threshold"],
            }
            for section, result in recommendations.items()
        },
        "stats": recommendations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate context semantic gating thresholds from offline samples.")
    parser.add_argument("dataset", help="Path to JSON dataset.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()
    result = asyncio.run(calibrate(Path(args.dataset)))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
