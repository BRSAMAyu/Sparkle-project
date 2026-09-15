from __future__ import annotations

from app.core.celery_tasks import send_task_reminders


def test_send_task_reminders_is_disabled_noop():
    result = send_task_reminders.run()

    assert result == {
        "status": "disabled",
        "reason": "task reminders are handled by the mobile local scheduler",
    }
