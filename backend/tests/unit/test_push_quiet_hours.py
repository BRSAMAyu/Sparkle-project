"""Regression tests for quiet-hours window math (P1')."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.push_delivery_service import PushDeliveryService


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 21, hour, minute, tzinfo=UTC).replace(tzinfo=None)


def test_non_cross_midnight_window_only_suppresses_inside_window():
    """P1': 12:00-14:00 这类非跨午夜窗口，旧公式并集覆盖全天导致永久免打扰。"""
    assert PushDeliveryService._is_in_quiet_hours(now=_at(13), quiet_start="12:00", quiet_end="14:00") is True
    assert PushDeliveryService._is_in_quiet_hours(now=_at(9), quiet_start="12:00", quiet_end="14:00") is False
    assert PushDeliveryService._is_in_quiet_hours(now=_at(15), quiet_start="12:00", quiet_end="14:00") is False


def test_cross_midnight_window_still_suppressed():
    assert PushDeliveryService._is_in_quiet_hours(now=_at(23), quiet_start="22:00", quiet_end="08:00") is True
    assert PushDeliveryService._is_in_quiet_hours(now=_at(3, 30), quiet_start="22:00", quiet_end="08:00") is True
    assert PushDeliveryService._is_in_quiet_hours(now=_at(12), quiet_start="22:00", quiet_end="08:00") is False


def test_equal_start_end_means_no_quiet_window():
    assert PushDeliveryService._is_in_quiet_hours(now=_at(13), quiet_start="12:00", quiet_end="12:00") is False


def test_malformed_values_do_not_crash_or_expand_silence():
    assert PushDeliveryService._is_in_quiet_hours(now=_at(13), quiet_start="abc", quiet_end="08:00") is False
    assert PushDeliveryService._is_in_quiet_hours(now=_at(13), quiet_start="99:99", quiet_end="08:00") is False
    assert PushDeliveryService._is_in_quiet_hours(now=_at(13), quiet_start="2200", quiet_end="08:00") is False
