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
    FrictionDiagnosis,
    apply_question_answer,
    diagnose_friction,
    resolve_answer_branch_detail,
)
from app.aurora.intervention_policy import evaluate_intervention_policy
from app.core.policy_patch import SURFACE_PAYLOAD_KEYS
from app.services.policy_patch_service import PolicyPatchService

FRICTION_CHAT_WIRING_VERSION = "friction-chat-wiring.v3"

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


@dataclass
class FrictionWiringOutcome:
    """process_turn 的结构化产出（to_dict 后进 response metadata）。

    非 frozen：``_emit`` 按 ask/act 出口增量填充 question/intervention/policy_patch
    面（服务内部装配载体；对外仍是 to_dict 的只读投影）。
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


class FrictionChatWiringService:
    """chat 决策路径的 A-03/A-05 接线（一个 db 会话一个实例；Redis 可缺席）。"""

    def __init__(self, db: AsyncSession | None, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._patches = PolicyPatchService(db) if db is not None else None    # ------------------------------------------------------------------
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
                        annotations={
                            "answer_resolution": "unresolved_weak_free_text",
                            "wiring_gate": WIRING_GATE_WEAK_ANSWER,
                        },
                    )
        if branch_key is None:
            # 无解析 → 问题保持 pending（用户可稍后点选）；本轮零问句零行动。
            return FrictionWiringOutcome(
                mode="answer_replay",
                outcome="ask",
                friction_type=str(pending.get("friction_type") or "unknown"),
                lifecycle_tag=str(pending.get("lifecycle_tag") or "unattributed"),
                annotations={"answer_resolution": "unresolved_pending_kept"},
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
        return await self._emit(
            user_id=user_id,
            session_id=session_id,
            diagnosis=diagnosis,
            mode="answer_replay",
            payload_ctx=payload_ctx,
            annotations={"answer_resolution": resolution, "answered_branch_key": branch_key},
            now=now,
        )

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
            return FrictionWiringOutcome(
                mode="fresh",
                outcome="no_action",
                friction_type=diagnosis.friction_type,
                lifecycle_tag=diagnosis.lifecycle_tag,
                diagnosis=diagnosis.to_dict(),
                annotations={"wiring_gate": gate_reason},
            )
        return await self._emit(
            user_id=user_id,
            session_id=session_id,
            diagnosis=diagnosis,
            mode="fresh",
            payload_ctx=payload_ctx,
            annotations={},
            now=now,
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
            diagnosis=diagnosis.to_dict(),
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
