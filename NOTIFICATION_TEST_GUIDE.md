#!/bin/bash
# Notification System Testing Script
# This script helps verify the notification system implementation

set -e

echo "🔔 Notification System Testing Guide"
echo "===================================="
echo ""

# Check if services are running
echo "📡 Checking service status..."
echo ""

# Check PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is NOT running"
    echo "   Start with: make dev-all"
    echo ""
    read -p "Start PostgreSQL now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose up -d postgres
        sleep 3
    fi
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is NOT running"
    echo "   Start with: make dev-all"
fi

echo ""
echo "📊 Database Migration"
echo "--------------------"
cd backend
echo "Running: alembic upgrade head"
alembic upgrade head
echo "✅ Database migration complete"
cd ..
echo ""

echo "🔧 Backend Tests"
echo "----------------"
echo "Run these commands to test the backend:"
echo ""
echo "  # Test StateNotificationService"
echo "  cd backend"
echo "  pytest tests/services/test_state_notification_service.py -v"
echo ""
echo "  # Test Plans API integration"
echo "  pytest tests/api/v1/test_plans.py::test_archive_plan_sends_notification -v"
echo ""

echo "📱 Frontend Tests"
echo "----------------"
echo "Run these commands to test the frontend:"
echo ""
echo "  # Test StateChangeEvent parsing"
echo "  cd mobile"
echo "  flutter test test/features/chat/models/state_change_event_test.dart"
echo ""
echo "  # Test WebSocket service integration"
echo "  flutter test test/features/chat/data/services/websocket_chat_service_v2_test.dart"
echo ""

echo "🎯 Manual Testing Checklist"
echo "---------------------------"
echo ""
echo "1. Plan Archive Notification:"
echo "   - Open the Flutter app"
echo "   - Navigate to Plans screen"
echo "   - Long-press a plan and select 'Archive'"
echo "   - ✅ Should see: '✅ 已归档计划：[Plan Name]'"
echo "   - ✅ Should show: '✓ 释放了 X 个任务配额'"
echo "   - ✅ Should show: '✓ 新主计划：[Name]'"
echo ""
echo "2. Plan Restore Notification:"
echo "   - Go to Archived Plans"
echo "   - Select a plan and tap 'Restore'"
echo "   - ✅ Should see: '🔄 已恢复计划：[Plan Name]'"
echo ""
echo "3. Settings Update Notification:"
echo "   - Navigate to Settings"
echo "   - Change 'Transparency Level' from 0 to 2"
echo "   - ✅ Should see: '⚙️ 设置已更新：透明度级别'"
echo "   - ✅ Should show: '旧值：0' and '新值：2'"
echo ""
echo "4. Verify WebSocket Messages:"
echo "   - Open browser console (Chrome) or app logs"
echo "   - Filter by 'WebSocket' or 'ws'"
echo "   - ✅ Should see: {type: 'delta', metadata: {state_change_event: {...}}}"
echo ""

echo "🐛 Debugging Tips"
echo "-----------------"
echo ""
echo "Backend logs:"
echo "  docker compose logs -f grpc-server | grep 'notification'"
echo ""
echo "Frontend logs:"
echo "  # In Flutter, add this debug print:"
echo "  debugPrint('🔄 State change: ${event.changeType}');"
echo ""
echo "WebSocket messages:"
echo "  # Add this in websocket_chat_service_v2.dart:"
echo "  debugPrint('🔔 WebSocket message: $data');"
echo ""

echo "📝 Verification Queries"
echo "----------------------"
echo ""
echo "Check database tables:"
echo "  docker compose exec postgres psql -U sparkle -c \""
echo "    SELECT COUNT(*) FROM notification_interactions;"
echo "  \""
echo ""
echo "Check Redis cache:"
echo "  docker compose exec redis redis-cli KEYS 'ws:online:*'"
echo ""

echo "✅ Ready to test!"
echo ""
echo "For full implementation status, see:"
echo "  NOTIFICATION_SYSTEM_IMPLEMENTATION_STATUS.md"
echo ""
