from app.models.plan import Plan


def test_plan_model_defines_primary_and_relationships_once():
    assert list(Plan.__table__.columns.keys()).count("is_primary") == 1
    assert "user" in Plan.__mapper__.relationships
    assert "tasks" in Plan.__mapper__.relationships
