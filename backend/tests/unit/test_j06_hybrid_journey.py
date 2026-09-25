"""J-06 · Hybrid Flagship Journey 端到端 ——「AI 降摩擦但不偷走目标」验收证据.

红测先行（本文件提交时链路尚断，逐条对应卡面 work/acceptance）：

1. **四段链断点（红1）**：X-07 已给通用步骤机制，但没有任何面把
   「Agent prep → Human judgment → Agent execute/check → Outcome」装配成
   可泛化的真实旅程——``hybrid_journey_service`` 缺失，四个段无实现。
2. **judgment 被代决（红2，卡魂）**：判断段（选材料/定方向）是用户的
   goal-defining 价值判断——服务层必须结构性拒绝空选择（AI 不得填默认）、
   agent 路径完成 human 步必须被 X-07 owner 纪律拦截。
3. **source/citation 结构（红3）**：每段产物带统一 citation 结构
   （citation_id/scheme/ref/source_ref）；草稿无引用或引用越出用户选择集
   → 确定性 check 诚实失败，不产 artifact。
4. **真实工具/材料（acceptance①）**：prep 走真实注册工具
   ``retrieve_user_material``（ToolExecutor 真实执行链：权限判定 + X-06
   账本行 + 真实检索），材料是真实 StoredFile/DocumentChunk 行；草稿
   prompt 必须包含真实 chunk 原文（真实数据流，非预录）。
5. **G-02 接线一致（acceptance②）**：Outcome 段确认后任务经既有
   TaskService 完成路径产出 POSITIVE outcome；G-02 吸收器点亮恰一次；
   run receipt（SUCCEEDED）同因合并只补溯源——不重复点亮。

分层纪律：本服务是装配层（J-04/J-05 同款）——run 脊柱 = X-05/X-07
AgentRunService；工具执行 = X-06 ToolExecutor（不旁路）；outcome 捕获 =
X-08 既有函数；图谱吸收 = G-02 既有消费者。零新真源语义（唯一新表
hybrid_journey_artifacts 只存旅程自己的分段产物与 citation 结构）。
"""

from __future__ import annotations

import uuid
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.memory import MemoryGoal
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.agent_run_service import AgentRunService
from tests.unit.test_action_command_service import _OUTBOX_DDL, _make_user

pytestmark = pytest.mark.asyncio

#: 真实材料原文（seed 进 DocumentChunk；prep 检索与 LLM prompt 都必须真实命中）
_CHUNK_A = (
    "联邦学习通过在本地设备上训练模型并仅共享梯度更新来保护数据隐私，"
    "但梯度本身可能泄露训练分布信息。"
)
_CHUNK_B = (
    "差分隐私通过向梯度注入校准噪声提供可证明的隐私保障，"
    "隐私预算 epsilon 的选取需要权衡效用与隐私。"
)
_CHUNK_C = "知识蒸馏可以把大模型能力压缩到端侧小模型，是联邦场景下降低通信开销的候选方案。"

#: G-02 吸收器的 evidence 账本表（test_outcome_absorption 同款 sqlite DDL）。
_MASTERY_AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS mastery_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        old_mastery INTEGER NOT NULL,
        new_mastery INTEGER NOT NULL,
        reason TEXT,
        request_id TEXT,
        revision INTEGER DEFAULT 1,
        created_at DATETIME NOT NULL
    )
"""


class _RecordingBus:
    """事件总线记录桩（Redis 为外部设施；发射面断言 + 测试提速）。

    被测行为的真部分：X-08 捕获映射（纯函数）与 G-02 吸收器（真实 DB）。
    总线只记录「发射了什么」，与 X-05B testkit 的隔离纪律同哲学。
    """

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str | None = None):
        self.published.append((event_type, dict(payload)))
        return "stub"


@pytest.fixture(name="bus_stub")
async def bus_stub_fixture(monkeypatch):
    """把 reliable 总线 publish 替换为记录桩（事件是广播加速，不是真源）。"""
    from app.core.event_bus import event_bus_reliable

    stub = _RecordingBus()
    monkeypatch.setattr(event_bus_reliable, "publish", stub.publish)
    return stub


@pytest_asyncio.fixture(name="j06_db")
async def j06_db_fixture(monkeypatch):
    """独立 sqlite 引擎 + X-06 executor 会话工厂指向同引擎（X-06 测试同法）。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in (*_OUTBOX_DDL, _MASTERY_AUDIT_DDL):
            await conn.execute(text(ddl))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import app.orchestration.executor as executor_module

    monkeypatch.setattr(executor_module, "_agent_run_session_factory", factory)
    monkeypatch.setattr(executor_module, "_ledger_session_factory", factory)

    async with factory() as db:
        yield db
    await engine.dispose()


async def _seed_goal(db: AsyncSession, user: User) -> MemoryGoal:
    """J-02/J-04 真源形态：onboarding goal 落 memory_goals（active）。"""
    goal = MemoryGoal(
        user_id=user.id,
        title="写一篇联邦学习与隐私保护的小型研究综述",
        status="active",
        source_type="user_state",
        evidence_refs=[{"type": "user_state", "id": "onboarding", "schema_version": "onboarding.v1"}],
        metadata_payload={"goal_type": "research"},
    )
    db.add(goal)
    await db.flush()
    return goal


async def _seed_task(db: AsyncSession, user: User, node: KnowledgeNode | None = None) -> Task:
    """真实在飞任务（G-02 节点解析链：knowledge_node_id 优先）。"""
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION

    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="完成联邦学习综述大纲",
        type=TaskType.LEARNING,
        estimated_minutes=45,
        status=TaskStatus.IN_PROGRESS,
        knowledge_node_id=node.id if node is not None else None,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="一份带引用的研究综述大纲",
        smallest_useful_step={"description": "从材料中提炼大纲", "useful_because": ["produces_artifact"]},
        execution_mode="hybrid",
        cognitive_ownership="user_core",
    )
    db.add(task)
    await db.flush()
    return task


async def _seed_materials(db: AsyncSession, user: User) -> tuple[StoredFile, list[DocumentChunk]]:
    """真实材料行：StoredFile + DocumentChunk（检索真源；非 mock/预录）。"""
    stored = StoredFile(
        user_id=user.id,
        file_name="federated_learning_notes.pdf",
        mime_type="application/pdf",
        file_size=4096,
        bucket="test",
        object_key=f"j06-{uuid4()}",
        status="processed",
    )
    db.add(stored)
    await db.flush()
    chunks = [
        DocumentChunk(
            file_id=stored.id,
            user_id=user.id,
            chunk_index=index,
            content=content,
            section_title="联邦学习",
            page_numbers=[index + 1],
        )
        for index, content in enumerate((_CHUNK_A, _CHUNK_B, _CHUNK_C))
    ]
    for chunk in chunks:
        db.add(chunk)
    await db.flush()
    return stored, chunks


def _scripted_outline_llm(expected_snippets: tuple[str, ...]):
    """脚本化 LLM（注入面；生产默认走真实 GENERATION/FAST tier）.

    证据面（acceptance①真实数据流）：记录收到的 prompt，测试据此断言
    prompt 由**真实检索命中的 chunk 原文**构成；草稿按 prompt 中真实出现
    的片段生成 [S#] 引用——没有片段就拒绝起草（不是预录输出）。
    """

    async def _chat(messages, **_kwargs):
        prompt = str(messages[-1]["content"])
        cited: list[str] = []
        for index, snippet in enumerate(expected_snippets, start=1):
            if snippet in prompt:
                cited.append(f"[S{index}]")
        if not cited:
            raise AssertionError("scripted LLM received prompt without real chunk content")
        return (
            "## 研究综述大纲\n\n"
            "1. 问题定义：隐私保护下的分布式训练 " + " ".join(cited) + "\n"
            "2. 技术路线对比与威胁模型分析\n"
            "3. 评测口径与开放问题\n"
        )

    return _chat


async def _absorb(j06_db: AsyncSession, payload: dict):
    """G-02 真实吸收器（Redis 总线为外部设施；消费者路由测试用真实 DB + 真实逻辑）。"""
    from app.services.galaxy.outcome_absorption_service import GalaxyOutcomeAbsorber

    return await GalaxyOutcomeAbsorber(j06_db).absorb_outcome(payload)


# ============================================================================
# 红1 · 四段链端到端：prep(真实工具) → judgment(人) → execute/check → outcome
# ============================================================================


async def test_hybrid_journey_four_stage_chain_end_to_end(j06_db, bus_stub):
    """四段全通：真实材料 → prep 引用候选 → 用户选择 → 带引用草稿 + 确定性
    check → 产出 artifact → 任务完成 + outcome 捕获；每步产物可溯源。"""
    from app.services.hybrid_journey_service import (
        HYBRID_JOURNEY_TRACE_ID,
        confirm_outcome,
        get_hybrid_journey_state,
        start_hybrid_journey,
        submit_judgment,
    )
    from app.services.outcome_capture_service import (
        build_outcome_recorded_payload,
        build_run_receipt_outcome,
        build_task_outcome_capture,
    )


    user = await _make_user(j06_db)
    await _seed_goal(j06_db, user)
    node = KnowledgeNode(name="联邦学习", importance_level=3, is_seed=True)
    j06_db.add(node)
    await j06_db.flush()
    task = await _seed_task(j06_db, user, node)
    stored, chunks = await _seed_materials(j06_db, user)
    await j06_db.commit()

    # X-06 executor 的 run 权威会话指向测试引擎（StaticPool 同连接）

    # ---- 段1+2 启动：prep（真实工具检索）→ judgment awaiting（轮到用户）----
    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    run_view = started["run"]
    assert run_view["trace_id"] == HYBRID_JOURNEY_TRACE_ID
    steps = run_view["steps"]
    assert [s["step_id"] for s in steps] == ["prep", "judgment", "execute_check", "outcome"]
    assert [s["owner"] for s in steps] == ["agent", "human", "agent", "hybrid"], "四段链 owner 排列"

    # prep 产物：真实 chunk 引用（citation 结构断言，红3）
    citations = started["citations"]
    assert len(citations) >= 2, "真实检索必须命中种子材料"
    real_chunk_ids = {str(c.id) for c in chunks}
    for index, citation in enumerate(citations, start=1):
        assert citation["citation_id"] == f"S{index}"
        assert citation["scheme"] == "document_chunk"
        assert citation["ref"] in real_chunk_ids, "引用必须指向真实 chunk 行（非编造）"
        assert citation["source_ref"] == f"document_chunk://{citation['ref']}"
        assert citation["file_id"] == str(stored.id)
        assert citation["snippet"]

    # prep 走真实 X-06 执行链：账本行 + 权限判定留痕
    from app.models.agent_tool_call import AgentToolCall

    ledger_rows = (
        (await j06_db.execute(select(AgentToolCall).where(AgentToolCall.user_id == user.id)))
        .scalars()
        .all()
    )
    assert any(row.tool_name == "retrieve_user_material" and row.run_id is not None for row in ledger_rows)
    prep_row = next(row for row in ledger_rows if row.tool_name == "retrieve_user_material")
    assert prep_row.permission_decision is not None and prep_row.permission_decision.get("allowed") is True
    assert (prep_row.result or {}).get("data", {}).get("results"), "账本行保留真实检索结果（重放面）"

    # 分段产物行（hybrid_journey_artifacts）：prep 段 citation 结构
    assert started["artifacts"][0]["stage"] == "prep"
    assert started["artifacts"][0]["citations"] == citations

    # 段2：轮到用户——awaiting step 是 judgment，且显式说明「为什么需要你决定」
    awaiting = run_view["awaiting_step"]
    assert awaiting is not None and awaiting["step_id"] == "judgment"
    assert awaiting["owner"] == "human" and awaiting["state"] == "awaiting"
    brief = started["judgment_brief"]
    assert brief["why_human_key"], "判断段必须显式给出『需要你决定的原因』的结构化键"
    reason_text = brief.get("why_human") or ""
    assert ("你" in reason_text) and ("决定" in reason_text), "判断归属说明必须面向用户"
    assert brief["options"] == citations, "候选引用必须随判断面给出"

    # ---- 段2 用户判断：选择真实引用子集（AI 不代决的结构化入口）----
    chosen = [citations[0], citations[1]]
    llm = _scripted_outline_llm((chosen[0]["snippet"], chosen[1]["snippet"]))
    judged = await submit_judgment(
        j06_db,
        user_id=user.id,
        run_id=run_view["run_id"],
        selected_refs=[c["source_ref"] for c in chosen],
        focus_note="优先隐私机制对比",
        idempotency_key="judge-1",
        llm_chat=llm,
    )

    # 段3：agent 起草 + 确定性 check（引用必须落在用户选择集内；
    # 真实数据流证据由 _scripted_outline_llm 的 prompt 断言承担）
    outline_artifact = next(a for a in judged["artifacts"] if a["stage"] == "execute_check")
    assert outline_artifact["citations"], "checked outline 必须携带引用结构"
    outline_citation_refs = {c["source_ref"] for c in outline_artifact["citations"]}
    assert outline_citation_refs <= {c["source_ref"] for c in chosen}, "草稿引用不得越出用户选择"
    assert outline_artifact["payload"]["check"]["passed"] is True
    assert set(outline_artifact["payload"]["check"]["cited_ids"]) == {"S1", "S2"}
    assert "[S1]" in outline_artifact["payload"]["outline_markdown"]

    # 段4 前半：agent 备好产出，轮到用户确认交付（hybrid 所有权）
    awaiting_outcome = judged["run"]["awaiting_step"]
    assert awaiting_outcome is not None and awaiting_outcome["step_id"] == "outcome"
    assert awaiting_outcome["owner"] == "hybrid"
    assert any(ref["scheme"] == "journey_artifact" for ref in awaiting_outcome["artifacts"])

    # ---- 段4 用户确认交付：任务完成（既有 TaskService 路径）→ run SUCCEEDED ----
    confirmed = await confirm_outcome(
        j06_db,
        user_id=user.id,
        run_id=run_view["run_id"],
        idempotency_key="confirm-1",
    )
    await j06_db.refresh(task)
    assert task.status == TaskStatus.COMPLETED, "Outcome 段经既有完成路径落任务终态"
    evidence_record = (task.guide_json or {}).get("completion_evidence_record", [])[0]
    assert evidence_record["source"] == "user"
    assert any(entry["evidence_kind"] == "artifact" for entry in evidence_record["entries"]), "完成带 artifact 证据"
    assert confirmed["run"]["status"] == "SUCCEEDED"
    assert confirmed["run"]["result_ref"]["scheme"] == "journey_artifact"
    outcome_artifact = next(a for a in confirmed["artifacts"] if a["stage"] == "outcome")
    assert outcome_artifact["citations"], "outcome 产物同样携带 citation 结构"

    # X-08 receipt：SUCCEEDED run 的 outcome 捕获函数对本 run 可用（真实函数面）
    from app.models.agent_run import AgentRun

    run_row = (
        await j06_db.execute(select(AgentRun).where(AgentRun.id == uuid.UUID(run_view["run_id"])))
    ).scalar_one()
    receipt_capture = build_run_receipt_outcome(run_row)
    assert receipt_capture.polarity.value == "positive"
    assert receipt_capture.correlation.get("task_id") == str(task.id)

    # G-02 接线（红5 主断言在本文件独立测试中放大）；此处断言两条事件面真实可构造
    task_payload = build_outcome_recorded_payload(build_task_outcome_capture(task))
    receipt_payload = build_outcome_recorded_payload(receipt_capture)
    assert task_payload["polarity"] == "positive"
    assert receipt_payload["correlation_task_id"] == task_payload["correlation_task_id"]

    # 重开回放（acceptance：持久化状态面）
    state = await get_hybrid_journey_state(j06_db, user_id=user.id, run_id=run_view["run_id"])
    assert state["run"]["status"] == "SUCCEEDED"
    assert len(state["artifacts"]) >= 3, "四段产物可回放（prep/judgment/execute_check/outcome）"
    assert state["task"]["id"] == str(task.id)


# ============================================================================
# 红2 · 卡魂：judgment 不可被代决（空选择拒绝 + agent 路径拒绝 + 未知引用拒绝）
# ============================================================================


async def test_judgment_cannot_be_decided_on_behalf_of_user(j06_db):
    """AI 不得替用户做 judgment 段的决定：
    - 空选择 → 422 judgment_required（服务层结构性拒绝，绝不填默认集合）；
    - agent 路径完成 human 步 → X-07 owner 纪律 ValueError；
    - 选择集之外的材料 → 422（引用必须出自真实 prep 候选）。
    判定后 run 仍 AWAITING_USER、judgment 步无完成戳、无新产物行。"""
    from app.core.run_steps import find_step
    from app.services.hybrid_journey_service import (
        JudgmentRequiredError,
        start_hybrid_journey,
        submit_judgment,
    )

    user = await _make_user(j06_db)
    await _seed_goal(j06_db, user)
    task = await _seed_task(j06_db, user, None)
    await _seed_materials(j06_db, user)
    await j06_db.commit()


    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    run_id = started["run"]["run_id"]

    with pytest.raises(JudgmentRequiredError):
        await submit_judgment(
            j06_db,
            user_id=user.id,
            run_id=run_id,
            selected_refs=[],
            idempotency_key="judge-empty",
        )

    # run 未被动过：仍 AWAITING_USER，judgment 无完成戳
    service = AgentRunService(j06_db)
    run_row = await service.get_run(run_id, user_id=user.id)
    assert run_row.status.value == "AWAITING_USER"
    judgment_step = find_step(run_row.steps, "judgment")
    assert judgment_step.get("completion") is None

    # agent 路径完成 human 步 → owner 纪律拦截（结构性不可代决）
    with pytest.raises(ValueError) as owner_error:
        await service.complete_agent_step(run_id, step_id="judgment", artifact_refs=[])
    assert "owner" in str(owner_error.value)

    # 选择集之外（编造引用）→ 422
    from app.services.hybrid_journey_service import JudgmentUnknownSourceError

    with pytest.raises(JudgmentUnknownSourceError):
        await submit_judgment(
            j06_db,
            user_id=user.id,
            run_id=run_id,
            selected_refs=["document_chunk://not-a-real-chunk"],
            idempotency_key="judge-fake",
        )


# ============================================================================
# 红3 · 确定性 check：无引用/越集引用的草稿诚实失败，不产 artifact；可重试
# ============================================================================


async def test_check_rejects_uncited_or_out_of_set_draft(j06_db):
    """草稿没有 [S#] 或引用了用户未选的来源 → JourneyCheckError（诚实 503 面），
    execute_check 不产产物行；同判断重放（幂等路径）换合规草稿后收敛。"""
    from app.services.hybrid_journey_service import (
        JourneyCheckError,
        start_hybrid_journey,
        submit_judgment,
    )

    user = await _make_user(j06_db)
    await _seed_goal(j06_db, user)
    task = await _seed_task(j06_db, user, None)
    await _seed_materials(j06_db, user)
    await j06_db.commit()


    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    run_id = started["run"]["run_id"]
    citations = started["citations"]
    chosen = citations[:2]

    # 草稿无任何 [S#]：check 必须拒绝（伪产物不合法）
    async def _uncited_llm(messages, **_kwargs):
        assert chosen[0]["snippet"] in str(messages[-1]["content"]), "prompt 必须含真实材料"
        return "## 大纲\n1. 问题定义\n2. 方法对比\n3. 结论\n"

    with pytest.raises(JourneyCheckError):
        await submit_judgment(
            j06_db,
            user_id=user.id,
            run_id=run_id,
            selected_refs=[c["source_ref"] for c in chosen],
            idempotency_key="judge-1",
            llm_chat=_uncited_llm,
        )

    run_row = await AgentRunService(j06_db).get_run(run_id, user_id=user.id)
    assert run_row.status.value == "RUNNING", "check 失败后 run 停在执行态（可重试），不假装完成"
    from app.models.hybrid_journey import HybridJourneyArtifact

    stages = (
        (
            await j06_db.execute(
                select(HybridJourneyArtifact).where(HybridJourneyArtifact.run_id == run_row.id)
            )
        )
        .scalars()
        .all()
    )
    assert all(a.stage != "execute_check" for a in stages), "失败的草稿不落产物"

    # 越集引用：LLM 引了未选择的 S9 → check 拒绝（防编造来源）
    async def _out_of_set_llm(messages, **_kwargs):
        return "## 大纲\n1. 问题定义 [S9]\n"

    with pytest.raises(JourneyCheckError):
        await submit_judgment(
            j06_db,
            user_id=user.id,
            run_id=run_id,
            selected_refs=[c["source_ref"] for c in chosen],
            idempotency_key="judge-1",
            llm_chat=_out_of_set_llm,
        )

    # 同判断幂等重放 → 合规草稿收敛（重试语义：run 恢复推进）
    good_llm = _scripted_outline_llm((chosen[0]["snippet"], chosen[1]["snippet"]))
    judged = await submit_judgment(
        j06_db,
        user_id=user.id,
        run_id=run_id,
        selected_refs=[c["source_ref"] for c in chosen],
        idempotency_key="judge-1",
        llm_chat=good_llm,
    )
    assert next(a for a in judged["artifacts"] if a["stage"] == "execute_check")


# ============================================================================
# 红5 · G-02 接线一致：点亮恰一次，同因 receipt 只补溯源（不重复点亮）
# ============================================================================


async def test_g02_absorption_lights_once_with_receipt_dedup(j06_db, bus_stub):
    """完整旅程 → 用户确认 → 任务完成 outcome（POSITIVE）→ G-02 融合恰一次；
    SUCCEEDED run receipt 同因合并 = duplicate（只补溯源）；双面重放幂等。"""
    from app.models.galaxy import UserNodeStatus
    from app.services.galaxy.outcome_absorption_service import (
        ABSORBED_OUTCOMES_SNAPSHOT_KEY,
        OUTCOME_EVIDENCE_AUDIT_REASON,
    )
    from app.services.hybrid_journey_service import (
        confirm_outcome,
        start_hybrid_journey,
        submit_judgment,
    )
    from app.services.outcome_capture_service import (
        build_outcome_recorded_payload,
        build_run_receipt_outcome,
        build_task_outcome_capture,
    )

    user = await _make_user(j06_db)
    await _seed_goal(j06_db, user)
    node = KnowledgeNode(name="差分隐私", importance_level=3, is_seed=True)
    j06_db.add(node)
    await j06_db.flush()
    task = await _seed_task(j06_db, user, node)
    await _seed_materials(j06_db, user)
    await j06_db.commit()


    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    run_id = started["run"]["run_id"]
    citations = started["citations"]
    llm = _scripted_outline_llm(tuple(c["snippet"] for c in citations[:2]))
    await submit_judgment(
        j06_db,
        user_id=user.id,
        run_id=run_id,
        selected_refs=[c["source_ref"] for c in citations[:2]],
        idempotency_key="judge-g02",
        llm_chat=llm,
    )
    await confirm_outcome(j06_db, user_id=user.id, run_id=run_id, idempotency_key="confirm-g02")
    await j06_db.refresh(task)
    assert task.status == TaskStatus.COMPLETED

    async def _audit_rows():
        from sqlalchemy import text as sa_text

        rows = await j06_db.execute(
            sa_text(
                "SELECT request_id FROM mastery_audit_log "
                "WHERE user_id = :uid AND node_id = :nid AND reason = :reason"
            ),
            {"uid": str(user.id), "nid": str(node.id), "reason": OUTCOME_EVIDENCE_AUDIT_REASON},
        )
        return list(rows.fetchall() or [])

    async def _status() -> UserNodeStatus:
        result = await j06_db.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node.id)
        )
        return result.scalar_one()

    # ① 任务完成 outcome（X-08 既有映射；G-02 既有消费者）→ 点亮
    absorber = await _absorb(j06_db, build_outcome_recorded_payload(build_task_outcome_capture(task)))
    assert absorber is not None and absorber.action == "lit", "任务完成 outcome 必须真实点亮"
    status = await _status()
    mastery_after_task = float(status.mastery_score)
    assert len(await _audit_rows()) == 1, "证据行恰一条（append-only 幂等门）"

    # ② 同因 run receipt（J-06 Outcome 段产出的 receipt 面）→ duplicate 只补溯源
    from app.models.agent_run import AgentRun

    run_row = (
        await j06_db.execute(select(AgentRun).where(AgentRun.id == uuid.UUID(run_id)))
    ).scalar_one()
    receipt_result = await _absorb(
        j06_db, build_outcome_recorded_payload(build_run_receipt_outcome(run_row))
    )
    assert receipt_result.action == "duplicate", "同因 receipt 不二次融合（不重复点亮）"
    assert float((await _status()).mastery_score) == pytest.approx(mastery_after_task), "掌握度不双计"
    assert len(await _audit_rows()) == 1

    # ③ 双面重放 → 幂等（仍是恰一次点亮）
    await _absorb(j06_db, build_outcome_recorded_payload(build_task_outcome_capture(task)))
    await _absorb(j06_db, build_outcome_recorded_payload(build_run_receipt_outcome(run_row)))
    assert float((await _status()).mastery_score) == pytest.approx(mastery_after_task)
    assert len(await _audit_rows()) == 1

    # ④ 溯源：两个事件面都在 graph_event_sources 可追溯（reference_id = outcome id）
    status = await _status()
    snapshot = dict(status.learning_path_snapshot or {})
    sources = snapshot.get("graph_event_sources") or []
    reference_ids = {entry.get("reference_id") for entry in sources}
    from app.core.outcome_ledger import OutcomeSource, derive_outcome_id

    assert (
        derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task.id) in reference_ids
    )
    assert build_run_receipt_outcome(run_row).outcome_id in reference_ids
    absorbed = (snapshot.get(ABSORBED_OUTCOMES_SNAPSHOT_KEY) or {})
    assert absorbed, "absorbed marker 面存在（极性翻转防御的数据面）"


# ============================================================================
# 红4 · 诚实失败：无目标/无任务/无材料的结构化拒绝（不伪造旅程）
# ============================================================================


async def test_start_honest_failures(j06_db):
    """无 active goal → NoActiveGoalError；无在飞任务 → NoTaskAnchorError；
    材料库为空 → NoMaterialError（旅程不编造引用）。"""
    from app.services.hybrid_journey_service import (
        NoActiveGoalError,
        NoMaterialError,
        NoTaskAnchorError,
        start_hybrid_journey,
    )

    user = await _make_user(j06_db)
    await j06_db.commit()

    with pytest.raises(NoActiveGoalError):
        await start_hybrid_journey(j06_db, user_id=user.id)

    await _seed_goal(j06_db, user)
    await j06_db.commit()
    with pytest.raises(NoTaskAnchorError):
        await start_hybrid_journey(j06_db, user_id=user.id)

    task = await _seed_task(j06_db, user, None)
    await j06_db.commit()
    with pytest.raises(NoMaterialError):
        await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
