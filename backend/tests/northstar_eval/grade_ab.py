"""NORTHSTAR · GRADE-AB 判卷档 A/B 评测运行器（B-QWEN 假设 A 备弹）。

使命（v3-output/B-QWEN/REPORT.md §4 假设 A）：判卷/诊断结构化面上，
qwen3.8-flash 档（blended $0.00025/1k）可替代现役 PRO 档 qwen3.7-plus 思考
（$0.0012/1k，-79% 成本），采纳门槛 = 「≥100 题一致率差 ≤3pp」。本模块把这个
门槛变成可执行资产：静态金标题包（grade_ab_pack.json，离散数学 100 题）+
双档对照运行器。**不切流**：零 env 改动、零产品代码改动，两档均经
LLMRouter ``select_model(force_tier=…)`` 显式 tier 参数直调。

臂定义（与假设 A 的 `LLM_TIER_PRO=dashscope_standard_thinking` 切换 wire 等价）：
- 档 A（现役，对照臂）：force_tier=PRO  → dashscope_reason（qwen3.7-plus 思考），
  wire 不注入 enable_thinking（provider 默认思考开）；
- 档 B（候选臂）：force_tier=STANDARD → dashscope_standard_thinking（qwen3.8-flash），
  wire 注入 enable_thinking=false（``dashscope_enable_thinking_param`` 键于
  ``config.tier``，与 env 换 PRO 池首位后的生产 wire 行为一致——即假设 A 实际
  上线形态）。

判卷契约（一次判卷）：输入=题干/标准答案/学生作答/学生自报置信度（镜像
``exam_sprint_diagnostic_service`` 诊断判卷面 confidence 口径）；输出=对错判定
verdict + 分数 score + 错误类型 error_type（ERROR_ANALYST 枚举：知识性/理解性/
计算性/粗心，另加 none/blank）+ 根因要点。JSON 解析消费
``LLMService._parse_json_payload`` 同口径（`<think>` 剥离 + 块提取）。

纯净性红线（评测有效性）：live 路径**绕过 llm_fallback_manager / 熔断器**，
router 解析后直调 ``OpenAICompatibleProvider.chat``——降级链若介入会把 B 臂
污染成其他模型，A/B 即失效。失败按题记 error，不换模型。

判定门槛（B-QWEN §4 冻结，防事后合理化）：
- gate ①：错误类型分类一致率（vs 金标）差 ≤ 3.0pp → pass；
- gate ②：JSON 解析成功率差 ≤ 2.0pp → pass；
- 两条全过 → adoption_signal=pass（成本锚点比另报，不参与判定）。

用法（backend/ 下）::

    # 无 key 装配自检（纪律：绝不调真实 LLM）
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        python3.11 tests/northstar_eval/grade_ab.py --dry-run

    # 真实 key 冒烟（主会话执行；worktree 无 .env）：
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        DASHSCOPE_API_KEY=sk-... python3.11 tests/northstar_eval/grade_ab.py \
        --limit 5            # 先 5 题冒烟再全量

    # 全量（100 题 ×2 臂；串行，预计 A 臂 ~8min + B 臂 ~2min）
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        DASHSCOPE_API_KEY=sk-... python3.11 tests/northstar_eval/grade_ab.py

输出：控制台逐题对照表 + 汇总/gate 判定；JSON 落盘
``$GRADE_AB_OUT_DIR``（默认 <repo>/v3-output/GRADE-AB/runs）/
``grade_ab_run_<ts>.json``（逐题两臂判定/一致项/分歧清单/成本估算/时延）。
凭据不落盘：api_key 只以是否在场布尔出现在证据里。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# 模块可被 `python3 -m tests.northstar_eval.grade_ab` 与
# `python3.11 tests/northstar_eval/grade_ab.py`（卡面 dry-run 命令）两种方式调起：
# 后者 sys.path[0] 是本目录，需先把 backend/ 挂上才能 import app.*。
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SCHEMA_RUN = "sparkle.northstar_eval.grade_ab.run.v1"

#: 判定门槛（B-QWEN 假设 A 冻结值，单位：百分点 pp）
GATE_ERROR_TYPE_PP = 3.0
GATE_PARSE_RATE_PP = 2.0

#: 判卷协议常量（两臂同参，保证 A/B 单变量）
GRADING_TEMPERATURE = 0.3  # ERROR_ANALYST profile 温度（agent_profiles.py:415）
CALL_TIMEOUT_S_DEFAULT = 120.0  # PRO 思考档单题上限（real_drive WS 上限同量级）
RAW_HEAD_KEEP = 200  # 逐题原始输出截断留存（分歧取证用，证据瘦身）

SYSTEM_PROMPT = """你是 Sparkle 的错题判卷引擎（评测专用、只读）。给定题目、标准答案、学生作答与学生自报置信度，请判卷并只输出一个 JSON 对象（无其他文本、无 markdown 围栏）：
{"verdict":"correct|partial|wrong","score":<0到1的小数>,"error_type":"none|knowledge|understanding|calculation|careless|blank","brief":"不超过40字的根因要点"}
字段规则：
- verdict：correct=完全正确；partial=仅简答题部分正确（主结论对、次要部分缺失或有误）；wrong=错误或空白。
- score：1.0=全对；0.0=全错或空白；partial 按要点比例给 0~1 之间。
- error_type（学生错误类型，verdict=correct 时恒为 none）：none=无错；knowledge=概念/定理/公式记错；understanding=概念知道但理解或应用偏差；calculation=方法思路对但运算错；careless=笔误/漏看条件/抄写滑笔（实质思路正确）；blank=未作答（作答为空时必为 blank 且 verdict=wrong）。
- brief：一句话定位错在哪一步/哪个概念；correct 时写"无"。"""


# ---------------------------------------------------------------------------
# app 模块延迟导入（--help / json 校验不触发 settings 装配）
# ---------------------------------------------------------------------------


def _app_imports():
    """按需导入 app.core.*：返回 (AgentRole, ModelTier, TaskType, llm_router, enable_thinking_param)。"""
    from app.core.agent_profiles import AgentRole, ModelTier, TaskType
    from app.core.llm_router import dashscope_enable_thinking_param, llm_router

    return AgentRole, ModelTier, TaskType, llm_router, dashscope_enable_thinking_param


# ---------------------------------------------------------------------------
# 题包：加载 + 校验 + 构成表
# ---------------------------------------------------------------------------

VERDICT_VOCAB = ("correct", "partial", "wrong")
ERROR_TYPE_VOCAB = ("none", "knowledge", "understanding", "calculation", "careless", "blank")
QTYPE_VOCAB = ("single_choice", "judge", "short_answer")
CONFIDENCE_VOCAB = ("certain", "fuzzy", "guess")
#: 部分正确的评测分档约定（产品确定性 grader 是连续分；本包金标按 0.5 档）
GOLD_SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
MIN_PACK_QUESTIONS = 100  # B-QWEN 假设 A 门槛的题量下限


def load_pack(path: Path) -> dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_pack(pack)
    if problems:
        raise SystemExit("pack validation failed:\n  - " + "\n  - ".join(problems))
    return pack


def validate_pack(pack: dict[str, Any]) -> list[str]:
    """结构+语义校验（dry-run 与 live 同门：坏包不许进评测）。"""
    problems: list[str] = []
    if pack.get("schema") != "sparkle.northstar_eval.grade_ab.pack.v1":
        problems.append(f"unexpected schema: {pack.get('schema')!r}")
    questions = pack.get("questions") or []
    if len(questions) < MIN_PACK_QUESTIONS:
        problems.append(f"question count {len(questions)} < {MIN_PACK_QUESTIONS} (B-QWEN gate floor)")
    seen: set[str] = set()
    for q in questions:
        qid = str(q.get("id", ""))
        where = f"[{qid or '?'}]"
        if qid in seen:
            problems.append(f"{where} duplicate id")
        seen.add(qid)
        if q.get("qtype") not in QTYPE_VOCAB:
            problems.append(f"{where} bad qtype {q.get('qtype')!r}")
        if q.get("student_confidence") not in CONFIDENCE_VOCAB:
            problems.append(f"{where} bad student_confidence {q.get('student_confidence')!r}")
        gold = q.get("gold") or {}
        if gold.get("verdict") not in VERDICT_VOCAB:
            problems.append(f"{where} bad gold.verdict {gold.get('verdict')!r}")
        if gold.get("error_type") not in ERROR_TYPE_VOCAB:
            problems.append(f"{where} bad gold.error_type {gold.get('error_type')!r}")
        if not str(gold.get("brief") or "").strip():
            problems.append(f"{where} gold.brief empty")
        if q.get("author_confidence") not in ("high", "medium"):
            problems.append(f"{where} author_confidence must be high|medium（诚实申报面）")
        answer = str(q.get("student_answer") or "")
        if q["qtype"] == "single_choice":
            choices = q.get("choices") or []
            if q.get("standard_answer") not in choices:
                problems.append(f"{where} standard_answer not among choices")
            if answer and answer not in choices:
                problems.append(f"{where} student_answer not among choices")
        elif q["qtype"] == "judge":
            if q.get("standard_answer") not in ("对", "错"):
                problems.append(f"{where} judge standard_answer must be 对/错")
            if answer and answer not in ("对", "错"):
                problems.append(f"{where} judge student_answer must be 对/错")
        # 语义互锁：correct↔none、blank↔空作答
        if gold.get("verdict") == "correct" and gold.get("error_type") != "none":
            problems.append(f"{where} correct verdict must pair error_type=none")
        if gold.get("error_type") == "blank" and answer != "":
            problems.append(f"{where} blank gold but non-empty student_answer")
        if answer == "" and gold.get("error_type") != "blank":
            problems.append(f"{where} empty student_answer must pair error_type=blank")
    return problems


def pack_composition(pack: dict[str, Any]) -> dict[str, Any]:
    questions = pack["questions"]
    return {
        "question_count": len(questions),
        "verdicts": dict(Counter(q["gold"]["verdict"] for q in questions)),
        "error_types": dict(Counter(q["gold"]["error_type"] for q in questions)),
        "qtypes": dict(Counter(q["qtype"] for q in questions)),
        "domains": dict(Counter(q["domain"] for q in questions)),
        "confidences": dict(Counter(q["student_confidence"] for q in questions)),
        "boundaries": dict(Counter(str(q.get("boundary")) for q in questions)),
        "author_confidence": dict(Counter(q["author_confidence"] for q in questions)),
    }


def build_messages(q: dict[str, Any]) -> list[dict[str, str]]:
    """一次判卷的输入装配（两臂逐字节相同——A/B 单变量=模型档位）。"""
    item: dict[str, Any] = {
        "题目类型": q["qtype"],
        "题干": q["stem"],
        "标准答案": q["standard_answer"],
        "学生作答": q["student_answer"] if q["student_answer"] else "（空白，未作答）",
        "学生自报置信度": q["student_confidence"],
    }
    if q["qtype"] == "single_choice":
        item["选项"] = " | ".join(q["choices"])
    user = json.dumps(item, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请判卷：\n{user}"},
    ]


# ---------------------------------------------------------------------------
# 双档路由解析（LLMRouter 显式 tier 参数直调——不依赖 env 切换）
# ---------------------------------------------------------------------------


def resolve_arm(tier_name: str) -> dict[str, Any]:
    """tier → 实际模型解析证据（model_key/价格/wire 思考参数/key 在场）。"""
    AgentRole, ModelTier, TaskType, llm_router, enable_thinking_param = _app_imports()
    tier = ModelTier[tier_name]
    selection = llm_router.select_model(
        AgentRole.ERROR_ANALYST,
        task_type=TaskType.ERROR_DIAGNOSIS,
        force_tier=tier,  # 显式 tier 直调：生产同一入口（llm_router.select_model），env 不动
    )
    client_kwargs = llm_router.get_openai_client_kwargs(selection)
    wire = enable_thinking_param(selection.config.tier, selection.config.thinking_mode)
    return {
        "arm_tier_requested": tier_name,
        "resolved_tier": selection.config.tier.value,
        "model_key": selection.model_key,
        "model_name": selection.config.model_name,
        "provider": selection.config.provider.value,
        "cost_per_1k_usd": selection.config.cost_per_1k_tokens,
        "avg_latency_ms_registered": selection.config.avg_latency_ms,
        "thinking_wire": wire if wire is not None else "not-injected(provider-default-thinking-on)",
        "extra_body": client_kwargs.get("extra_body"),
        "api_key_present": bool(client_kwargs.get("api_key")),
        "selection_reason": selection.reason,
    }


def est_tokens(text: str) -> int:
    """诚实粗估（heuristic）：CJK≈0.6 token/字，非 CJK≈0.25 token/字符。仅供两臂相对比较。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return int(round(cjk * 0.6 + (len(text) - cjk) * 0.25))


# ---------------------------------------------------------------------------
# live 判卷（provider 直调，零 fallback——纯净性红线）
# ---------------------------------------------------------------------------


def _parse_grader_output(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """消费 LLMService._parse_json_payload 同口径（<think> 剥离 + JSON 块提取）。

    返回 (payload, parse_error)。payload 存在时再做枚举归一。
    """
    from app.services.llm_service import LLMService

    payload = LLMService._parse_json_payload(raw, response_kind="reasoning")
    if not isinstance(payload, dict):
        return None, "json_not_object" if payload is not None else "json_unparseable"
    return payload, None


def _normalize_judgement(payload: dict[str, Any]) -> dict[str, Any]:
    verdict = str(payload.get("verdict", "")).strip().lower()
    error_type = str(payload.get("error_type", "")).strip().lower()
    try:
        score = max(0.0, min(1.0, float(payload.get("score"))))
    except (TypeError, ValueError):
        score = None
    return {
        "verdict": verdict if verdict in VERDICT_VOCAB else f"invalid:{verdict or 'missing'}",
        "score": score,
        "error_type": error_type if error_type in ERROR_TYPE_VOCAB else f"invalid:{error_type or 'missing'}",
        "brief": str(payload.get("brief") or "")[:120],
        "enum_valid": verdict in VERDICT_VOCAB and error_type in ERROR_TYPE_VOCAB,
    }


async def grade_arm_live(
    arm_label: str,
    arm: dict[str, Any],
    questions: list[dict[str, Any]],
    call_timeout_s: float,
) -> list[dict[str, Any]]:
    """单臂串行判卷。失败按题记 error（不降级、不换模型——评测纯净性红线）。"""
    from app.core.llm_router import llm_router
    from app.services.llm.providers import OpenAICompatibleProvider

    # 由本臂解析证据重建 selection 级 kwargs（与 _build_provider_for_selection 同构）
    AgentRole, ModelTier, TaskType, _llm_router, _etp = _app_imports()
    selection = llm_router.select_model(
        AgentRole.ERROR_ANALYST, task_type=TaskType.ERROR_DIAGNOSIS, force_tier=ModelTier[arm["arm_tier_requested"]]
    )
    client_kwargs = llm_router.get_openai_client_kwargs(selection)
    request_kwargs = {
        k: v for k, v in client_kwargs.items() if k not in {"api_key", "base_url", "model", "temperature"}
    }
    provider = OpenAICompatibleProvider(
        api_key=client_kwargs["api_key"], base_url=client_kwargs["base_url"], timeout_seconds=call_timeout_s
    )
    if not provider.has_api_key:
        raise SystemExit(
            f"arm {arm_label}: DASHSCOPE_API_KEY 为空——真实运行需主会话注入 key"
            "（worktree 无 .env，属预期；--dry-run 不需要 key）"
        )

    results: list[dict[str, Any]] = []
    for q in questions:
        messages = build_messages(q)
        prompt_text = messages[0]["content"] + messages[1]["content"]
        started = time.monotonic()
        entry: dict[str, Any] = {"id": q["id"], "latency_ms": None, "est_prompt_tokens": est_tokens(prompt_text)}
        try:
            raw = await asyncio.wait_for(
                provider.chat(
                    messages,
                    model=client_kwargs["model"],
                    temperature=GRADING_TEMPERATURE,
                    **request_kwargs,
                ),
                timeout=call_timeout_s,
            )
            entry["latency_ms"] = int((time.monotonic() - started) * 1000)
            entry["raw_head"] = raw[:RAW_HEAD_KEEP]
            entry["est_completion_tokens"] = est_tokens(raw)
            payload, parse_error = _parse_grader_output(raw)
            if payload is None:
                entry.update({"parse_ok": False, "parse_error": parse_error, "judgement": None})
            else:
                judgement = _normalize_judgement(payload)
                entry.update({"parse_ok": True, "parse_error": None, "judgement": judgement})
            entry["est_cost_usd"] = round(
                (entry["est_prompt_tokens"] + entry.get("est_completion_tokens", 0)) / 1000.0 * arm["cost_per_1k_usd"],
                6,
            )
        except Exception as exc:  # noqa: BLE001 — 单题失败原样入证据，绝不降级重试换模型
            entry["latency_ms"] = int((time.monotonic() - started) * 1000)
            entry.update(
                {
                    "parse_ok": False,
                    "parse_error": f"call_failed:{type(exc).__name__}",
                    "judgement": None,
                    "error": repr(exc)[:300],
                    "est_cost_usd": 0.0,
                }
            )
        results.append(entry)
        mark = entry["judgement"]["verdict"] if entry.get("judgement") else (entry.get("parse_error") or "?")
        print(f"  [{arm_label}] {q['id']}: {mark} ({entry['latency_ms']}ms)")
    return results


# ---------------------------------------------------------------------------
# 对照与判定
# ---------------------------------------------------------------------------


def _pctl(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, math.ceil(p * len(ordered)) - 1)
    return round(ordered[idx], 1)


def judge_question(entry: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """单题单臂 vs 金标：verdict/error_type 命中 + score 绝对误差。"""
    j = entry.get("judgement")
    if not entry.get("parse_ok") or j is None:
        return {"verdict_match": False, "error_type_match": False, "score_abs_err": None}
    return {
        "verdict_match": j["verdict"] == gold["verdict"],
        "error_type_match": j["error_type"] == gold["error_type"],
        "score_abs_err": (None if j["score"] is None else round(abs(j["score"] - GOLD_SCORE[gold["verdict"]]), 3)),
    }


def build_report(pack: dict[str, Any], runs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """对照表 + 汇总 + gate 判定（runs: arm_label -> 逐题结果）。"""
    questions = pack["questions"]
    gold_by_id = {q["id"]: q for q in questions}
    per_question: list[dict[str, Any]] = []
    arm_labels = sorted(runs)

    def _arm_metrics(label: str) -> dict[str, Any]:
        entries = runs[label]
        judged = [judge_question(e, gold_by_id[e["id"]]["gold"]) for e in entries]
        n = len(entries)
        parse_ok = sum(1 for e in entries if e.get("parse_ok"))
        latencies = [e["latency_ms"] for e in entries if e.get("latency_ms") is not None]
        return {
            "questions": n,
            "parse_ok": parse_ok,
            "parse_rate": round(parse_ok / max(n, 1), 4),
            "verdict_accuracy": round(sum(1 for j in judged if j["verdict_match"]) / max(n, 1), 4),
            "error_type_match_rate": round(sum(1 for j in judged if j["error_type_match"]) / max(n, 1), 4),
            "score_mae": (
                round(
                    sum(j["score_abs_err"] for j in judged if j["score_abs_err"] is not None)
                    / max(sum(1 for j in judged if j["score_abs_err"] is not None), 1),
                    4,
                )
            ),
            "total_est_cost_usd": round(sum(e.get("est_cost_usd", 0.0) for e in entries), 4),
            "latency_ms_p50": _pctl([float(x) for x in latencies], 0.50),
            "latency_ms_p95": _pctl([float(x) for x in latencies], 0.95),
            "call_failures": sum(1 for e in entries if e.get("parse_error", "").startswith("call_failed")),
        }

    metrics = {label: _arm_metrics(label) for label in arm_labels}
    for q in questions:
        row: dict[str, Any] = {
            "id": q["id"],
            "domain": q["domain"],
            "qtype": q["qtype"],
            "boundary": q.get("boundary"),
            "gold": {"verdict": q["gold"]["verdict"], "error_type": q["gold"]["error_type"]},
        }
        for label in arm_labels:
            entry = next(e for e in runs[label] if e["id"] == q["id"])
            row[label] = {
                "verdict": (entry.get("judgement") or {}).get("verdict"),
                "error_type": (entry.get("judgement") or {}).get("error_type"),
                "parse_ok": entry.get("parse_ok", False),
                "vs_gold": judge_question(entry, q["gold"]),
            }
        if len(arm_labels) == 2:
            a, b = runs[arm_labels[0]], runs[arm_labels[1]]
            ea = next(e for e in a if e["id"] == q["id"])
            eb = next(e for e in b if e["id"] == q["id"])
            ja, jb = ea.get("judgement"), eb.get("judgement")
            row["mutual"] = {
                "verdict_agree": bool(ja and jb and ja["verdict"] == jb["verdict"]),
                "error_type_agree": bool(ja and jb and ja["error_type"] == jb["error_type"]),
            }
        per_question.append(row)

    summary: dict[str, Any] = {"arms": metrics}
    gate: dict[str, Any] = {"evaluated": False, "adoption_signal": "not-evaluated"}
    if len(arm_labels) == 2:
        m_a, m_b = metrics[arm_labels[0]], metrics[arm_labels[1]]
        etype_diff_pp = round(abs(m_a["error_type_match_rate"] - m_b["error_type_match_rate"]) * 100, 2)
        parse_diff_pp = round(abs(m_a["parse_rate"] - m_b["parse_rate"]) * 100, 2)
        gate_1_pass = etype_diff_pp <= GATE_ERROR_TYPE_PP
        gate_2_pass = parse_diff_pp <= GATE_PARSE_RATE_PP
        mutual_verdict = round(sum(1 for r in per_question if r["mutual"]["verdict_agree"]) / len(per_question), 4)
        mutual_etype = round(sum(1 for r in per_question if r["mutual"]["error_type_agree"]) / len(per_question), 4)
        summary["delta"] = {
            "error_type_match_diff_pp": etype_diff_pp,
            "parse_rate_diff_pp": parse_diff_pp,
            "mutual_verdict_agree_rate": mutual_verdict,
            "mutual_error_type_agree_rate": mutual_etype,
            "cost_ratio_b_over_a": (
                round(m_b["total_est_cost_usd"] / m_a["total_est_cost_usd"], 4)
                if m_a["total_est_cost_usd"] > 0
                else None
            ),
        }
        gate = {
            "evaluated": True,
            "gate_1_error_type_pp": {"threshold": GATE_ERROR_TYPE_PP, "actual": etype_diff_pp, "pass": gate_1_pass},
            "gate_2_parse_rate_pp": {"threshold": GATE_PARSE_RATE_PP, "actual": parse_diff_pp, "pass": gate_2_pass},
            "adoption_signal": "pass" if (gate_1_pass and gate_2_pass) else "reject",
        }
    disagreements = [
        {
            "id": r["id"],
            "gold": r["gold"],
            "mutual": r.get("mutual"),
            "arms": {label: r[label] for label in arm_labels},
        }
        for r in per_question
        if (len(arm_labels) == 2 and not (r["mutual"]["verdict_agree"] and r["mutual"]["error_type_agree"]))
        or any(not r[label]["vs_gold"]["verdict_match"] for label in arm_labels)
    ]
    return {"per_question": per_question, "summary": summary, "gate": gate, "disagreements": disagreements}


# ---------------------------------------------------------------------------
# 控制台呈现
# ---------------------------------------------------------------------------


def print_table(report: dict[str, Any], arm_labels: list[str]) -> None:
    head = (
        f"{'id':6} {'domain':8} {'gold(v/e)':22} "
        + " ".join(f"{f'{label}(v/e)':30} {'ok':4}" for label in arm_labels)
        + ("  eq" if len(arm_labels) == 2 else "")
    )
    print(head)
    print("-" * len(head))
    for row in report["per_question"]:
        gold = f"{row['gold']['verdict']}/{row['gold']['error_type']}"
        cells = []
        for label in arm_labels:
            cell = row[label]
            v = (cell["verdict"] or "null")[:18]
            e = (cell["error_type"] or "null")[:9]
            cells.append(f"{v:18} {e:9} {str(cell['parse_ok'])[0]:1}")
        eq = ""
        if len(arm_labels) == 2:
            eq = "v" if row["mutual"]["verdict_agree"] else ("e" if row["mutual"]["error_type_agree"] else "-")
        print(
            f"{row['id']:6} {row['domain'][:7]:8} {gold:22} {cells[0]:30} {cells[1]:30}  {eq}"
            if len(arm_labels) == 2
            else f"{row['id']:6} {row['domain'][:7]:8} {gold:22} {cells[0]:30}"
        )


def print_summary(arm_evidence: dict[str, dict[str, Any]], report: dict[str, Any], arm_labels: list[str]) -> None:
    print("\n=== 汇总（metrics vs 金标） ===")
    for label in arm_labels:
        m = report["summary"]["arms"][label]
        ev = arm_evidence[label]
        print(
            f"  档 {label}: {ev['model_key']} ({ev['model_name']}, tier={ev['resolved_tier']}, "
            f"${ev['cost_per_1k_usd']}/1k, thinking_wire={ev['thinking_wire']})\n"
            f"        verdict_acc={m['verdict_accuracy']}  etype_match={m['error_type_match_rate']}  "
            f"parse_rate={m['parse_rate']}  score_MAE={m['score_mae']}\n"
            f"        cost_est=${m['total_est_cost_usd']}  latency p50={m['latency_ms_p50']}ms "
            f"p95={m['latency_ms_p95']}ms  call_fail={m['call_failures']}"
        )
    if report["gate"]["evaluated"]:
        d = report["summary"]["delta"]
        g = report["gate"]
        print(
            f"\n  gate ①错误类型一致率差: {d['error_type_match_diff_pp']}pp (≤{GATE_ERROR_TYPE_PP}) → "
            f"{'PASS' if g['gate_1_error_type_pp']['pass'] else 'FAIL'}\n"
            f"  gate ②JSON 解析成功率差: {d['parse_rate_diff_pp']}pp (≤{GATE_PARSE_RATE_PP}) → "
            f"{'PASS' if g['gate_2_parse_rate_pp']['pass'] else 'FAIL'}\n"
            f"  互判一致率: verdict={d['mutual_verdict_agree_rate']} etype={d['mutual_error_type_agree_rate']}\n"
            f"  成本估算比 B/A: {d['cost_ratio_b_over_a']}\n"
            f"  ⇒ adoption_signal = {g['adoption_signal']}"
        )
    if report["disagreements"]:
        ids = ", ".join(d["id"] for d in report["disagreements"])
        print(f"\n  分歧/错判清单（{len(report['disagreements'])} 题）: {ids}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def default_out_dir() -> Path:
    env = os.environ.get("GRADE_AB_OUT_DIR")
    if env:
        return Path(env)
    return BACKEND_DIR.parent / "v3-output" / "GRADE-AB" / "runs"


def run(args: argparse.Namespace) -> int:
    started = time.monotonic()
    AgentRole, ModelTier, TaskType, llm_router, _ = _app_imports()  # noqa: F841 — 装配自检
    pack_path = Path(args.pack)
    pack = load_pack(pack_path)
    questions = pack["questions"][: args.limit] if args.limit else pack["questions"]
    composition = pack_composition(pack)

    arm_labels = [a.strip().upper() for a in args.arm.split(",") if a.strip()]
    tier_by_arm = {"A": "PRO", "B": "STANDARD"}
    arm_evidence = {label: resolve_arm(tier_by_arm[label]) for label in arm_labels}

    print("=== GRADE-AB 判卷档 A/B 评测（B-QWEN 假设 A 备弹） ===")
    print(
        f"mode={'dry-run' if args.dry_run else 'live'}  pack={pack_path.name}  "
        f"questions={len(questions)}/{composition['question_count']}  out={args.out_dir}"
    )
    for label in arm_labels:
        ev = arm_evidence[label]
        print(
            f"  档 {label}: force_tier={ev['arm_tier_requested']} → {ev['model_key']} ({ev['model_name']}, "
            f"${ev['cost_per_1k_usd']}/1k, thinking_wire={ev['thinking_wire']}, key={'有' if ev['api_key_present'] else '无'})"
        )
    if len(arm_evidence) == 2 and all(arm_evidence[l].get("cost_per_1k_usd") for l in arm_evidence):
        ratio = arm_evidence["B"]["cost_per_1k_usd"] / arm_evidence["A"]["cost_per_1k_usd"]
        print(f"  成本锚点比 B/A = {ratio:.4f}（{-100 * (1 - ratio):.1f}%，B-QWEN 预期 -79%）")
    print(f"  gates: ①错误类型一致率差 ≤ {GATE_ERROR_TYPE_PP}pp；②JSON 解析成功率差 ≤ {GATE_PARSE_RATE_PP}pp")
    print("  题包构成: " + json.dumps(composition, ensure_ascii=False, sort_keys=True))

    if args.dry_run:
        # 装配自检：全量题渲染判卷提示词（模板/字段完整性），不调任何 LLM。
        rendered = 0
        prompt_sha = hashlib.sha256()
        for q in questions:
            messages = build_messages(q)
            if len(messages) != 2 or not messages[1]["content"]:
                raise SystemExit(f"prompt assembly failed for {q['id']}")
            prompt_sha.update(json.dumps(messages, ensure_ascii=False).encode())
            rendered += 1
        run_payload = {
            "schema": SCHEMA_RUN,
            "meta": _meta(pack_path, "dry-run", questions, arm_evidence, prompt_sha.hexdigest()),
            "composition": composition,
            "summary": {
                "arms": {},
                "note": "dry-run 装配骨架：无 LLM 结果，仅证明题包加载/双档路由解析/提示词装配/落盘通路",
            },
            "gate": {"evaluated": False, "adoption_signal": "not-evaluated"},
            "disagreements": [],
            "per_question": [{"id": q["id"], "arm_a": None, "arm_b": None} for q in questions],
        }
        out_path = _write_run(args.out_dir, run_payload)
        print(
            f"\n[dry-run] 提示词装配 {rendered} 题 OK（prompt_sha256={prompt_sha.hexdigest()[:16]}…）；"
            f"双档路由解析 OK；输出骨架已落盘：{out_path}"
        )
        return 0

    # live：key 预检（诚实拒绝，不半跑）
    if not arm_evidence[arm_labels[0]]["api_key_present"]:
        raise SystemExit(
            "DASHSCOPE_API_KEY 为空——live 运行需注入 key。worktree 无 .env 属预期，"
            "由主会话执行（见模块 docstring 冒烟命令）；或先 --dry-run。"
        )

    runs: dict[str, list[dict[str, Any]]] = {}
    for label in arm_labels:
        print(f"\n--- 档 {label} 判卷中（{len(questions)} 题，串行、零 fallback） ---")
        runs[label] = asyncio.run(grade_arm_live(label, arm_evidence[label], questions, args.timeout))

    report = build_report(pack, runs)
    prompt_sha = hashlib.sha256()
    for q in questions:
        prompt_sha.update(json.dumps(build_messages(q), ensure_ascii=False).encode())
    run_payload = {
        "schema": SCHEMA_RUN,
        "meta": _meta(pack_path, "live", questions, arm_evidence, prompt_sha.hexdigest()),
        "composition": composition,
        **report,
    }
    out_path = _write_run(args.out_dir, run_payload)
    print_table(report, arm_labels)
    print_summary(arm_evidence, report, arm_labels)
    print(f"\n证据已落盘: {out_path}  (耗时 {time.monotonic() - started:.1f}s)")
    return 0


def _meta(
    pack_path: Path,
    mode: str,
    questions: list[dict[str, Any]],
    arm_evidence: dict[str, dict[str, Any]],
    prompt_sha: str,
) -> dict[str, Any]:
    from app.core.llm_router import llm_router

    return {
        "run_id": f"GRADE-AB-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "pack_path": str(pack_path),
        "pack_sha256": hashlib.sha256(pack_path.read_bytes()).hexdigest(),
        "question_count": len(questions),
        "grading_temperature": GRADING_TEMPERATURE,
        "agent_role": "ERROR_ANALYST",
        "task_type": "ERROR_DIAGNOSIS",
        "routing_entry": "llm_router.select_model(force_tier=…)，env 未切换",
        "arms": arm_evidence,
        "registered_model_configs": len(llm_router._available_models),
        "gates": {"error_type_pp": GATE_ERROR_TYPE_PP, "parse_rate_pp": GATE_PARSE_RATE_PP},
        "prompt_sha256": prompt_sha,
        "cost_estimation": "est_tokens=CJK*0.6+other*0.25（heuristic，两臂同提示词故相对可比）；单价取 router 注册锚点",
        "credentials": "api_key 仅以布尔在场记录，绝不落盘",
    }


def _write_run(out_dir: Path, payload: dict[str, Any]) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"grade_ab_run_{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GRADE-AB 判卷档 A/B 评测运行器（B-QWEN 假设 A 备弹；不切流）")
    parser.add_argument(
        "--dry-run", action="store_true", help="无 key 装配自检：题包加载/双档路由解析/提示词装配/落盘，不调 LLM"
    )
    parser.add_argument(
        "--pack",
        default=str(BACKEND_DIR / "tests" / "northstar_eval" / "grade_ab_pack.json"),
        help="题包路径（默认同目录 grade_ab_pack.json）",
    )
    parser.add_argument("--out-dir", default=str(default_out_dir()), help="证据目录（默认 v3-output/GRADE-AB/runs）")
    parser.add_argument("--arm", default="A,B", help="跑哪些臂（默认 A,B）")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 题（冒烟用）")
    parser.add_argument("--timeout", type=float, default=CALL_TIMEOUT_S_DEFAULT, help="单题调用上限秒")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
