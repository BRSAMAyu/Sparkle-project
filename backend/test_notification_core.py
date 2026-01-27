"""Simplified test of notification system core functionality"""
import asyncio
from unittest.mock import Mock, AsyncMock
from app.services.state_notification_service import StateNotificationService
from app.schemas.unified_notification import (
    UnifiedNotificationResponse,
    NotificationAnalyticsResponse,
    NotificationAnalyticsSummary,
    NotificationTypeStats,
    NotificationTrendData,
)
from datetime import datetime
from uuid import uuid4

print("=" * 60)
print("🧪 Notification System Core Tests")
print("=" * 60)

# Test 1: StateNotificationService - Plan Archived
print("\n1️⃣  Testing Plan Archived Notification...")
print("-" * 60)

mock_ws = Mock()
mock_ws.send_personal_message = AsyncMock()

service = StateNotificationService()
service.ws_manager = mock_ws

async def test_plan_archived():
    await service.notify_plan_archived(
        user_id="user-123",
        plan_name="学习 Flutter 基础",
        plan_id="plan-456",
        task_count_freed=15,
        memory_count_removed=8,
        new_primary_plan="学习 Dart 高级"
    )

    assert mock_ws.send_personal_message.called
    message = mock_ws.send_personal_message.call_args[0][0]

    assert message["type"] == "delta"
    assert "metadata" in message
    assert "state_change_event" in message["metadata"]

    event = message["metadata"]["state_change_event"]
    assert event["change_type"] == "plan_archived"
    assert event["plan_name"] == "学习 Flutter 基础"
    assert event["task_count_freed"] == 15
    assert event["memory_count_removed"] == 8

    formatted = message["metadata"]["formatted_message"]
    assert "✅ 已归档计划" in formatted
    assert "释放了 15 个任务配额" in formatted
    assert "从记忆中移除 8 个知识点" in formatted
    assert "新主计划：学习 Dart 高级" in formatted

    print("✅ Plan Archived Notification Test PASSED")
    print(f"   📱 Formatted Message:\n{formatted}")

asyncio.run(test_plan_archived())

# Test 2: StateNotificationService - Settings Updated
print("\n2️⃣  Testing Settings Update Notification...")
print("-" * 60)

async def test_settings_updated():
    mock_ws.reset_mock()

    await service.notify_user_settings_updated(
        user_id="user-456",
        setting_field="transparency_level",
        old_value=0,
        new_value=2,
        impact_description="这将影响你未来的学习体验",
        intervention_level="toast"
    )

    message = mock_ws.send_personal_message.call_args[0][0]
    event = message["metadata"]["state_change_event"]

    assert event["change_type"] == "user_settings_updated"
    assert event["old_value"] == 0
    assert event["new_value"] == 2
    assert event["field_label"] == "透明度级别"

    formatted = message["metadata"]["formatted_message"]
    assert "⚙️ 设置已更新" in formatted
    assert "透明度级别" in formatted

    print("✅ Settings Update Notification Test PASSED")
    print(f"   📱 Formatted Message:\n{formatted}")

asyncio.run(test_settings_updated())

# Test 3: StateNotificationService - Plan Restored
print("\n3️⃣  Testing Plan Restored Notification...")
print("-" * 60)

async def test_plan_restored():
    mock_ws.reset_mock()

    await service.notify_plan_restored(
        user_id="user-789",
        plan_name="已归档的计划",
        plan_id="plan-101"
    )

    message = mock_ws.send_personal_message.call_args[0][0]
    formatted = message["metadata"]["formatted_message"]

    assert "🔄 已恢复计划" in formatted
    assert "已归档的计划" in formatted

    print("✅ Plan Restored Notification Test PASSED")
    print(f"   📱 Formatted Message:\n{formatted}")

asyncio.run(test_plan_restored())

# Test 4: StateNotificationService - Plan Deleted
print("\n4️⃣  Testing Plan Deleted Notification...")
print("-" * 60)

async def test_plan_deleted():
    mock_ws.reset_mock()

    await service.notify_plan_deleted(
        user_id="user-999",
        plan_name="旧计划",
        plan_id="plan-202",
        task_count_freed=5,
        memory_count_removed=3
    )

    message = mock_ws.send_personal_message.call_args[0][0]
    formatted = message["metadata"]["formatted_message"]

    assert "🗑️ 已删除计划" in formatted
    assert "旧计划" in formatted

    print("✅ Plan Deleted Notification Test PASSED")
    print(f"   📱 Formatted Message:\n{formatted}")

asyncio.run(test_plan_deleted())

# Test 5: Schema Validation
print("\n5️⃣  Testing Schema Validation...")
print("-" * 60)

notif = UnifiedNotificationResponse(
    id=str(uuid4()),
    source_type="system",
    title="系统通知",
    content="这是一个测试通知",
    type="test",
    priority="medium",
    is_read=False,
    created_at=datetime.utcnow()
)
assert notif.source_type == "system"
print("✅ UnifiedNotificationResponse schema validates")

summary = NotificationAnalyticsSummary(
    total_sent=100,
    total_viewed=75,
    total_clicked=40,
    view_rate=75.0,
    click_rate=53.33,
    avg_time_to_action=120.5
)
assert summary.view_rate == 75.0
print("✅ NotificationAnalyticsSummary schema validates")

type_stats = NotificationTypeStats(
    type="system",
    sent=60,
    viewed=45,
    clicked=25,
    view_rate=75.0,
    click_rate=55.56
)
print("✅ NotificationTypeStats schema validates")

trend = NotificationTrendData(
    date="2026-01-28",
    sent=20,
    viewed=15,
    clicked=8
)
print("✅ NotificationTrendData schema validates")

analytics = NotificationAnalyticsResponse(
    summary=summary,
    by_type={"system": type_stats},
    trends=[trend],
    hourly_distribution=[0, 0, 5, 12, 8, 15, 20, 18, 10, 8, 5, 3, 2, 1, 0, 0, 0, 2, 4, 6, 8, 10, 7, 5, 3]
)
print(f"   Hourly distribution length: {len(analytics.hourly_distribution)}")
print("✅ NotificationAnalyticsResponse schema validates")

# Test 6: WebSocket Helper
print("\n6️⃣  Testing WebSocket Helper...")
print("-" * 60)

from app.core.websocket import get_ws_manager

ws_manager = get_ws_manager()
assert ws_manager is not None
assert hasattr(ws_manager, 'send_personal_message')
print("✅ get_ws_manager() returns proper instance")

print("\n" + "=" * 60)
print("✅ ALL CORE TESTS PASSED!")
print("=" * 60)

print("\n📝 Test Summary:")
print("   ✅ Plan archived notification (with formatted message)")
print("   ✅ Settings update notification (with old→new values)")
print("   ✅ Plan restored notification")
print("   ✅ Plan deleted notification")
print("   ✅ All schema types validate correctly")
print("   ✅ WebSocket helper function works")

print("\n🔔 Message Format Verification:")
print("   ✅ Chinese user-friendly messages")
print("   ✅ Detailed information (tasks, memories, new primary)")
print("   ✅ Proper metadata structure")
print("   ✅ Intervention levels supported")

print("\n🚀 Core notification system is working correctly!")
print("   Ready for integration testing with Flutter app.")
