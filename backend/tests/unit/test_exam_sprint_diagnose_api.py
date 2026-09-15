from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.exam_sprint import router
from app.models.galaxy import KnowledgeNode

app = FastAPI()
app.include_router(router, prefix="/api/v1/exam-sprint")


@pytest.mark.asyncio
async def test_exam_sprint_generate_and_grade_api_round_trip(db_session, test_user):
    names = [
        "分层模型与协议栈",
        "IP / 子网划分",
        "路由基础",
        "TCP 可靠传输",
        "TCP 拥塞控制",
        "HTTP / DNS",
        "链路层基础",
    ]
    for name in names:
        db_session.add(
            KnowledgeNode(
                id=uuid4(),
                name=name,
                description=name,
                importance_level=2,
                source_type="seed",
                dominant_sector_code="VOID",
                sector_classification_status="pending",
            )
        )
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        generate_resp = await ac.post(
            "/api/v1/exam-sprint/diagnose/generate",
            json={
                "subject": "计算机网络",
                "question_count": 10,
                "knowledge_nodes": [{"name": name} for name in names],
            },
        )

        assert generate_resp.status_code == 200
        generate_payload = generate_resp.json()
        assert len(generate_payload["coverage_domains"]) >= 5
        assert len(generate_payload["questions"]) == 10

        answers = []
        for question in generate_payload["questions"]:
            grader = generate_payload["grading_payload"][question["question_id"]]
            if question["domain"] == "TCP 拥塞控制":
                answer = "错误答案"
            elif grader["question_type"] == "single_choice":
                answer = str((grader["correct_choice_index"] or 0) + 1)
            else:
                answer = grader["accepted_answers"][0] if grader["accepted_answers"] else " ".join(grader["required_keywords"])
            answers.append(
                {
                    "question_id": question["question_id"],
                    "answer": answer,
                    "confidence": "certain",
                }
            )

        grade_resp = await ac.post(
            "/api/v1/exam-sprint/diagnose/grade",
            json={
                "subject": "计算机网络",
                "answers": answers,
                "grading_payload": generate_payload["grading_payload"],
                "knowledge_nodes": [{"name": name} for name in names],
                "days_left": 6,
            },
        )

    assert grade_resp.status_code == 200
    grade_payload = grade_resp.json()
    assert "estimated_score_now" in grade_payload
    assert grade_payload["top_bottlenecks"]
    assert grade_payload["recommended_path"] in {"minimum_pass", "score_max"}
    assert grade_payload["node_mastery_updates"]
    app.dependency_overrides = {}
