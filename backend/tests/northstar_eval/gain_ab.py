"""NORTHSTAR · GAIN-EVAL 记忆/画像真实增益消融评测运行器（C 纵队用户令备弹）。

使命（用户令：「memory/星图/向量索引/用户画像必须证明正向增益，发现污染/
幻觉/负增益即修」）：这些能力的增益此前**未被系统证明过**。本模块把证明变成
可执行资产：20 个可判分场景（离散数学冲刺语境，`gain_scenarios.json`）×
A/B 双臂（同场景完整上下文 vs 逐能力消融）× 确定性优先判分。**不切任何
生产开关**：全部经真实装配链（``app.api.v1.chat.get_user_context``）在进程内
以评测杠杆实现消融，生产 env / Redis / DB 零改动。

臂定义（注入点与开关盘点见 v3-output/GAIN-EVAL/REPORT.md §1）：
- 臂 A（FULL，对照臂）：生产默认装配——USE_CONTEXT_PACK=True + 记忆预算
  原样 + profile_context 正常附加；
- 臂 B-MEM（记忆消融）：``MemoryService`` 三个召回源读方法
  （list_preference_records / list_active_goals / list_recent_episodic）
  在评测期间返回空——召回源置空等价"记忆能力关闭"（pack 三段、M-05 selfcheck
  输入、conflict resolution、metadata.evidence_summary 回灌面全部为空）
  ——**无产品开关，属申报项**（``ENABLE_CONTEXT_SOURCE_MEMORY`` 只控
  manifest 计量，控不了注入；预算钳 0 会被 evidence_summary 回灌绕过，
  见 REPORT 盘点表）；
- 臂 C-PROF（画像消融）：``ProfileContextService.get_profile_context`` 抛
  ProfileUnavailable，走生产 fail-soft 分支（chat.py 内层 except→不附加）
  ——**无产品开关，属申报项**；
- 臂 E-NOPACK（全个性化消融参照）：真实总开关 ``USE_CONTEXT_PACK=False``
  （legacy 旧上下文路径）+ 画像消融——量化全部个性化的合计增益；
- 探针 D-VEC（向量/文档检索开关验证）：真实总开关
  ``ENABLE_DOCUMENT_CONTEXT_INJECTION=False`` 强制 doc-context kill-switch
  读 off → pack ``document_context_controls.enabled=False``——只证开关在位与
  传播，不当判分臂（文档 chunk 注入走 orchestrator 侧，进程内无端到端面；
  ``AURORA_DOC_CONTEXT_MODE`` 是分类器预算档而非注入开关，盘点见 REPORT）；
- 探针 G-GALAXY（星图注入开关验证）：真实三态开关
  ``AURORA_STAGE39_GALAXY_INJECT_MODE=off`` 经 stage39 kill-switch 读回
  ——同上，注入点在 orchestrator sidecar，进程内无 prompt 装配面，真实
  冒烟留主会话。

判分契约（确定性优先）：每场景 judge.kind=deterministic（expect_groups
逐组命中 + forbidden 罚分，0-1 连续分）或 llm（规则不可判的风格/定制类，
照 ``profile_eval_llm_judge`` 先例：STANDARD 档、严格 JSON、rubric 评分、
失败诚实 fallback 不重试）。增益判定（20 场景规模的冻结门槛，防事后合理化）：
- 正增益：消融臂在**依赖类场景**上均值比 A 低 ≥ 15pp（gain ≥ +0.15）；
- 负增益嫌疑（红旗）：消融臂在依赖类场景上 ≥ A（能力没帮上忙甚至帮倒忙）；
- 污染红旗：消融臂在 **baseline 场景**上比 A 低 > 15pp（能力关闭伤及无辜
  =装配污染）；baseline 上 A/B-MEM/C-PROF 提示词应逐字节相同（dry-run 硬断言）。

纯净性红线：live 臂调用经 ``llm_router.select_model(force_tier=PRO)`` 解析后
直调 ``OpenAICompatibleProvider.chat``，**绕过 llm_fallback_manager/熔断器**
（降级链介入会把消融臂污染成其他模型，A/B 即失效）；失败按场景记 error，
不换模型。评测杠杆只在本进程内生效，进程退出即消失，生产零残留。

用法（backend/ 下）::

    # 无 key 装配自检（纪律：绝不调真实 LLM）——同时是消融接线证明：
    # 每场景每臂装配真实提示词，并硬断言「A 含事实、消融臂不含、正交臂保留」
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        python3.11 tests/northstar_eval/gain_ab.py --dry-run

    # 真实 key 冒烟（主会话执行；worktree 无 .env）：
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        DASHSCOPE_API_KEY=sk-... python3.11 tests/northstar_eval/gain_ab.py \
        --limit 4            # 先 4 场景冒烟再全量

    # 全量（20 场景 ×4 臂 + 判分；串行）
    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        DASHSCOPE_API_KEY=sk-... python3.11 tests/northstar_eval/gain_ab.py

输出：控制台逐场景对照表 + 增益矩阵/红旗清单；JSON 落盘
``$GAIN_AB_OUT_DIR``（默认 <repo>/v3-output/GAIN-EVAL/runs）/
``gain_ab_run_<ts>.json``。凭据不落盘：api_key 只以是否在场布尔出现在证据里。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

# 模块可被 `python3 -m tests.northstar_eval.gain_ab` 与
# `python3.11 tests/northstar_eval/gain_ab.py` 两种方式调起：后者 sys.path[0]
# 是本目录，需先把 backend/ 挂上才能 import app.*。
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SCHEMA_PACK = "sparkle.northstar_eval.gain_ab.pack.v1"
SCHEMA_RUN = "sparkle.northstar_eval.gain_ab.run.v1"

#: 场景集规模下限（卡面：20 个可判分场景）
MIN_SCENARIOS = 20
#: 每依赖类别下限（设计构成 8/6/6）
MIN_PER_CATEGORY = {"memory": 6, "profile": 5, "baseline": 5}

CATEGORY_VOCAB = ("memory", "profile", "baseline")
JUDGE_KIND_VOCAB = ("deterministic", "llm")

#: 增益判定门槛（冻结值；0-1 分制，单位=分差）
GAIN_POSITIVE_THRESHOLD = 0.15  # 依赖类：A − 消融臂 ≥ 0.15 → 正增益
BASELINE_DRIFT_THRESHOLD = 0.15  # baseline：|A − 消融臂| > 0.15 → 污染红旗

#: 协议常量（两臂同参，保证 A/B 单变量=上下文）
CHAT_TEMPERATURE = 0.3  # 评测常数：主聊生成档温和采样
CALL_TIMEOUT_S_DEFAULT = 120.0
JUDGE_TIMEOUT_S = 60.0
JUDGE_MAX_TOKENS = 400
ANSWER_HEAD_KEEP = 400  # 逐场景回答截断留存（证据瘦身）
RAW_HEAD_KEEP = 200

#: 提示词臂（有消融杠杆的才做臂）；探针臂只验开关传播，不进判分
PROMPT_ARMS = ("A", "B-MEM", "C-PROF", "E-NOPACK")
PROBE_ARMS = ("D-VEC", "G-GALAXY")

ARM_DESCRIPTIONS = {
    "A": "FULL 生产默认装配（USE_CONTEXT_PACK=True + 记忆预算原样 + 画像附加）",
    "B-MEM": "记忆消融（评测杠杆：MemoryService 召回源置空——无产品开关，申报项）",
    "C-PROF": "画像消融（评测杠杆：get_profile_context 抛错→生产 fail-soft 不附加——无产品开关，申报项）",
    "E-NOPACK": "全个性化消融参照（真实总开关 USE_CONTEXT_PACK=False legacy 路径 + 画像消融）",
    "D-VEC": "探针：ENABLE_DOCUMENT_CONTEXT_INJECTION=False（真实开关）→ pack document_context_controls 传播验证",
    "G-GALAXY": "探针：AURORA_STAGE39_GALAXY_INJECT_MODE=off（真实开关）→ stage39 kill-switch 读回验证",
}

JUDGE_SYSTEM_PROMPT = (
    "你是 Sparkle 的只读评测判分器（只判分、不执行、不写任何数据）。"
    "给定用户消息、判分要点（rubric）与一个 AI 助手的回答，按 rubric 给 0~1 分："
    "1.0=完全体现要点，0=完全没体现，中间按体现比例给分。"
    '只输出一个 JSON 对象（无其他文本、无 markdown 围栏）：{"score":<0到1的小数>,"rationale":"不超过60字的判分理由"}'
)

# ---------------------------------------------------------------------------
# 评测杠杆（进程内 monkeypatch，等价"一行 env"的消融入口；收工即消失）
# ---------------------------------------------------------------------------

_ZERO_MEMORY_ACTIVE = False  # B-MEM 臂：记忆召回源置空（preferences/goals/episodic）
_PROFILE_OFF_ACTIVE = False  # C-PROF/E-NOPACK 臂：get_profile_context 抛错
_LEVERS_INSTALLED = False


class ProfileUnavailable(RuntimeError):
    """C-PROF 臂注入的受控异常：走生产 fail-soft 分支（chat.py 内层 except）。"""


def install_eval_levers() -> dict[str, Any]:
    """装配链上装评测杠杆（进程内一次性幂等）。

    1) MemoryService 三个召回源读方法包装：_ZERO_MEMORY_ACTIVE 时返回空——
       召回源置空是比"预算钳 0"更彻底的消融：pack 三段、M-05 selfcheck 输入、
       conflict resolution、以及 metadata.evidence_summary（prompts.py:3784
       的【画像证据摘要】回灌面会把预算裁掉的 goals 标题带回 prompt——预算
       杠杆存在该泄漏面，源置空则全链干净）全部为空，等价"记忆能力关闭"；
    2) ProfileContextService.get_profile_context 包装：_PROFILE_OFF_ACTIVE
       时抛 ProfileUnavailable——chat.get_user_context 的内层 except 捕获后
       不附加画像（生产既有 fail-soft 行为，无需新代码路径）。
    """
    global _LEVERS_INSTALLED
    from app.core.context_budget import ContextBudgetScheduler  # noqa: F401 — 装配自检
    from app.services.memory_service import MemoryService
    from app.services.profile_context_service import ProfileContextService

    if _LEVERS_INSTALLED:
        return {}
    _LEVERS_INSTALLED = True

    _orig_list_prefs = MemoryService.list_preference_records
    _orig_list_history = MemoryService.list_preference_history
    _orig_list_goals = MemoryService.list_active_goals
    _orig_list_episodic = MemoryService.list_recent_episodic

    async def _zero_prefs(self, user_id):
        if _ZERO_MEMORY_ACTIVE:
            return []
        return await _orig_list_prefs(self, user_id)

    async def _zero_history(self, user_id):
        # list_preference_history 也要置空：conflict resolver 用全版本链做
        # winner 裁决（context_pack.build 的 pref_history 入参），只置空
        # list_preference_records 会被 resolver 从历史链复活记忆偏好。
        if _ZERO_MEMORY_ACTIVE:
            return []
        return await _orig_list_history(self, user_id)

    async def _zero_goals(self, user_id, now=None):
        if _ZERO_MEMORY_ACTIVE:
            return []
        return await _orig_list_goals(self, user_id, now=now)

    async def _zero_episodic(self, user_id, *args, **kwargs):
        if _ZERO_MEMORY_ACTIVE:
            return []
        return await _orig_list_episodic(self, user_id, *args, **kwargs)

    MemoryService.list_preference_records = _zero_prefs
    MemoryService.list_preference_history = _zero_history
    MemoryService.list_active_goals = _zero_goals
    MemoryService.list_recent_episodic = _zero_episodic

    _orig_get = ProfileContextService.get_profile_context

    async def patched_get(self, user_id, **kwargs):
        if _PROFILE_OFF_ACTIVE:
            raise ProfileUnavailable("gain_ab C-PROF ablation lever")
        return await _orig_get(self, user_id, **kwargs)

    ProfileContextService.get_profile_context = patched_get
    return {
        "memory_service": (
            MemoryService,
            _orig_list_prefs,
            _orig_list_history,
            _orig_list_goals,
            _orig_list_episodic,
        ),
        "profile_service": (ProfileContextService, _orig_get),
    }


# ---------------------------------------------------------------------------
# 场景包：加载 + 校验 + 构成表
# ---------------------------------------------------------------------------


def load_pack(path: Path) -> dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_pack(pack)
    if problems:
        raise SystemExit("pack validation failed:\n  - " + "\n  - ".join(problems))
    return pack


def validate_pack(pack: dict[str, Any]) -> list[str]:
    """结构+语义校验（dry-run 与 live 同门：坏包不许进评测）。"""
    problems: list[str] = []
    if pack.get("schema") != SCHEMA_PACK:
        problems.append(f"unexpected schema: {pack.get('schema')!r}")
    scenarios = pack.get("scenarios") or []
    if len(scenarios) < MIN_SCENARIOS:
        problems.append(f"scenario count {len(scenarios)} < {MIN_SCENARIOS} (卡面下限)")
    seen: set[str] = set()
    counts: dict[str, int] = dict.fromkeys(CATEGORY_VOCAB, 0)
    for sc in scenarios:
        sid = str(sc.get("id", ""))
        where = f"[{sid or '?'}]"
        if sid in seen:
            problems.append(f"{where} duplicate id")
        seen.add(sid)
        if sc.get("category") not in CATEGORY_VOCAB:
            problems.append(f"{where} bad category {sc.get('category')!r}")
            continue
        counts[sc["category"]] += 1
        if not str(sc.get("user_message") or "").strip():
            problems.append(f"{where} user_message empty")
        judge = sc.get("judge") or {}
        if judge.get("kind") not in JUDGE_KIND_VOCAB:
            problems.append(f"{where} bad judge.kind {judge.get('kind')!r}")
        elif judge["kind"] == "deterministic":
            groups = judge.get("expect_groups") or []
            if not groups or any(not isinstance(g, list) or not g for g in groups):
                problems.append(f"{where} deterministic judge needs non-empty expect_groups")
            bad_forbidden = [f for f in (judge.get("forbidden") or []) if not isinstance(f, str) or not f.strip()]
            if bad_forbidden:
                problems.append(f"{where} forbidden must be list of non-empty strings")
        elif judge["kind"] == "llm" and not str(judge.get("rubric") or "").strip():
            problems.append(f"{where} llm judge needs rubric")
        if not str(sc.get("scoring_note") or "").strip():
            problems.append(f"{where} scoring_note empty（判分要点申报面）")
        if sc["category"] in ("memory", "profile") and not (sc.get("probe_terms") or []):
            problems.append(f"{where} {sc['category']} scenario needs probe_terms（装配探针依赖）")
        seed = sc.get("seed") or {}
        for epi in seed.get("episodic") or []:
            if not str(epi.get("summary") or "").strip():
                problems.append(f"{where} episodic seed summary empty")
        for pref in seed.get("preferences") or []:
            if not str(pref.get("pref_key") or "").strip() or "pref_value" not in pref:
                problems.append(f"{where} preference seed needs pref_key+pref_value")
        for goal in seed.get("goals") or []:
            if not str(goal.get("title") or "").strip():
                problems.append(f"{where} goal seed title empty")
        know = seed.get("knowledge") or {}
        names = [n.get("name") for n in know.get("nodes") or []]
        if know and (not names or any(not n for n in names)):
            problems.append(f"{where} knowledge seed nodes need names")
        for st in know.get("study") or []:
            if st.get("node") not in names:
                problems.append(f"{where} study record references unknown node {st.get('node')!r}")
    for cat, floor in MIN_PER_CATEGORY.items():
        if counts[cat] < floor:
            problems.append(f"category {cat} count {counts[cat]} < {floor}")
    return problems


def pack_composition(pack: dict[str, Any]) -> dict[str, Any]:
    scenarios = pack["scenarios"]
    return {
        "scenario_count": len(scenarios),
        "categories": {cat: sum(1 for s in scenarios if s["category"] == cat) for cat in CATEGORY_VOCAB},
        "judge_kinds": {kind: sum(1 for s in scenarios if s["judge"]["kind"] == kind) for kind in JUDGE_KIND_VOCAB},
    }


# ---------------------------------------------------------------------------
# 播种（每场景一个全新用户；数据面彼此隔离）
# ---------------------------------------------------------------------------


async def seed_scenario(db, seed: dict[str, Any]) -> Any:
    """按场景 seed 声明播种：返回 (user, seeded_faces)。

    seeded_faces 记录实际落库的依赖数据面（episodic/preferences/goals/
    knowledge），供证据面申报"这个场景到底种了什么"。
    """
    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
    from app.models.memory import MemoryGoal, MemoryPreference
    from app.models.subject import Subject
    from app.models.user import User
    from app.services.memory_service import MemoryService

    user_id = uuid4()
    db.add(
        User(
            id=user_id,
            username=f"gainab_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db.commit()

    faces = {"episodic": 0, "preferences": 0, "goals": 0, "knowledge_nodes": 0}
    memory_service = MemoryService(db)
    now = datetime.now(UTC).replace(tzinfo=None)

    for epi in seed.get("episodic") or []:
        await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=str(epi["summary"]),
            source_type="chat",
            source_id=str(uuid4()),
            source_lane="direct_capture",
            occurred_at=now - timedelta(hours=float(epi.get("hours_ago", 24))),
            importance_score=0.9,
            confidence=0.95,
            tags=list(epi.get("tags") or []),
            evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
            evidence_token=str(uuid4()),
            emit_system_update=False,
        )
        faces["episodic"] += 1

    for pref in seed.get("preferences") or []:
        db.add(
            MemoryPreference(
                user_id=user_id,
                pref_key=str(pref["pref_key"]),
                pref_value=pref["pref_value"],
                version=1,
                evidence_score=0.9,
                evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
            )
        )
        faces["preferences"] += 1
    if faces["preferences"]:
        await db.commit()

    for goal in seed.get("goals") or []:
        target = now.date() + timedelta(days=int(goal.get("days_ahead", 5)))
        db.add(
            MemoryGoal(
                user_id=user_id,
                title=str(goal["title"]),
                status=str(goal.get("status", "active")),
                target_date=target,
                evidence_score=0.9,
                evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
            )
        )
        faces["goals"] += 1
    if faces["goals"]:
        await db.commit()

    know = seed.get("knowledge") or {}
    if know:
        subject_name = str(know.get("subject", "离散数学"))
        subject = (await db.execute(select(Subject).where(Subject.name == subject_name))).scalar_one_or_none()
        if subject is None:
            subject = Subject(name=subject_name, category="数学")
            db.add(subject)
            await db.commit()

        node_ids: dict[str, Any] = {}
        node_mastery: dict[str, float] = {}
        for node in know.get("nodes") or []:
            node_row = KnowledgeNode(
                name=str(node["name"]),
                subject_id=subject.id,
                status="published",
                source_type="seed",
            )
            db.add(node_row)
            await db.flush()
            node_ids[str(node["name"])] = node_row.id
            node_mastery[str(node["name"])] = float(node.get("mastery", 50.0))
            mastery = node_mastery[str(node["name"])]
            db.add(
                UserNodeStatus(
                    user_id=user_id,
                    node_id=node_row.id,
                    mastery_score=mastery,
                    bkt_mastery_prob=max(0.0, min(mastery / 100.0, 1.0)),
                    is_unlocked=True,
                    study_count=2,
                    last_study_at=now - timedelta(hours=6),
                )
            )
            faces["knowledge_nodes"] += 1
        await db.commit()

        for st in know.get("study") or []:
            node_name = str(st["node"])
            node_id = node_ids.get(node_name)
            if node_id is None:
                continue
            delta = float(st.get("delta", 5.0))
            db.add(
                StudyRecord(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=30,
                    mastery_delta=delta,
                    # 近期掌握度变化语义：initial = 当前值 − 增量（MasteryChange
                    # 投影 old/new 即由这两个字段相加得出）
                    initial_mastery=max(0.0, node_mastery.get(node_name, delta) - delta),
                )
            )
        await db.commit()

    user = await db.get(User, user_id)
    return user, faces


# ---------------------------------------------------------------------------
# 真实装配链双臂装配（chat.get_user_context 同一入口；settings 就地恢复）
# ---------------------------------------------------------------------------


async def assemble_arm(db, user, scenario: dict[str, Any], arm: str) -> dict[str, Any]:
    """单场景单臂：经生产装配链产出 system prompt + 证据面。

    杠杆开闭就地完成（try/finally 恢复），臂与臂之间零串扰。
    """
    global _ZERO_MEMORY_ACTIVE, _PROFILE_OFF_ACTIVE
    from app.api.v1.chat import get_user_context
    from app.config import settings
    from app.orchestration.prompts import build_system_prompt

    use_pack = arm != "E-NOPACK"
    zero_memory = arm == "B-MEM"
    profile_off = arm in ("C-PROF", "E-NOPACK")

    saved_pack = settings.USE_CONTEXT_PACK
    started = time.monotonic()
    try:
        settings.USE_CONTEXT_PACK = use_pack
        _ZERO_MEMORY_ACTIVE = zero_memory
        _PROFILE_OFF_ACTIVE = profile_off
        payload = {
            "message": scenario["user_message"],
            "request_id": str(uuid4()),
            "trace_id": str(uuid4()),
        }
        context = await get_user_context(db, user.id, payload)
        prompt = build_system_prompt(context, {"messages": []})
    finally:
        settings.USE_CONTEXT_PACK = saved_pack
        _ZERO_MEMORY_ACTIVE = False
        _PROFILE_OFF_ACTIVE = False

    pack_meta = (context.get("context_pack") or {}).get("metadata") or {}
    doc_controls = pack_meta.get("document_context_controls") or {}
    return {
        "arm": arm,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_chars": len(prompt),
        "profile_attached": "profile_context" in context,
        "use_context_pack": use_pack,
        "doc_controls_enabled": doc_controls.get("enabled"),
        "doc_controls_mode": doc_controls.get("mode"),
        "token_usage": (context.get("context_pack") or {}).get("token_usage") or {},
        "assembly_ms": int((time.monotonic() - started) * 1000),
        "assembly_error": None,
    }


async def assemble_arm_safe(db, user, scenario: dict[str, Any], arm: str) -> dict[str, Any]:
    try:
        return await assemble_arm(db, user, scenario, arm)
    except Exception as exc:  # noqa: BLE001 — 单臂装配失败原样入证据，不中断其余臂
        return {
            "arm": arm,
            "prompt": None,
            "prompt_sha256": None,
            "prompt_chars": 0,
            "profile_attached": None,
            "use_context_pack": arm != "E-NOPACK",
            "doc_controls_enabled": None,
            "doc_controls_mode": None,
            "token_usage": {},
            "assembly_ms": None,
            "assembly_error": f"{type(exc).__name__}: {exc}"[:300],
        }


# ---------------------------------------------------------------------------
# 装配探针（不同臂的有效性/正交性硬断言——消融接线证明）
# ---------------------------------------------------------------------------


def check_differentiators(scenario: dict[str, Any], arms: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """逐场景断言：A 含事实、消融臂不含、正交臂保留、baseline 无泄漏。

    返回失败清单（空=接线有效）。这些断言同时是 dry-run 的退出条件与 live
    证据面的组成部分——消融没切干净的场景不许进增益判定。
    """
    failures: list[dict[str, Any]] = []
    category = scenario["category"]
    probes = scenario.get("probe_terms") or []

    def _has(arm: str, term: str) -> bool:
        prompt = (arms.get(arm) or {}).get("prompt") or ""
        return term in prompt

    for arm in PROMPT_ARMS:
        if (arms.get(arm) or {}).get("prompt") is None:
            failures.append(
                {
                    "id": scenario["id"],
                    "check": f"{arm}:assembly",
                    "detail": (arms.get(arm) or {}).get("assembly_error"),
                }
            )
    if failures:
        return failures

    if category == "memory":
        for term in probes:
            if not _has("A", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "A:contains_fact",
                        "detail": f"term={term!r} 未进臂 A 提示词（召回链被切，场景需修）",
                    }
                )
            if _has("B-MEM", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "B-MEM:fact_removed",
                        "detail": f"term={term!r} 仍在 B-MEM（记忆消融失效）",
                    }
                )
            if _has("E-NOPACK", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "E-NOPACK:fact_removed",
                        "detail": f"term={term!r} 仍在 E-NOPACK（总开关未切断记忆面）",
                    }
                )
            if not _has("C-PROF", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "C-PROF:memory_orthogonal",
                        "detail": f"term={term!r} 从 C-PROF 消失（画像消融不应伤记忆）",
                    }
                )
    elif category == "profile":
        for term in probes:
            if not _has("A", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "A:contains_profile",
                        "detail": f"term={term!r} 未进臂 A 提示词（画像链被切，场景需修）",
                    }
                )
            if _has("C-PROF", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "C-PROF:profile_removed",
                        "detail": f"term={term!r} 仍在 C-PROF（画像消融失效）",
                    }
                )
            if _has("E-NOPACK", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "E-NOPACK:profile_removed",
                        "detail": f"term={term!r} 仍在 E-NOPACK（总开关未切断画像面）",
                    }
                )
            if not _has("B-MEM", term):
                failures.append(
                    {
                        "id": scenario["id"],
                        "check": "B-MEM:profile_orthogonal",
                        "detail": f"term={term!r} 从 B-MEM 消失（记忆消融不应伤画像）",
                    }
                )
    else:  # baseline：零种子。B-MEM 提示词必须与 A 逐字节相同（记忆面守卫）；
        # C-PROF 允许结构性差异——生产画像面对零数据用户也注入基础内容
        # （【画像快照】/【画像证据摘要】等，见 REPORT 红旗申报），这不是
        # 用户数据污染，但差异由调用方记录进证据面供人审。
        if arms["B-MEM"]["prompt_sha256"] != arms["A"]["prompt_sha256"]:
            failures.append(
                {
                    "id": scenario["id"],
                    "check": "B-MEM:baseline_neutral",
                    "detail": "baseline 场景提示词与臂 A 不一致——记忆关闭改变了无辜场景的装配（泄漏面）",
                }
            )
    return failures


async def run_switch_probes(db, scenario: dict[str, Any]) -> dict[str, Any]:
    """开关探针：真实三态开关的就地传播验证（不进判分）。

    - D-VEC：ENABLE_DOCUMENT_CONTEXT_INJECTION=False（真实总开关，settings.py:814）
      → AuroraDocContextKillSwitchService.get_mode() 强制 off
      → pack document_context_controls.enabled=False
      （注：AURORA_DOC_CONTEXT_MODE 是分类器预算档 auto/live/on/skip，
      不是注入开关——盘点见 REPORT §1）
    - G-GALAXY：AURORA_STAGE39_GALAXY_INJECT_MODE off→stage39 kill-switch 读回 off
    """
    from app.config import settings
    from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService

    probes: dict[str, Any] = {}
    user, _ = await seed_scenario(db, scenario.get("seed") or {})

    saved_doc = settings.ENABLE_DOCUMENT_CONTEXT_INJECTION
    try:
        settings.ENABLE_DOCUMENT_CONTEXT_INJECTION = False
        off_ctx = await assemble_arm(db, user, scenario, "A")
    finally:
        settings.ENABLE_DOCUMENT_CONTEXT_INJECTION = saved_doc
    default_ctx = await assemble_arm(db, user, scenario, "A")
    probes["D-VEC"] = {
        "switch": "ENABLE_DOCUMENT_CONTEXT_INJECTION",
        "default": {"mode": default_ctx["doc_controls_mode"], "enabled": default_ctx["doc_controls_enabled"]},
        "off": {"mode": off_ctx["doc_controls_mode"], "enabled": off_ctx["doc_controls_enabled"]},
        "pass": off_ctx["doc_controls_enabled"] is False and default_ctx["doc_controls_enabled"] is True,
    }

    saved_galaxy = settings.AURORA_STAGE39_GALAXY_INJECT_MODE
    try:
        settings.AURORA_STAGE39_GALAXY_INJECT_MODE = "off"
        off_mode = await AuroraStage39KillSwitchService().get_feature_mode("galaxy_inject")
    finally:
        settings.AURORA_STAGE39_GALAXY_INJECT_MODE = saved_galaxy
    default_mode = await AuroraStage39KillSwitchService().get_feature_mode("galaxy_inject")
    probes["G-GALAXY"] = {
        "switch": "AURORA_STAGE39_GALAXY_INJECT_MODE",
        "default": default_mode,
        "off": off_mode,
        "pass": off_mode == "off" and default_mode == "live",
    }
    return probes


# ---------------------------------------------------------------------------
# 判分（确定性优先；llm kind 照 profile_eval_llm_judge 先例）
# ---------------------------------------------------------------------------


def judge_deterministic(answer: str, judge: dict[str, Any]) -> dict[str, Any]:
    """expect_groups 逐组命中（组内 OR）+ forbidden 罚分（每命中 −0.5，下限 0）。"""
    groups = judge.get("expect_groups") or []
    hits = [any(term in answer for term in group) for group in groups]
    forbidden = judge.get("forbidden") or []
    forbidden_hits = [term for term in forbidden if term in answer]
    score = (sum(hits) / len(groups)) if groups else 0.0
    score = max(0.0, score - 0.5 * len(forbidden_hits))
    return {
        "kind": "deterministic",
        "score": round(score, 4),
        "groups_hit": sum(hits),
        "groups_total": len(groups),
        "forbidden_hits": forbidden_hits,
    }


async def judge_llm(answer: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """profile_eval_llm_judge 先例同款：STANDARD 档、严格 JSON、失败诚实 fallback。"""
    from app.core.agent_profiles import AgentRole, ModelTier, TaskType
    from app.services.llm_service import get_configured_llm_service_for_tier

    rubric = scenario["judge"].get("rubric", "")
    user_payload = json.dumps(
        {
            "scenario_id": scenario["id"],
            "user_message": scenario["user_message"],
            "rubric": rubric,
            "assistant_answer": answer,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    started = time.monotonic()
    try:
        llm = await get_configured_llm_service_for_tier(
            AgentRole.DEEP_ANALYST,
            ModelTier.STANDARD,
            task_type=TaskType.DEEP_REASONING,
            reasoning_mode="deep",
        )
        raw = await asyncio.wait_for(
            llm.reason_json(
                [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_payload},
                ],
                temperature=0.0,
                max_tokens=JUDGE_MAX_TOKENS,
            ),
            timeout=JUDGE_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001 — judge 失败诚实入证据，不重试不降级
        return {
            "kind": "llm",
            "score": None,
            "rationale": f"judge unavailable: {type(exc).__name__}",
            "fallback_used": True,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    if not isinstance(raw, dict):
        return {
            "kind": "llm",
            "score": None,
            "rationale": "judge returned non-json payload",
            "fallback_used": True,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    try:
        score = max(0.0, min(1.0, float(raw.get("score"))))
    except (TypeError, ValueError):
        return {
            "kind": "llm",
            "score": None,
            "rationale": "judge score unparsable",
            "fallback_used": True,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    return {
        "kind": "llm",
        "score": round(score, 4),
        "rationale": str(raw.get("rationale") or "")[:120],
        "fallback_used": False,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


async def judge_answer(answer: str, scenario: dict[str, Any]) -> dict[str, Any]:
    if scenario["judge"]["kind"] == "deterministic":
        return judge_deterministic(answer, scenario["judge"])
    return await judge_llm(answer, scenario)


# ---------------------------------------------------------------------------
# live 臂调用（provider 直调，零 fallback——纯净性红线）
# ---------------------------------------------------------------------------


def est_tokens(text: str) -> int:
    """诚实粗估（heuristic）：CJK≈0.6 token/字，非 CJK≈0.25 token/字符。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return int(round(cjk * 0.6 + (len(text) - cjk) * 0.25))


def resolve_chat_arm() -> dict[str, Any]:
    """现役主力档（force_tier=PRO）解析证据——两臂同模型，单变量=上下文。"""
    AgentRole, ModelTier, TaskType, llm_router, _ = _app_imports()
    selection = llm_router.select_model(
        AgentRole.GENERATION,
        task_type=TaskType.STANDARD_RESPONSE,
        force_tier=ModelTier.PRO,
    )
    client_kwargs = llm_router.get_openai_client_kwargs(selection)
    return {
        "model_key": selection.model_key,
        "model_name": selection.config.model_name,
        "cost_per_1k_usd": selection.config.cost_per_1k_tokens,
        "api_key_present": bool(client_kwargs.get("api_key")),
        "client_kwargs": client_kwargs,
    }


def _app_imports():
    from app.core.agent_profiles import AgentRole, ModelTier, TaskType
    from app.core.llm_router import llm_router

    return AgentRole, ModelTier, TaskType, llm_router, None


async def answer_arm_live(
    arm_evidence: dict[str, Any], system_prompt: str, user_message: str, timeout_s: float
) -> dict[str, Any]:
    from app.services.llm.providers import OpenAICompatibleProvider

    client_kwargs = arm_evidence["client_kwargs"]
    request_kwargs = {
        k: v for k, v in client_kwargs.items() if k not in {"api_key", "base_url", "model", "temperature"}
    }
    provider = OpenAICompatibleProvider(
        api_key=client_kwargs["api_key"], base_url=client_kwargs["base_url"], timeout_seconds=timeout_s
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    started = time.monotonic()
    try:
        raw = await asyncio.wait_for(
            provider.chat(messages, model=client_kwargs["model"], temperature=CHAT_TEMPERATURE, **request_kwargs),
            timeout=timeout_s,
        )
        return {
            "answer": raw,
            "answer_head": raw[:ANSWER_HEAD_KEEP],
            "latency_ms": int((time.monotonic() - started) * 1000),
            "est_completion_tokens": est_tokens(raw),
            "call_error": None,
        }
    except Exception as exc:  # noqa: BLE001 — 单场景失败原样入证据，绝不降级重试换模型
        return {
            "answer": None,
            "answer_head": "",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "est_completion_tokens": 0,
            "call_error": f"{type(exc).__name__}: {exc}"[:300],
        }


# ---------------------------------------------------------------------------
# 增益判定（冻结门槛）
# ---------------------------------------------------------------------------


def build_gain_matrix(scenarios: list[dict[str, Any]], results: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """results[scenario_id][arm] = {"score": float|None, ...} → 增益矩阵 + 红旗。"""

    def _mean(scores: list[float]) -> float | None:
        return round(sum(scores) / len(scores), 4) if scores else None

    def _arm_scores(sc_list: list[dict[str, Any]], arm: str) -> list[float]:
        out = []
        for sc in sc_list:
            entry = results.get(sc["id"], {}).get(arm) or {}
            if isinstance(entry.get("score"), (int, float)):
                out.append(float(entry["score"]))
        return out

    memory_sc = [s for s in scenarios if s["category"] == "memory"]
    profile_sc = [s for s in scenarios if s["category"] == "profile"]
    baseline_sc = [s for s in scenarios if s["category"] == "baseline"]

    capabilities = [
        {"capability": "memory（跨会话记忆/偏好/目标注入）", "ablated_arm": "B-MEM", "dependent": memory_sc},
        {"capability": "profile（用户画像 knowledge_summary 注入）", "ablated_arm": "C-PROF", "dependent": profile_sc},
        {
            "capability": "context-pack 全个性化面（总开关）",
            "ablated_arm": "E-NOPACK",
            "dependent": memory_sc + profile_sc,
        },
    ]
    matrix: list[dict[str, Any]] = []
    red_flags: list[dict[str, Any]] = []
    for cap in capabilities:
        arm = cap["ablated_arm"]
        dep = cap["dependent"]
        mean_a = _mean(_arm_scores(dep, "A"))
        mean_b = _mean(_arm_scores(dep, arm))
        base_a = _mean(_arm_scores(baseline_sc, "A"))
        base_b = _mean(_arm_scores(baseline_sc, arm))
        gain = round(mean_a - mean_b, 4) if mean_a is not None and mean_b is not None else None
        if gain is None:
            verdict = "not-evaluated（有臂缺分——诚实申报，不猜）"
        elif mean_b >= mean_a:
            verdict = "negative-gain-suspect（消融臂 ≥ 完整臂：能力未证明正向增益→红旗）"
            red_flags.append(
                {
                    "kind": "negative_gain_suspect",
                    "capability": cap["capability"],
                    "detail": f"{arm} 在依赖类场景均值 {mean_b} ≥ A {mean_a}",
                }
            )
        elif gain >= GAIN_POSITIVE_THRESHOLD:
            verdict = f"positive（gain={gain} ≥ +{GAIN_POSITIVE_THRESHOLD}）"
        else:
            verdict = f"inconclusive（0 < gain={gain} < +{GAIN_POSITIVE_THRESHOLD}，20 场景规模下不作正增益宣称）"
        if base_a is not None and base_b is not None and (base_a - base_b) > BASELINE_DRIFT_THRESHOLD:
            red_flags.append(
                {
                    "kind": "baseline_pollution",
                    "capability": cap["capability"],
                    "detail": f"{arm} 在 baseline 场景比 A 低 {round(base_a - base_b, 4)}（能力关闭伤及无辜）",
                }
            )
        matrix.append(
            {
                "capability": cap["capability"],
                "ablated_arm": arm,
                "dependent_mean_a": mean_a,
                "dependent_mean_ablated": mean_b,
                "gain_a_minus_ablated": gain,
                "positive_threshold": GAIN_POSITIVE_THRESHOLD,
                "verdict": verdict,
                "baseline_mean_a": base_a,
                "baseline_mean_ablated": base_b,
            }
        )

    # 逐场景红旗：消融臂在 A 得满档的依赖场景上明显更差 / A 得零而消融臂得分（幻觉嫌疑）
    for sc in scenarios:
        if sc["category"] == "baseline":
            continue
        for cap in capabilities:
            if sc not in cap["dependent"]:
                continue
            arm = cap["ablated_arm"]
            sa = (results.get(sc["id"], {}).get("A") or {}).get("score")
            sb = (results.get(sc["id"], {}).get(arm) or {}).get("score")
            if not isinstance(sa, (int, float)) or not isinstance(sb, (int, float)):
                continue
            if sa - sb >= 0.5:
                red_flags.append(
                    {
                        "kind": "per_scenario_regression",
                        "capability": cap["capability"],
                        "detail": f"{sc['id']}: A={sa} vs {arm}={sb}（消融后显著退化，符合正增益方向的单场景证据）",
                    }
                )
            if sb - sa >= 0.5:
                red_flags.append(
                    {
                        "kind": "per_scenario_hallucination_suspect",
                        "capability": cap["capability"],
                        "detail": f"{sc['id']}: {arm}={sb} > A={sa}（消融后反而更好——能力注入可疑污染/误导，需人审）",
                    }
                )
    return {"capabilities": matrix, "red_flags": red_flags}


# ---------------------------------------------------------------------------
# 控制台呈现
# ---------------------------------------------------------------------------


def print_table(
    scenarios: list[dict[str, Any]], results: dict[str, dict[str, dict[str, Any]]], arms: list[str]
) -> None:
    head = f"{'id':34} {'cat':8} " + " ".join(f"{a:10}" for a in arms)
    print(head)
    print("-" * len(head))
    for sc in scenarios:
        cells = []
        for arm in arms:
            entry = results.get(sc["id"], {}).get(arm) or {}
            score = entry.get("score")
            mark = "?" if entry.get("call_error") else "-"
            cells.append(
                f"{'--' if score is None else format(score, '.2f'):>10}" if score is not None else f"{mark:>10}"
            )
        print(f"{sc['id']:34} {sc['category'][:7]:8} " + " ".join(cells))


def print_summary(matrix: dict[str, Any]) -> None:
    print(f"\n=== 增益矩阵（A − 消融臂，依赖类场景；门槛 +{GAIN_POSITIVE_THRESHOLD:.2f}） ===")
    for cap in matrix["capabilities"]:
        print(
            f"  {cap['capability']}\n"
            f"    臂 {cap['ablated_arm']}: dep A={cap['dependent_mean_a']} dep 消融={cap['dependent_mean_ablated']} "
            f"gain={cap['gain_a_minus_ablated']} → {cap['verdict']}\n"
            f"    baseline: A={cap['baseline_mean_a']} 消融={cap['baseline_mean_ablated']}"
        )
    if matrix["red_flags"]:
        print(f"\n  红旗清单（{len(matrix['red_flags'])} 项）：")
        for flag in matrix["red_flags"]:
            print(f"    - [{flag['kind']}] {flag['capability']}: {flag['detail']}")
    else:
        print("\n  红旗清单：空")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def default_out_dir() -> Path:
    env = os.environ.get("GAIN_AB_OUT_DIR")
    if env:
        return Path(env)
    return BACKEND_DIR.parent / "v3-output" / "GAIN-EVAL" / "runs"


async def _async_run(args: argparse.Namespace) -> int:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.core.cache import cache_service
    from app.models.base import Base

    # 评测进程内：Redis 永不连接（kill-switch / 缓存全部走 settings 兜底路径）
    cache_service.redis = None
    install_eval_levers()

    # 注册全量模型元数据（app.models.__init__ 存在个别模块未聚合的先例——
    # theater_candidate_bundle 等；逐模块 import 保证 create_all 外键可解析）
    import importlib
    import pkgutil

    import app.models

    for _mod in pkgutil.iter_modules(app.models.__path__):
        if not _mod.name.startswith("_"):
            importlib.import_module(f"app.models.{_mod.name}")

    engine = create_async_engine(
        args.database_url,
        connect_args={"check_same_thread": False} if args.database_url.startswith("sqlite") else {},
        poolclass=StaticPool if args.database_url.startswith("sqlite") else None,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    started = time.monotonic()
    pack = load_pack(Path(args.pack))
    scenarios = select_scenarios(pack, args)
    composition = pack_composition(pack)

    arm_evidence = None
    if not args.dry_run:
        arm_evidence = resolve_chat_arm()
        if not arm_evidence["api_key_present"]:
            raise SystemExit(
                "DASHSCOPE_API_KEY 为空——live 运行需注入 key。worktree 无 .env 属预期，"
                "由主会话执行（见模块 docstring 冒烟命令）；或先 --dry-run。"
            )

    print("=== GAIN-EVAL 记忆/画像真实增益消融评测 ===")
    print(
        f"mode={'dry-run' if args.dry_run else 'live'}  pack={Path(args.pack).name}  "
        f"scenarios={len(scenarios)}/{composition['scenario_count']}  prompt_arms={','.join(PROMPT_ARMS)}  "
        f"probe_arms={','.join(PROBE_ARMS)}"
    )
    if arm_evidence:
        print(
            f"  主力档: force_tier=PRO → {arm_evidence['model_key']} ({arm_evidence['model_name']}, "
            f"${arm_evidence['cost_per_1k_usd']}/1k, key={'有' if arm_evidence['api_key_present'] else '无'})"
        )
    print(f"  构成: {json.dumps(composition, ensure_ascii=False, sort_keys=True)}")
    print(f"  门槛: 正增益 ≥ +{GAIN_POSITIVE_THRESHOLD}；baseline 漂移红旗 > {BASELINE_DRIFT_THRESHOLD}")

    all_failures: list[dict[str, Any]] = []
    probes: dict[str, Any] = {}
    results: dict[str, dict[str, dict[str, Any]]] = {}
    per_scenario: list[dict[str, Any]] = []

    async with session_factory() as db:
        probe_scenario = scenarios[0]
        probes = await run_switch_probes(db, probe_scenario)
        for name, probe in probes.items():
            print(
                f"  探针 {name}: switch={probe['switch']} off→{probe['off']} 默认→{probe['default']} {'PASS' if probe['pass'] else 'FAIL'}"
            )
            if not probe["pass"]:
                all_failures.append({"id": "probe", "check": f"{name}:switch", "detail": f"{name} 开关传播验证失败"})

        for index, scenario in enumerate(scenarios):
            user, faces = await seed_scenario(db, scenario.get("seed") or {})
            arms: dict[str, dict[str, Any]] = {}
            for arm in PROMPT_ARMS:
                arms[arm] = await assemble_arm_safe(db, user, scenario, arm)
            failures = check_differentiators(scenario, arms)
            all_failures.extend(failures)
            row = {
                "id": scenario["id"],
                "category": scenario["category"],
                "seeded_faces": faces,
                "differentiator_failures": failures,
                "baseline_profile_structure_diff_chars": (
                    arms["C-PROF"]["prompt_chars"] - arms["A"]["prompt_chars"]
                    if scenario["category"] == "baseline"
                    and arms["C-PROF"]["prompt_sha256"] != arms["A"]["prompt_sha256"]
                    else None
                ),
                "arms": {
                    arm: {
                        "prompt_sha256": arms[arm]["prompt_sha256"],
                        "prompt_chars": arms[arm]["prompt_chars"],
                        "profile_attached": arms[arm]["profile_attached"],
                        "doc_controls_enabled": arms[arm]["doc_controls_enabled"],
                        "token_usage": arms[arm]["token_usage"],
                        "assembly_ms": arms[arm]["assembly_ms"],
                        "assembly_error": arms[arm]["assembly_error"],
                    }
                    for arm in PROMPT_ARMS
                },
            }
            results[scenario["id"]] = {}

            if args.dry_run:
                status = "OK" if not failures else f"FAIL({len(failures)})"
                print(f"  [{index + 1}/{len(scenarios)}] {scenario['id']}: 装配4臂+探针 {status}")
                per_scenario.append(row)
                continue

            # live：逐臂作答 + 判分（消融接线失败的场景照样跑——增益面与接线面分开申报）
            for arm in PROMPT_ARMS:
                arm_entry = arms[arm]
                if arm_entry["prompt"] is None:
                    results[scenario["id"]][arm] = {"score": None, "call_error": arm_entry["assembly_error"]}
                    continue
                call = await answer_arm_live(arm_evidence, arm_entry["prompt"], scenario["user_message"], args.timeout)
                if call["call_error"]:
                    results[scenario["id"]][arm] = {"score": None, **call}
                    print(f"  [{index + 1}/{len(scenarios)}] {scenario['id']} {arm}: CALL_FAIL {call['call_error']}")
                    continue
                judgement = await judge_answer(call["answer"], scenario)
                results[scenario["id"]][arm] = {
                    "score": judgement.get("score"),
                    **call,
                    "judge": judgement,
                    "est_prompt_tokens": est_tokens(arm_entry["prompt"]),
                }
                score = judgement.get("score")
                print(
                    f"  [{index + 1}/{len(scenarios)}] {scenario['id']} {arm}: "
                    f"score={'--' if score is None else format(score, '.2f')} ({call['latency_ms']}ms)"
                )
            row["arms"].update(
                {
                    arm: {
                        **row["arms"][arm],
                        "score": (results[scenario["id"]].get(arm) or {}).get("score"),
                        "answer_head": (results[scenario["id"]].get(arm) or {}).get("answer_head"),
                        "judge": (results[scenario["id"]].get(arm) or {}).get("judge"),
                        "call_error": (results[scenario["id"]].get(arm) or {}).get("call_error"),
                    }
                    for arm in PROMPT_ARMS
                }
            )
            per_scenario.append(row)

    await engine.dispose()

    if args.dry_run:
        run_payload = {
            "schema": SCHEMA_RUN,
            "meta": _meta(args, pack, "dry-run", scenarios, composition),
            "switch_probes": probes,
            "differentiator_failures": all_failures,
            "summary": {"note": "dry-run 装配骨架：真实装配链 4 臂提示词 + 开关传播 + 消融接线硬断言，无 LLM 结果"},
            "gain_matrix": None,
            "per_scenario": per_scenario,
        }
        out_path = _write_run(args.out_dir, run_payload)
        if all_failures:
            print(f"\n[dry-run] 消融接线断言失败 {len(all_failures)} 项：")
            for failure in all_failures[:20]:
                print(f"    - {failure['id']} / {failure['check']}: {failure['detail']}")
            raise SystemExit(f"dry-run wiring failures: {len(all_failures)}（消融没切干净/召回被切，场景或杠杆需修）")
        print(
            f"\n[dry-run] {len(scenarios)} 场景 × {len(PROMPT_ARMS)} 臂真实装配链装配 OK；"
            f"开关探针 { {k: v['pass'] for k, v in probes.items()} }；消融接线断言全绿；输出已落盘：{out_path}"
        )
        return 0

    matrix = build_gain_matrix(scenarios, results)
    print_table(scenarios, results, PROMPT_ARMS)
    print_summary(matrix)
    run_payload = {
        "schema": SCHEMA_RUN,
        "meta": _meta(args, pack, "live", scenarios, composition, arm_evidence=arm_evidence),
        "switch_probes": probes,
        "differentiator_failures": all_failures,
        **matrix,
        "per_scenario": per_scenario,
    }
    out_path = _write_run(args.out_dir, run_payload)
    print(f"\n证据已落盘: {out_path}  (耗时 {time.monotonic() - started:.1f}s)")
    if all_failures:
        print(
            f"注意：{len(all_failures)} 项装配接线断言失败——对应场景的增益结论不可信（见 JSON differentiator_failures）"
        )
    return 0


def _meta(
    args: argparse.Namespace,
    pack: dict[str, Any],
    mode: str,
    scenarios: list[dict[str, Any]],
    composition: dict[str, Any],
    arm_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": f"GAIN-EVAL-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "pack_path": str(args.pack),
        "pack_sha256": hashlib.sha256(Path(args.pack).read_bytes()).hexdigest(),
        "scenario_count": len(scenarios),
        "composition": composition,
        "prompt_arms": {arm: ARM_DESCRIPTIONS[arm] for arm in PROMPT_ARMS},
        "probe_arms": {arm: ARM_DESCRIPTIONS[arm] for arm in PROBE_ARMS},
        "ablation_entry_disclosure": {
            "B-MEM": "无产品开关——评测杠杆（MemoryService 三个召回源读方法置空）；ENABLE_CONTEXT_SOURCE_* 只控 manifest 计量不控注入",
            "C-PROF": "无产品开关——评测杠杆（get_profile_context 抛错→生产 fail-soft 分支）",
            "E-NOPACK": "真实总开关 USE_CONTEXT_PACK=False（进程内 settings 置换，生产零改动）",
            "D-VEC": "真实开关 ENABLE_DOCUMENT_CONTEXT_INJECTION=False（进程内 settings 置换，生产零改动）",
            "G-GALAXY": "真实开关 AURORA_STAGE39_GALAXY_INJECT_MODE=off（进程内 settings 置换，生产零改动）",
        },
        "chat_model": (
            {k: arm_evidence[k] for k in ("model_key", "model_name", "cost_per_1k_usd", "api_key_present")}
            if arm_evidence
            else None
        ),
        "chat_temperature": CHAT_TEMPERATURE,
        "routing_entry": "llm_router.select_model(force_tier=PRO)，env 未切换；provider 直调零 fallback",
        "judge_protocol": "确定性规则优先（expect_groups+forbidden）；llm kind 照 profile_eval_llm_judge 先例（STANDARD 档严格 JSON）",
        "gates": {"gain_positive": GAIN_POSITIVE_THRESHOLD, "baseline_drift": BASELINE_DRIFT_THRESHOLD},
        "credentials": "api_key 仅以布尔在场记录，绝不落盘",
    }


def _write_run(out_dir: Path, payload: dict[str, Any]) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"gain_ab_run_{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(args: argparse.Namespace) -> int:
    return asyncio.run(_async_run(args))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GAIN-EVAL 记忆/画像真实增益消融评测运行器（不切生产开关）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="无 key 装配自检：真实装配链 4 臂提示词 + 开关传播 + 消融接线硬断言，不调 LLM",
    )
    parser.add_argument(
        "--pack",
        default=str(BACKEND_DIR / "tests" / "northstar_eval" / "gain_scenarios.json"),
        help="场景包路径（默认同目录 gain_scenarios.json）",
    )
    parser.add_argument("--out-dir", default=str(default_out_dir()), help="证据目录（默认 v3-output/GAIN-EVAL/runs）")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 场景（冒烟用）")
    parser.add_argument(
        "--ids",
        default=None,
        help="只跑指定场景（逗号分隔 id；pytest 守卫用——每类别抽 1 例做快速接线断言）",
    )
    parser.add_argument("--timeout", type=float, default=CALL_TIMEOUT_S_DEFAULT, help="单场景调用上限秒")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
        help="评测用数据库（默认进程内 SQLite；生产 DB 永不被触碰）",
    )
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    return run(args)


def select_scenarios(pack: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    scenarios = pack["scenarios"]
    if args.ids:
        wanted = [x.strip() for x in args.ids.split(",") if x.strip()]
        by_id = {s["id"]: s for s in scenarios}
        missing = [x for x in wanted if x not in by_id]
        if missing:
            raise SystemExit(f"--ids not in pack: {missing}")
        return [by_id[x] for x in wanted]
    if args.limit:
        return scenarios[: args.limit]
    return scenarios


if __name__ == "__main__":
    raise SystemExit(main())
