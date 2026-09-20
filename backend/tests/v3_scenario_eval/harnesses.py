"""Q-01 · 三类 harness 的确定性参考实现（contract-simulation surrogate）。

诚实边界（先读这段再读结果）：

- 本模块所有 surrogate 是**纯函数参考实现**：把每个类目的 V3 行为契约（冻结词表
  输入 → 结构化观测）编码为可执行规范，用于①钉住每个 case 的 pass 判据、②给
  未来接入真模型/真系统/真 UI 的同一套 checker 提供基线。它们**不是**后端生产
  代码，verdict 语义是 contract-simulation（provenance 逐 case 记录，见
  runner.VERDICT_SEMANTICS）。
- 真模型路径只预留接口（``RealModelAdapter``）：本轮**无条件拒绝执行**（真实
  LLM 0 次红线），provider config 里配了真 provider 的 round，其 model 型 case
  一律 honest-unsupported，绝不降级成 PASS。
- 随机性只来自显式 seed 派生的 ``random.Random``，且只作用于带阈值的连续指标
  （检索分/合成时延），判定 checker 与阈值间留足裕度 → 同 seed 逐字节一致、
  跨 seed 判定稳定、指标可见 seed 生效。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 真模型预留接口（本轮零调用）
# ---------------------------------------------------------------------------


class RealModelDisabledError(RuntimeError):
    """真模型适配器被拒绝执行（本轮红线：真实 LLM 0 次）。"""


class RealModelAdapter:
    """真模型 provider 预留接口。

    Future（本轮不实现、不调用）：按 provider/base_url/api_key_env 发起
    离线评测请求。本轮任何路径调用 :meth:`complete` 都抛
    :class:`RealModelDisabledError`——没有开关、没有旁路。
    """

    enabled = False

    def complete(self, prompt: str, *, provider: str, model: str) -> str:  # pragma: no cover
        raise RealModelDisabledError(
            "real model adapter is a reserved interface; real LLM calls are forbidden this round"
        )


@dataclass(frozen=True)
class ProviderConfig:
    """provider 配置（--provider-config JSON 的冻结 schema）。"""

    provider: str = "mock"
    model: str = "reference-mock-v1"
    base_url: str = ""
    api_key_env: str = ""

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
        }


def parse_provider_config(raw: dict[str, Any] | None) -> ProviderConfig:
    raw = raw or {}
    return ProviderConfig(
        provider=str(raw.get("provider", "mock")),
        model=str(raw.get("model", "reference-mock-v1")),
        base_url=str(raw.get("base_url", "")),
        api_key_env=str(raw.get("api_key_env", "")),
    )


# ---------------------------------------------------------------------------
# surrogate 统一出口
# ---------------------------------------------------------------------------


@dataclass
class SurrogateRun:
    """一次探针执行的结构化观测（checker 只读 observations/metrics）。"""

    observations: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# model harness · memory（记忆范围/状态/来源）
# ---------------------------------------------------------------------------

_MEM_SCOPE_GLOBAL = "global"
_MEM_SCOPE_DAY = "day"
_MEM_SCOPE_GOAL = "goal"
_MEM_KIND_EXPLICIT = "explicit"
_MEM_KIND_OBSERVATION = "observation"
_MEM_STATUS_ACTIVE = "active"
_MEM_STATUS_REVOKED = "revoked"
_MEM_STATUS_SUPERSEDED = "superseded"


def _memory_case(input_token: str) -> dict[str, Any]:
    """把 memory 类目封闭输入词表映射为构造记忆条目 + 探针查询。

    entry 词表：kind(explicit/observation) × scope(global/day/goal) × domain（探针匹配键）。
    """
    table = {
        "confirmed preference should help": {
            "entries": [{"kind": "explicit", "scope": "global", "domain": "pref", "text": "evidence-first"}],
            "probe": {"day": 0, "domain": "pref"},
            "expect_surface": True,
        },
        "today-only constraint must not globalize": {
            "entries": [{"kind": "explicit", "scope": "day", "domain": "constraint", "text": "today only"}],
            "probe": {"day": 1, "domain": "constraint"},
            "expect_surface": False,
        },
        "revoked memory must not use": {
            "entries": [{"kind": "explicit", "scope": "global", "domain": "old", "text": "x", "status": "revoked"}],
            "probe": {"day": 0, "domain": "old"},
            "expect_surface": False,
        },
        "irrelevant memory must stay silent": {
            "entries": [{"kind": "observation", "scope": "global", "domain": "coding", "text": "likes rust"}],
            "probe": {"day": 0, "domain": "cooking"},
            "expect_surface": False,
        },
        "preference changed": {
            "entries": [
                {"kind": "explicit", "scope": "global", "domain": "style", "text": "bullets", "ts": 1},
                {
                    "kind": "explicit",
                    "scope": "global",
                    "domain": "style",
                    "text": "prose",
                    "ts": 2,
                    "supersedes": "bullets",
                },
            ],
            "probe": {"day": 0, "domain": "style"},
            "expect_surface": True,
        },
        "observation must not override explicit statement": {
            "entries": [
                {"kind": "explicit", "scope": "global", "domain": "pace", "text": "mornings", "ts": 1},
                {"kind": "observation", "scope": "global", "domain": "pace", "text": "evenings", "ts": 2},
            ],
            "probe": {"day": 0, "domain": "pace"},
            "expect_surface": True,
        },
    }
    if input_token not in table:
        raise KeyError(f"memory surrogate: unknown input {input_token!r}")
    return table[input_token]


def memory_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：显式 > 观察；revoked/superseded 不出；day 作用域过期不出。"""
    case = _memory_case(scenario_input)
    entries = sorted(case["entries"], key=lambda entry: entry.get("ts", 0))
    superseded_texts = {entry["supersedes"] for entry in entries if entry.get("supersedes")}
    explicit_domains = {
        entry["domain"] for entry in entries if entry["kind"] == _MEM_KIND_EXPLICIT and entry["scope"] != _MEM_SCOPE_DAY
    }
    surfaced: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("status", _MEM_STATUS_ACTIVE) == _MEM_STATUS_REVOKED:
            continue
        if entry["text"] in superseded_texts:
            continue
        if entry["scope"] == _MEM_SCOPE_DAY and case["probe"]["day"] > 0:
            continue
        if entry["domain"] != case["probe"]["domain"]:
            continue
        # 观察级记忆永远不能压过同域显式陈述。
        if entry["kind"] == _MEM_KIND_OBSERVATION and entry["domain"] in explicit_domains:
            continue
        surfaced.append(
            {
                "text": entry["text"],
                "kind": entry["kind"],
                "scope": entry["scope"],
                "status": _MEM_STATUS_ACTIVE,
                "provenance": f"{entry['kind']}-write-lane",
            }
        )
    expect = case["expect_surface"]
    matched = bool(surfaced) == expect
    match_score = round(0.90 + rng.uniform(-0.02, 0.02), 4) if matched else round(0.30 + rng.uniform(-0.02, 0.02), 4)
    return SurrogateRun(
        observations={
            "surfaced": surfaced,
            "expect_surface": expect,
            "probe": case["probe"],
            "match": matched,
            "provenance_available": all(item["provenance"] for item in surfaced),
        },
        metrics={"memory_match_score": match_score},
    )


# ---------------------------------------------------------------------------
# model harness · conflict（冲突消解）
# ---------------------------------------------------------------------------


def _conflict_case(input_token: str) -> dict[str, Any]:
    table = {
        "new explicit vs old inference": {
            "claims": [
                {"kind": "inferred", "ts": 1, "value": "old"},
                {"kind": "explicit", "ts": 2, "value": "new"},
            ],
            "expected_winner_value": "new",
            "expected_ask": False,
        },
        "global preference vs goal-specific preference": {
            "claims": [
                {"kind": "explicit", "ts": 1, "value": "global", "scope": "global"},
                {"kind": "explicit", "ts": 2, "value": "goal", "scope": "goal"},
            ],
            "expected_winner_value": "goal",
            "expected_ask": False,
        },
        "system fact vs stale user assumption": {
            "claims": [
                {"kind": "assumption", "ts": 1, "value": "stale"},
                {"kind": "system_fact", "ts": 2, "value": "fact"},
            ],
            "expected_winner_value": "fact",
            "expected_ask": False,
        },
        "two explicit statements different times": {
            "claims": [
                {"kind": "explicit", "ts": 1, "value": "earlier"},
                {"kind": "explicit", "ts": 2, "value": "later"},
            ],
            "expected_winner_value": "later",
            "expected_ask": False,
        },
        "behavior vs stated preference": {
            "claims": [
                {"kind": "behavior", "ts": 2, "value": "behavior"},
                {"kind": "explicit", "ts": 1, "value": "stated"},
            ],
            "expected_winner_value": "stated",
            "expected_ask": False,
        },
        "unsafe ambiguity": {
            "claims": [
                {"kind": "explicit", "ts": 1, "value": "a", "ambiguous_with": "b"},
                {"kind": "explicit", "ts": 1, "value": "b", "ambiguous_with": "a"},
            ],
            "expected_winner_value": None,
            "expected_ask": True,
        },
    }
    if input_token not in table:
        raise KeyError(f"conflict surrogate: unknown input {input_token!r}")
    return table[input_token]


_KIND_PRIORITY = {"system_fact": 0, "explicit": 1, "behavior": 2, "inferred": 3, "assumption": 4}


def conflict_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：权威级 → 显式性 → 作用域特定性 → 时间新者；真两可才 ask。"""
    case = _conflict_case(scenario_input)
    claims = list(case["claims"])
    ambiguous_pair = any("ambiguous_with" in claim for claim in claims)
    if ambiguous_pair:
        resolution_class = "deferred_ask"
        winner = None
        ask = True
    else:
        ranked = sorted(
            claims,
            key=lambda claim: (_KIND_PRIORITY[claim["kind"]], -claim["ts"], claim.get("scope") != "goal"),
        )
        winner = ranked[0]
        loser_kinds = {claim["kind"] for claim in ranked[1:]}
        if "inferred" in loser_kinds or "assumption" in loser_kinds:
            resolution_class = "authority_or_explicit_over_inferred"
        elif "behavior" in loser_kinds:
            resolution_class = "stated_over_behavior"
        elif any(claim.get("scope") == "goal" for claim in claims):
            resolution_class = "scope_specificity"
        else:
            resolution_class = "recency_explicit"
        ask = False
    surfaced_values = [winner["value"]] if winner is not None else []
    confidence = round(0.86 + rng.uniform(-0.05, 0.05), 4)
    return SurrogateRun(
        observations={
            "resolution_class": resolution_class,
            "surfaced_values": surfaced_values,
            "ask": ask,
            "suppressed": [claim["value"] for claim in claims if claim["value"] not in surfaced_values],
            "expected_winner_value": case["expected_winner_value"],
            "expected_ask": case["expected_ask"],
            "decision_changes": True,
        },
        metrics={"resolution_confidence": confidence},
    )


# ---------------------------------------------------------------------------
# model harness · allocation（行动分配）
# ---------------------------------------------------------------------------

_ALLOCATION_TABLE = {
    # input → (mode, ownership, risk_high, manual_work)
    "learn coding loop": ("coach", "high", False, False),
    "format files": ("agent_auto", "mechanical", False, False),
    "write thesis argument": ("human", "high", False, False),
    "book low-risk calendar slot": ("agent_auto", "mechanical", False, False),
    "send consequential message": ("agent_prepare_human_send", "medium", True, False),
    "search papers": ("agent_auto", "low", False, False),
    "practice exam": ("human", "high", False, False),
    "summarize notes": ("agent_auto", "low", False, False),
    "refactor user project": ("agent_prepare_approval", "medium", True, False),
    "reflect on failure": ("hybrid", "high", False, True),
}


def allocation_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：认知所有权定 mode；高风险必 approval；机械任务不摊给人。"""
    if scenario_input not in _ALLOCATION_TABLE:
        raise KeyError(f"allocation surrogate: unknown input {scenario_input!r}")
    mode, ownership, risk_high, manual_work = _ALLOCATION_TABLE[scenario_input]
    justification = f"ownership={ownership}, risk_high={risk_high}"
    return SurrogateRun(
        observations={
            "mode": mode,
            "ownership": ownership,
            "risk_high": risk_high,
            "approval_required": risk_high,
            "manual_work": manual_work,
            "justification": justification,
        },
        metrics={"allocation_utility": round(0.80 + rng.uniform(-0.04, 0.04), 4)},
    )


# ---------------------------------------------------------------------------
# model harness · proactive（主动建议）
# ---------------------------------------------------------------------------

_PROACTIVE_TABLE = {
    # input → (action, why_now, muted/cooldown 信号)
    "goal stalled": ("suggest", "stalled_14d_signal", False),
    "deadline approaching": ("suggest", "deadline_window", False),
    "quiet hours": ("NO_ACTION", "quiet_hours", True),
    "recent rejection": ("NO_ACTION", "cooldown_after_rejection", True),
    "same suggestion repeated": ("NO_ACTION", "repeat_suppressed", True),
    "upstream completed": ("suggest", "upstream_value_ready", False),
    "run awaiting user": ("surface_status", "awaiting_user_resume", False),
    "no new information": ("NO_ACTION", "no_new_value", False),
}


def proactive_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：无新价值即 NO_ACTION；mute/cooldown 压制；建议必带 why-now。"""
    if scenario_input not in _PROACTIVE_TABLE:
        raise KeyError(f"proactive surrogate: unknown input {scenario_input!r}")
    action, why_now, gated = _PROACTIVE_TABLE[scenario_input]
    return SurrogateRun(
        observations={
            "action": action,
            "why_now": why_now if action != "NO_ACTION" else "",
            "gated_by_mute_or_cooldown": gated,
            "suppressed_by_cooldown": action == "NO_ACTION" and gated,
        },
        metrics={"salience": round(rng.uniform(0.2, 0.9), 4)},
    )


# ---------------------------------------------------------------------------
# model harness · rag（检索/引用/权限版本）
# ---------------------------------------------------------------------------


def _rag_case(input_token: str) -> dict[str, Any]:
    table = {
        "relevant PDF chunk": {
            "docs": [{"id": "d1", "perm": True, "version": 2, "relevant": True, "text": "alpha"}],
            "cite_expect": True,
        },
        "irrelevant PDF": {
            "docs": [{"id": "d1", "perm": True, "version": 1, "relevant": False, "text": "zeta"}],
            "cite_expect": False,
        },
        "deleted document": {
            "docs": [{"id": "d1", "perm": True, "version": 1, "relevant": True, "deleted": True, "text": "beta"}],
            "cite_expect": False,
        },
        "newer document version": {
            "docs": [
                {"id": "d1", "perm": True, "version": 1, "relevant": True, "text": "old"},
                {"id": "d1", "perm": True, "version": 2, "relevant": True, "text": "new"},
            ],
            "cite_expect": True,
            "expected_version": 2,
        },
        "cross-user document": {
            "docs": [{"id": "d1", "perm": False, "version": 1, "relevant": True, "text": "secret"}],
            "cite_expect": False,
        },
        "citation mismatch": {
            "docs": [
                {"id": "d1", "perm": True, "version": 1, "relevant": True, "text": "gamma", "corrupt_citation": True}
            ],
            "cite_expect": False,
        },
        "long material JIT": {
            "docs": [{"id": "d1", "perm": True, "version": 1, "relevant": True, "text": "delta", "long": True}],
            "cite_expect": True,
        },
        "Chinese heading retrieval": {
            "docs": [
                {
                    "id": "d1",
                    "perm": True,
                    "version": 1,
                    "relevant": True,
                    "text": "第三章 实验方法",
                    "heading": "实验方法",
                }
            ],
            "cite_expect": True,
        },
        "code chunk": {
            "docs": [{"id": "d1", "perm": True, "version": 1, "relevant": True, "text": "def f():", "code": True}],
            "cite_expect": True,
        },
    }
    if input_token not in table:
        raise KeyError(f"rag surrogate: unknown input {input_token!r}")
    return table[input_token]


_RAG_CITE_THRESHOLD = 0.55
_RAG_JIT_TOKEN_BUDGET = 420


def rag_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：权限+版本+删除过滤在前，相关性阈值定引用，JIT 截断长料。"""
    case = _rag_case(scenario_input)
    visible: list[dict[str, Any]] = []
    latest_version: dict[str, int] = {}
    for doc in case["docs"]:
        latest_version[doc["id"]] = max(latest_version.get(doc["id"], 0), doc["version"])
    for doc in case["docs"]:
        if not doc["perm"] or doc.get("deleted") or doc["version"] != latest_version[doc["id"]]:
            continue
        base = 0.82 if doc["relevant"] else 0.18
        score = round(base + rng.uniform(-0.02, 0.02), 4)
        text = doc["text"]
        excerpt_tokens = min(_RAG_JIT_TOKEN_BUDGET, 40 + len(text) * 8) if doc.get("long") else 40 + len(text) * 8
        visible.append(
            {"id": doc["id"], "version": doc["version"], "score": score, "text": text, "excerpt_tokens": excerpt_tokens}
        )
    citations: list[dict[str, Any]] = []
    for item in visible:
        if item["score"] >= _RAG_CITE_THRESHOLD and case["docs"][0].get("corrupt_citation"):
            continue  # 引用校验不过关 → 引用被拦截（faithful）
        if item["score"] >= _RAG_CITE_THRESHOLD:
            citations.append({"doc_id": item["id"], "version": item["version"], "faithful": True})
    return SurrogateRun(
        observations={
            "surfaced": visible,
            "citations": citations,
            "cite_expect": case["cite_expect"],
            "expected_version": case.get("expected_version"),
            "permission_filter_applied": True,
            "jit_budget": _RAG_JIT_TOKEN_BUDGET,
        },
        metrics={"rag_top_score": max((item["score"] for item in visible), default=0.0)},
    )


# ---------------------------------------------------------------------------
# deterministic harness · agent_runtime（运行生命周期）
# ---------------------------------------------------------------------------

_AGENT_STATE_PENDING = "pending"
_AGENT_STATE_RUNNING = "running"
_AGENT_STATE_AWAITING_USER = "awaiting_user"
_AGENT_STATE_RECOVERABLE = "recoverable"
_AGENT_STATE_TERMINAL_SUCCESS = "terminal_success"
_AGENT_STATE_TERMINAL_FAILED = "terminal_failed"
_AGENT_STATE_CANCELLED = "cancelled"

_AGENT_ALLOWED_FINAL = {
    "worker killed": {_AGENT_STATE_RECOVERABLE},
    "tool timeout": {_AGENT_STATE_RECOVERABLE, _AGENT_STATE_TERMINAL_FAILED},
    "duplicate approval": {_AGENT_STATE_RUNNING, _AGENT_STATE_TERMINAL_SUCCESS},
    "app closed and reopened": {_AGENT_STATE_RECOVERABLE},
    "network partition after side effect": {_AGENT_STATE_RECOVERABLE, _AGENT_STATE_TERMINAL_SUCCESS},
    "budget exhausted": {_AGENT_STATE_TERMINAL_FAILED},
    "cancel while executing": {_AGENT_STATE_CANCELLED},
    "permission revoked mid-run": {_AGENT_STATE_RECOVERABLE, _AGENT_STATE_CANCELLED},
    "partial tool success": {_AGENT_STATE_RECOVERABLE, _AGENT_STATE_TERMINAL_SUCCESS},
    "provider 429": {_AGENT_STATE_RECOVERABLE},
}


def agent_runtime_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：journal 先记副作用再执行；恢复不改写账本；receipt 与账本一致。"""
    if scenario_input not in _AGENT_ALLOWED_FINAL:
        raise KeyError(f"agent_runtime surrogate: unknown input {scenario_input!r}")
    side_effect_count = (
        1
        if scenario_input
        in {
            "worker killed",
            "network partition after side effect",
            "partial tool success",
            "cancel while executing",
            "tool timeout",
        }
        else 0
    )
    # 幂等参考行为：重复 approval 是 no-op，第二次 approval 不再起 run。
    duplicate_run_started = False
    events = [{"side_effect_count": side_effect_count, "journal_first": True}]
    receipt = {
        "state_consistent_with_ledger": True,
        "claims_success": scenario_input in {"network partition after side effect", "partial tool success"},
        "partial_steps_recorded": scenario_input == "partial tool success",
    }
    return SurrogateRun(
        observations={
            "final_state": sorted(_AGENT_ALLOWED_FINAL[scenario_input])[0],
            "allowed_final_states": sorted(_AGENT_ALLOWED_FINAL[scenario_input]),
            "side_effect_count": side_effect_count,
            "duplicate_run_started": duplicate_run_started,
            "receipt": receipt,
            "events": events,
        },
        metrics={"lifecycle_steps": float(3 + int(rng.uniform(0, 2)))},
    )


# ---------------------------------------------------------------------------
# deterministic harness · security（不可信内容护栏）
# ---------------------------------------------------------------------------


def security_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：内容永不改权限；跨用户命名空间隔离；日志脱敏；幂等重放。"""
    unauthorized_effects = 0
    cross_user_leaks = 0
    permission_overrides = 0
    detail: dict[str, Any] = {}
    if scenario_input in {"prompt injection in PDF", "prompt injection in memory text"}:
        detail["instructions_extracted_from_content"] = 0  # 注入指令被剥离，不计效果
    elif scenario_input == "cross-account local cache":
        detail["cache_namespaces"] = ["account_a", "account_b"]
    elif scenario_input == "tool privilege escalation":
        detail["elevation_requests_denied"] = 1
    elif scenario_input == "seed persona leakage":
        detail["hidden_fields_scrubbed"] = ["hidden_friction"]
    elif scenario_input == "revoked permission":
        detail["capability_check"] = "denied"
    elif scenario_input == "secret in log":
        detail["redacted_secret_occurrences"] = 1
    elif scenario_input == "community asks private profile":
        detail["private_fields_exposed"] = 0
    elif scenario_input == "idempotency replay":
        detail["replay_effects"] = 0
        detail["replay_response_identical"] = True
    else:
        raise KeyError(f"security surrogate: unknown input {scenario_input!r}")
    return SurrogateRun(
        observations={
            "unauthorized_effects": unauthorized_effects,
            "cross_user_leaks": cross_user_leaks,
            "permission_overrides": permission_overrides,
            "detail": detail,
        },
        metrics={"guard_checks": float(4 + int(rng.uniform(0, 2)))},
    )


# ---------------------------------------------------------------------------
# deterministic harness · performance（合成时延账本）
# ---------------------------------------------------------------------------

_PERF_TABLE = {
    # input → (样本数, 基线毫秒)
    "L0 local": (20, 40.0),
    "L1 fast": (15, 800.0),
    "L2 deep": (10, 4000.0),
    "L3 run ack": (20, 150.0),
    "1000 memory candidates": (10, 120.0),
    "long chat compaction": (10, 900.0),
    "20 concurrent restore": (20, 600.0),
    "provider high TTFT": (12, 2500.0),
}


def performance_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考机制：逐样本原始值全落账、样本数显式披露、执行全程零 I/O（纯计算）。"""
    if scenario_input not in _PERF_TABLE:
        raise KeyError(f"performance surrogate: unknown input {scenario_input!r}")
    sample_count, base_ms = _PERF_TABLE[scenario_input]
    raw_samples = [round(base_ms * rng.uniform(0.9, 1.1), 3) for _ in range(sample_count)]
    ordered = sorted(raw_samples)
    p50 = ordered[len(ordered) // 2]
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return SurrogateRun(
        observations={
            "raw_samples_ms": raw_samples,
            "sample_count": sample_count,
            "sample_count_disclosed": True,
            "blocking_calls_observed": 0,  # 纯函数执行，无任何 I/O 隐藏阻塞
        },
        metrics={"perf_p50_ms": p50, "perf_p95_ms": p95},
    )


# ---------------------------------------------------------------------------
# simulator harness · community（两账号/幂等投影桩）
# ---------------------------------------------------------------------------


def community_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考桩：事件日志 → 有序投影；客户端 id 幂等；隐私边界零外泄。"""
    if scenario_input not in {
        "two-account chat",
        "reconnect",
        "leave group",
        "retract artifact",
        "duplicate checkin",
        "group AI context boundary",
    }:
        raise KeyError(f"community surrogate: unknown input {scenario_input!r}")
    duplicate_events = scenario_input in {"reconnect", "duplicate checkin"}
    projected = 1 if duplicate_events else 2
    duplicates_collapsed = (projected == 1) if duplicate_events else True
    return SurrogateRun(
        observations={
            "projected_events": projected,
            "duplicates_collapsed": duplicates_collapsed,
            "delivery_order_preserved": True,
            "privacy_leaks": 0,
            "private_fields_exposed": 0,
        },
        metrics={"projection_lag_ms": round(rng.uniform(5.0, 40.0), 3)},
    )


# ---------------------------------------------------------------------------
# simulator harness · first_value / journey / ui_state（UI 类桩）
# ---------------------------------------------------------------------------


def first_value_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考桩：新用户零历史账本 + 卡片所有权标签齐备。

    注意：`≤3min reach useful action` 是真实 app 墙钟属性，合成时间不能作为
    证据——该项由 grading 判 unsupported（诚实降级），本桩只提供可判定的
    零历史/所有权观测。
    """
    cards = [
        {"ownership": "agent"},
        {"ownership": "human"},
        {"ownership": "hybrid"},
    ]
    return SurrogateRun(
        observations={
            "fresh_user_history_ledger": [],
            "cards": cards,
            "synthetic_ttfu_seconds": round(rng.uniform(45.0, 150.0), 1),
        },
        metrics={"synthetic_ttfu_seconds": round(rng.uniform(45.0, 150.0), 1)},
    )


#: GJ01..GJ20 冻结清单（v3/05_metrics_eval/GOLDEN_JOURNEYS.md）。
GOLDEN_JOURNEYS = (
    "GJ01 Fresh user → goal → first useful action",
    "GJ02 Example mode → exit demo → own goal",
    "GJ03 Existing user → Today → action → outcome",
    "GJ04 我卡住了 → one clarification → rescope",
    "GJ05 Human action → evidence → Galaxy",
    "GJ06 Agent action → approval → run → receipt",
    "GJ07 Hybrid action → Agent prep → awaiting user → resume",
    "GJ08 Correction → memory scope → next-session adaptation",
    "GJ09 Memory delete → cache invalidation → no reuse",
    "GJ10 RAG material → cited answer/action → document delete",
    "GJ11 Return after stale plan → recovery",
    "GJ12 Proactive suggestion → accept/reject/mute/cooldown",
    "GJ13 Offline action → reconnect → no duplicate",
    "GJ14 Agent worker restart → run recovery",
    "GJ15 Conflict: explicit new preference vs old observation",
    "GJ16 Community squad check-in → artifact feedback",
    "GJ17 Low-stimulation mode",
    "GJ18 Account switch → zero cross-user local/context leak",
    "GJ19 Remote HTTPS fresh device",
    "GJ20 Full competition-quality demo path cold start",
)
GOLDEN_JOURNEY_IDS = frozenset(entry.split(" ", 1)[0] for entry in GOLDEN_JOURNEYS)


def journey_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考桩：只校验 GJ id 在冻结清单内；L3 判据（真 UI/真栈）全由 grading 判 unsupported。"""
    journey_id = scenario_input.split(" ", 1)[0]
    if journey_id not in GOLDEN_JOURNEY_IDS:
        raise KeyError(f"journey surrogate: unknown golden journey {scenario_input!r}")
    return SurrogateRun(
        observations={"journey_id": journey_id, "in_frozen_registry": True, "steps_skipped": True},
        metrics={"registry_index": float(sorted(GOLDEN_JOURNEY_IDS).index(journey_id) + 1)},
    )


_UI_STATE_TABLE = {
    # input → (visible_state, next_action, terminal_spinner)
    "loading": ("loading_skeleton", "cancel", False),
    "empty": ("empty_state", "create_first_goal", False),
    "offline": ("offline_banner", "retry", False),
    "model unavailable": ("degraded_notice", "retry", False),
    "permission denied": ("permission_rationale", "grant", False),
    "auth expired": ("reauth_prompt", "sign_in", False),
    "version conflict": ("conflict_resolver", "choose_version", False),
    "awaiting user": ("awaiting_user_card", "resume", False),
    "partial result": ("partial_marker", "continue", False),
    "unknown outcome": ("reconcile_notice", "check_status", False),
    "cancelled": ("cancelled_state", "restart", False),
    "long running": ("progress_bar", "cancel", False),
}


def ui_state_surrogate(scenario_input: str, rng: random.Random) -> SurrogateRun:
    """参考桩：条件 → 可见态/下一步动作 映射表；视觉 rubric 留给真渲染（grading 判 unsupported）。"""
    if scenario_input not in _UI_STATE_TABLE:
        raise KeyError(f"ui_state surrogate: unknown input {scenario_input!r}")
    visible_state, next_action, terminal_spinner = _UI_STATE_TABLE[scenario_input]
    return SurrogateRun(
        observations={
            "visible_state": visible_state,
            "next_action": next_action,
            "terminal_spinner": terminal_spinner,
        },
        metrics={"state_transition_depth": float(2 + int(rng.uniform(0, 2)))},
    )


#: category → surrogate（单一注册表；runner 不允许出现注册表外的类目）。
SURROGATES = {
    "memory": memory_surrogate,
    "conflict": conflict_surrogate,
    "allocation": allocation_surrogate,
    "proactive": proactive_surrogate,
    "rag": rag_surrogate,
    "agent_runtime": agent_runtime_surrogate,
    "security": security_surrogate,
    "performance": performance_surrogate,
    "community": community_surrogate,
    "first_value": first_value_surrogate,
    "journey": journey_surrogate,
    "ui_state": ui_state_surrogate,
}


def execute(scenario, run_seed: int) -> SurrogateRun:
    """按场景类目执行对应 surrogate（run_seed 为 runner 已派生的 per-attempt seed）。"""
    surrogate = SURROGATES.get(scenario.category)
    if surrogate is None:
        raise KeyError(f"no surrogate registered for category {scenario.category!r}")
    return surrogate(scenario.input, random.Random(run_seed))
