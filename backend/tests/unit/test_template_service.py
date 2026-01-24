import pytest

from app.services.template_registry import TemplateRegistry
from app.services.template_service import TemplateService


@pytest.mark.asyncio
async def test_template_service_renders_template():
    registry = TemplateRegistry()
    registry.load_templates()
    service = TemplateService(registry)

    selected = await service.select_variant(
        intent_type="recover_to_task",
        support_level=4,
        user_id="user-1",
    )

    rendered = service.render(
        selected,
        {"task_name": "数学作业", "suggested_step": "读题"},
    )

    assert "数学作业" in rendered
    assert "读题" in rendered
