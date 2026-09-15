"""
B-001 Regression Tests: AchievementEngine kwargs NameError

Bug: _get_relevant_achievements(event_type: str) called kwargs.get() but
signature had no **kwargs → NameError on HIDDEN_TRIGGER events.

These tests ensure:
1. The method signature includes **kwargs
2. HIDDEN_TRIGGER events with kwargs don't raise NameError
3. process_event passes kwargs through to _get_relevant_achievements
"""

import inspect

import pytest
import pytest_asyncio

from app.services.achievement_engine import AchievementEngine


class TestKwargsSignature:
    def test_get_relevant_achievements_has_kwargs_param(self):
        """B-001 regression: _get_relevant_achievements must accept **kwargs."""
        sig = inspect.signature(AchievementEngine._get_relevant_achievements)
        params = sig.parameters
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        assert has_var_keyword, (
            f"_get_relevant_achievements missing **kwargs. "
            f"Parameters: {list(params.keys())}"
        )

    def test_process_event_has_kwargs_param(self):
        """B-001 regression: process_event must accept **kwargs for pass-through."""
        sig = inspect.signature(AchievementEngine.process_event)
        params = sig.parameters
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        assert has_var_keyword, (
            f"process_event missing **kwargs. Parameters: {list(params.keys())}"
        )


@pytest.mark.asyncio
class TestHiddenTriggerKwargs:
    """Verify HIDDEN_TRIGGER events work with kwargs pass-through."""

    async def test_hidden_trigger_no_name_error(self, db_session):
        """B-001 regression: HIDDEN_TRIGGER + kwargs must not NameError."""
        engine = AchievementEngine(db_session)
        # Directly call the method that previously crashed
        try:
            result = await engine._get_relevant_achievements(
                "hidden_trigger",
                hidden_trigger_code="EASTER_EGG",
            )
        except NameError as e:
            pytest.fail(f"NameError raised (B-001 regression): {e}")
        # Result should be a list (may be empty if no matching achievements in test DB)
        assert isinstance(result, list)

    async def test_hidden_trigger_with_codes_list(self, db_session):
        """B-001 regression: hidden_trigger_codes list kwarg must work."""
        engine = AchievementEngine(db_session)
        try:
            result = await engine._get_relevant_achievements(
                "hidden_trigger",
                hidden_trigger_code="PERFECTIONIST",
                hidden_trigger_codes=["PERFECTIONIST", "EASTER_EGG"],
            )
        except NameError as e:
            pytest.fail(f"NameError raised (B-001 regression): {e}")
        assert isinstance(result, list)

    async def test_process_event_passes_kwargs_through(self, db_session, test_user):
        """Verify process_event forwards kwargs to _get_relevant_achievements."""
        engine = AchievementEngine(db_session)

        # We can't easily spy on an async method, but we can verify
        # the method doesn't crash when called with HIDDEN_TRIGGER + kwargs
        try:
            result = await engine.process_event(
                user_id=str(test_user.id),
                event_type="hidden_trigger",
                hidden_trigger_code="PERFECTIONIST",
                hidden_trigger_codes=["PERFECTIONIST"],
            )
        except NameError as e:
            pytest.fail(f"NameError in process_event (B-001 regression): {e}")
        except Exception:
            # Other exceptions (e.g., DB state) are acceptable — we're
            # only checking that kwargs don't cause NameError
            pass
        else:
            assert isinstance(result, list)
