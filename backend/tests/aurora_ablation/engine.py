"""A-08 · 四臂纵向会话循环：真实 Aurora 服务驱动 + 确定性结果模型。

一天（会话）的驱动序列（四臂唯一差异在能力面投影）：

1. **日 tick**：真实 spine ``expire_stale``（backdate 时间戳下的真实过期判定）；
2. **chat 决策面**（非 fixed 臂）：真实 ``FrictionChatWiringService.process_turn``
   （spine 状态证据 + A-05 patch 重排 + A-02 规则评估 + ask→answer 闭环）；
3. **恢复旅程面**（非 fixed 臂）：真实 ``StuckJourneyService.start/answer/correct``
   （DB 真源事实 → A-03 诊断 → 单问 → 纠正垫后）；
4. **结果模型**（冻结规则，见模块尾 ``RESULT_RULES``）：主提名 → 当轮解决；
   次提名 → 次轮解决；错位/无行动 → 重试（词牌升级 + 纠正）；预算 3 会话；
5. **经验回路**（full/no_memory 臂）：真实 D-05 exposure/accept/outcome 关联 →
   真实 A-05 patch propose/admit（证据门）/confirm → 后续会话
   ``patched_decision_inputs`` 重排。

fixed 臂零引擎调用：固定模板对任何卡点会话恒回 ``explain``（卡面「固定模板」
基线；无澄清/无适应/无纠正通道——如实按模板 bot 能力建模）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.aurora.friction_diagnosis import (
    FRICTION_INTERVENTION_NOMINATIONS,
    FRICTION_TYPE_TO_LIFECYCLE_TAG,
)
from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from tests.aurora_ablation.persona import (
    ABLATION_SPEC_VERSION,
    EPISODE_SESSION_BUDGET,
    FIXED_TEMPLATE_INTERVENTION,
    ControlSession,
    Episode,
    PersonaSpec,
    friction_spine_key,
    match_class,
    truthful_branch_key,
    utterance_for,
)
from tests.aurora_ablation.world import PersonaWorld

__all__ = ["run_persona_arm", "RESULT_RULES_VERSION"]

RESULT_RULES_VERSION = "aurora_ablation_result_rules.v1"

#: 结果模型冻结常量（REPORT §口径；改动需 bump RESULT_RULES_VERSION）：
#: - primary → 当轮解决；secondary → 次轮解决（同族建议的滞后收敛）；
#: - wrong/无行动 → 重试；预算 ``EPISODE_SESSION_BUDGET`` 会话。
RESULT_RULES = {
    "budget": EPISODE_SESSION_BUDGET,
    "primary_resolves_in": 1,
    "secondary_resolves_in": 2,
}


@dataclass
class _EpisodeState:
    """引擎侧 episode 簿记（世界/服务真源在 DB/Redis；此处只是时间线账）。"""

    episode: Episode
    scheduled_day: int
    attempt: int = 0
    resolved: bool = False
    resolved_day: int | None = None
    resolved_by_intervention: str | None = None
    secondary_pending: bool = False
    decisions: list[dict[str, Any]] = field(default_factory=list)
    correction_filed: bool = False


async def run_persona_arm(spec: PersonaSpec, *, arm: str) -> list[dict[str, Any]]:
    """跑一个 persona × 一个臂的完整时间线；返回逐会话 raw 记录。"""
    records: list[dict[str, Any]] = []
    async with PersonaWorld(spec, arm=arm) as world:
        engine = _ArmEngine(world, spec=spec, arm=arm, records=records)
        await engine.run()
    return records


class _ArmEngine:
    """单臂驱动器（一个 PersonaWorld 一个实例）。"""

    def __init__(
        self,
        world: PersonaWorld,
        *,
        spec: PersonaSpec,
        arm: str,
        records: list[dict[str, Any]],
    ) -> None:
        self.world = world
        self.spec = spec
        self.arm = arm
        self.records = records
        self.sim_day = 0
        self.occupied_until = -1
        self.episode: _EpisodeState | None = None
        self.resolved_episodes = 0
        self.counters = {
            "engine_diagnose_turns": 0,
            "chat_turns": 0,
            "journey_starts": 0,
            "questions_asked": 0,
            "corrections_filed": 0,
            "exposures_recorded": 0,
            "exposure_refusals": 0,
            "outcomes_associated": 0,
            "patches_proposed": 0,
            "patches_admitted": 0,
            "patches_confirmed": 0,
            "patches_rejected": 0,
            "patch_reorders": 0,
        }

    # ------------------------------------------------------------------ main

    async def run(self) -> None:
        for event in self.spec.timeline:
            self.sim_day = max(self.occupied_until + 1, event.day)
            if isinstance(event, ControlSession):
                await self._run_control(event)
                self.occupied_until = max(self.occupied_until, self.sim_day)
                continue
            # 新 episode 开局：上一段未收口则先收口（预算内未解决——真实
            # 世界语义：放弃并留痕，no_memory 臂不留痕）。
            if self.episode is not None and not self.episode.resolved:
                await self._fail_episode(self.episode)
            self.episode = _EpisodeState(episode=event, scheduled_day=self.sim_day)
            await self.world.begin_episode_world(event, self.sim_day)
            await self._run_episode(self.episode)
        if self.episode is not None and not self.episode.resolved:
            await self._fail_episode(self.episode)

    # ------------------------------------------------------------- sessions

    async def _run_episode(self, state: _EpisodeState) -> None:
        while not state.resolved and state.attempt < EPISODE_SESSION_BUDGET:
            await self._stuck_session(state)
            self.occupied_until = max(self.occupied_until, self.sim_day)
            if not state.resolved:
                state.attempt += 1
                self.sim_day += 1  # 重试占下一模拟日

    async def _run_control(self, event: ControlSession) -> None:
        await self.world.day_tick(self.sim_day)
        record = self._base_record(event.day, "control")
        chat: dict[str, Any] | None = None
        if self.arm != "fixed_policy":
            chat = await self._chat_turn(
                event.utterance,
                session_id=f"ctl-{self.spec.persona_id}-{self.sim_day}",
            )
        intrusion = False
        if chat is not None:
            selected = str(((chat.get("intervention") or {}).get("selected")) or "")
            emitted = bool(selected) and selected not in ("no_action", "abstain")
            intrusion = chat["question"] is not None or emitted
        record.update(
            {
                "truth": None,
                "chat": chat,
                "journey": None,
                "control_intrusion": intrusion,
                "note": event.note,
            }
        )
        self.records.append(record)

    async def _stuck_session(self, state: _EpisodeState) -> None:
        episode = state.episode
        await self.world.day_tick(self.sim_day)
        utterance = utterance_for(self.spec, episode, state.attempt)
        record = self._base_record(self.sim_day, "stuck")
        record["truth"] = episode.friction_type
        record["episode_id"] = (
            f"{self.spec.persona_id}:d{state.scheduled_day}:{episode.friction_type}"
        )
        record["attempt"] = state.attempt
        record["utterance"] = utterance

        chat_decision: dict[str, Any] | None = None
        journey_decision: dict[str, Any] | None = None
        questions_this_session = 0

        used: str | None
        if self.arm == "fixed_policy":
            used = FIXED_TEMPLATE_INTERVENTION
            record["fixed_template"] = {"intervention": used}
        else:
            chat_decision = await self._chat_turn(
                utterance,
                session_id=f"ep-{self.spec.persona_id}-{state.scheduled_day}-{state.attempt}",
                truth=episode.friction_type,
            )
            if chat_decision is not None and chat_decision["question"] is not None:
                questions_this_session += 1
            journey_decision = await self._journey_turn(
                truth=episode.friction_type,
                session_key=f"{state.scheduled_day}-{state.attempt}",
            )
            if journey_decision is not None and journey_decision["question_asked"]:
                questions_this_session += 1
            used = self._decision_used(journey_decision, chat_decision)

        mc = match_class(used, episode.friction_type)
        used_surface = self._used_surface(journey_decision, chat_decision)
        record.update(
            {
                "chat": chat_decision,
                "journey": journey_decision,
                "decision_used": used,
                "used_surface": used_surface,
                "match_class": mc,
            }
        )
        resolved_now = False
        if mc == "primary" or mc == "secondary" and (state.secondary_pending or state.attempt >= 1):
            resolved_now = True
        elif mc == "secondary":
            state.secondary_pending = True

        # 纠正反馈环： acted 错位 + persona 有纠正倾向 + 臂有纠正记忆通道。
        correction: dict[str, Any] | None = None
        if (
            not resolved_now
            and mc == "wrong"
            and self.spec.correction_propensity == "active"
            and self.arm in ("full", "no_experience")
            and journey_decision is not None
            and journey_decision["main_intervention"] is not None
            and used_surface == "journey"
        ):
            correction = await self._journey_correct(
                friction_type=str(journey_decision["friction_type"]),
                session_key=f"{state.scheduled_day}-{state.attempt}",
            )
            state.correction_filed = True

        record.update(
            {
                "resolved_now": resolved_now,
                "used_uncertain": self._used_uncertain(journey_decision, chat_decision, used_surface),
                "correction": correction,
                "questions_this_session": questions_this_session,
            }
        )
        state.decisions.append(
            {
                "day": self.sim_day,
                "intervention": used,
                "match_class": mc,
                "surface": self._used_surface(journey_decision, chat_decision),
            }
        )

        if resolved_now:
            state.resolved = True
            state.resolved_day = self.sim_day
            state.resolved_by_intervention = used
            await self.world.complete_episode_task(self.sim_day)
            self.resolved_episodes += 1
            await self.world.refresh_goal_progress()
            if self.arm in ("full", "no_memory"):
                await self._experience_loop(state, record, used_surface=used_surface)
        self.records.append(record)
        if resolved_now:
            self.records.append(
                {
                    "kind": "episode_end",
                    "arm": self.arm,
                    "persona": self.spec.persona_id,
                    "arc": self.spec.arc,
                    "sim_day": self.sim_day,
                    "spec_version": ABLATION_SPEC_VERSION,
                    "episode_id": record["episode_id"],
                    "truth": episode.friction_type,
                    "resolved": True,
                    "sessions_used": state.attempt + 1,
                    "resolving_intervention": used,
                    "resolving_match_class": mc,
                    "resolving_surface": used_surface,
                }
            )

    def _decision_used(
        self,
        journey: dict[str, Any] | None,
        chat: dict[str, Any] | None,
    ) -> str | None:
        """persona 行动依据：按 persona 首选通道（channel）取该面的可行动
        决策；首选面未行动时跟随另一面（真实用户的两面并存行为）。
        两面决策全量保留（指标分面计算）。"""
        journey_act = None
        if journey is not None and journey.get("main_intervention") is not None:
            journey_act = str(journey["main_intervention"]["type"])
        chat_act = None
        if chat is not None and chat.get("intervention") is not None:
            selected = str(chat["intervention"].get("selected") or "")
            if selected and selected not in ("no_action", "abstain"):
                chat_act = selected
        first, second = (
            (journey_act, chat_act) if self.spec.channel == "journey" else (chat_act, journey_act)
        )
        return first or second

    def _used_uncertain(
        self,
        journey: dict[str, Any] | None,
        chat: dict[str, Any] | None,
        used_surface: str,
    ) -> bool | None:
        """被跟随决策的不确定标注（B1 best-guess 面；指标 uncertain_act_rate）。"""
        if used_surface == "journey" and journey is not None:
            return bool(journey.get("uncertain"))
        if used_surface == "chat" and chat is not None:
            data = chat.get("intervention") or {}
            return bool(data.get("uncertain"))
        return None

    def _used_surface(self, journey: dict[str, Any] | None, chat: dict[str, Any] | None) -> str:
        journey_act = journey is not None and journey.get("main_intervention") is not None
        chat_act = False
        if chat is not None and chat.get("intervention") is not None:
            selected = str(chat["intervention"].get("selected") or "")
            chat_act = bool(selected) and selected not in ("no_action", "abstain")
        if self.spec.channel == "journey":
            if journey_act:
                return "journey"
            return "chat" if chat_act else "none"
        if chat_act:
            return "chat"
        return "journey" if journey_act else "none"

    # ------------------------------------------------------------ chat face

    async def _chat_turn(
        self,
        utterance: str,
        *,
        session_id: str,
        truth: str | None = None,
    ) -> dict[str, Any] | None:
        """真实 ``FrictionChatWiringService.process_turn``（ask→truthful answer 闭环）。"""
        from app.services.friction_chat_wiring import FRICTION_ANSWER_CONTEXT_KEY, FrictionChatWiringService

        assert self.world.session is not None and self.world.user_id is not None
        now = await self.world.now_at(self.sim_day)
        svc = FrictionChatWiringService(self.world.session, self.world.redis)
        self.counters["chat_turns"] += 1
        outcome = await svc.process_turn(
            user_id=str(self.world.user_id),
            session_id=session_id,
            user_message=utterance,
            user_context_payload={
                "active_goals": [{"name": "期末计算机网络冲 85 分"}],
                "plan_context": {"plan_id": str(self.world.plan_id)},
            },
            now=now,
        )
        record = self._chat_record(outcome)
        if outcome.mode == "degraded":
            record["degraded"] = True
            return record
        self.counters["engine_diagnose_turns"] += 1

        if outcome.outcome == "ask" and outcome.question is not None and truth is not None:
            # truthful 回答：branch_key 直传主路径（生产客户端同款通道）。
            branch = truthful_branch_key(str(outcome.question["question_id"]), truth)
            self.counters["chat_turns"] += 1
            answer_outcome = await svc.process_turn(
                user_id=str(self.world.user_id),
                session_id=session_id,
                user_message=utterance,
                user_context_payload={
                    "active_goals": [{"name": "期末计算机网络冲 85 分"}],
                    "plan_context": {"plan_id": str(self.world.plan_id)},
                },
                request_extra_context={
                    FRICTION_ANSWER_CONTEXT_KEY: {
                        "question_id": outcome.question["question_id"],
                        "branch_key": branch,
                    }
                },
                now=now,
            )
            record = self._chat_record(answer_outcome)
            record["answer_branch"] = branch
            record["answer_resolution"] = (outcome.annotations or {}).get("answer_resolution")
            if answer_outcome.mode != "degraded":
                self.counters["engine_diagnose_turns"] += 1
        if record.get("patch_moves"):
            self.counters["patch_reorders"] += 1
        record["spine_keys_at_turn"] = await self.world.active_spine_keys()
        return record

    def _chat_record(self, outcome: Any) -> dict[str, Any]:
        data = outcome.to_dict()
        return {
            "mode": data.get("mode"),
            "outcome": data.get("outcome"),
            "friction_type": data.get("friction_type"),
            "question": data.get("question"),
            "intervention": data.get("intervention"),
            "patch_moves": (data.get("policy_patch") or {}).get("moves") or [],
            "applied_patch_ids": (data.get("policy_patch") or {}).get("applied_patch_ids") or [],
            "annotations": data.get("annotations") or {},
        }

    # --------------------------------------------------------- journey face

    async def _journey_turn(self, *, truth: str, session_key: str) -> dict[str, Any] | None:
        from app.services.stuck_journey_service import StuckJourneyService

        assert self.world.session is not None and self.world.user_id is not None
        svc = StuckJourneyService(self.world.session)
        now = await self.world.now_at(self.sim_day)
        self.counters["journey_starts"] += 1
        payload = await svc.start(
            user_id=self.world.user_id,
            surface="home",
            now=now,
        )
        record = self._journey_record(payload)
        record["decision_id_basis"] = f"journey:{session_key}"

        if payload.get("outcome") == "ask" and payload.get("question") is not None:
            qid = str(payload["question"]["question_id"])
            branch = truthful_branch_key(qid, truth)
            answer_payload = await svc.answer(
                user_id=self.world.user_id,
                surface="home",
                question_id=qid,
                branch_key=branch,
                now=now,
            )
            record = self._journey_record(answer_payload)
            record["answer_branch"] = branch
            record["question_cap_reached"] = bool(
                (answer_payload.get("annotations") or {}).get("question_cap_reached")
            )
        return record

    async def _journey_correct(self, *, friction_type: str, session_key: str) -> dict[str, Any] | None:
        from app.services.stuck_journey_service import STUCK_JOURNEY_SURFACES, StuckJourneyService

        assert self.world.session is not None and self.world.user_id is not None
        surface = "home"
        assert surface in STUCK_JOURNEY_SURFACES
        svc = StuckJourneyService(self.world.session)
        now = await self.world.now_at(self.sim_day)
        result = await svc.correct(
            user_id=self.world.user_id,
            surface=surface,
            friction_type=friction_type,
            reason_text="不是这个原因",
            now=now,
        )
        self.counters["corrections_filed"] += 1
        journey = result.get("journey") or {}
        return {
            "corrected_friction_type": friction_type,
            "post_correction_outcome": journey.get("outcome"),
            "post_correction_friction_type": journey.get("friction_type"),
            "post_correction_intervention": (
                (journey.get("main_intervention") or {}).get("type")
                if journey.get("main_intervention")
                else None
            ),
            "session_key": session_key,
        }

    def _journey_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        main = payload.get("main_intervention")
        return {
            "outcome": payload.get("outcome"),
            "friction_type": payload.get("friction_type"),
            "uncertain": bool(payload.get("uncertain")),
            "question": payload.get("question"),
            "question_asked": payload.get("question") is not None,
            "main_intervention": main,
            "context": payload.get("context"),
            "receipt": payload.get("receipt"),
        }

    # ----------------------------------------------------- experience loop

    async def _experience_loop(
        self, state: _EpisodeState, record: dict[str, Any], *, used_surface: str
    ) -> None:
        """真实 D-05 漏斗 + A-05 patch 回路（full/no_memory 臂）。

        exposure/accept/outcome 全走真实 ``InterventionLifecycleService``；
        patch 走真实 ``PolicyPatchService.propose → admit（真实证据门）→
        confirm（persona 确认，与真实交互语义一致）。
        """
        from app.core.outcome_ledger import OutcomeEntry, OutcomePolarity, OutcomeSource, TruthClass
        from app.services.intervention_lifecycle_service import InterventionLifecycleService
        from app.services.policy_patch_service import PolicyPatchService

        assert self.world.session is not None and self.world.user_id is not None
        episode = state.episode
        used = state.resolved_by_intervention
        assert used is not None
        spine_key = friction_spine_key(episode.friction_type)
        tag = FRICTION_TYPE_TO_LIFECYCLE_TAG[episode.friction_type]
        now = await self.world.now_at(self.sim_day)
        session = self.world.session
        user_id = self.world.user_id
        lifecycle = InterventionLifecycleService(session)

        contract = self._surface_contract(used, episode, used_surface)
        exposure = await lifecycle.record_exposure(
            decision=contract,
            user_id=user_id,
            goal_type="exam",
            friction_state_key=spine_key,
            plan_id=self.world.plan_id,
            window_hours=72,
            occurred_at=now,
            emit=False,
        )
        record["exposure"] = {
            "recorded": exposure.recorded,
            "reason": exposure.reason,
            "decision_id": exposure.decision_id,
        }
        if exposure.recorded:
            self.counters["exposures_recorded"] += 1
            await lifecycle.record_response(
                decision_id=exposure.decision_id,
                user_id=user_id,
                event_type="accepted",
                occurred_at=now,
                emit=False,
            )
            # outcome 关联：persona 真实完成任务（world 侧刚 COMPLETED 的任务）。
            task_row = await self._current_completed_task()
            if task_row is not None:
                outcome_entry = OutcomeEntry(
                    outcome_id=_outcome_id(str(task_row.id)),
                    source=OutcomeSource.TASK_COMPLETION,
                    source_id=str(task_row.id),
                    user_id=str(user_id),
                    occurred_at=now,
                    truth_class=TruthClass.SELF_REPORTED,
                    polarity=OutcomePolarity.POSITIVE,
                    source_ref=f"tasks://{task_row.id}",
                    correlation={"task_id": str(task_row.id), "plan_id": str(self.world.plan_id)},
                    minutes=30.0,
                )
                assoc = await lifecycle.record_outcome_association(
                    decision_id=exposure.decision_id,
                    outcome=outcome_entry,
                    emit=False,
                )
                record["outcome_association"] = {
                    "recorded": assoc.recorded,
                    "reason": assoc.reason,
                }
                if assoc.recorded:
                    self.counters["outcomes_associated"] += 1
                    self.world.resolved_refs.setdefault(tag, []).append(exposure.decision_id)
        else:
            self.counters["exposure_refusals"] += 1

        # patch 回路：同 tag 攒到 ≥1 条已关联正向 outcome 的 decision 即提议
        # prefer patch（证据门真实核验）；single_observation → persona confirm。
        refs = self.world.resolved_refs.get(tag) or []
        if not refs:
            return
        patches = PolicyPatchService(session)
        evidence_refs = tuple(f"decision://{d}" for d in refs[-2:])
        proposed = await patches.propose_patch(
            user_id,
            surface="intervention_preference",
            payload={"intervention": used, "direction": "prefer"},
            evidence_refs=evidence_refs,
            provenance="decision_loop",
            scope_friction_tag=tag,
            now=now,
        )
        self.counters["patches_proposed"] += 1
        record["patch_proposal"] = {
            "ok": proposed.record is not None,
            "violations": list(proposed.reasons),
            "patch_id": proposed.record.patch_id if proposed.record is not None else None,
            "idempotent": proposed.idempotent,
        }
        if proposed.record is None:
            self.counters["patches_rejected"] += 1
            return
        admitted = await patches.admit_evidence(user_id, proposed.record.patch_id, now=now)
        self.counters["patches_admitted"] += 1
        state_after = admitted.record.state if admitted.record is not None else None
        record["patch_admission"] = {
            "ok": admitted.record is not None,
            "state": state_after,
            "reasons": list(admitted.reasons),
        }
        if admitted.record is not None and admitted.record.state == "evidenced":
            confirmed = await patches.confirm_patch(user_id, admitted.record.patch_id, now=now)
            self.counters["patches_confirmed"] += 1
            record["patch_confirmation"] = {
                "ok": confirmed.record is not None,
                "state": confirmed.record.state if confirmed.record is not None else None,
            }

    def _surface_contract(self, used: str, episode: Episode, used_surface: str) -> dict[str, Any]:
        """旅程决策的契约载荷（A-01 冻结形状；生命周期服务 coerce 消费）。

        execution_mode 取目录标称镜像（无分配事实的面）；requires_allocation
        成员不带 mode → 契约校验拒 → 真实 refusal（结构守卫，如实计数）。
        """
        item = INTERVENTION_CATALOG[used]
        mode = None
        if not item.is_inert and not item.requires_allocation:
            mode = item.nominal_execution_mode
        return {
            "user_id": str(self.world.user_id),
            "intervention_type": used,
            "rationale_summary": (
                f"A-08 纵向评估 · 模拟日 {self.sim_day} · {episode.friction_type} 卡点恢复旅程决策"
            ),
            "cognition_tier": "l1_light" if used_surface == "chat" else "l2_intervention",
            "execution_mode": mode,
            "governance_mode": "live",
            "trigger_point": "chat_turn" if used_surface == "chat" else "stuck_journey",
            "evidence_refs": ["user_state://stuck_journey"],
            "annotations": {"surface": used_surface, "eval": "A-08"},
        }

    async def _current_completed_task(self) -> Any | None:
        from app.models.task import Task, TaskStatus

        assert self.world.session is not None and self.world.user_id is not None
        row = (
            (
                await self.world.session.execute(
                    select(Task)
                    .where(
                        Task.user_id == self.world.user_id,
                        Task.status == TaskStatus.COMPLETED,
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.completed_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        return row

    # ------------------------------------------------------------- helpers

    async def _fail_episode(self, state: _EpisodeState) -> None:
        """预算内未收口：世界侧放弃留痕（no_memory 臂不留痕——软删）。"""
        await self.world.abandon_episode_task(self.sim_day)
        self.records.append(
            {
                "kind": "episode_fail",
                "arm": self.arm,
                "persona": self.spec.persona_id,
                "arc": self.spec.arc,
                "sim_day": self.sim_day,
                "spec_version": ABLATION_SPEC_VERSION,
                "episode_id": (
                    f"{self.spec.persona_id}:d{state.scheduled_day}:{state.episode.friction_type}"
                ),
                "truth": state.episode.friction_type,
                "resolved": False,
                "attempts": state.attempt,
                "decisions": state.decisions,
            }
        )
        self.episode = None

    def _base_record(self, day: int, kind: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "arc": self.spec.arc,
            "sim_day": day,
            "spec_version": ABLATION_SPEC_VERSION,
            "result_rules_version": RESULT_RULES_VERSION,
            "nominations_truth": (
                list(FRICTION_INTERVENTION_NOMINATIONS.get(self.episode.episode.friction_type, ()))
                if self.episode is not None and kind == "stuck"
                else None
            ),
        }


def _outcome_id(task_id: str) -> str:
    return "outc_" + hashlib.sha256(f"task_completion:{task_id}".encode()).hexdigest()[:32]
