from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import (
    DiagnoseConfidence,
    DiagnosticAnswerSubmission,
    DiagnosticGenerateRequest,
    DiagnosticGradeRequest,
    DiagnosticKnowledgeNode,
)
from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService

_NODE_NAMES = (
    "分层模型与协议栈",
    "IP / 子网划分",
    "路由基础",
    "TCP 可靠传输",
    "TCP 拥塞控制",
    "HTTP / DNS",
    "链路层基础",
)


def _correct_answer(grader) -> str:
    if grader.question_type == "single_choice":
        return str((grader.correct_choice_index or 0) + 1)
    if grader.accepted_answers:
        return grader.accepted_answers[0]
    return " ".join(grader.required_keywords)


@pytest.mark.asyncio
async def test_exam_sprint_diagnostic_service_generates_grades_and_updates_mastery(db_session, test_user):
    user_id = test_user.id
    seeded_nodes = []
    node_ids = {}
    for name in _NODE_NAMES:
        node = KnowledgeNode(
            id=uuid4(),
            name=name,
            description=f"{name} 节点",
            importance_level=3,
            source_type="seed",
            dominant_sector_code="VOID",
            sector_classification_status="pending",
        )
        seeded_nodes.append(node)
        node_ids[name] = str(node.id)
        db_session.add(node)
    await db_session.commit()

    service = ExamSprintDiagnosticService(db_session)
    knowledge_nodes = [DiagnosticKnowledgeNode(node_id=node.id, name=node.name) for node in seeded_nodes]
    generated = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(
            subject="计算机网络",
            question_count=12,
            knowledge_nodes=knowledge_nodes,
        ),
    )

    assert len(generated.questions) == 12
    assert len(generated.coverage_domains) >= 5
    assert any(question.question_type == "short_answer" for question in generated.questions)

    wrong_domains = {"TCP 拥塞控制", "IP / 子网划分"}
    answers = []
    for question in generated.questions:
        grader = generated.grading_payload[question.question_id]
        if question.domain in wrong_domains:
            answers.append(
                DiagnosticAnswerSubmission(
                    question_id=question.question_id,
                    answer="错误答案",
                    confidence=DiagnoseConfidence.CERTAIN,
                )
            )
        else:
            answers.append(
                DiagnosticAnswerSubmission(
                    question_id=question.question_id,
                    answer=_correct_answer(grader),
                    confidence=DiagnoseConfidence.CERTAIN,
                )
            )

    graded = await service.grade(
        user_id=user_id,
        request=DiagnosticGradeRequest(
            subject="计算机网络",
            answers=answers,
            grading_payload=generated.grading_payload,
            knowledge_nodes=knowledge_nodes,
            days_left=5,
            pass_score=60,
            update_galaxy=True,
        ),
    )

    assert graded.estimated_score_now < 85
    assert graded.recommended_path == "minimum_pass"
    top_names = [item.node_name for item in graded.top_bottlenecks]
    assert "TCP 拥塞控制" in top_names
    assert "IP / 子网划分" in top_names

    status_rows = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_id))
    ).scalars().all()
    assert status_rows
    mastery_by_node = {str(row.node_id): float(row.mastery_score or 0.0) for row in status_rows}
    assert mastery_by_node[node_ids["IP / 子网划分"]] < 50.0
    assert mastery_by_node[node_ids["TCP 拥塞控制"]] < 50.0

    prefs = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
    ).scalar_one()
    assert prefs.explicit["cold_start_context"]["recommended_path"] == "minimum_pass"
    assert prefs.explicit["cold_start_context"]["diagnostic_estimated_score"] == graded.estimated_score_now
    assert len(prefs.explicit["cold_start_context"]["diagnostic_node_mastery_snapshot"]) >= 5
    assert "TCP 拥塞控制" in prefs.explicit["cold_start_context"]["diagnostic_coverage_domains"]
    assert len(prefs.explicit["knowledge_gaps"]) >= 2
