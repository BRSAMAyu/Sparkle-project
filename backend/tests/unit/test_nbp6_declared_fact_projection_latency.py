"""NBP-6（NORTHSTAR-LOOP3）：WS 声明 fact → 今日面板投影延迟 30-90s 消除回归。

验收现场（v3-output/NORTHSTAR-LOOP3/REPORT.md NBP-6 + evidence/snapshot-memory-episodic-{30,90}s.json）：
V1-A 轮收尾 enqueue 后 30s 读 /api/v1/memory/episodic 0 条、90s 读 3 条。
带内实证：候选抽取 occurred_at=15:27:38.13（enqueue 即跑，`loop.create_task`
无排队）→ episodic created_at=15:28:29.36，**带内滞留 51.2s**；30s 探针
（15:28:27.7）差 1.6s 扑空。

根因（修复前）：``WorkingMemoryPipelineService.process_chat_turn`` 把全部候选
（含明示事实）排在 ``LlmExtractorService.dry_run_extract`` 的真实 LLM 往返之后
——每轮一次 ``llm_service.chat_json``（fallback 链首块超时 45s/90s，供应商
拥塞时更久），而明示事实抽取是确定性正则（零 LLM），与 LLM 输出零依赖，
其 working-memory upsert + ``promote_entry_now``（episodic 即时固化）却被
串行阻塞。读面（/api/v1/memory/episodic、pending-commitments、goal_today_view）
全部直查 DB 零缓存 → 面板延迟 = 写入延迟，全在带内这一段。

修复：declared 快车道先于 LLM 抽取执行（upsert+promote 只耗 Redis+DB 写）；
LLM 抽取面（规则/LLM 候选补强腿）照旧其后运行，抽取质量零变化。

红线断言：
- LLM 抽取仍被调用（不因重排被跳过）；
- declared 候选不因重排被双处理（mention_count 不虚增）；
- working_memory=off 时行为零变化（LLM dry-run 照跑、零 episodic 写入）；
- 轮内写入提交后，今日面板读面（list_recent_episodic / pending-commitments）
  无 sleep 立即可见（读面零缓存的结构性证明）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services import commitment_parser as commitment_parser_module
from app.services import memory_inferred_write_lane as lane_module
from app.services.accountability_mvp_service import AccountabilityMvpService
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.llm_extractor_service import LlmExtractorService
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService
from app.services.memory_service import MemoryService
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.services.working_memory_pipeline_service import WorkingMemoryPipelineService
from app.working_memory.service import WorkingMemoryService

# B1 验收原句（与 NBP-1 回归同源：考试/弱点/约束三句明示事实）。
B1_ONBOARDING_MESSAGE = (
    "你好，我要开始备考：离散数学期末考试在 7 天后（闭卷，100 分卷）。"
    "我的情况：自评当前掌握度大约 42/100；最薄弱的章是图论（CH4）；"
    "一个具体的困惑：我总是分不清欧拉回路和哈密顿回路的判定条件，考试肯定考。"
    "我每天只能投入 165 分钟。请帮我建立目标并给我冲刺计划。"
)

FROZEN_NOW = datetime(2026, 9, 21, 12, 0, 0)


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch):
    monkeypatch.setattr(commitment_parser_module, "_utcnow", lambda: FROZEN_NOW)
    monkeypatch.setattr(lane_module, "_utcnow", lambda: FROZEN_NOW)


def _patch_kill_switch_modes(monkeypatch, *, working_memory: str, llm_extractor: str) -> None:
    """确定性 kill-switch：Redis/设置缺省都不参与，测试自持。"""

    async def _mode(self, key: str) -> str:  # noqa: ANN001
        if key == "working_memory_enabled":
            return working_memory
        if key == "llm_extractor_enabled":
            return llm_extractor
        # consolidation_enabled / storage_gate_enabled 等其余键保持 live 语义
        # （promote_entry_now 需要 consolidation live 才提升）。
        return "live"

    monkeypatch.setattr(AuroraStage19KillSwitchService, "get_feature_mode", _mode)


async def _create_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _create_user_turn(db_session, user_id, session_id, content: str) -> ChatMessage:
    message = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.USER,
        content=content,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


async def _lane_episodic_rows(db_session, user_id) -> list[EpisodicMemory]:
    return (
        (
            await db_session.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user_id,
                    EpisodicMemory.source_lane == "inferred_extraction",
                    EpisodicMemory.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )


class TestDeclaredFactProjectionLatency:
    """NBP-6 核心：明示事实投影不得排在 LLM 抽取往返之后。"""

    @pytest.mark.asyncio
    async def test_declared_fact_written_before_llm_extractor_call(
        self, db_session, monkeypatch
    ):
        """红→绿：LLM 抽取被调用的时刻，declared facts 必须已先行落库。

        侦探面在 ``dry_run_extract`` 入口（即 pipeline 走完快车道之后、LLM
        往返开始之前）检查同一 session——顺序执行、零并发、零 wall-clock：
        - 修复后：快车道先跑 → 抽取时刻考试/弱点/约束三句已在 episodic；
          LLM 无论多慢（45s 首块超时 + fallback 重试），投影早已提交。
        - 修复前（回归红）：declared 候选排在抽取之后 → 抽取时刻 0 条。
        """
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        _patch_kill_switch_modes(monkeypatch, working_memory="live", llm_extractor="live")

        observed: dict = {"extractor_called": False}

        async def _spy_extract(*args, **kwargs):
            observed["extractor_called"] = True
            # 此刻必须已完成 declared 快车道（写入与提交）。
            observed["rows_at_extract_time"] = await _lane_episodic_rows(db_session, user.id)
            return []

        monkeypatch.setattr(LlmExtractorService, "dry_run_extract", _spy_extract)

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的，已整理。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        assert observed["extractor_called"], "重排后 LLM 抽取仍必须被调用（不得被跳过）"
        rows = observed["rows_at_extract_time"]
        assert len(rows) >= 3, (
            f"LLM 抽取开始前明示事实必须已全部落库（考试/弱点/约束），实际 {len(rows)}"
        )
        assert any("期末考试" in (row.summary or "") for row in rows)
        assert any("薄弱" in (row.summary or "") for row in rows)
        assert any("165" in (row.summary or "") for row in rows)

    @pytest.mark.asyncio
    async def test_declared_candidates_not_double_processed_after_reorder(
        self, db_session, monkeypatch
    ):
        """红线：快车道接管 declared 候选后，后置循环不得再处理一遍
        （否则 declared 集合被处理两次：promote 翻倍、upsert 虚增
        mention_count，扭曲 >=3 固化门槛）。

        注：B1 句型里规则候选与 weakness 明示事实是同一句 → semantic_key
        在「规则 lane × declared lane」各 upsert 一次属既有形态（mention
        语义），不是双处理；双处理的表现是 promote 调用数翻倍 + upsert
        总数多出 len(declared)。"""
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        _patch_kill_switch_modes(monkeypatch, working_memory="live", llm_extractor="live")

        async def _fast_extract(*args, **kwargs):
            return []

        monkeypatch.setattr(LlmExtractorService, "dry_run_extract", _fast_extract)

        upsert_keys: list[str] = []
        original_upsert = WorkingMemoryService.upsert_entry

        async def _spy_upsert(self, *, text, semantic_key, **kwargs):
            upsert_keys.append(semantic_key)
            return await original_upsert(self, text=text, semantic_key=semantic_key, **kwargs)

        monkeypatch.setattr(WorkingMemoryService, "upsert_entry", _spy_upsert)

        promote_calls: list[dict] = []
        original_promote = WorkingMemoryConsolidationService.promote_entry_now

        async def _spy_promote(self, *, user_id, session_id, entry, declared_fact=False):
            promote_calls.append({"entry_id": entry.entry_id, "declared_fact": declared_fact})
            return await original_promote(
                self, user_id=user_id, session_id=session_id, entry=entry, declared_fact=declared_fact
            )

        monkeypatch.setattr(WorkingMemoryConsolidationService, "promote_entry_now", _spy_promote)

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        # 期望集：declared 候选数 + 规则候选（0/1，确定性可算）。
        declared = service.extract_declared_fact_candidates(
            user_id=user.id,
            user_message=B1_ONBOARDING_MESSAGE,
            evidence_token=str(turn.id),
        )
        rule = service.extract_candidate(
            user_id=user.id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的。",
            evidence_token=str(turn.id),
        )
        expected_total = len(declared) + (1 if rule is not None else 0)

        assert len(promote_calls) == len(declared), (
            f"declared 提升必须恰好每候选一次，实际 {len(promote_calls)} 次（期望 {len(declared)}）"
        )
        assert all(item["declared_fact"] is True for item in promote_calls)
        assert len(upsert_keys) == expected_total, (
            f"upsert 总数 {len(upsert_keys)} != declared({len(declared)}) + rule({1 if rule is not None else 0})——"
            "declared 集合疑似被后置循环二次处理"
        )

    @pytest.mark.asyncio
    async def test_today_surfaces_visible_immediately_after_write(self, db_session, monkeypatch):
        """读面零缓存证明：写账一提交（同轮内），今日/账本读面无 sleep 立即可见。

        ``list_recent_episodic`` 即 /api/v1/memory/episodic 的取数层（LOOP3
        探针 30s/90s 两次扑空的同一读面）；pending-commitments 是守约面板
        的取数层（未来 due_at 的考试不进 pending 属正确产品语义，此处断言
        账本面可见 + due_at 正确）。
        """
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        _patch_kill_switch_modes(monkeypatch, working_memory="live", llm_extractor="live")

        async def _fast_extract(*args, **kwargs):
            return []

        monkeypatch.setattr(LlmExtractorService, "dry_run_extract", _fast_extract)

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的，已整理。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        # 无 sleep：写账返回后立刻走面板取数层。
        ledger = await MemoryService(db_session).list_recent_episodic(user.id, limit=20)
        ledger_text = " | ".join(str(row.summary or "") for row in ledger)
        assert "期末考试" in ledger_text, f"账本读面未即时可见考试事实：{ledger_text}"
        assert "薄弱" in ledger_text
        assert "165" in ledger_text

        exam_row = next(row for row in ledger if "期末考试" in (row.summary or ""))
        assert exam_row.due_at == datetime(2026, 9, 28, 18, 0, 0), "due_at 必须随写账即时正确"

        # 守约面板取数层可用且不误报未来承诺（due_at 在未来 → 不进 pending）。
        pending = await AccountabilityMvpService(db_session).list_pending_commitments(user_id=user.id)
        assert all(
            "期末考试" not in (item.summary or "") for item in pending
        ), "未来 due_at 的考试承诺不得进入待到期列表（正确产品语义）"

    @pytest.mark.asyncio
    async def test_working_memory_off_keeps_legacy_behavior(self, db_session, monkeypatch):
        """红线：pipeline 层 wm=off 时零变化——LLM dry-run 照跑、返回空、
        零 episodic 写入（declared 快车道同样被关闭）。

        （lane 层 wm=off 的 fallback 直写是 NBP-1 既有行为，由
        test_memory_declared_fact_capture.py 锁定，此处不重复。）"""
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        _patch_kill_switch_modes(monkeypatch, working_memory="off", llm_extractor="shadow")

        extractor_calls: list[dict] = []

        async def _probe_extract(*args, **kwargs):
            extractor_calls.append(kwargs)
            return []

        monkeypatch.setattr(LlmExtractorService, "dry_run_extract", _probe_extract)

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        declared = MemoryInferredWriteLaneService(db_session).extract_declared_fact_candidates(
            user_id=user.id,
            user_message=B1_ONBOARDING_MESSAGE,
            evidence_token=str(turn.id),
        )
        assert declared, "前置失效：B1 句型必须产出 declared 候选"

        pipeline = WorkingMemoryPipelineService(db_session)
        entries = await pipeline.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的。",
            evidence_token=str(turn.id),
            rule_candidate=None,
            declared_candidates=declared,
        )

        assert entries == [], "wm=off 时 pipeline 必须返回空（零变化）"
        assert extractor_calls, "wm=off 时 LLM dry-run 抽取必须照跑（既有观测面）"
        rows = await _lane_episodic_rows(db_session, user.id)
        assert rows == [], "wm=off 时 pipeline 不得有任何 episodic 写入（零变化）"
