import json
from pathlib import Path


def test_follow_up_question_templates_are_frozen_and_bounded() -> None:
    path = Path(__file__).resolve().parents[2] / "app" / "services" / "follow_up_question_templates.v1.json"
    templates = json.loads(path.read_text(encoding="utf-8"))

    assert len(templates) <= 6
    assert len({item["template_id"] for item in templates}) == len(templates)
    assert all(item["category"] == "task_sufficiency" for item in templates)
    assert all(str(item["message"]).strip() for item in templates)
