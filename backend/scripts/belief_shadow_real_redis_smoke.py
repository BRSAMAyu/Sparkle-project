#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.cache import cache_service  # noqa: E402
from app.services.analytics.belief_trace_inspector import BeliefTraceInspector  # noqa: E402
from app.services.chat_signal_collector import ChatSignalCollector  # noqa: E402
from app.services.evidence.conversational_extractor import ConversationalEvidenceExtractor  # noqa: E402
from app.services.evidence.fusion_engine import FusionEngine  # noqa: E402


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run a real Redis belief shadow smoke test.")
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--message", default="我现在真的好累，今天感觉什么都不想做，不知道从哪里开始。")
    parser.add_argument("--actual-router-mode", default="execution_first")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if cache_service.redis is None:
        await cache_service.init_redis()
    if cache_service.redis is None:
        print("Redis is not configured", file=sys.stderr)
        return 2

    user_id = uuid4() if args.user_id in (None, "random") else UUID(str(args.user_id))

    collector = ChatSignalCollector(
        redis=cache_service.redis,
        evidence_extractor=ConversationalEvidenceExtractor(llm_enabled=False),
    )
    conversation_id = f"belief-smoke-{uuid4()}"
    await collector.collect_signals(
        user_id=user_id,
        user_message=args.message,
        ai_response="我先帮你把第一步压到最小。",
        conversation_id=conversation_id,
        turn_index=1,
        actual_router_mode=args.actual_router_mode,
        routing_trace_id=f"rt-{conversation_id}",
        route_history_decision_id=f"rh-{conversation_id}",
        routing_outcome_signal_id=f"sig-{conversation_id}",
    )

    key = FusionEngine.BELIEF_TRACE_KEY.format(user_id=str(user_id))
    raw = await cache_service.redis.lrange(key, 0, 20)
    trace = None
    if raw:
        item = raw[0].decode("utf-8") if isinstance(raw[0], bytes) else raw[0]
        trace = json.loads(item)
    summary = BeliefTraceInspector().summarize(list(raw or []))
    result = {
        "schema_version": "belief_shadow_real_redis_smoke.v1",
        "redis_key": key,
        "user_id": str(user_id),
        "trace_found": trace is not None,
        "trace": trace,
        "trace_summary": {
            "total_traces": summary["total_traces"],
            "comparable_traces": summary["comparable_traces"],
            "evidence_source_counts": summary["evidence_source_counts"],
            "llm_evidence_rate": summary["llm_evidence_rate"],
            "heuristic_fallback_evidence_rate": summary["heuristic_fallback_evidence_rate"],
            "f1_quality_gate": summary["f1_quality_gate"],
        },
        "required_fields_present": bool(
            trace
            and trace.get("actual_router_mode")
            and (trace.get("router_shadow_projection") or {}).get("shadow_mode")
            and trace.get("belief_variable_evidence_counts")
        ),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"Redis key: {key}")
        print(f"Trace found: {result['trace_found']}")
        print(f"Required fields present: {result['required_fields_present']}")
        if trace:
            print(f"actual_router_mode={trace.get('actual_router_mode')}")
            print(f"shadow_mode={(trace.get('router_shadow_projection') or {}).get('shadow_mode')}")
            print(f"evidence_counts={trace.get('belief_variable_evidence_counts')}")
    return 0 if result["required_fields_present"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
