"""WIRING-1 · A-03/A-05 chat 决策路径接线服务（FIX-43 接线 + FIX-34 接线）。

把三个「已交付但未接进生产」的引擎接进 chat 决策路径（本模块 = 唯一装配点；
``ChatOrchestrator.process_stream`` 在 context 装配后单点调用 ``process_turn``，
产出经 ``state.context_data["friction_decision"]`` → response metadata 出面）：

0. **V3-FIX-49 · fresh 出口词牌门（v2，2026-09-26）**：orchestrator 对每条
   非工具消息无门调用 ``process_turn``，A-08 四臂消融实证对照会话侵入率
   84%~100%——无词牌普通消息 + stale spine → S1 直出建议（full 臂 21/25）；
   零证据普通消息 → U1 根分裂澄清问（no_experience 臂 25/25）。门契约：
   **fresh 轮 ask/act 出面必须携带正向摩擦自报词牌**（``utterance_matches``
   非空），否则静默 ``no_action``（``annotations.wiring_gate`` 记门原因）。
   降噪不关死：回答闭环不设门、带词牌诊断全链照常、旅程面（用户主动入口）
   不经过本服务——A-08 full 臂「真摩擦介入优于固定模板」的主结论依赖此通道。
   **V3-FIX-111 修订（v3，2026-09-26）**：「回答闭环不设门」的前提「用户在
   回答」仅由 branch_key 直传主路径**结构保证**；自由文本回退层新增
   FIX-49 同构的置信/意图门（``resolve_answer_branch_detail`` 置信面）：
   弱词面命中（单字话语标记「对了」/长消息低覆盖擦碰）不 apply、不 act，
   pending 保持（``wiring_gate=silent_weak_free_text_answer`` 可审计）——
   自由文本不得仅凭词面直出 act。

1. **A-03 摩擦诊断触发（FIX-43a）**：从既有 context 装配
   ``FrictionDiagnosisInput``（utterance=用户消息、spine_state_keys=spine
   state_index 活跃键、task_anchor/has_active_goal=stage34 active_goals、
   clarification_preference=A-05 clarification patch 投影、预算计数=本服务
   会话/日计数），调用 ``diagnose_friction``。装配面**结构诚实**：context
   里不存在的事实保持 None（不猜——引擎对缺省维度保守，unknown 不假诊断）。

2. **ask 闭环（FIX-43a）**：``outcome=="ask"`` 时问句载荷
   （question_id + 渲染文本 + **带 branch_key 的 branch_options**）进
   response metadata（客户端渲染建议选项）；下一轮用户回答经
   **branch_key 直传**（``request_extra_context["friction_answer"]``）或
   自由文本回退（``resolve_answer_branch``，v1_1 最长词牌修复后的解析面）
   → ``apply_question_answer`` 重放诊断（闭环节点，X-09 面已合入的
   输入快照语义）→ 新诊断照常走 act/ask 出口。pending 问题存
   Redis（per user+session，TTL 24h）；Redis 缺席时闭环降级为
   不可用（fresh 诊断照常）——chat 主链路零风险。

3. **A-02 提名通道前置（FIX-43 policy_factors_patch 并入）**：``act`` 出口
   把 ``diagnosis.policy_factors_patch()`` 的 ``nominated`` 前置于既有
   提名（friction 模块 docstring 的调用方约定），再交 A-05 补丁面。

4. **A-05 决策输入接线（FIX-34）**：act 出口实际调用
   ``PolicyPatchService.patched_decision_inputs``（提名重排 + X-02/
   proactive/explanation 因子投影 + 归因），产出 ``nominated`` 喂
   ``evaluate_intervention_policy``（A-02 规则守卫照常）——「策略补丁
   影响决策输入」的 chat 决策环落地。DELTA-2（applied_patch_ids 是
   user 级 active 集归因、非 scope 窄化）与 P3-5（inputs 缓存 120s TTL
   陈旧窗口）语义沿用服务层既有契约，本层不复制判定。

5. **V4-I04 · 无动作仍可纠正与一次决策性澄清**（``NO_ACTION_CORRECTION_MODE``
   ∈ {off, shadow, live}，默认 **off** = 本条零行为）：
   - no_action/abstain 面（含 FIX-49 门拦静默面）挂**自由补充入口**（FIX97
     裁决：单一自由输入「还有什么情况需要我知道？」，不依赖错误行动、
     至多 2 个不同操作后果例子）；
   - 已答 1 个自动澄清轮后引擎仍想追问 → **出口斜坡**（不 surfaced 第二问；
     保守可试方案只能来自引擎自身「预算已用完」B1 出口，零伪造第二诊断）；
   - 用户可**跳过/暂停**（封闭词表+否定前缀守卫「宁漏报」，先于分支解析）；
   - **纠正追踪**（行动改变依据：前后出口 + 答句分支 + reason 码 + 证据
     引用）随 ``context_data["friction_decision"]`` checkpoint 持久——重开
     可见。一审 F-1 整改收口：以上干预面的**行为应用只归 live**；shadow =
     指标+结构化日志+观察注记（不清 pending、不产 no_action、不压制第二问
     ——「shadow=观察零行为变化」红线）；off = 行为级零差量（version 串与
     3 个 null 键除外，见 evidence 勘误）。live 激活时显式 WARN，响应
     I03 N-2「消费侧显式标识」。

词表纪律：零新 event name、零新 ref scheme、prompt 本体零改动（问句经
metadata 出面，不经 prompt 渲染）。

韧性契约：``process_turn`` 对任何上游异常降级 ``mode="degraded"``（chat
主链路永不因接线失败中断）；LLM 0 次（全链确定性服务）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.friction_diagnosis import (
    FRICTION_DIAGNOSIS_VERSION,
    FRICTION_INTERVENTION_NOMINATIONS,
    FrictionDiagnosis,
    apply_question_answer,
    diagnose_friction,
    resolve_answer_branch_detail,
)
from app.aurora.intervention_policy import evaluate_intervention_policy
from app.aurora.no_action_supplement import (
    budget_declared_replay,
    clarification_exit_ramp,
    classify_supplement_constraint,
    conservative_option_from,
    correction_trace,
    difficulty_not_chased,
    match_pause_marker,
    match_skip_marker,
    supplement_entry,
)
from app.core.metrics import AURORA_NO_ACTION_CORRECTION_TOTAL
from app.core.policy_patch import SURFACE_PAYLOAD_KEYS
from app.services.policy_patch_service import PolicyPatchService

FRICTION_CHAT_WIRING_VERSION = "friction-chat-wiring.v4"

#: V3-FIX-49 · chat 面 fresh 出口词牌门的静默出口原因（annotations.wiring_gate）：
#: - 无词牌 + unknown（U1 根分裂澄清问）：对零摩擦证据的普通消息发问卷 = 过度
#:   个性化主源头之一（A-08 no_experience 臂对照侵入 25/25）；
#: - 无词牌 + ask/act（Q1/S1）：stale spine（48h 窗口内）/context 推断单独驱动
#:   的介入（A-08 full 臂对照侵入 21/25，含 S1 直出建议）。
WIRING_GATE_UNKNOWN = "silent_unknown_no_friction_evidence"
WIRING_GATE_NO_WORDMARK = "silent_no_utterance_wordmark"
#: V3-FIX-111 · answer_replay 自由文本回退的弱词面命中静默原因（FIX-49 同构门）：
#: 自由文本不得仅凭词面直出 act——单字话语标记（「对了」）/长消息低覆盖擦碰
#: 不构成「用户在回答」的证据；不 apply、pending 保持（可点选或改述）。
WIRING_GATE_WEAK_ANSWER = "silent_weak_free_text_answer"

#: V3-FIX-114 · 门拦静默出口的 clarify 问句身份替身（封闭问题库 question_id；
#: 渲染全文不出口——与 friction_diagnosis ``_act`` 的单点渲染出处对齐，测试
#: 以 ``_QUESTION_BANK_INDEX["q_standard_clarity"].question_id`` 双钉防漂移）。
_GATE_CLARIFY_QUESTION_REF = "q_standard_clarity"

#: pending 问题 Redis 键（per user+session；TTL 一天——跨天会话按过期处理）。
PENDING_KEY_TEMPLATE = "friction:pending:{user_id}:{session_id}"
PENDING_TTL_SECONDS = 24 * 3600
#: 日预算计数键（per user per day；TTL 两天覆盖时区漂移）。
DAY_BUDGET_KEY_TEMPLATE = "friction:dayasked:{user_id}:{day}"
DAY_BUDGET_TTL_SECONDS = 48 * 3600

#: chat 轮次的生产能力面（A-02 R1 守卫入参；chat 管道事实恒真）。
CHAT_TURN_CAPABILITIES = frozenset({"chat", "llm_generate"})

#: branch_key 直传的请求 extra_context 键（客户端把用户点选的分支键原样回传
#: ——「回答按键解析不走自由文本词牌」的主路径；自由文本解析是回退层）。
FRICTION_ANSWER_CONTEXT_KEY = "friction_answer"

#: V4-I04 · no_action 纠正面的行为档位缓存（fail-closed：未知值按 off + WARN）。
_CORRECTION_MODE_WARNED = False


def _correction_mode() -> str:
    """``settings.NO_ACTION_CORRECTION_MODE`` 档位读取（fail-closed 不猜）。

    off = 零行为（V3 链路**行为级**零差量——payload 仅 version 串 v3→v4 与
    ``to_dict`` 新增的 3 个 null 键不同，见 evidence 勘误）；shadow = 指标+
    结构化日志留痕、行为零变化（marker/澄清观察仅注记，不清 pending、不产
    no_action——一审 F-1 整改后词表行为应用 live-only）；live = 载荷出面。
    live 首次激活打显式 WARN（I03 N-2「消费侧显式标识」：本卡即 no_action
    纠正面 live 裁决语义的归属卡，避免运维误读）。
    """
    global _CORRECTION_MODE_WARNED
    from app.config import settings

    mode = str(getattr(settings, "NO_ACTION_CORRECTION_MODE", "off") or "off").strip().lower()
    if mode not in ("off", "shadow", "live"):
        logger.warning("[FrictionWiring] unknown NO_ACTION_CORRECTION_MODE={!r}; treating as off", mode)
        return "off"
    if mode == "live" and not _CORRECTION_MODE_WARNED:
        _CORRECTION_MODE_WARNED = True
        logger.warning(
            "[FrictionWiring] NO_ACTION_CORRECTION_MODE=live: 无动作自由补充/出口斜坡/纠正追踪"
            "消费面已激活（V4-I04 live 裁决语义；关闭请回设 off）"
        )
    return mode


def _record_correction_metric(surface: str, mode: str) -> None:
    try:
        AURORA_NO_ACTION_CORRECTION_TOTAL.labels(surface=surface, mode=mode).inc()
    except Exception:  # pragma: no cover - 遥测失败不影响主链路
        logger.opt(exception=True).warning("no-action correction metric failed")


def _with_shadow_marker_observation(
    annotations: dict[str, Any],
    observation: dict[str, Any] | None,
) -> dict[str, Any]:
    """F-1 整改 · shadow 观察注记随行（纯函数）。

    shadow 档 marker 命中的观察记录（kind/marker/applied=False）注入出口
    annotations——行为零应用（不清 pending、不产 no_action），注记只声明
    「live 将做什么」。observation 为 None（off/live 或无命中）原样返回。
    """
    if observation is None:
        return annotations
    return {**annotations, "shadow_marker_observation": observation}


def _contender_primary_nominations(diagnosis: FrictionDiagnosis) -> dict[str, str]:
    """竞争带成员 → 首要提名映射（读引擎公开常量，零复制语义）。

    只保留首要提名**互不相同**的成员——FIX97 例子纪律：至多 2 个且必须
    「不同操作后果」，同名/不可得不给（不摆卡点清单）。
    """
    contenders = diagnosis.annotations.get("contenders")
    if not isinstance(contenders, list):
        return {}
    mapping: dict[str, str] = {}
    for ftype in contenders:
        nominations = FRICTION_INTERVENTION_NOMINATIONS.get(str(ftype)) or ()
        if nominations and nominations[0] not in mapping.values():
            mapping[str(ftype)] = nominations[0]
    return mapping


@dataclass
class FrictionWiringOutcome:
    """process_turn 的结构化产出（to_dict 后进 response metadata）。

    非 frozen：``_emit`` 按 ask/act 出口增量填充 question/intervention/policy_patch
    面（服务内部装配载体；对外仍是 to_dict 的只读投影）。

    V4-I04 新增三面（``NO_ACTION_CORRECTION_MODE=live`` 才出面；shadow/off 恒
    None——shadow 只留指标与结构化日志，payload 零变化）：

    - ``supplement_entry``：no_action/abstain/无提案面的自由补充入口（FIX97）；
    - ``exit_ramp``：澄清预算（≤1 自动轮）尽后的封闭出口斜坡——**结构上不携带
      追问**（question 恒 None，``clarification_exit_ramp`` 保证）；
    - ``correction_trace``：澄清/纠正后的行动改变依据追踪（随 checkpoint 持久，
      重开可见；``user_can.skip/pause`` 恒真）。
    """

    version: str = FRICTION_CHAT_WIRING_VERSION
    mode: str = "degraded"  # fresh / answer_replay / degraded
    outcome: str = "no_action"  # FrictionDiagnosis.outcome
    friction_type: str = "unknown"
    lifecycle_tag: str = "unattributed"
    diagnosis: Mapping[str, Any] = field(default_factory=dict)
    question: Mapping[str, Any] | None = None
    intervention: Mapping[str, Any] | None = None
    policy_patch: Mapping[str, Any] | None = None
    supplement_entry: Mapping[str, Any] | None = None
    exit_ramp: Mapping[str, Any] | None = None
    correction_trace: Mapping[str, Any] | None = None
    annotations: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "mode": self.mode,
            "outcome": self.outcome,
            "friction_type": self.friction_type,
            "lifecycle_tag": self.lifecycle_tag,
            "diagnosis": dict(self.diagnosis),
            "question": dict(self.question) if self.question else None,
            "intervention": dict(self.intervention) if self.intervention else None,
            "policy_patch": dict(self.policy_patch) if self.policy_patch else None,
            "supplement_entry": dict(self.supplement_entry) if self.supplement_entry else None,
            "exit_ramp": dict(self.exit_ramp) if self.exit_ramp else None,
            "correction_trace": dict(self.correction_trace) if self.correction_trace else None,
            "annotations": dict(self.annotations),
        }


def _fresh_turn_gate_reason(diagnosis: FrictionDiagnosis) -> str | None:
    """V3-FIX-49 · fresh 出口词牌门的判据（纯函数；answer_replay 不经过此门）。

    - ask/act 出面要求 utterance 携带正向摩擦自报词牌（``utterance_matches``
      非空——引擎注记的词牌证据面）；无词牌 → 静默。
    - 无词牌 + unknown（U1 根分裂澄清问）单独记门原因（问卷式追问面）。
    - no_action 出口本来就静默，不过门。
    """
    if diagnosis.outcome not in ("ask", "act"):
        return None
    matched = diagnosis.annotations.get("utterance_matches")
    if matched:
        return None
    if diagnosis.outcome == "ask" and diagnosis.friction_type == "unknown":
        return WIRING_GATE_UNKNOWN
    return WIRING_GATE_NO_WORDMARK


def _strip_input_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """V3-FIX-142 · 出口载荷剔除 ``annotations.input_snapshot`` 副本（纯函数投影）。

    ``input_snapshot``（utterance/task_anchor 用户内容全文）只服务闭环节点：
    Redis pending 重放源（``_save_pending`` 写 / ``_answer_turn`` 读）与预算
    计数——诊断对象本体上的它原样保留；response metadata 出面副本零消费方
    （仅 response_builder json 序列化出面），整体剔除零损失（FIX-62 零消息
    文本同律；FIX-114 门拦投影的同构扩展到全出口）。
    """
    annotations = payload.get("annotations")
    if isinstance(annotations, Mapping) and "input_snapshot" in annotations:
        payload["annotations"] = {key: value for key, value in annotations.items() if key != "input_snapshot"}
    return payload


def _gate_silent_diagnosis_payload(diagnosis: FrictionDiagnosis) -> dict[str, Any]:
    """V3-FIX-114 · 门拦静默出口的 diagnosis 载荷脱敏投影（纯函数）。

    门拦即「问句未出面」：顶层 outcome=no_action、question=None，但引擎的
    ``diagnosis.to_dict()`` 仍内嵌完整 question 对象（渲染问句全文 + 分支
    选项标签，含 task_anchor 用户内容）与 clarify 渲染全文——潜在消费方按
    顶层 outcome 判静默、按 diagnosis 渲染问句即翻车（wt424 /tmp 探针实证）。
    出口载荷与静默语义对齐：

    - ``question`` 置 None（与顶层 ``outcome.question`` 一致——载荷一致性即
      本卡验收判据；问句身份仍可由 ``reasons`` 的 U1/Q1 reason 码审计）；
    - ``suggested_clarifying_question`` 渲染全文 → 封闭问题库 question_id
      身份（FIX-62 类名/指纹同律：留身份不留文本；出处唯一——
      friction_diagnosis ``_act`` 的 ``q_standard_clarity`` 单点渲染）；
    - ``annotations.input_snapshot`` 整体剔除（V3-FIX-142，经
      ``_strip_input_snapshot``——全出口统一投影）。

    其余判定量（friction_type/reasons/posterior/evidence_refs 等）原样保留
    ——脱敏不抹审计。只动出口载荷构造，门判定（``_fresh_turn_gate_reason``）
    零接触。
    """
    payload = diagnosis.to_dict()
    payload["question"] = None
    if payload.get("suggested_clarifying_question"):
        payload["suggested_clarifying_question"] = _GATE_CLARIFY_QUESTION_REF
    return _strip_input_snapshot(payload)


class FrictionChatWiringService:
    """chat 决策路径的 A-03/A-05 接线（一个 db 会话一个实例；Redis 可缺席）。"""

    def __init__(self, db: AsyncSession | None, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._patches = (
            PolicyPatchService(db) if db is not None else None
        )  # ------------------------------------------------------------------

    # 对外主入口
    # ------------------------------------------------------------------

    async def process_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
        user_context_payload: Mapping[str, Any] | None = None,
        request_extra_context: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> FrictionWiringOutcome:
        """单轮接线：pending 回答闭环优先，否则新鲜诊断。

        任何内部失败 → ``mode="degraded"``（零提名、零问句、零写路径）。
        """
        try:
            ctx = request_extra_context if isinstance(request_extra_context, Mapping) else {}
            payload_ctx = user_context_payload if isinstance(user_context_payload, Mapping) else {}
            pending = await self._load_pending(user_id, session_id)
            if pending is not None:
                return await self._answer_turn(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    pending=pending,
                    request_extra_context=ctx,
                    payload_ctx=payload_ctx,
                    now=now,
                )
            return await self._fresh_turn(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                payload_ctx=payload_ctx,
                request_extra_context=ctx,
                now=now,
            )
        except Exception as exc:  # noqa: BLE001 — chat 主链路韧性契约
            logger.warning("friction chat wiring degraded (chat path unaffected): user={} err={}", user_id, exc)
            return FrictionWiringOutcome(mode="degraded", annotations={"degraded": True, "error": str(exc)})

    # ------------------------------------------------------------------
    # 轮次路：回答闭环 / 新鲜诊断
    # ------------------------------------------------------------------

    async def _answer_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
        pending: dict[str, Any],
        request_extra_context: Mapping[str, Any],
        payload_ctx: Mapping[str, Any],
        now: datetime | None,
    ) -> FrictionWiringOutcome:
        question_id = str(pending.get("question_id") or "")
        correction_mode = _correction_mode()
        # V4-I04 一审 F-1 整改：跳过/暂停词表的**行为应用**只归 live——
        # - live：marker 先于分支解析出面（_skip_turn/_pause_turn——跳过/暂停
        #   不是回答，不消耗答案解析面）；
        # - shadow：只观察（指标+结构化日志+shadow 注记），**不清 pending、
        #   不产 no_action、不压制第二问**——「shadow=观察零行为变化」红线
        #   （一审实测 shadow 下「先暂停一下」清 pending+no_action 与声明不符）；
        # - off：词表零接触（V3 链路行为级零差量：version 串 v3→v4 与 3 个
        #   null 键除外，见 evidence 勘误）。
        shadow_marker_observation: dict[str, Any] | None = None
        if correction_mode == "live":
            pause_marker = match_pause_marker(user_message)
            if pause_marker is not None:
                return await self._pause_turn(
                    user_id=user_id, session_id=session_id, pending=pending, marker=pause_marker
                )
            skip_marker = match_skip_marker(user_message)
            if skip_marker is not None:
                return await self._skip_turn(
                    user_id=user_id, session_id=session_id, pending=pending, marker=skip_marker, now=now
                )
        elif correction_mode == "shadow":
            pause_marker = match_pause_marker(user_message)
            skip_marker = None if pause_marker is not None else match_skip_marker(user_message)
            if pause_marker is not None or skip_marker is not None:
                shadow_marker_observation = {
                    "kind": "pause" if pause_marker is not None else "skip",
                    "marker": pause_marker if pause_marker is not None else skip_marker,
                    "applied": False,  # shadow 只观察：live-only 行为本档零应用
                }
                _record_correction_metric("marker_observation", "shadow")
                logger.info(
                    "[FrictionWiring] shadow marker observation kind={} marker={} (live-only behavior NOT applied: pending kept)",
                    shadow_marker_observation["kind"],
                    shadow_marker_observation["marker"],
                )
        # 1) branch_key 直传（主路径）：客户端回传结构化答案。
        branch_key: str | None = None
        resolution = "pending_absent"
        answer_ctx = request_extra_context.get(FRICTION_ANSWER_CONTEXT_KEY)
        if isinstance(answer_ctx, Mapping) and str(answer_ctx.get("question_id") or "") == question_id:
            candidate = str(answer_ctx.get("branch_key") or "").strip()
            options = {str(opt.get("key") or "") for opt in pending.get("branch_options") or []}
            if candidate in options:
                branch_key = candidate
                resolution = "branch_key_direct"
        # 2) 自由文本回退（v1_1 最长词牌解析面）+ V3-FIX-111 置信/意图门：
        #    自由文本不得仅凭词面直出 act——弱词面命中（单字话语标记/低覆盖
        #    擦碰）不 apply，pending 保持；branch_key 直传不受门影响（结构
        #    保证「用户在回答」，FIX-49 免门声明只对该主路径成立）。
        if branch_key is None and user_message.strip():
            resolved = resolve_answer_branch_detail(question_id, user_message)
            if resolved is not None:
                if resolved.confident:
                    branch_key = resolved.branch_key
                    resolution = "free_text_lexical"
                else:
                    return FrictionWiringOutcome(
                        mode="answer_replay",
                        outcome="ask",
                        friction_type=str(pending.get("friction_type") or "unknown"),
                        lifecycle_tag=str(pending.get("lifecycle_tag") or "unattributed"),
                        annotations=_with_shadow_marker_observation(
                            {
                                "answer_resolution": "unresolved_weak_free_text",
                                "wiring_gate": WIRING_GATE_WEAK_ANSWER,
                            },
                            shadow_marker_observation,
                        ),
                    )
        if branch_key is None:
            # 无解析 → 问题保持 pending（用户可稍后点选）；本轮零问句零行动。
            # shadow 的 marker 观察注记随行（行为与 off 同构：pending 保持）。
            return FrictionWiringOutcome(
                mode="answer_replay",
                outcome="ask",
                friction_type=str(pending.get("friction_type") or "unknown"),
                lifecycle_tag=str(pending.get("lifecycle_tag") or "unattributed"),
                annotations=_with_shadow_marker_observation(
                    {"answer_resolution": "unresolved_pending_kept"},
                    shadow_marker_observation,
                ),
            )

        # 闭环节点：apply_question_answer 以 pending 快照为重放源（诊断是输入
        # 的纯函数——X-09 输入快照语义，不引入第二状态源）。
        stub = FrictionDiagnosis(annotations={"input_snapshot": dict(pending.get("input_snapshot") or {})})
        asked_session = int(pending.get("questions_asked_session") or 1)
        asked_day = await self._day_counter(user_id, now=now) or int(pending.get("questions_asked_day") or 1)
        clarification = await self._clarification_preference(user_id)
        diagnosis = apply_question_answer(
            stub,
            question_id,
            branch_key,
            questions_asked_session=asked_session,
            questions_asked_day=asked_day,
            clarification_preference=clarification,
        )
        await self._clear_pending(user_id, session_id)
        # V4-I04 · 一次决策性澄清：已答 1 个自动澄清轮后引擎仍想追问 → 不 surfaced
        # 第二问，以「预算已用完」声明触发引擎自身 B1/B2/B3 出口 + 出口斜坡
        # （直接说情况/保守可试方案/先暂停）。一审 F-1 整改：该压制同属 marker/
        # 澄清干预面——**只归 live**；shadow 只观察（V3 第二问照常出面，行为与
        # off 零差量），off 不干预（V3 允许问句预算 2）。
        annotations: dict[str, Any] = _with_shadow_marker_observation(
            {"answer_resolution": resolution, "answered_branch_key": branch_key},
            shadow_marker_observation,
        )
        exit_ramp: dict[str, Any] | None = None
        if correction_mode == "live" and diagnosis.outcome == "ask":
            annotations["suppressed_second_ask"] = (
                diagnosis.question.question_id if diagnosis.question is not None else None
            )
            annotations["exit_reason"] = "v4_clarification_budget_exhausted"
            diagnosis = budget_declared_replay(
                dict(pending.get("input_snapshot") or {}),
                answer=(question_id, branch_key),
                clarification_preference=clarification,
            )
            exit_ramp = clarification_exit_ramp(
                conservative_option=conservative_option_from(diagnosis),
                prior_question_id=question_id,
            )
            _record_correction_metric("exit_ramp", correction_mode)
        elif correction_mode == "shadow" and diagnosis.outcome == "ask":
            # shadow 只观察：live 将在此压制第二问并给出口斜坡——本档零应用。
            _record_correction_metric("second_ask_observation", "shadow")
            logger.info(
                "[FrictionWiring] shadow second_ask observation question={} (live would suppress + exit ramp; behavior unchanged)",
                diagnosis.question.question_id if diagnosis.question is not None else None,
            )
        base = await self._emit(
            user_id=user_id,
            session_id=session_id,
            diagnosis=diagnosis,
            mode="answer_replay",
            payload_ctx=payload_ctx,
            annotations=annotations,
            now=now,
        )
        if correction_mode != "off":
            # 纠正追踪：行动改变依据可追踪（live 出面 / shadow 留痕不出面）。
            trace = correction_trace(
                before_outcome="ask",
                after_outcome=diagnosis.outcome,
                basis={
                    "channel": "clarification_answer",
                    "answer_resolution": resolution,
                    "answered_branch_key": branch_key,
                    "reason_codes": list(diagnosis.reasons),
                    "evidence_refs": list(diagnosis.evidence_refs),
                    "exit_ramp_reason": annotations.get("exit_reason"),
                },
            )
            _record_correction_metric("trace", correction_mode)
            if correction_mode == "live":
                base.correction_trace = trace
                base.exit_ramp = exit_ramp
            else:
                logger.info(
                    "[FrictionWiring] shadow trace id={} before=ask after={} ramp={}",
                    trace["trace_id"],
                    diagnosis.outcome,
                    exit_ramp is not None,
                )
        return base

    async def _skip_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        pending: Mapping[str, Any],
        marker: str,
        now: datetime | None,
    ) -> FrictionWiringOutcome:
        """V4-I04 · 用户跳过当前问句：pending 清除 + 保守可试方案或如实无行动。

        一审 F-1 整改：本方法即 marker 的**行为应用**，入口仅 ``_answer_turn``
        的 live 分支（shadow/off 不会到达——shadow 只留观察注记）。
        保守方案只能来自引擎自身「预算已用完」出口（B1 best-guess，uncertain
        如实标注）——本层零伪造诊断；B2/B3 无行动出口如实给纯斜坡（不锁聊天）。
        """
        correction_mode = _correction_mode()
        await self._clear_pending(user_id, session_id)
        _record_correction_metric("skip", correction_mode)
        diagnosis = budget_declared_replay(dict(pending.get("input_snapshot") or {}))
        trace = correction_trace(
            before_outcome="ask",
            after_outcome=diagnosis.outcome,
            basis={
                "channel": "clarification_skip",
                "marker": marker,
                "question_id": str(pending.get("question_id") or ""),
                "reason_codes": list(diagnosis.reasons),
            },
            skipped=True,
        )
        exit_ramp = clarification_exit_ramp(
            conservative_option=conservative_option_from(diagnosis),
            reason="user_skipped_clarification",
            prior_question_id=str(pending.get("question_id") or ""),
        )
        base = await self._emit(
            user_id=user_id,
            session_id=session_id,
            diagnosis=diagnosis,
            mode="answer_replay",
            payload_ctx={},
            annotations={"clarification_exit": "skip", "skip_marker": marker},
            now=now,
        )
        if correction_mode == "live":
            base.correction_trace = trace
            base.exit_ramp = exit_ramp
        else:
            logger.info("[FrictionWiring] shadow skip trace id={} after={}", trace["trace_id"], diagnosis.outcome)
        return base

    async def _pause_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        pending: Mapping[str, Any],
        marker: str,
    ) -> FrictionWiringOutcome:
        """V4-I04 · 用户暂停：本域静默（零提名、零问句、零写路径），随时可继续。

        一审 F-1 整改：本方法即 marker 的**行为应用**（清 pending + no_action
        出口），入口仅 ``_answer_turn`` 的 live 分支——shadow 档对同一句子只留
        观察注记、pending 保持（「shadow=观察零行为变化」红线）。
        输入与返回继续可用（FIX97 同律）；追踪记录 paused=True——暂停是可见的
        用户选择，不是永久失败固化。
        """
        correction_mode = _correction_mode()
        await self._clear_pending(user_id, session_id)
        _record_correction_metric("pause", correction_mode)
        trace = correction_trace(
            before_outcome="ask",
            after_outcome="no_action",
            basis={
                "channel": "clarification_pause",
                "marker": marker,
                "question_id": str(pending.get("question_id") or ""),
            },
            paused=True,
        )
        base = FrictionWiringOutcome(
            mode="answer_replay",
            outcome="no_action",
            friction_type=str(pending.get("friction_type") or "unknown"),
            lifecycle_tag=str(pending.get("lifecycle_tag") or "unattributed"),
            annotations={"clarification_exit": "pause", "paused": True, "pause_marker": marker},
        )
        if correction_mode == "live":
            base.correction_trace = trace
        else:
            logger.info("[FrictionWiring] shadow pause trace id={}", trace["trace_id"])
        return base

    async def _fresh_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
        payload_ctx: Mapping[str, Any],
        request_extra_context: Mapping[str, Any],
        now: datetime | None,
    ) -> FrictionWiringOutcome:
        input_mapping = await self.assemble_input(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            user_context_payload=payload_ctx,
            request_extra_context=request_extra_context,
            now=now,
        )
        diagnosis = diagnose_friction(input_mapping)
        # V3-FIX-49 · fresh 出口词牌门（降噪不关死）：orchestrator 对每条非工具
        # 消息无门调用本服务（WIRING-1 生产接线），A-08 四臂消融实证两条侵入
        # 机制——①零证据普通消息恒触发 U1 根分裂澄清问；②stale spine 单独
        # 驱动 S1 直出建议/Q1 追问。chat 面的 ask/act 出面必须携带**正向摩擦
        # 自报词牌**（utterance 词牌命中非空）；否则静默 no_action（门原因入
        # annotations，可审计）。回答闭环（answer_replay）与本服务外的旅程面
        # （用户主动「我卡住了」）不受门影响——真摩擦介入通道保持全通。
        gate_reason = _fresh_turn_gate_reason(diagnosis)
        if gate_reason is not None:
            # V3-FIX-114 · 静默出口载荷脱敏：被拦问句全文（question 对象/
            # clarify 渲染文本）不进 metadata——只动载荷构造，门判定不变。
            base = FrictionWiringOutcome(
                mode="fresh",
                outcome="no_action",
                friction_type=diagnosis.friction_type,
                lifecycle_tag=diagnosis.lifecycle_tag,
                diagnosis=_gate_silent_diagnosis_payload(diagnosis),
                annotations={"wiring_gate": gate_reason},
            )
            self._attach_supplement_entry(base, diagnosis)
            return base
        base = await self._emit(
            user_id=user_id,
            session_id=session_id,
            diagnosis=diagnosis,
            mode="fresh",
            payload_ctx=payload_ctx,
            annotations={},
            now=now,
        )
        self._attach_supplement_entry(base, diagnosis)
        # V4-I04 · 自由补充消费面：fresh 轮的 utterance 本身就是用户主动补充
        # （FIX-49 门保证 fresh act/ask 必带正向自报词牌；用户主动不占系统追问
        # 预算）。产出纠正追踪 + 临时约束分类 + 难度守卫复核——行动改变依据
        # 可追踪（live 出面 / shadow 留痕）。
        correction_mode = _correction_mode()
        if correction_mode != "off":
            constraint = classify_supplement_constraint(user_message)
            guard_ok = difficulty_not_chased((), diagnosis.posterior, after_annotations=diagnosis.annotations)
            if base.outcome in ("act", "ask") or constraint is not None or not guard_ok:
                trace = correction_trace(
                    before_outcome=None,
                    after_outcome=base.outcome,
                    basis={
                        "channel": "free_supplement",
                        "reason_codes": list(diagnosis.reasons),
                        "evidence_refs": list(diagnosis.evidence_refs),
                        "constraint_kind": (constraint or {}).get("kind"),
                        "constraint_scope": (constraint or {}).get("scope"),
                        "difficulty_guard_ok": guard_ok,
                        "budget_impact": "none",
                    },
                )
                _record_correction_metric("free_supplement", correction_mode)
                if correction_mode == "live":
                    base.correction_trace = trace
                else:
                    logger.info(
                        "[FrictionWiring] shadow free_supplement trace id={} outcome={} constraint={}",
                        trace["trace_id"],
                        base.outcome,
                        (constraint or {}).get("kind"),
                    )
        return base

    def _attach_supplement_entry(self, base: FrictionWiringOutcome, diagnosis: FrictionDiagnosis) -> None:
        """V4-I04 · FIX97：no_action/abstain 面挂自由补充入口（live 出面）。

        该入口**不依赖错误行动存在**（FIX97 核心语义），不受 FIX-49 词牌门
        影响——门拦的是「无词牌介入面」，补充入口是用户主动出口，恒可达。
        shadow/off 档 payload 零变化（指标+日志留痕）。
        """
        mode = _correction_mode()
        if mode == "off" or base.outcome not in ("no_action", "abstain"):
            return
        entry = supplement_entry(
            outcome=base.outcome,
            contender_primary_nominations=_contender_primary_nominations(diagnosis),
            friction_type=diagnosis.friction_type,
        )
        if entry is None:
            return
        _record_correction_metric("supplement_entry", mode)
        if mode == "live":
            base.supplement_entry = entry
        else:
            logger.info(
                "[FrictionWiring] shadow supplement_entry available outcome={} examples={}",
                base.outcome,
                len(entry["examples"]),
            )

    # ------------------------------------------------------------------
    # 出口装配：ask → pending+问句载荷；act → A-05 补丁面 + A-02 评估
    # ------------------------------------------------------------------

    async def _emit(
        self,
        *,
        user_id: str,
        session_id: str,
        diagnosis: FrictionDiagnosis,
        mode: str,
        payload_ctx: Mapping[str, Any],
        annotations: Mapping[str, Any],
        now: datetime | None,
    ) -> FrictionWiringOutcome:
        base = FrictionWiringOutcome(
            mode=mode,
            outcome=diagnosis.outcome,
            friction_type=diagnosis.friction_type,
            lifecycle_tag=diagnosis.lifecycle_tag,
            # V3-FIX-142 · 全出口载荷剔除 input_snapshot 副本（utterance 用户
            # 原话全文不进 response metadata；诊断对象本体零接触——下方预算
            # 计数与 _save_pending 重放源读的仍是对象 annotations）。
            diagnosis=_strip_input_snapshot(diagnosis.to_dict()),
            annotations=dict(annotations),
        )
        if diagnosis.outcome == "ask" and diagnosis.question is not None:
            asked_session = (
                int((diagnosis.annotations.get("input_snapshot") or {}).get("questions_asked_session") or 0) + 1
            )
            await self._save_pending(user_id, session_id, diagnosis, asked_session=asked_session, now=now)
            await self._bump_day_counter(user_id, now=now)
            base.question = {
                "question_id": diagnosis.question.question_id,
                "text": diagnosis.question.text,
                "branch_options": [{"key": key, "label": label} for key, label in diagnosis.question.branch_options],
                "information_gain_bits": round(diagnosis.question.information_gain_bits, 6),
                "decision_sensitive": diagnosis.question.decision_sensitive,
            }
            base.annotations = {
                **base.annotations,
                "answer_channel": "branch_key_direct_preferred",
            }
            return base

        if diagnosis.outcome == "act" and diagnosis.nominated_interventions:
            decision = await self._decide_intervention(
                user_id=user_id,
                diagnosis=diagnosis,
                payload_ctx=payload_ctx,
            )
            if decision is not None:
                base.intervention = decision["intervention"]
                base.policy_patch = decision["policy_patch"]
        return base

    async def _decide_intervention(
        self,
        *,
        user_id: str,
        diagnosis: FrictionDiagnosis,
        payload_ctx: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """act 出口的决策输入链（FIX-34 / FIX-43 落点）：

        ``policy_factors_patch().nominated`` **前置**并入提名通道（friction
        模块的调用方约定）→ ``patched_decision_inputs``（A-05：重排 + 因子
        投影 + 归因；120s 进程缓存契约沿用）→ A-02 规则评估（守卫照常）。
        """
        if self._patches is None:
            return None
        friction_nominated = tuple(diagnosis.policy_factors_patch().get("nominated") or ())
        if not friction_nominated:
            return None
        patched = await self._patches.patched_decision_inputs(
            user_id,
            nominated=friction_nominated,
            friction_tag=diagnosis.lifecycle_tag,
        )
        task_context = bool(payload_ctx.get("plan_context") or payload_ctx.get("current_task"))
        evaluation = evaluate_intervention_policy(
            {
                "nominated": patched.nominated,
                "capabilities": CHAT_TURN_CAPABILITIES,
                "has_task_context": task_context,
            }
        )
        return {
            "intervention": {
                "selected": evaluation.selected,
                "feasible": list(evaluation.feasible_interventions),
                "why": list(evaluation.why),
                "friction_nominated": list(friction_nominated),
                "friction_type": diagnosis.friction_type,
                "uncertain": diagnosis.uncertain,
                "contract_annotations": diagnosis.contract_annotations(),
            },
            "policy_patch": {
                "policy_patch_version": patched.policy_patch_version,
                "applied_patch_ids": list(patched.applied_patch_ids),
                "nominated_patched": list(patched.nominated),
                "moves": [
                    {
                        "patch_id": move.patch_id,
                        "surface": move.surface,
                        "intervention": move.intervention,
                        "direction": move.direction,
                        "from_rank": move.from_rank,
                        "to_rank": move.to_rank,
                    }
                    for move in patched.moves
                ],
                "explanation_style": patched.explanation_style,
            },
        }

    # ------------------------------------------------------------------
    # 输入装配（从既有 context；缺事实保持 None——不猜）
    # ------------------------------------------------------------------

    async def assemble_input(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
        user_context_payload: Mapping[str, Any] | None,
        request_extra_context: Mapping[str, Any] | None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        payload_ctx = user_context_payload if isinstance(user_context_payload, Mapping) else {}

        active_goals = payload_ctx.get("active_goals")
        goals = [g for g in active_goals if isinstance(g, Mapping)] if isinstance(active_goals, list) else []
        task_anchor = None
        for goal in goals:
            name = str(goal.get("name") or "").strip()
            if name:
                task_anchor = name[:60]
                break

        clarification = await self._clarification_preference(user_id)
        asked_session = await self._session_counter(user_id, session_id)
        asked_day = await self._day_counter(user_id, now=now)

        return {
            "utterance": user_message or "",
            "spine_state_keys": await self._spine_state_keys(user_id),
            "task_anchor": task_anchor,
            "has_active_goal": bool(goals) if goals else None,
            "has_task_context": bool(payload_ctx.get("plan_context") or payload_ctx.get("current_task")) or None,
            "clarification_preference": clarification,
            "questions_asked_session": asked_session,
            "questions_asked_day": asked_day,
        }

    async def _spine_state_keys(self, user_id: str) -> list[str]:
        """spine state_index 活跃键（只读；值域归一交引擎 coerce——未知键被
        引擎登记 annotations 后忽略）。Redis 缺席 → 空集（行为信号诊断照常）。"""
        if self.redis is None:
            return []
        try:
            raw = await self.redis.smembers(f"spine:state_index:{user_id}")
        except Exception:
            return []
        keys: list[str] = []
        for entry in raw or ():
            key = entry if isinstance(entry, str) else entry.decode("utf-8", "ignore")
            if key and key not in keys:
                keys.append(key)
        return keys

    async def _clarification_preference(self, user_id: str) -> str | None:
        """A-05 clarification patch → ask_more/ask_less（预算面反向通道；
        无 db/无 patch → None）。scope 未约束维度放行（PolicyPatch.scope_matches）。"""
        if self._patches is None:
            return None
        try:
            patches = await self._patches.effective_patches(user_id)
        except Exception:
            return None
        for patch in patches:
            if patch.surface != "clarification":
                continue
            if not patch.scope_matches(goal_type=None, friction_tag=None):
                continue
            mode_key = SURFACE_PAYLOAD_KEYS["clarification"]
            value = str(patch.payload.get(mode_key) or "").strip()
            if value:
                return value
        return None

    # ------------------------------------------------------------------
    # pending 问题存储 + 预算计数（Redis；缺席降级）
    # ------------------------------------------------------------------

    def _pending_key(self, user_id: str, session_id: str) -> str:
        return PENDING_KEY_TEMPLATE.format(user_id=user_id, session_id=session_id)

    async def _load_pending(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(self._pending_key(user_id, session_id))
        except Exception:
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except (ValueError, TypeError):
            return None

    async def _save_pending(
        self,
        user_id: str,
        session_id: str,
        diagnosis: FrictionDiagnosis,
        *,
        asked_session: int,
        now: datetime | None,
    ) -> None:
        if self.redis is None or diagnosis.question is None:
            return
        record = {
            "question_id": diagnosis.question.question_id,
            "text": diagnosis.question.text,
            "branch_options": [{"key": key, "label": label} for key, label in diagnosis.question.branch_options],
            "friction_type": diagnosis.friction_type,
            "lifecycle_tag": diagnosis.lifecycle_tag,
            "input_snapshot": dict(diagnosis.annotations.get("input_snapshot") or {}),
            "questions_asked_session": asked_session,
            "schema_version": FRICTION_DIAGNOSIS_VERSION,
            "asked_at": (now or datetime.utcnow()).isoformat(),
        }
        try:
            await self.redis.set(
                self._pending_key(user_id, session_id),
                json.dumps(record, ensure_ascii=False),
                ex=PENDING_TTL_SECONDS,
            )
        except Exception:
            logger.debug("friction pending save failed (non-fatal): user={}", user_id)

    async def _clear_pending(self, user_id: str, session_id: str) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.delete(self._pending_key(user_id, session_id))
        except Exception:
            pass

    async def _session_counter(self, user_id: str, session_id: str) -> int:
        pending = await self._load_pending(user_id, session_id)
        if pending is not None:
            return int(pending.get("questions_asked_session") or 0)
        return 0

    def _day_key(self, user_id: str, now: datetime | None) -> str:
        day = (now or datetime.utcnow()).strftime("%Y%m%d")
        return DAY_BUDGET_KEY_TEMPLATE.format(user_id=user_id, day=day)

    async def _day_counter(self, user_id: str, *, now: datetime | None) -> int:
        if self.redis is None:
            return 0
        try:
            raw = await self.redis.get(self._day_key(user_id, now))
        except Exception:
            return 0
        if raw is None:
            return 0
        try:
            return int(raw if isinstance(raw, (int, float, str)) else 0)
        except (TypeError, ValueError):
            return 0

    async def _bump_day_counter(self, user_id: str, *, now: datetime | None) -> None:
        if self.redis is None:
            return
        try:
            key = self._day_key(user_id, now)
            count = await self.redis.get(key)
            try:
                current = int(count) if count is not None else 0
            except (TypeError, ValueError):
                current = 0
            await self.redis.set(key, str(current + 1), ex=DAY_BUDGET_TTL_SECONDS)
        except Exception:
            pass
