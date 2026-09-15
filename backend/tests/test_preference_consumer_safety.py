"""Regression test for ISSUE-20260503-1701-F2.

Verifies that PreferenceEventConsumer has:
1. _running flag and stop() method for graceful shutdown
2. Retry count tracking and DLQ for poison messages
3. _handle_failed_message routing (retry vs DLQ)
"""
import inspect
from pathlib import Path

import pytest

CONSUMER_PATH = Path(__file__).resolve().parents[2] / "backend" / "app" / "services" / "preference_event_consumer.py"


def test_has_stop_method():
    """PreferenceEventConsumer must have a stop() method."""
    source = CONSUMER_PATH.read_text()
    assert "def stop(self)" in source, "PreferenceEventConsumer must implement stop()"


def test_has_running_flag():
    """PreferenceEventConsumer must use a _running flag instead of while True."""
    source = CONSUMER_PATH.read_text()
    assert "self._running = False" in source, "stop() must set _running = False"
    assert "self._running = True" in source, "start() must set _running = True"
    assert "while self._running:" in source, "start() must use while self._running instead of while True"
    assert "while True:" not in source, "start() must NOT use while True:"


def test_has_retry_and_dlq():
    """PreferenceEventConsumer must have retry count and DLQ mechanism."""
    source = CONSUMER_PATH.read_text()
    assert "_handle_failed_message" in source, "Must have _handle_failed_message method"
    assert "_requeue_for_retry" in source, "Must have _requeue_for_retry method"
    assert "_move_to_dlq" in source, "Must have _move_to_dlq method"
    assert "MAX_RETRIES" in source, "Must define MAX_RETRIES constant"
    assert ":dlq" in source, "DLQ stream must have :dlq suffix"


def test_handle_event_raises_on_failure():
    """_handle_event must raise exceptions (not swallow) so _handle_failed_message can route them."""
    source = CONSUMER_PATH.read_text()
    lines = source.split("\n")
    in_handle_event = False
    last_except_line = ""
    for i, line in enumerate(lines):
        if "async def _handle_event" in line:
            in_handle_event = True
        elif in_handle_event and "async def " in line and "_handle_event" not in line:
            in_handle_event = False
        elif in_handle_event:
            if "except Exception" in line:
                last_except_line = line.strip()
            if "raise" in line and in_handle_event:
                return
    assert False, "_handle_event inner except must re-raise so _handle_failed_message can route to retry/DLQ"


def test_no_while_true():
    """The consumer must not have any bare while True: loops."""
    source = CONSUMER_PATH.read_text()
    lines = source.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "while True:":
            pytest.fail(f"Found 'while True:' at line {i+1} — use 'while self._running:' instead")
