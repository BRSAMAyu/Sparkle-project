"""D-08 · 数据飞轮纵向驱动器（双臂 × Day0/3/7 探针 + 反馈事件）。

驱动纪律（A-08 同源）：
- **世界 = 模拟对象**（User/Plan/Goal/Task/记忆行按时间线 backdate 落库）；
  **Aurora/记忆/理解/outcome/patch 语义零直写**——全部经真实服务；
- **可控时钟**：世界冻结 t0（进入世界的真实墙钟），模拟日 d 的时刻 =
  ``t0 - (d + 0.5)`` 天；服务带 ``now`` 通道直传；无 ``now`` 通道的服务写入
  （judge 落行 / pack telemetry / memory correction）在本模拟步末用 Core
  update 显式回填 ``created_at``（A-08 onupdate 覆盖同款纪律）；
- **persona 决策是显式模型**（seeded，全部落 raw）：对引擎问题 truthful 作答
  （A-08 同款 ``truthful_branch_key``）；旅程面误判 → file「不是这个原因」；
  注入的旧偏好被察觉 → deny（Day1）/ retract（Day4）；其余反馈事件见
  ``protocol.py``。
- 双臂唯一差异 = 反馈事件是否发生（flywheel 开 / no_feedback 关）；世界事件
  （任务完成、探针话轮、记忆种子）两臂完全一致。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import update

from app.aurora.friction_diagnosis import FRICTION_TYPE_TO_LIFECYCLE_TAG
from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from tests.aurora_ablation.persona import (
    ABLATION_SPEC_VERSION,
    Episode,
    PersonaSpec,
    friction_spine_key,
    match_class,
    truthful_branch_key,
)
from tests.aurora_ablation.world import PersonaWorld, sim_clock
from tests.d08_flywheel.protocol import (
    CONTROL_DAY,
    CONTROL_UTTERANCE,
    D08_SPEC_VERSION,
    EVENT_DAYS,
    PROBE_DAYS,
    STALE_KEY,
    ProbeComposition,
    memory_seeds_for,
    probe_composition,
)

__all__ = ["run_persona_arm"]

#: 模拟时间线跨度（天）：sim day d 的真实时刻 = 世界原点 t0 − (SPAN−1−d) 天
#: ——**Day0 最旧、Day7 最近**（纵向叙事沿真实时间正向积累）。A-08
#: ``sim_clock(d) = wall − (d + 0.5)`` 的映射经 ``_wd`` 反转复用（世界侧
#: 方法只消费映射后的 day 值，时间戳语义不变）。
_SPAN_DAYS = 8


async def run_persona_arm(spec: PersonaSpec, *, arm: str) -> list[dict[str, Any]]:
    """跑一个 persona × 一个臂的完整 D-08 时间线；返回逐记录 raw。"""
    records: list[dict[str, Any]] = []
    async with PersonaWorld(spec, arm="full") as world:
        engine = _FlywheelEngine(world, spec=spec, arm=arm, records=records)
        await engine.run()
    return records


class _FlywheelEngine:
    """单臂驱动器（一个 persona 世界一个实例）。"""

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
        self.comp: ProbeComposition = probe_composition(spec)
        self.feedback_on = arm == "flywheel"
        #: 世界时钟原点（进入世界的真实墙钟；所有模拟时刻相对它 backdate）。
        _, wall = sim_clock(0)
        self.t0: datetime = wall
        self.counters = {
            "corrections_filed": 0,
            "patches_proposed": 0,
            "patches_admitted": 0,
            "patches_confirmed": 0,
            "reference_accepted": 0,
            "reference_denied": 0,
            "retractions": 0,
            "exposures_recorded": 0,
            "outcomes_associated": 0,
            "judgments_persisted": 0,
            "pack_builds": 0,
        }
        self._episode_seq = 0
        self._associations_total = 0
        self._correction_ids: list[str] = []
        self._patch_ids: list[str] = []

    # ------------------------------------------------------------------ clock

    def _wd(self, day: int) -> int:
        """sim day → A-08 sim_clock 的 day 值（反转映射；Day0 最旧 Day7 最新）。"""
        return _SPAN_DAYS - 1 - day

    def _moment(self, day: int) -> datetime:
        moment, _ = sim_clock(self._wd(day))
        return moment

    # ------------------------------------------------------------------ main

    async def run(self) -> None:
        assert self.world.session is not None and self.world.user_id is not None
        self.records.append(self._meta_record())
        await self._seed_memories()

        # Day0 基线探针（世界开局：任务 + 失败痕迹 + spine，一次 seeding）。
        episode0 = self._episode_like()
        await self.world.begin_episode_world(episode0, self._wd(PROBE_DAYS[0]))
        probe0 = await self._probe(PROBE_DAYS[0])

        # Day1 事件：世界收口 + D-05 关联（两臂）→ 反馈事件（仅 flywheel）。
        await self._complete_and_associate(EVENT_DAYS[0], probe0)
        if self.feedback_on:
            await self._feedback_after_probe(EVENT_DAYS[0], probe0, retract=False)

        # Day3 中程探针（同构：新任务 + spine 重写；失败痕迹沿用 Day0 seeding，
        # 仍在 14 天窗口内——探针上下文事实恒同）。
        await self._begin_probe_world(PROBE_DAYS[1])
        probe3 = await self._probe(PROBE_DAYS[1])

        # Day4 事件。
        await self._complete_and_associate(EVENT_DAYS[1], probe3)
        if self.feedback_on:
            await self._feedback_after_probe(EVENT_DAYS[1], probe3, retract=True)

        # Day5 对照话轮（over-personalization 探针）。
        await self._control_turn(CONTROL_DAY)

        # Day7 终测探针。
        await self._begin_probe_world(PROBE_DAYS[2])
        await self._probe(PROBE_DAYS[2])

    # ----------------------------------------------------------- meta/roots

    def _meta_record(self) -> dict[str, Any]:
        return {
            "kind": "meta",
            "spec_version": D08_SPEC_VERSION,
            "ablation_spec_version": ABLATION_SPEC_VERSION,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "arc": self.spec.arc,
            "channel": self.spec.channel,
            "composition": {
                "friction_truth": self.comp.friction_truth,
                "days_stalled": self.comp.days_stalled,
                "failure_count": self.comp.failure_count,
                "utterance": self.comp.utterance,
                "truth_primary": self.comp.truth_primary,
            },
            "feedback_on": self.feedback_on,
        }

    def _episode_like(self) -> Episode:
        self._episode_seq += 1
        tier = "weak" if self.spec.explicitness in ("vague", "mixed") else "strong"
        return Episode(
            kind="episode",
            start_day=0,
            friction_type=self.comp.friction_truth,
            first_wordmark_tier=tier,
            failure_count=self.comp.failure_count,
            days_stalled=self.comp.days_stalled,
            note=f"D08 probe episode #{self._episode_seq}",
        )

    # ----------------------------------------------------------- world bits

    async def _begin_probe_world(self, day: int) -> None:
        """探针日开局：新 STUCK 任务（S backdate 相对当日）。

        失败痕迹不重播（Day0 seeding 的痕迹仍在 14 天窗口内）——三探针的
        context 事实（失败数 = F+1 个含当前 STUCK、dsp < 阈值）恒同。
        经验 spine 不写（D-08 五面口径不含经验面；spine TTL 读语义以真实
        墙钟判定，backdate 写入只可能产生不可读的死写或 d7 单侧可见——
        两者都破坏探针同构性；A-08 V3-FIX-49 已登记该面的侵入性）。
        """
        from app.models.task import Task, TaskStatus, TaskType

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        moment = self._moment(day)
        stalled_at = moment - timedelta(days=self.comp.days_stalled)
        task = Task(
            user_id=self.world.user_id,
            plan_id=self.world.plan_id,
            title=f"任务 · TCP {self.comp.friction_truth} 关卡",
            type=TaskType.LEARNING,
            tags=["d08"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.STUCK,
            order_index=day,
            updated_at=stalled_at,
            created_at=stalled_at,
            paused_at=stalled_at,
        )
        session.add(task)
        await session.commit()
        self.world.episode_task_id = task.id

    async def _seed_memories(self) -> None:
        """persona 偏好记忆种子（世界数据；经真实模型行，backdate 落库）。"""
        from app.models.memory import MemoryPreference

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        anchor = self._moment(PROBE_DAYS[0])
        for seed in memory_seeds_for(self.spec.persona_id):
            created = anchor - timedelta(days=seed.created_days_ago)
            session.add(
                MemoryPreference(
                    user_id=self.world.user_id,
                    pref_key=seed.pref_key,
                    pref_value=seed.pref_value,
                    version=1,
                    confidence=seed.confidence,
                    evidence_score=seed.evidence_score,
                    created_at=created,
                    updated_at=created,
                )
            )
        await session.commit()

    async def _backdate_step_writes(self, day: int) -> None:
        """本模拟步内服务侧写入的 created_at 显式回填到该步模拟时刻。

        覆盖理解面窗口查询读取的三张表（judge 落行 / pack telemetry /
        memory correction）；带 ``now`` 通道的服务（journey/chat/patch/
        lifecycle）已直传模拟时刻，无需回填。
        """
        from app.models.aurora_stage20 import AuroraJudgmentRecord
        from app.models.context_pack import ContextPackRun
        from app.models.memory import MemoryCorrection

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        moment = self._moment(day)
        for model in (AuroraJudgmentRecord, ContextPackRun, MemoryCorrection):
            await session.execute(
                update(model)
                .where(model.user_id == self.world.user_id, model.created_at >= self.t0)
                .values(created_at=moment)
            )
        await session.commit()

    # --------------------------------------------------------------- probes

    async def _probe(self, day: int) -> dict[str, Any]:
        """同构探针：chat 话轮 + journey 旅程 + 记忆包 + 确定性 judge + 五面快照。"""
        record: dict[str, Any] = {
            "kind": "probe",
            "spec_version": D08_SPEC_VERSION,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "sim_day": day,
            "utterance": self.comp.utterance,
        }
        chat = await self._chat_turn(day, utterance=self.comp.utterance, truth=self.comp.friction_truth)
        journey = await self._journey_turn(day)
        pack = await self._pack_build(day)
        judgment = await self._judge(day, chat=chat)
        await self._backdate_step_writes(day)

        followed = self._followed(chat, journey)
        record["chat"] = chat
        record["journey"] = journey
        record["followed"] = followed
        record["judgment"] = judgment
        record["faces"] = {
            "understanding": await self._understanding_face(day),
            "memory": await self._memory_face(pack),
            "intervention": self._intervention_face(chat, journey, followed),
            "outcome": {
                "associations_total": self._associations_total,
            },
            "personalization": await self._personalization_face(),
        }
        self.records.append(record)
        return record

    async def _chat_turn(self, day: int, *, utterance: str, truth: str | None) -> dict[str, Any]:
        from app.services.friction_chat_wiring import (
            FRICTION_ANSWER_CONTEXT_KEY,
            FrictionChatWiringService,
        )

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        now = await self.world.now_at(self._wd(day))
        session_id = f"d08-{self.spec.persona_id}-{self.arm}-d{day}"
        await self._write_user_message(day, utterance=utterance, session_id=session_id)
        svc = FrictionChatWiringService(session, self.world.redis)
        payload_ctx: dict[str, Any] = {
            "active_goals": [{"name": "期末计算机网络冲 85 分"}],
            "plan_context": {"plan_id": str(self.world.plan_id)},
        }
        outcome = await svc.process_turn(
            user_id=str(self.world.user_id),
            session_id=session_id,
            user_message=utterance,
            user_context_payload=payload_ctx,
            now=now,
        )
        record = self._chat_record(outcome)
        if outcome.mode != "degraded" and outcome.outcome == "ask" and outcome.question is not None and truth is not None:
            branch = truthful_branch_key(str(outcome.question["question_id"]), truth)
            answer_outcome = await svc.process_turn(
                user_id=str(self.world.user_id),
                session_id=session_id,
                user_message=utterance,
                user_context_payload=payload_ctx,
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
        return record

    async def _write_user_message(self, day: int, *, utterance: str, session_id: str) -> None:
        import uuid

        from app.models.chat import ChatMessage, MessageRole

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        moment = self._moment(day)
        session.add(
            ChatMessage(
                user_id=self.world.user_id,
                # 列为 GUID——由会话语义串派生确定性 UUID（同会话同 id）。
                session_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"d08://{session_id}")),
                role=MessageRole.USER,
                content=utterance,
                created_at=moment,
            )
        )
        await session.commit()

    @staticmethod
    def _chat_record(outcome: Any) -> dict[str, Any]:
        data = outcome.to_dict()
        intervention = data.get("intervention") or {}
        return {
            "mode": data.get("mode"),
            "outcome": data.get("outcome"),
            "friction_type": data.get("friction_type"),
            "question_asked": data.get("question") is not None,
            "selected": intervention.get("selected"),
            "uncertain": bool(intervention.get("uncertain")),
            "nominated": list(intervention.get("friction_nominated") or []),
            "applied_patch_ids": list((data.get("policy_patch") or {}).get("applied_patch_ids") or []),
            "patch_moves": list((data.get("policy_patch") or {}).get("moves") or []),
            "lifecycle_tag": (intervention.get("contract_annotations") or {}).get("friction_lifecycle_tag"),
        }

    async def _journey_turn(self, day: int) -> dict[str, Any]:
        from app.services.stuck_journey_service import StuckJourneyService

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        svc = StuckJourneyService(session)
        now = await self.world.now_at(self._wd(day))
        payload = await svc.start(user_id=self.world.user_id, surface="home", now=now)
        record = self._journey_record(payload)
        if payload.get("outcome") == "ask" and payload.get("question") is not None:
            qid = str(payload["question"]["question_id"])
            branch = truthful_branch_key(qid, self.comp.friction_truth)
            answer_payload = await svc.answer(
                user_id=self.world.user_id,
                surface="home",
                question_id=qid,
                branch_key=branch,
                now=now,
            )
            record = self._journey_record(answer_payload)
            record["answer_branch"] = branch
        return record

    @staticmethod
    def _journey_record(payload: dict[str, Any]) -> dict[str, Any]:
        main = payload.get("main_intervention")
        receipt = payload.get("receipt") or {}
        return {
            "outcome": payload.get("outcome"),
            "friction_type": payload.get("friction_type"),
            "uncertain": bool(payload.get("uncertain")),
            "question_asked": payload.get("question") is not None,
            "intervention": (main or {}).get("type"),
            "adjusted_by_correction": bool((main or {}).get("adjusted_by_correction")),
            "active_corrections": int(receipt.get("active_corrections") or 0),
            "applied_correction_ids": list(receipt.get("applied_correction_ids") or []),
        }

    async def _pack_build(self, day: int) -> dict[str, Any]:
        from app.core.context_pack import ContextPackBuilder

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        builder = ContextPackBuilder(session)
        pack = await builder.build(
            self.world.user_id,
            intent="chat",
            query_text=self.comp.utterance,
        )
        self.counters["pack_builds"] += 1
        surfaced = [str(k) for k in pack.preferences]
        selfcheck = ((pack.metadata or {}).get("memory_selfcheck") or {})
        stale_keys = [k for k in surfaced if k.startswith(STALE_KEY)]
        stale_row = await self._memory_row(stale_keys[0]) if stale_keys else None
        return {
            "surfaced_keys": surfaced,
            "surfaced_count": len(surfaced),
            "goals_count": len(pack.goals),
            "episodic_count": len(pack.episodic_memories),
            "stale_surfaced": bool(stale_keys),
            "stale_position": surfaced.index(stale_keys[0]) if stale_keys else None,
            "selfcheck_input_count": int(selfcheck.get("input_count") or 0),
            "selfcheck_surfaced_count": int(selfcheck.get("surfaced_count") or 0),
            "stale_row": stale_row,
        }

    async def _memory_row(self, pref_key: str) -> dict[str, Any] | None:
        from sqlalchemy import select

        from app.models.memory import MemoryPreference

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        rows = (
            (
                await session.execute(
                    select(MemoryPreference).where(
                        MemoryPreference.user_id == self.world.user_id,
                        MemoryPreference.pref_key == pref_key,
                    )
                )
            )
            .scalars()
            .all()
        )
        latest = max(rows, key=lambda r: r.version, default=None)
        if latest is None:
            return None
        return {
            "memory_id": str(latest.id),
            "version": int(latest.version),
            "confidence": round(float(latest.confidence or 0.0), 4),
            "evidence_score": round(float(latest.evidence_score or 0.0), 4),
            "correction_count": int(latest.correction_count or 0),
            "retracted_at": latest.retracted_at.isoformat() if latest.retracted_at else None,
        }

    async def _judge(self, day: int, *, chat: dict[str, Any]) -> dict[str, Any]:
        """真实 Stage20 确定性 judge（coverage 维度数据源）。

        声明的局限：生产里 ``CurrentTurnParseResult`` 由模型解析面产出；本
        harness 以**固定解析**（同一探针词牌 → 同一解析）喂入——被隔离的是
        解析面波动，judge 本身与落行路径全真实。``UserStateV1`` 信封取自世界
        真实行（当前 STUCK 任务数）——聚合投影为简化版，REPORT 声明。
        """
        from app.services.sufficiency_judge_schema import CurrentTurnParseResult
        from app.services.sufficiency_judge_service import SufficiencyJudgeService
        from app.state_aggregator.schema import UserStateV1

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        stuck_count = await self._in_flight_stuck_count()
        state = UserStateV1(user_id=self.world.user_id)
        judgment = SufficiencyJudgeService().evaluate(
            user_state=state,
            current_turn=CurrentTurnParseResult(
                intent="study_planning",
                intent_confidence=0.9,
                information_sufficient=True,
                target_object_resolved=True,
                constraint_explicit=False,
            ),
        )
        record_id = await SufficiencyJudgeService.persist_judgment(
            session, user_state=state, judgment=judgment
        )
        self.counters["judgments_persisted"] += 1
        return {
            "persisted": record_id is not None,
            "context_sufficiency": float(judgment.context_sufficiency.score),
            "task_sufficiency": float(judgment.task_sufficiency.score),
            "context_missing": list(judgment.context_sufficiency.missing_dimensions),
            "in_flight_stuck_count": stuck_count,
        }

    async def _in_flight_stuck_count(self) -> int:
        from sqlalchemy import func, select

        from app.models.task import Task, TaskStatus

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        total = (
            await session.execute(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.user_id == self.world.user_id,
                    Task.status == TaskStatus.STUCK,
                    Task.deleted_at.is_(None),
                )
            )
        ).scalar()
        return int(total or 0)

    # ------------------------------------------------------------- faces

    async def _understanding_face(self, day: int) -> dict[str, Any]:
        """真实 D-03 五维（真实表取数 + core 纯函数；缺数据 = unknown）。"""
        from datetime import timedelta as _td

        from app.services.understanding_dimensions_service import (
            UnderstandingDimensionsService,
            dimensions_from_inputs,
        )

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        svc = UnderstandingDimensionsService(session)
        metric_date = (self._moment(day) + _td(hours=12)).date()
        inputs = await svc.collect_window_inputs(user_id=self.world.user_id, day=metric_date)
        values = dimensions_from_inputs(inputs)
        return {
            "metric_date": metric_date.isoformat(),
            "dimensions": {name: v.to_dict() for name, v in values.items()},
            "window_inputs": {
                "context_scores": list(inputs.context_scores),
                "usage_opportunities": inputs.usage_opportunities,
                "correctness_negatives": inputs.correctness_negatives,
                "unresolved_conflicts": inputs.unresolved_conflicts,
                "scope_feedback_total": inputs.scope_feedback_total,
                "scope_negatives": inputs.scope_negatives,
                "utility_accepted": inputs.utility_accepted,
                "utility_corrected": inputs.utility_corrected,
                "utility_denied": inputs.utility_denied,
                "lag_days": [round(x, 4) for x in inputs.lag_days],
                "user_messages": list(inputs.user_messages),
            },
        }

    async def _memory_face(self, pack: dict[str, Any]) -> dict[str, Any]:
        return {
            "pack": pack,
            "reference_outcomes": {
                "accepted": self.counters["reference_accepted"],
                "denied": self.counters["reference_denied"],
            },
            "retractions": self.counters["retractions"],
        }

    def _intervention_face(
        self,
        chat: dict[str, Any],
        journey: dict[str, Any],
        followed: dict[str, Any],
    ) -> dict[str, Any]:
        used = followed.get("intervention")
        journey_intervention = journey.get("intervention")
        chat_selected = chat.get("selected")
        chat_act = chat_selected if chat_selected not in (None, "", "no_action", "abstain") else None
        return {
            "chat": chat,
            "journey": journey,
            "followed": followed,
            "match_class": match_class(used, self.comp.friction_truth) if used else None,
            "journey_match": (
                match_class(journey_intervention, self.comp.friction_truth)
                if journey_intervention
                else None
            ),
            "chat_match": (
                match_class(chat_act, self.comp.friction_truth) if chat_act else None
            ),
        }

    async def _personalization_face(self) -> dict[str, Any]:
        from app.services.policy_patch_service import PolicyPatchService

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        patches = await PolicyPatchService(session).effective_patches(self.world.user_id)
        return {
            "active_patches": len(patches),
            "active_patch_ids": sorted(p.patch_id for p in patches),
            "corrections_filed": self.counters["corrections_filed"],
            "applied_correction_ids": list(self._correction_ids),
        }

    def _followed(self, chat: dict[str, Any], journey: dict[str, Any]) -> dict[str, Any]:
        """被跟随决策（A-08 行动模型：首选通道面优先，静默跟随另一面）。"""
        chat_act = chat.get("selected")
        if chat_act in (None, "", "no_action", "abstain"):
            chat_act = None
        journey_act = journey.get("intervention")
        first, second = (
            (journey_act, chat_act)
            if self.spec.channel == "journey"
            else (chat_act, journey_act)
        )
        used = first or second
        if used is None:
            return {"intervention": None, "surface": "none"}
        if self.spec.channel == "journey":
            surface = "journey" if used == journey_act else "chat"
        else:
            surface = "chat" if used == chat_act else "journey"
        return {"intervention": used, "surface": surface}

    # ------------------------------------------------------------- events

    async def _complete_and_associate(self, day: int, probe: dict[str, Any]) -> None:
        """世界收口（persona 完成探针任务）+ 真实 D-05 exposure/accept/outcome。"""
        from app.core.outcome_ledger import OutcomeEntry, OutcomePolarity, OutcomeSource, TruthClass
        from app.services.intervention_lifecycle_service import InterventionLifecycleService

        await self.world.complete_episode_task(self._wd(day))
        await self.world.refresh_goal_progress()
        followed = probe["followed"]
        used = followed.get("intervention")
        event: dict[str, Any] = {
            "kind": "event",
            "spec_version": D08_SPEC_VERSION,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "sim_day": day,
            "event_type": "outcome_association",
            "followed_intervention": used,
            "followed_surface": followed.get("surface"),
        }
        if used is None:
            event["skipped"] = "no_actionable_decision"
            self.records.append(event)
            return
        session = self.world.session
        assert session is not None and self.world.user_id is not None
        now = await self.world.now_at(self._wd(day))
        spine_key = friction_spine_key(self.comp.friction_truth)
        tag = FRICTION_TYPE_TO_LIFECYCLE_TAG[self.comp.friction_truth]
        lifecycle = InterventionLifecycleService(session)
        contract = self._surface_contract(str(used), followed.get("surface") or "chat", day=day)
        exposure = await lifecycle.record_exposure(
            decision=contract,
            user_id=self.world.user_id,
            goal_type="exam",
            friction_state_key=spine_key,
            plan_id=self.world.plan_id,
            window_hours=72,
            occurred_at=now,
            emit=False,
        )
        event["exposure"] = {"recorded": exposure.recorded, "reason": exposure.reason}
        if not exposure.recorded:
            self.records.append(event)
            return
        self.counters["exposures_recorded"] += 1
        await lifecycle.record_response(
            decision_id=exposure.decision_id,
            user_id=self.world.user_id,
            event_type="accepted",
            occurred_at=now,
            emit=False,
        )
        task_row = await self._latest_completed_task()
        if task_row is None:
            event["skipped"] = "no_completed_task_row"
            self.records.append(event)
            return
        outcome_entry = OutcomeEntry(
            outcome_id=_outcome_id(str(task_row.id)),
            source=OutcomeSource.TASK_COMPLETION,
            source_id=str(task_row.id),
            user_id=str(self.world.user_id),
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
        event["association"] = {"recorded": assoc.recorded, "reason": assoc.reason}
        if assoc.recorded:
            self.counters["outcomes_associated"] += 1
            self._associations_total += 1
            event["decision_id"] = exposure.decision_id
            self.world.resolved_refs.setdefault(tag, []).append(exposure.decision_id)
        self.records.append(event)

    def _surface_contract(self, used: str, surface: str, *, day: int) -> dict[str, Any]:
        """旅程/chat 决策的契约载荷（A-01 冻结形状；A-08 同款投影）。

        ``rationale_summary`` 携带模拟日——decision_id 内容寻址，跨事件唯一
        （否则 D-05 exposure 去重会把第二段 outcome 关联判 duplicate）。
        """
        item = INTERVENTION_CATALOG[used]
        mode = None
        if not item.is_inert and not item.requires_allocation:
            mode = item.nominal_execution_mode
        return {
            "user_id": str(self.world.user_id),
            "intervention_type": used,
            "rationale_summary": (
                f"D-08 飞轮纵向评估 · 模拟日 {day} · {self.comp.friction_truth} 卡点决策"
            ),
            "cognition_tier": "l1_light" if surface == "chat" else "l2_intervention",
            "execution_mode": mode,
            "governance_mode": "live",
            "trigger_point": "chat_turn" if surface == "chat" else "stuck_journey",
            "evidence_refs": ["user_state://stuck_journey"],
            "annotations": {"surface": surface, "eval": "D-08"},
        }

    async def _latest_completed_task(self) -> Any | None:
        from sqlalchemy import select

        from app.models.task import Task, TaskStatus

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        row = (
            (
                await session.execute(
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

    async def _feedback_after_probe(self, day: int, probe: dict[str, Any], *, retract: bool) -> None:
        """飞轮反馈事件（仅 flywheel 臂）：纠正 / patch / 记忆反馈。"""
        await self._maybe_file_correction(day, probe)
        await self._maybe_patch(day)
        await self._memory_feedback(day, retract=retract)
        await self._backdate_step_writes(day)

    async def _maybe_file_correction(self, day: int, probe: dict[str, Any]) -> None:
        """旅程面误判 → 「不是这个原因」纠正（真实 ``correct()``）。"""
        journey = probe["faces"]["intervention"]["journey"]
        diagnosed = journey.get("friction_type")
        event: dict[str, Any] = {
            "kind": "event",
            "spec_version": D08_SPEC_VERSION,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "sim_day": day,
            "event_type": "journey_correction",
            "diagnosed_friction_type": diagnosed,
            "truth": self.comp.friction_truth,
        }
        if (
            journey.get("outcome") != "act"
            or diagnosed is None
            or diagnosed == self.comp.friction_truth
        ):
            event["skipped"] = "diagnosis_matches_truth_or_not_act"
            self.records.append(event)
            return
        from app.services.stuck_journey_service import StuckJourneyService

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        svc = StuckJourneyService(session)
        now = await self.world.now_at(self._wd(day))
        result = await svc.correct(
            user_id=self.world.user_id,
            surface="home",
            friction_type=str(diagnosed),
            reason_text="不是这个原因",
            now=now,
        )
        self.counters["corrections_filed"] += 1
        correction_id = str(result.get("correction_id"))
        self._correction_ids.append(correction_id)
        journey_after = result.get("journey") or {}
        event.update(
            {
                "correction_id": correction_id,
                "corrected_friction_type": diagnosed,
                "post_correction_friction_type": journey_after.get("friction_type"),
                "post_correction_intervention": ((journey_after.get("main_intervention") or {}).get("type")),
            }
        )
        self.records.append(event)

    async def _maybe_patch(self, day: int) -> None:
        """A-05 patch 回路：prefer 真值主干预（同 tag 证据门 → confirm）。"""
        from app.services.policy_patch_service import PolicyPatchService

        truth_primary = self.comp.truth_primary
        tag = FRICTION_TYPE_TO_LIFECYCLE_TAG[self.comp.friction_truth]
        refs = self.world.resolved_refs.get(tag) or []
        event: dict[str, Any] = {
            "kind": "event",
            "spec_version": D08_SPEC_VERSION,
            "arm": self.arm,
            "persona": self.spec.persona_id,
            "sim_day": day,
            "event_type": "patch_proposal",
            "prefer_intervention": truth_primary,
            "scope_friction_tag": tag,
            "evidence_refs": [f"decision://{d}" for d in refs[-2:]],
        }
        if truth_primary is None or not refs:
            event["skipped"] = "no_truth_primary_or_no_evidence"
            self.records.append(event)
            return
        session = self.world.session
        assert session is not None and self.world.user_id is not None
        now = await self.world.now_at(self._wd(day))
        patches = PolicyPatchService(session)
        proposed = await patches.propose_patch(
            self.world.user_id,
            surface="intervention_preference",
            payload={"intervention": truth_primary, "direction": "prefer"},
            evidence_refs=tuple(f"decision://{d}" for d in refs[-2:]),
            provenance="decision_loop",
            scope_friction_tag=tag,
            now=now,
        )
        self.counters["patches_proposed"] += 1
        event["proposal"] = {
            "ok": proposed.record is not None,
            "idempotent": proposed.idempotent,
            "violations": list(proposed.reasons),
        }
        if proposed.record is None:
            self.records.append(event)
            return
        patch_id = str(proposed.record.patch_id)
        event["patch_id"] = patch_id
        admitted = await patches.admit_evidence(self.world.user_id, patch_id, now=now)
        self.counters["patches_admitted"] += 1
        state_after = admitted.record.state if admitted.record is not None else None
        event["admission"] = {"ok": admitted.record is not None, "state": state_after}
        if admitted.record is not None and admitted.record.state == "evidenced":
            confirmed = await patches.confirm_patch(self.world.user_id, patch_id, now=now)
            self.counters["patches_confirmed"] += 1
            event["confirmation"] = {
                "ok": confirmed.record is not None,
                "state": confirmed.record.state if confirmed.record is not None else None,
            }
            if confirmed.record is not None:
                self._patch_ids.append(patch_id)
        self.records.append(event)

    async def _memory_feedback(self, day: int, *, retract: bool) -> None:
        """记忆反馈：注入旧偏好 → deny（Day1）/ retract（Day4）；其余注入 accept。"""
        from sqlalchemy import select

        from app.models.memory import MemoryPreference
        from app.services.memory_service import MemoryService

        session = self.world.session
        assert session is not None and self.world.user_id is not None
        last_probe = next(
            r for r in reversed(self.records) if r.get("kind") == "probe"
        )
        surfaced: list[str] = last_probe["faces"]["memory"]["pack"]["surfaced_keys"]
        pref_rows = (
            (
                await session.execute(
                    select(MemoryPreference).where(MemoryPreference.user_id == self.world.user_id)
                )
            )
            .scalars()
            .all()
        )
        latest_by_key: dict[str, MemoryPreference] = {}
        for pref_row in pref_rows:
            if pref_row.deleted_at is not None or pref_row.retracted_at is not None:
                continue
            if (
                pref_row.pref_key not in latest_by_key
                or pref_row.version > latest_by_key[pref_row.pref_key].version
            ):
                latest_by_key[str(pref_row.pref_key)] = pref_row
        svc = MemoryService(session)
        for key in surfaced:
            row: MemoryPreference | None = latest_by_key.get(key)
            if row is None:
                continue
            is_stale = str(key).startswith(STALE_KEY)
            outcome = "denied" if is_stale else "accepted"
            result = await svc.record_memory_reference_outcome(
                kind="preference",
                memory_id=row.id,
                user_id=self.world.user_id,
                outcome=outcome,
                reason="现在改成晚上学了" if outcome == "denied" else None,
            )
            if result is None:
                continue
            if outcome == "denied":
                self.counters["reference_denied"] += 1
            else:
                self.counters["reference_accepted"] += 1
            self.records.append(
                {
                    "kind": "event",
                    "spec_version": D08_SPEC_VERSION,
                    "arm": self.arm,
                    "persona": self.spec.persona_id,
                    "sim_day": day,
                    "event_type": "memory_reference_outcome",
                    "pref_key": key,
                    "outcome": outcome,
                    "confidence_after": result.get("confidence"),
                    "evidence_score_after": result.get("evidence_score"),
                }
            )
        if retract:
            stale_keys = [k for k in latest_by_key if str(k).startswith(STALE_KEY)]
            stale_row = latest_by_key[stale_keys[0]] if stale_keys else None
            if stale_row is None:
                self.records.append(
                    {
                        "kind": "event",
                        "spec_version": D08_SPEC_VERSION,
                        "arm": self.arm,
                        "persona": self.spec.persona_id,
                        "sim_day": day,
                        "event_type": "memory_retract",
                        "skipped": "stale_row_absent_or_already_retracted",
                    }
                )
                return
            ok = await svc.retract_memory(
                kind="preference",
                memory_id=stale_row.id,
                user_id=self.world.user_id,
                reason="这条偏好早就不对了对",
                reason_code="user_revoke",
            )
            if ok:
                self.counters["retractions"] += 1
            self.records.append(
                {
                    "kind": "event",
                    "spec_version": D08_SPEC_VERSION,
                    "arm": self.arm,
                    "persona": self.spec.persona_id,
                    "sim_day": day,
                    "event_type": "memory_retract",
                    "pref_key": STALE_KEY,
                    "memory_id": str(stale_row.id),
                    "retracted": bool(ok),
                }
            )
    async def _control_turn(self, day: int) -> None:
        """对照话轮：正常推进语句——考察系统是否过度介入（两臂同跑）。

        生产语义里每个 chat 话轮都伴随 context pack 组装与 Stage20 judge——
        对照话轮同样驱动（记忆消费标记/使用机会/judgment 落行 = 真实副产物）。
        """
        chat = await self._chat_turn(day, utterance=CONTROL_UTTERANCE, truth=None)
        pack = await self._pack_build(day)
        judgment = await self._judge(day, chat=chat)
        await self._backdate_step_writes(day)
        emitted = bool(chat.get("selected")) and chat["selected"] not in ("no_action", "abstain")
        intrusion = bool(chat.get("question_asked")) or emitted
        self.records.append(
            {
                "kind": "control",
                "spec_version": D08_SPEC_VERSION,
                "arm": self.arm,
                "persona": self.spec.persona_id,
                "sim_day": day,
                "chat": chat,
                "control_intrusion": intrusion,
                "pack_surfaced_count": pack["surfaced_count"],
                "judgment_persisted": judgment["persisted"],
            }
        )


def _outcome_id(task_id: str) -> str:
    import hashlib

    return "outc_" + hashlib.sha256(f"task_completion:{task_id}".encode()).hexdigest()[:32]
