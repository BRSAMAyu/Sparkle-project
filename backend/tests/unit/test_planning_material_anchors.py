from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument, UserNodeStatus
from app.models.user import User
from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager
from app.orchestration.sufficiency_checker import SufficiencyChecker, SufficiencyStatus
from app.services.galaxy_service import GalaxyService


@pytest.mark.asyncio
async def test_galaxy_service_summarizes_uploaded_materials_for_planning(db_session) -> None:
    user = User(username="materials_user", email="materials@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    stored_file = StoredFile(
        user_id=user.id,
        file_name="OS.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"os-{uuid4()}",
        status="processed",
    )
    db_session.add(stored_file)
    await db_session.flush()
    node = KnowledgeNode(
        name="CPU 调度指标",
        description="操作系统中的 CPU Scheduling 指标",
        source_file_id=stored_file.id,
        chunk_refs=[0, 1],
    )
    db_session.add_all(
        [
            node,
            KnowledgeNodeDocument(user_id=user.id, node=node, file=stored_file, is_primary=True),
            UserNodeStatus(user_id=user.id, node=node, mastery_score=22.0, is_unlocked=True),
            DocumentChunk(
                file=stored_file,
                user_id=user.id,
                chunk_index=0,
                section_title="Chapter 3 CPU 调度指标",
                page_numbers=[12, 13],
                content="CPU scheduling metrics include turnaround time, response time, and throughput. " * 30,
            ),
            DocumentChunk(
                file=stored_file,
                user_id=user.id,
                chunk_index=1,
                section_title="Chapter 3 RR 时间片轮转调度",
                page_numbers=[14, 15],
                content="Round robin scheduling uses a time quantum and preemption to improve fairness. " * 30,
            ),
        ]
    )
    await db_session.commit()

    summary = await GalaxyService(db_session).summarize_study_materials_for_planning(
        user_id=user.id,
        topic_hints=["CPU 调度", "操作系统"],
    )

    assert summary["has_materials"] is True
    assert summary["available_materials"] == ["OS.pdf"]
    assert summary["matched_documents_count"] >= 1
    document = summary["documents"][0]
    assert document["file_name"] == "OS.pdf"
    assert "Chapter 3 CPU 调度指标" in document["section_titles"]
    assert document["estimated_read_minutes"] > 0
    attachment = document["node_attachments"][0]
    assert attachment["node_name"] == "CPU 调度指标"
    assert attachment["mastery_score"] == pytest.approx(22.0)
    assert "Chapter 3 CPU 调度指标" in attachment["section_titles"]


def test_planning_workflow_anchors_task_metadata_to_uploaded_materials() -> None:
    manager = PlanningWorkflowManager(redis_client={})
    session = PlanningSession(
        planning_session_id="planning-session",
        chat_session_id="chat-session",
        user_id="user-1",
        state="PLANNING",
        goal_raw="7天通过操作系统考试",
        collected={
            "subject": "操作系统",
            "exam_scope": "进程管理、调度、内存管理",
            "available_materials": ["OS.pdf"],
            "study_material_context": {
                "documents": [
                    {
                        "file_id": "file-os",
                        "file_name": "OS.pdf",
                        "preferred": True,
                        "sections": [
                            {
                                "section_title": "Chapter 3 CPU 调度指标",
                                "chunk_count": 2,
                                "page_numbers": [12, 13],
                                "estimated_read_minutes": 45,
                            }
                        ],
                        "node_attachments": [
                            {
                                "node_id": "node-cpu",
                                "node_name": "CPU 调度指标",
                                "mastery_score": 22.0,
                                "is_primary": True,
                                "section_titles": ["Chapter 3 CPU 调度指标"],
                                "estimated_read_minutes": 45,
                                "chunk_count": 2,
                            }
                        ],
                    }
                ],
                "available_materials": ["OS.pdf"],
                "has_materials": True,
            },
        },
    )
    phase = {
        "label": "核心攻克",
        "focus": "围绕 CPU 调度指标做闭卷输出与代表题验证。",
        "output": "完成调度算法对比表和 3 道甘特图题",
        "daily_hours": 2,
        "sprint_policy": {"sprint_mode": "seven_day_survival", "retrieval_policy": {}},
    }
    raw_spec = {
        "day": 3,
        "focus": "围绕 CPU 调度指标做闭卷输出与代表题验证。",
        "title_focus": "CPU 调度指标",
        "task_kind": "retrieval_drill",
        "estimated_minutes": 60,
        "subject_strategy": {
            "node_ids": ["os.cpu_scheduling"],
            "node_labels": ["CPU 调度指标"],
        },
    }

    anchored_spec = manager._attach_material_anchors_to_specs(
        session=session,
        phase=phase,
        specs=[raw_spec],
    )[0]
    guide_json = manager._build_task_guide_json(
        session=session,
        phase=phase,
        phase_index=2,
        default_daily_hours=2,
        day_number=3,
        day_focus=anchored_spec["focus"],
        day_spec=anchored_spec,
        aurora_state=None,
    )

    assert manager._task_title_focus(anchored_spec) == "CPU 调度指标（OS.pdf · Chapter 3 CPU 调度指标）"
    assert guide_json["material_coverage_status"] == "anchored"
    assert guide_json["primary_material"]["file_name"] == "OS.pdf"
    assert guide_json["primary_material"]["chapter_ref"] == "Chapter 3 CPU 调度指标"
    assert "OS.pdf" in guide_json["objective"]
    assert any("Chapter 3 CPU 调度指标" in step for step in guide_json["method_steps"])


@pytest.mark.asyncio
async def test_sufficiency_checker_can_raise_material_gap_clarification() -> None:
    checker = SufficiencyChecker(strict_mode=False)

    result = await checker.check(
        intent="create_plan",
        extracted_entities={"plan_title": "7天操作系统冲刺", "plan_type": "sprint"},
        conversation_context=[],
        planning_material_context={
            "enabled": True,
            "has_materials": True,
            "material_gaps": ["你还没有上传内存管理相关资料"],
            "subject": "操作系统",
        },
    )

    assert result.status == SufficiencyStatus.NEED_CLARIFICATION
    assert result.recommended_action == "ask"
    assert "内存管理" in str(result.clarification_text)
