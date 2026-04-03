from datetime import datetime
from uuid import uuid4

from app.schemas.cognitive import BehaviorPatternResponse


def test_behavior_pattern_response_normalizes_compound_pattern_type():
    payload = {
        "id": uuid4(),
        "user_id": uuid4(),
        "pattern_name": "拖延伴随焦虑",
        "pattern_type": "cognitive/emotional",
        "description": "测试",
        "solution_text": None,
        "evidence_ids": [],
        "confidence_score": 0.82,
        "frequency": 3,
        "is_archived": False,
        "last_observed_at": None,
        "last_decay_at": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    parsed = BehaviorPatternResponse.model_validate(payload)

    assert parsed.pattern_type.value == "cognitive"
