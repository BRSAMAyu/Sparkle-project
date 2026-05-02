from datetime import date, datetime, timedelta

import pytest

from app.models.calendar_event import CalendarEvent
from app.models.user_preferences import UserPreferencesCenter
from app.services.smart_schedule_service import SmartScheduleService
from app.schemas.smart_schedule import SmartScheduleRequest


def _minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


@pytest.mark.asyncio
async def test_smart_schedule_prefers_focus_aligned_slots_and_is_deterministic(db_session, test_user):
    target_date = date(2026, 4, 6)
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            version=1,
            explicit={},
            inferred={
                "peak_focus_hours": [14, 15],
                "inactive_push_hours": [10],
            },
        )
    )
    db_session.add_all(
        [
            CalendarEvent(
                user_id=test_user.id,
                title="Morning class",
                start_time=datetime(2026, 4, 6, 9, 0),
                end_time=datetime(2026, 4, 6, 10, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Lab block",
                start_time=datetime(2026, 4, 6, 12, 0),
                end_time=datetime(2026, 4, 6, 14, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Weekly seminar",
                start_time=datetime(2026, 3, 30, 16, 0),
                end_time=datetime(2026, 3, 30, 17, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Weekly seminar 2",
                start_time=datetime(2026, 3, 23, 16, 0),
                end_time=datetime(2026, 3, 23, 17, 0),
                source="manual",
                reminder_minutes=[],
            ),
        ]
    )
    await db_session.commit()

    service = SmartScheduleService(db_session)
    request = SmartScheduleRequest(
        estimated_minutes=60,
        energy_cost=5,
        difficulty=5,
        preferred_date=target_date,
    )

    first = await service.suggest_time_slots(test_user.id, request)
    second = await service.suggest_time_slots(test_user.id, request)

    assert [item.start_time for item in first.suggestions] == [item.start_time for item in second.suggestions]
    assert first.suggestions[0].start_time == "15:00"
    assert "peak_focus_hours" in (first.cognitive_insights or {})["signals_used"]
    assert "recurring_calendar_windows" in (first.cognitive_insights or {})["signals_used"]


@pytest.mark.asyncio
async def test_smart_schedule_respects_requested_duration_and_overlap_conflicts(db_session, test_user):
    target_date = date(2026, 4, 8)
    db_session.add_all(
        [
            CalendarEvent(
                user_id=test_user.id,
                title="Overnight duty",
                start_time=datetime(2026, 4, 7, 22, 0),
                end_time=datetime(2026, 4, 8, 8, 30),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Midday class",
                start_time=datetime(2026, 4, 8, 11, 0),
                end_time=datetime(2026, 4, 8, 12, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Afternoon lab",
                start_time=datetime(2026, 4, 8, 14, 0),
                end_time=datetime(2026, 4, 8, 16, 0),
                source="manual",
                reminder_minutes=[],
            ),
        ]
    )
    await db_session.commit()

    service = SmartScheduleService(db_session)
    response = await service.suggest_time_slots(
        test_user.id,
        SmartScheduleRequest(
            estimated_minutes=120,
            energy_cost=3,
            difficulty=3,
            preferred_date=target_date,
        ),
    )

    assert response.suggestions
    for suggestion in response.suggestions:
        start = _minutes(suggestion.start_time)
        end = _minutes(suggestion.end_time)
        assert end - start >= 120
        assert end <= 11 * 60 or start >= 12 * 60
        assert end <= 14 * 60 or start >= 16 * 60
        assert start >= 8 * 60 + 30


@pytest.mark.asyncio
async def test_smart_schedule_uses_achievement_peak_hours_as_fallback(db_session, test_user):
    target_date = date(2026, 4, 7)
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            version=1,
            explicit={},
            inferred={
                "achievement_peak_hours": [18, 19],
            },
        )
    )
    await db_session.commit()

    service = SmartScheduleService(db_session)
    response = await service.suggest_time_slots(
        test_user.id,
        SmartScheduleRequest(
            estimated_minutes=45,
            energy_cost=5,
            difficulty=4,
            preferred_date=target_date,
        ),
    )

    assert response.suggestions[0].start_time == "18:00"
    assert response.cognitive_insights["focus_hours"] == [18, 19]
    assert "achievement_peak_hours" in response.cognitive_insights["signals_used"]
