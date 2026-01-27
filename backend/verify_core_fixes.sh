#!/bin/bash
# 核心阻塞问题修复 - 快速验证脚本
# 使用方法: cd backend && bash verify_core_fixes.sh

set -e

echo "========================================"
echo "核心阻塞问题修复 - 快速验证"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
TOTAL=0
PASSED=0
FAILED=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL=$((TOTAL + 1))
    echo -n "[$TOTAL] $test_name ... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "🔍 第1步: 语法检查"
echo "-----------------------------------"
run_test "orchestrator.py 语法检查" \
    "python -m py_compile app/orchestration/orchestrator.py"
run_test "plan_review_service.py 语法检查" \
    "python -m py_compile app/orchestration/plan_review_service.py"
run_test "unified_intent_router.py 语法检查" \
    "python -m py_compile app/core/unified_intent_router.py"
echo ""

echo "🔍 第2步: 导入验证"
echo "-----------------------------------"
run_test "导入ChatOrchestrator" \
    "python -c 'from app.orchestration.orchestrator import ChatOrchestrator'"
run_test "导入PlanReviewService" \
    "python -c 'from app.orchestration.plan_review_service import PlanReviewService'"
run_test "导入UnifiedIntentRouter" \
    "python -c 'from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType'"
echo ""

echo "🔍 第3步: 新增方法验证"
echo "-----------------------------------"
run_test "检查_is_information_sufficient方法" \
    "python -c 'from app.orchestration.orchestrator import ChatOrchestrator; assert hasattr(ChatOrchestrator, \"_is_information_sufficient\")'"
run_test "检查_generate_clarifying_question方法" \
    "python -c 'from app.orchestration.orchestrator import ChatOrchestrator; assert hasattr(ChatOrchestrator, \"_generate_clarifying_question\")'"
run_test "检查track_rejection_count方法" \
    "python -c 'from app.orchestration.plan_review_service import PlanReviewService; assert hasattr(PlanReviewService, \"track_rejection_count\")'"
run_test "检查reset_rejection_count方法" \
    "python -c 'from app.orchestration.plan_review_service import PlanReviewService; assert hasattr(PlanReviewService, \"reset_rejection_count\")'"
echo ""

echo "🔍 第4步: 功能测试"
echo "-----------------------------------"
run_test "统一路由系统测试" \
    "python -c '
import asyncio
from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType

async def test():
    router = UnifiedIntentRouter(redis_client=None, llm_service=None)
    result = await router.route(\"帮我看学习习惯\", \"user\", \"session\", {})
    assert result.primary_intent == UnifiedIntentType.COGNITIVE_PRISM

asyncio.run(test())
'"

run_test "信息收集判断测试" \
    "python -c '
import asyncio
from app.orchestration.orchestrator import ChatOrchestrator

async def test():
    class MockRedis:
        async def get(self, key): return None
        async def set(self, key, value): pass
        async def setex(self, key, ttl, value): pass

    orchestrator = ChatOrchestrator(redis_client=MockRedis())
    result = await orchestrator._needs_information_collection(\"帮我制定计划\", None)
    assert result == True

asyncio.run(test())
'"

run_test "拒绝计数测试" \
    "python -c '
import asyncio
from app.orchestration.plan_review_service import PlanReviewService

async def test():
    class MockRedis:
        def __init__(self):
            self.data = {}
        async def incr(self, key):
            self.data[key] = self.data.get(key, 0) + 1
            return self.data[key]
        async def expire(self, key, ttl): pass
        async def delete(self, key): pass
        async def publish(self, channel, message): pass

    service = PlanReviewService(redis_client=MockRedis())
    count = await service.track_rejection_count(\"plan1\", \"user1\")
    assert count == 1

asyncio.run(test())
'"

echo ""

echo "🔍 第5步: 单元测试"
echo "-----------------------------------"
run_test "行为范式衰减测试" \
    "python -m pytest tests/unit/test_behavior_pattern_decay.py -v -q"
run_test "上下文包冲突测试" \
    "python -m pytest tests/unit/test_context_pack_conflicts.py -v -q"
echo ""

echo "========================================"
echo "📊 测试总结"
echo "========================================"
echo -e "总测试数: $TOTAL"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！${NC}"
    echo ""
    echo "✅ 代码可以安全启动和运行"
    echo ""
    echo "📋 下一步建议:"
    echo "   1. 启动服务: make dev-all && make grpc-server"
    echo "   2. 查看日志: docker compose logs -f grpc-server"
    echo "   3. 进行端到端测试"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  有 $FAILED 个测试失败，请检查上述错误${NC}"
    echo ""
    exit 1
fi
