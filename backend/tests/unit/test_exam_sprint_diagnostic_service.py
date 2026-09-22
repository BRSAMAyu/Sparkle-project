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
    DiagnosticQuestionGrader,
)
from app.services.exam_sprint_diagnostic_service import (
    _CN_TEMPLATES,
    _DM_TEMPLATES,
    _SUBJECT_TEMPLATE_SETS,
    ExamSprintDiagnosticService,
)
from app.sprint_packs.sprint_pack_loader import load_pack
from app.sprint_packs.sprint_pack_schema import SprintPackV1

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


# ---------------------------------------------------------------------------
# P0-1: discrete-mathematics diagnostic pack (NS-001 main-path BP-1 fix)
# ---------------------------------------------------------------------------


def _dm_template_correct_answer(template_key: str) -> str:
    """Canonical correct answer text for a dm template (server-side registry)."""
    for template in _DM_TEMPLATES:
        if template.template_key != template_key:
            continue
        if template.question_type == DiagnoseQuestionType.SINGLE_CHOICE and template.correct_choice_index is not None:
            return template.choices[template.correct_choice_index]
        if template.accepted_answers:
            return template.accepted_answers[0]
        return "，".join(template.required_keywords)
    raise KeyError(template_key)


@pytest.mark.asyncio
async def test_exam_sprint_diagnostic_supports_discrete_mathematics_subject(db_session, test_user):
    """P0-1 / LOOP1 BP-1 regression: NS-001（离散数学期末 7 天冲刺）的 Day1 第一张
    卡就是诊断分诊，`/diagnose/generate` 必须接受 subject=离散数学（此前 422），
    且 update_galaxy=True 时掌握度落到 canonical dm.* sprint-pack 星图节点；
    图论链答错时瓶颈应指向欧拉/哈密顿与图基础（NS-001 人设弱点）。"""
    user_id = test_user.id
    service = ExamSprintDiagnosticService(db_session)

    # 与 NS-001 real_drive B4 完全相同的请求面
    generated = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(subject="离散数学", question_count=15, days_left=7, pass_score=60.0),
    )
    assert len(generated.questions) == 15
    assert len(generated.coverage_domains) >= 5
    assert any(q.question_type == "short_answer" for q in generated.questions)

    # 科目标题变体（如「离散数学期末」）走同一题包
    variant = await service.generate(
        user_id=user_id,
        request=DiagnosticGenerateRequest(subject="离散数学期末", question_count=10),
    )
    assert len(variant.questions) == 10

    graph_keywords = ("graph_basics", "euler_hamilton", "图")
    answers = []
    for question in generated.questions:
        linked = " ".join(
            [*(question.linked_node_slugs or []), *(question.linked_node_names or [])]
        )
        is_graph = any(token in linked for token in graph_keywords)
        answers.append(
            DiagnosticAnswerSubmission(
                question_id=question.question_id,
                answer="答错了" if is_graph else _dm_template_correct_answer(question.question_id.split("_", 2)[-1]),
                confidence=DiagnoseConfidence.CERTAIN,
            )
        )

    graded = await service.grade(
        user_id=user_id,
        request=DiagnosticGradeRequest(
            subject="离散数学",
            diagnostic_id=generated.diagnostic_id,
            answers=answers,
            days_left=7,
            pass_score=60.0,
            update_galaxy=True,
        ),
    )
    assert graded.estimated_score_now < 90, "graph-chain answered wrong must not score full marks"
    bottleneck_names = " ".join(item.node_name for item in graded.top_bottlenecks)
    assert "欧拉图与哈密顿图" in bottleneck_names or "图的基本概念" in bottleneck_names

    # 掌握度全部解析为具体星图节点，且落在 canonical dm.* sprint-pack 节点上
    assert graded.node_mastery_updates
    assert all(item.node_id is not None for item in graded.node_mastery_updates)
    status_rows = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_id))
    ).scalars().all()
    assert status_rows, "discrete-math mastery must persist to the galaxy"
    node_ids = {row.node_id for row in status_rows}
    nodes = (
        await db_session.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))
    ).scalars().all()
    by_id = {str(node.id): node for node in nodes}
    dm_nodes = [node for node in nodes if node.source_type == "sprint_pack"]
    assert dm_nodes, "discrete-math topics should map onto canonical dm.* sprint-pack nodes"
    assert all(by_id[str(n.id)].name for n in dm_nodes), "dm.* nodes must carry Chinese labels from pack metadata"
    assert any("欧拉" in n.name or "哈密顿" in n.name for n in dm_nodes)


def test_discrete_mathematics_pack_structure_and_grading_invariants():
    """P0-1 content gate: the DM pack must be structurally complete and every
    question must grade canonically (correct answers full marks, wrong choice
    texts zero) before it is allowed near a student."""
    import json
    from pathlib import Path

    from app.services.exam_sprint_diagnostic_service import (
        _DM_CORE_TEMPLATE_KEYS,
        _DM_DEFAULT_NODES,
        _pack_node_suffix_index,
    )

    # 1) sprint pack JSON loads and validates; dm.* nodes carry chapter surface
    pack = load_pack("离散数学")
    assert pack is not None, "discrete_mathematics_v1.json must load for subject 离散数学"
    SprintPackV1.model_validate(pack)
    node_ids = {n["node_id"] for n in pack["knowledge_nodes"]}
    assert all(nid.startswith("dm.") for nid in node_ids)
    layers = {n.get("layer") for n in pack["knowledge_nodes"]}
    assert {
        "ch1_logic",
        "ch2_sets_relations",
        "ch3_functions",
        "ch4_graph_theory",
        "ch5_combinatorics",
        "ch6_algebraic_systems",
    } <= layers, "pack must cover all NS-001 curriculum chapters"
    for path_def in pack["paths"].values():
        assert set(path_def["ordered_nodes"]) <= node_ids, "path must reference existing nodes only"

    # 2) template set structure
    assert 15 <= len(_DM_TEMPLATES) <= 30
    assert len({t.template_key for t in _DM_TEMPLATES}) == len(_DM_TEMPLATES)
    domains = {t.domain for t in _DM_TEMPLATES if t.domain != "综合题"}
    assert len(domains) >= 5
    core_domains = {t.domain for t in _DM_TEMPLATES if t.template_key in _DM_CORE_TEMPLATE_KEYS}
    assert len(core_domains) >= 5, "core keys must span at least 5 domains (generate gate)"
    assert any(t.question_type == "short_answer" for t in _DM_TEMPLATES)

    # 3) every linked slug resolves to a canonical dm.* sprint-pack node
    suffix_index = _pack_node_suffix_index()
    for template in _DM_TEMPLATES:
        for slug in template.linked_node_slugs:
            node_id = suffix_index.get(slug)
            assert node_id and node_id.startswith("dm."), (template.template_key, slug)

    # 4) default diagnostic nodes match pack node suffixes exactly
    suffixes = {nid.split(".", 1)[1] for nid in node_ids}
    for node in _DM_DEFAULT_NODES:
        assert node["slug"] in suffixes, node["slug"]

    # 5) per-question grading invariants
    service = ExamSprintDiagnosticService(db=None)
    for template in _DM_TEMPLATES:
        grader = DiagnosticQuestionGrader(
            template_key=template.template_key,
            question_type=template.question_type,
            correct_choice_index=template.correct_choice_index,
            choices=list(template.choices),
            accepted_answers=list(template.accepted_answers),
            required_keywords=list(template.required_keywords),
            partial_keywords=list(template.partial_keywords),
        )
        if template.question_type == DiagnoseQuestionType.SINGLE_CHOICE:
            correct_text = template.choices[template.correct_choice_index]
            assert service._score_answer(correct_text, grader) == 1.0, template.template_key
            assert service._score_answer(str(template.correct_choice_index + 1), grader) == 1.0
            assert service._score_answer("abcd"[template.correct_choice_index], grader) == 1.0
            for wrong_text in (c for i, c in enumerate(template.choices) if i != template.correct_choice_index):
                assert service._score_answer(wrong_text, grader) == 0.0, (
                    f"{template.template_key}: wrong choice text {wrong_text!r} must not score"
                )
        else:
            canonical = (
                "，".join(template.required_keywords) if template.required_keywords else template.accepted_answers[0]
            )
            assert service._score_answer(canonical, grader) == 1.0, template.template_key
            assert service._score_answer("完全不会", grader) <= 0.4, template.template_key


def test_diagnose_choice_texts_do_not_alias_answer_indices_across_subjects():
    """Regression for the bare-digit alias hazard: _score_choice_answer accepts
    digit submissions as 0/1-based indices, so any wrong option whose TEXT is a
    small digit can silently score full marks. Invariant must hold for every
    subject pack (cn/ds/dm), not just discrete math."""
    from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService

    service = ExamSprintDiagnosticService(db=None)
    for set_name, subject_set in _SUBJECT_TEMPLATE_SETS.items():
        for template in subject_set.templates:
            if template.question_type != DiagnoseQuestionType.SINGLE_CHOICE:
                continue
            grader = DiagnosticQuestionGrader(
                template_key=template.template_key,
                question_type=template.question_type,
                correct_choice_index=template.correct_choice_index,
                choices=list(template.choices),
            )
            for idx, wrong_text in enumerate(template.choices):
                if idx == template.correct_choice_index:
                    continue
                score = service._score_answer(wrong_text, grader)
                assert score == 0.0, (
                    f"{set_name}/{template.template_key}: wrong choice text {wrong_text!r} "
                    f"scores {score} — digit text aliases the answer-index heuristic"
                )
