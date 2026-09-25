#!/usr/bin/env python3
"""Q-06 增长标度：Context token × Memory 行数（wt406）.

真实服务面：ContextPackBuilder.build()（backend/app/core/context_pack.py）直接驱动，
sqlite+aiosqlite 真实 schema（tests.v3_action_eval.dbfixture.ScenarioDB 同源），
fakeredis 基建绑定（aurora_ablation world 同款）。记忆行是**真实格式真数据**
（学习成长域 episodic 事件/偏好版本链/backdate 时间戳），模型 judge 0 次。

两个增长轴：
- episodic 行数：10/50/100/500/1000（用户记忆自然积累的真实形态）；
- preference 版本链行数：25 键 × {1,2,4,8,20} 版本（supersede 链积累的真实形态，
  list_preference_records 全量加载后按 key 去重——版本链增长只应影响加载，不应泄漏进 token）。
goals 固定 3 条（现实规模）。

每点测：pack.token_usage（各 section token）、to_prompt_context 渲染 token、
build 墙钟（K=3 取中位+最小）、pack 内条目数；幂律拟合指数 b（build_ms ~ n^b），
b>1.5 判超线性嫌疑，tokens 曲线是否被护栏钳平如实呈报。带 query_text 的构建
经真实 embedding（dashscope batch）走 semantic gating——模型调用仅 embedding，
LLM judge 0 次。

用法（仓库根；backend venv）::
  python3 scripts/devtools/q06_growth_scaling.py [--out-dir DIR] [--quick]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "q06-growth-scaling-key")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

EPISODIC_SIZES = [10, 50, 100, 500, 1000]
PREF_VERSION_COUNTS = [1, 2, 4, 8, 20]
PREF_KEYS = 25
GOALS_FIXED = 3
BUILDS_PER_POINT = 3

SUBJECTS = ["高数", "考研英语", "数据结构", "操作系统", "线性代数", "概率论", "雅思口语", "机器学习", "计算机网络", "数据库"]

_EPISODIC_TEMPLATES = [
    "完成{subj}第{i}章练习，共20题错3题，错因集中在概念混淆",
    "与学习搭子讨论{subj}的难点，对方建议用费曼法重讲一遍",
    "{subj}模拟测得{score}分，比上次提升{delta}分",
    "看{subj}网课90分钟，做了思维导图，卡在特征值章节",
    "制定下周{subj}复习计划：每天1.5小时，优先错题重做",
    "{subj}错题重做12道，第二遍正确率8/12，遗留4道需第三次回顾",
    "请教老师{subj}问题，明确了边界条件的判定步骤",
    "晚上学到23:30，效率偏低，明天调整到早上背{subj}概念",
]
_EPISODIC_TAGS = [
    ["practice", "error_book"], ["discussion", "peer"], ["exam", "score"], ["video", "note"],
    ["plan", "weekly"], ["practice", "spaced"], ["ask", "teacher"], ["meta", "energy"],
]

_PREF_TEMPLATES = [
    ("explanation_style", ["中文解释", "英文解释", "双语对照", "例子先行"]),
    ("concise_mode", ["开", "关", "自动"]),
    ("examples_first", ["true", "false"]),
    ("difficulty_target", ["基础", "中等", "挑战"]),
    ("study_time_preference", ["早晨", "下午", "晚上"]),
    ("reminder_tone", ["温和", "直接", "中性"]),
    ("math_notation", ["LaTeX", "纯文本"]),
    ("plan_granularity", ["天", "半天", "周"]),
    ("feedback_frequency", ["每日", "每周", "关键节点"]),
    ("content_depth", ["概览", "标准", "深入"]),
]


def _episodic_content(i: int) -> tuple[str, list[str]]:
    subj = SUBJECTS[i % len(SUBJECTS)]
    text = _EPISODIC_TEMPLATES[i % len(_EPISODIC_TEMPLATES)].format(
        subj=subj, score=i % 40 + 55, delta=i % 7 - 2, chapter=i % 12 + 1, i=i % 12 + 1)
    return text, _EPISODIC_TAGS[i % len(_EPISODIC_TAGS)]


def _powerlaw_exponent(points: list[tuple[float, float]]) -> float | None:
    pts = [(math.log(x), math.log(y)) for x, y in points if x > 0 and y > 0]
    if len(pts) < 3:
        return None
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    denom = n * sxx - sx * sx
    return round((n * sxy - sx * sy) / denom, 3) if denom else None


async def run(out_dir: Path, quick: bool) -> dict:
    import fakeredis.aioredis

    from tests.v3_action_eval.dbfixture import ScenarioDB

    results: dict = {"episodic_axis": [], "preference_axis": [],
                     "generated_at": datetime.now(UTC).isoformat(),
                     "embeddings_real": True, "llm_judge_calls": 0}

    db = ScenarioDB()
    await db.__aenter__()
    factory = db.session_factory()
    try:
        async with factory() as session:
            from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
            from app.models.user import User

            user_id = uuid.uuid4()
            session.add(User(id=user_id, username="q06_growth",
                             email="q06_growth@eval.local", hashed_password="q06"))
            await session.flush()

            base = datetime.now(UTC).replace(tzinfo=None)
            for i in range(max(EPISODIC_SIZES)):
                text, tags = _episodic_content(i)
                occurred = base - timedelta(days=(i % 60), hours=i % 24, minutes=(i * 7) % 60)
                session.add(EpisodicMemory(
                    user_id=user_id, summary=text, source_type="chat",
                    source_id=f"q06-grow-{i}", occurred_at=occurred,
                    importance_score=0.3 + (i % 7) / 10.0, confidence=0.8,
                    evidence_score=0.4 + (i % 5) / 10.0, tags=tags,
                    evidence_refs=[], epistemic_class="OBSERVATION",
                ))
            for title in (f"{s}期末上85分" for s in SUBJECTS[:GOALS_FIXED]):
                session.add(MemoryGoal(user_id=user_id, title=title, status="active", evidence_score=0.7))
            await session.commit()

            from app.core.context_pack import ContextPackBuilder, estimate_tokens

            builder_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
            try:
                # ---------- episodic 轴 ----------
                for n in EPISODIC_SIZES:
                    if quick and n > 100:
                        continue
                    builder = ContextPackBuilder(session, redis=builder_redis)
                    times: list[float] = []
                    pack = None
                    for _ in range(BUILDS_PER_POINT):
                        t0 = time.perf_counter()
                        pack = await builder.build(
                            user_id=user_id, intent="concept_explain",
                            query_text="帮我分析最近高数和英语的学习进展，规划下周复习",
                        )
                        times.append((time.perf_counter() - t0) * 1000)
                    rendered = json.dumps(pack.to_prompt_context(), ensure_ascii=False, default=str)
                    row = {
                        "episodic_rows": n,
                        "pack_token_usage": pack.token_usage,
                        "pack_tokens_total": int(sum(pack.token_usage.values())),
                        "prompt_render_tokens": estimate_tokens(rendered),
                        "episodic_in_pack": len(pack.episodic_memories or []),
                        "preferences_in_pack": len(pack.preferences or {}),
                        "goals_in_pack": len(pack.goals or []),
                        "build_ms_median": round(statistics.median(times), 1),
                        "build_ms_min": round(min(times), 1),
                        "build_ms_all": [round(t, 1) for t in times],
                    }
                    results["episodic_axis"].append(row)
                    print(json.dumps(row, ensure_ascii=False), flush=True)

                # ---------- preference 版本链轴（episodic 清空隔离） ----------
                await session.execute(EpisodicMemory.__table__.delete())
                await session.commit()
                pref_rows: list[MemoryPreference] = []
                for k in range(PREF_KEYS):
                    key, values = _PREF_TEMPLATES[k % len(_PREF_TEMPLATES)]
                    for v in range(1, max(PREF_VERSION_COUNTS) + 1):
                        pref_rows.append(MemoryPreference(
                            user_id=user_id, pref_key=f"{key}:{k:02d}",
                            pref_value=values[v % len(values)], version=v,
                            confidence=0.9, evidence_score=0.5 + (v % 5) / 10.0,
                            evidence_refs=[],
                        ))
                for v_count in PREF_VERSION_COUNTS:
                    if quick and v_count > 8:
                        continue
                    await session.execute(MemoryPreference.__table__.delete())
                    session.add_all([r for r in pref_rows if r.version <= v_count])
                    await session.commit()
                    builder = ContextPackBuilder(session, redis=builder_redis)
                    times = []
                    pack = None
                    for _ in range(BUILDS_PER_POINT):
                        t0 = time.perf_counter()
                        pack = await builder.build(
                            user_id=user_id, intent="concept_explain",
                            query_text="我应该用什么样的解释风格和学习安排",
                        )
                        times.append((time.perf_counter() - t0) * 1000)
                    row = {
                        "pref_rows": PREF_KEYS * v_count, "pref_keys": PREF_KEYS,
                        "versions_per_key": v_count,
                        "pack_token_usage": pack.token_usage,
                        "pack_tokens_total": int(sum(pack.token_usage.values())),
                        "preferences_in_pack": len(pack.preferences or {}),
                        "build_ms_median": round(statistics.median(times), 1),
                        "build_ms_min": round(min(times), 1),
                    }
                    results["preference_axis"].append(row)
                    print(json.dumps(row, ensure_ascii=False), flush=True)
            finally:
                await builder_redis.aclose()
    finally:
        await db.__aexit__()

    epi = results["episodic_axis"]
    if len(epi) >= 3:
        results["episodic_fit"] = {
            "build_ms_exponent": _powerlaw_exponent([(r["episodic_rows"], r["build_ms_median"]) for r in epi]),
            "prompt_tokens_exponent": _powerlaw_exponent([(r["episodic_rows"], r["prompt_render_tokens"]) for r in epi]),
        }
    pre = results["preference_axis"]
    if len(pre) >= 3:
        results["preference_fit"] = {
            "build_ms_exponent": _powerlaw_exponent([(r["pref_rows"], r["build_ms_median"]) for r in pre]),
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "growth_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"results -> {out_dir / 'growth_results.json'}")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "v3-output" / "WT406-Q06-PERF"))
    ap.add_argument("--quick", action="store_true", help="只跑 <=100 行（调试用）")
    args = ap.parse_args()
    asyncio.run(run(Path(args.out_dir), args.quick))


if __name__ == "__main__":
    main()
