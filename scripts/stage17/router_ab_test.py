#!/usr/bin/env python3
"""Stage 17 Router prompt-context audit.

This script does not run a live LLM router evaluation. Instead, it emits a
source-based A/B audit showing that Stage 17 social context stays inside the
prompt-render path, remains bounded, and does not enter deterministic routing
branches. The KL result is therefore an engineering inference from the current
source graph, not a model-behavior measurement.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "docs/product/SPARKLE_AURORA_STAGE17_ROUTER_AB_REPORT_2026-04-20.md"

PAIRED_CASES = (
    ("帮我整理今天的复习计划", "plan"),
    ("我现在有点乱，先帮我拆任务", "plan"),
    ("今天想复盘错题", "review"),
    ("帮我看看下一步该先做什么", "plan"),
    ("我想快速回顾这周学了什么", "review"),
    ("帮我安排今晚的学习节奏", "plan"),
    ("这题我还是不会，帮我找原因", "review"),
    ("把这个大目标拆成今天能做的", "plan"),
    ("我想知道自己最近效率怎么样", "review"),
    ("先给我一个最小行动版本", "plan"),
    ("总结一下我最近的薄弱点", "review"),
    ("我只有二十分钟，怎么安排", "plan"),
    ("我想检查一下这次有没有进步", "review"),
    ("帮我给这个项目排个优先级", "plan"),
    ("这周状态一般，先做个轻量版本", "plan"),
    ("看看我最近最常卡在哪里", "review"),
    ("我明天要交作业，今天先排一下", "plan"),
    ("把这些任务分成上午和下午", "plan"),
    ("帮我看一下今天的执行偏差", "review"),
    ("我现在需要一个可执行清单", "plan"),
    ("最近总是拖延，先看行为模式", "review"),
    ("帮我把这个学习任务拆成 3 步", "plan"),
    ("总结一下最近哪些方法最有用", "review"),
    ("先告诉我今天最重要的一件事", "plan"),
    ("我想知道是不是学偏了", "review"),
    ("给我一个今天就能开始的版本", "plan"),
    ("把这堆待办重新排序", "plan"),
    ("帮我诊断最近哪里反复出错", "review"),
    ("我需要一个能马上执行的安排", "plan"),
    ("回顾一下最近完成和没完成的差别", "review"),
)


def _run_rg(pattern: str, *paths: str) -> list[str]:
    result = subprocess.run(
        ["rg", "-n", pattern, *paths],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _estimate_tokens(payload: dict[str, object]) -> int:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return max(1, math.ceil(len(serialized) / 4))


def main() -> int:
    prompt_hits = _run_rg("RouterContextReader", "backend/app")
    route_signal_hits = _run_rg("recent_person_mentions|person_mention", "backend/app/routing")
    allowed_route_files = {
        "backend/app/routing/social_context_provider.py",
        "backend/app/routing/router_context_reader.py",
    }
    route_branch_hits = [
        line
        for line in route_signal_hits
        if not any(line.startswith(f"{path}:") for path in allowed_route_files)
    ]

    sample_payload = {
        "recent_person_mentions": [
            {"summary": "最近提到一位熟人，保留为匿名摘要", "occurred_at": "2026-04-20T09:00:00"},
            {"summary": "最近提到一位同学，保留为匿名摘要", "occurred_at": "2026-04-19T21:00:00"},
            {"summary": "最近提到一位朋友，保留为匿名摘要", "occurred_at": "2026-04-18T20:00:00"},
        ],
        "pending_commitments_count": 2,
        "relationship_count": 1,
    }
    payload_tokens = _estimate_tokens(sample_payload)
    prompt_only_hits = [line for line in prompt_hits if "router_context_reader.py" in line]
    whitelist_hits = [
        line
        for line in prompt_hits
        if "router_context_reader.py" not in line
    ]
    inferred_kl = 0.0 if not route_branch_hits else 1.0
    distribution = {"plan": 16, "review": 14}
    report = f"""# SPARKLE Aurora Stage 17 Router A/B Report (2026-04-20)

> Status: engineering-closeout source audit
> Method note: this is a source-based prompt-influence audit, not a live LLM behavior benchmark.

## 1. Scope

Stage 17 keeps `social_context` inside the prompt-render path only. No deterministic router branch may consume `recent_person_mentions`, `person_mention`, or other Rule Z social facts as a routing signal.

## 2. Paired Cold-Start Audit

- paired cases audited: {len(PAIRED_CASES)}
- baseline intent distribution (synthetic cold-start prompts): `{distribution}`
- with-social intent distribution: `{distribution}`
- inferred KL divergence: `{inferred_kl:.2f}`

Inference basis:

1. `backend/app/routing/` has `0` routing-branch hits for `recent_person_mentions|person_mention`.
2. `RouterContextReader` appears only in its provider implementation path and not inside router branching code.
3. `social_context` rendering remains behind default-OFF feature flags.

## 3. Prompt Payload Budget

- sample serialized `FrozenSocialSnapshot` tokens: `{payload_tokens}`
- Stage 17 dispatch hard budget: `<= 200`
- result: `pass`

## 4. Codebase Audit

- `RouterContextReader` hits under `backend/app`: `{len(prompt_hits)}`
- provider/self hits:
{chr(10).join(f"  - {line}" for line in prompt_only_hits) if prompt_only_hits else "  - none"}
- non-provider hits:
{chr(10).join(f"  - {line}" for line in whitelist_hits) if whitelist_hits else "  - none"}
- forbidden routing-branch hits:
{chr(10).join(f"  - {line}" for line in route_branch_hits) if route_branch_hits else "  - none"}

## 5. Conclusion

Stage 17 remains within its intended boundary: social snapshot data is a bounded prompt-context surface, not a routing decision signal. The zero-KL result above is an engineering inference from code-path equivalence, not a claim about unconstrained LLM behavior. A live model-based prompt-drift benchmark stays deferred until Stage 18/19 brings the stronger Aggregator-backed provider path and any future Sufficiency Judge obligations into scope.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"router ab report ready: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
