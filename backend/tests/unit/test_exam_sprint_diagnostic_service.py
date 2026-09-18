from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import (
    DiagnoseConfidence,
    DiagnoseQuestionType,
    DiagnosticAnswerSubmission,
    DiagnosticGenerateRequest,
    DiagnosticGradeRequest,
    DiagnosticKnowledgeNode,
)
from app.services.exam_sprint_diagnostic_service import _CN_TEMPLATES, ExamSprintDiagnosticService

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


def _template_correct_text(template_key: str) -> str:
    """Correct answer as free text, from the template registry (server side)."""
    for template in _CN_TEMPLATES:
        if template.template_key != template_key:
            continue
        if template.question_type == DiagnoseQuestionType.SINGLE_CHOICE and template.correct_choice_index is not None:
            return template.choices[template.correct_choice_index]
        if template.accepted_answers:
            return template.accepted_answers[0]
        return " ".join(template.required_keywords)
    raise KeyError(template_key)


def _template_answer_for(question_id: str) -> str:
    return _template_correct_text(question_id.split("_", 2)[-1])


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
                    answer=_template_answer_for(question.question_id),
                    confidence=DiagnoseConfidence.CERTAIN,
                )
            )

    graded = await service.grade(
        user_id=user_id,
        request=DiagnosticGradeRequest(
            subject="计算机网络",
            diagnostic_id=generated.diagnostic_id,
            answers=answers,
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


@pytest.mark.asyncio
async def test_exam_sprint_diagnostic_persists_mastery_without_matching_galaxy_nodes(db_session, test_user):
    """P1-E3 regression: with update_galaxy=True and NO same-name galaxy node,
    mastery updates must still land in the graph (topic nodes resolved to
    sprint-pack nodes created on demand), not be silently dropped."""
    user_id = test_user.id

    service = ExamSprintDiagnosticService(db_session)
    generated = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(subject="计算机网络", question_count=10),
    )

    answers = [
        DiagnosticAnswerSubmission(
            question_id=question.question_id,
            answer=_template_answer_for(question.question_id),
            confidence=DiagnoseConfidence.CERTAIN,
        )
        for question in generated.questions
    ]
    graded = await service.grade(
        user_id=user_id,
        request=DiagnosticGradeRequest(
            subject="计算机网络",
            diagnostic_id=generated.diagnostic_id,
            answers=answers,
            days_left=5,
            pass_score=60,
            update_galaxy=True,
        ),
    )

    assert graded.node_mastery_updates, "grade must compute per-node mastery updates"
    assert all(item.node_id is not None for item in graded.node_mastery_updates), (
        "every mastery update must resolve to a concrete galaxy node"
    )

    status_rows = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_id))
    ).scalars().all()
    assert status_rows, "mastery updates must be persisted to user_node_status"
    persisted_ids = {row.node_id for row in status_rows}
    assert all(item.node_id in persisted_ids for item in graded.node_mastery_updates)

    nodes = (
        await db_session.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(persisted_ids)))
    ).scalars().all()
    assert {node.id for node in nodes} == persisted_ids, "persisted mastery must reference real galaxy nodes"


@pytest.mark.asyncio
async def test_diagnose_generate_does_not_leak_answers_and_grade_uses_server_session(db_session, test_user):
    """P1-E4 regression: generate must not ship answer keys (grading_payload) to
    the client; grade must score from the server-side session via diagnostic_id,
    and option TEXT submissions must be graded correctly (not just index/letter)."""
    service = ExamSprintDiagnosticService(db_session)
    generated = await service.generate(
        user_id=test_user.id,
        request=DiagnosticGenerateRequest(subject="计算机网络", question_count=10),
    )

    # 1) answers never leave the server
    assert not getattr(generated, "grading_payload", None), "generate response must not carry grading_payload"
    response_json = generated.model_dump_json()
    for leaked_field in ("correct_choice_index", "accepted_answers", "required_keywords"):
        assert leaked_field not in response_json, f"generate response leaks {leaked_field}"

    # 2) client answers with option TEXT / natural short answers, graded via server session
    text_by_key = {}
    for template in _CN_TEMPLATES:
        if template.question_type == DiagnoseQuestionType.SINGLE_CHOICE and template.correct_choice_index is not None:
            text_by_key[template.template_key] = template.choices[template.correct_choice_index]
        elif template.accepted_answers:
            text_by_key[template.template_key] = template.accepted_answers[0]
        else:
            text_by_key[template.template_key] = " ".join(template.required_keywords)

    answers = [
        DiagnosticAnswerSubmission(
            question_id=question.question_id,
            answer=text_by_key[question.question_id.split("_", 2)[-1]],
            confidence=DiagnoseConfidence.CERTAIN,
        )
        for question in generated.questions
    ]
    graded = await service.grade(
        user_id=test_user.id,
        request=DiagnosticGradeRequest(
            subject="计算机网络",
            diagnostic_id=generated.diagnostic_id,
            answers=answers,
            days_left=5,
            pass_score=60,
            update_galaxy=False,
        ),
    )
    assert graded.estimated_score_now == 100.0, "all-correct text submissions must score full marks"


@pytest.mark.asyncio
async def test_exam_sprint_diagnostic_supports_data_structures_subject(db_session, test_user):
    """P1-E2 regression: the seeded「数据结构」scenario must generate and grade a
    diagnostic (previously 422 — whitelist was computer-networks only), with
    mastery landing on ds.* sprint-pack nodes."""
    user_id = test_user.id
    service = ExamSprintDiagnosticService(db_session)

    generated = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(subject="数据结构", question_count=10),
    )
    assert len(generated.questions) == 10
    assert len(generated.coverage_domains) >= 5
    assert any(q.question_type == "short_answer" for q in generated.questions)

    # subject title variants (seed scenario) resolve to the same pack
    variant = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(subject="数据结构期中", question_count=10),
    )
    assert len(variant.questions) == 10

    answers = [
        DiagnosticAnswerSubmission(
            question_id=question.question_id,
            answer="错误答案",
            confidence=DiagnoseConfidence.CERTAIN,
        )
        for question in generated.questions
    ]
    graded = await service.grade(
        user_id=user_id,
        request=DiagnosticGradeRequest(
            subject="数据结构",
            diagnostic_id=generated.diagnostic_id,
            answers=answers,
            days_left=5,
            pass_score=60,
            update_galaxy=True,
        ),
    )
    assert graded.node_mastery_updates
    assert all(item.node_id is not None for item in graded.node_mastery_updates)

    status_rows = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_id))
    ).scalars().all()
    assert status_rows, "data-structure mastery must persist to the galaxy"
    node_ids = {row.node_id for row in status_rows}
    nodes = (
        await db_session.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))
    ).scalars().all()
    by_id = {str(node.id): node for node in nodes}
    ds_pack_ids = {str(node.id) for node in nodes if node.source_type == "sprint_pack"}
    assert ds_pack_ids, "data-structure topics should map onto canonical ds.* sprint-pack nodes"
    # canonical ds pack nodes carry their Chinese labels from the pack metadata
    assert all(by_id[nid].name for nid in ds_pack_ids)
    assert any("排序" in by_id[nid].name or "堆" in by_id[nid].name for nid in ds_pack_ids)


@pytest.mark.asyncio
async def test_diagnose_unsupported_subject_gives_actionable_error(db_session, test_user):
    """daily-flow DF-4 regression: a real new student on an unpacked subject
    (eval used 大学物理) used to hit 422「知识节点覆盖不足，至少需要 5 个不同
    知识领域」— a dead-end that blamed the request payload even though no
    template pack exists for the subject (supplying nodes would still 422 at
    template selection). The error must instead say which subjects are
    supported and that the subject itself is the blocker."""
    service = ExamSprintDiagnosticService(db_session)

    with pytest.raises(ValueError) as excinfo:
        await service.generate(
            user_id=test_user.id,
            request=DiagnosticGenerateRequest(subject="大学物理", question_count=10),
        )

    message = str(excinfo.value)
    assert "知识节点覆盖不足" not in message
    assert "大学物理" in message
    assert "计算机网络" in message and "数据结构" in message
