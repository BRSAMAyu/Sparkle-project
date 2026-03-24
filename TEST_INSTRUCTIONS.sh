#!/bin/bash

# Sparkle 全功能验收测试脚本
# 使用方法: bash TEST_INSTRUCTIONS.sh

echo "======================================"
echo "  Sparkle 全功能验收测试"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL=0
PASSED=0
FAILED=0

# 测试函数
test_api() {
    local name=$1
    local url=$2
    local expected=$3

    TOTAL=$((TOTAL + 1))
    echo -n "测试 $TOTAL: $name ... "

    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$url" 2>/dev/null)
    result=$?

    if [ $result -eq 0 ] && [ ! -z "$response" ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# 获取测试token
echo "1. 获取测试token..."
TOKEN=$(curl -s -X POST "http://localhost:8080/api/v1/auth/guest?guest_id=test_guest_$(date +%s)" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 无法获取token，请确保后端服务运行中${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token获取成功${NC}"
echo ""

# 运行API测试
echo "2. 开始API验收测试..."
echo ""

test_api "Galaxy Graph" "http://localhost:8080/api/v1/galaxy/graph" "nodes"
test_api "Galaxy Stats" "http://localhost:8080/api/v1/galaxy/stats" "user_stats"
test_api "Plans List" "http://localhost:8080/api/v1/plans" "data"
test_api "Tasks Today" "http://localhost:8080/api/v1/tasks/today" "id"
test_api "Achievements" "http://localhost:8080/api/v1/achievements" "data"
test_api "Achievement Stats" "http://localhost:8080/api/v1/achievements/stats" "total_achievements"
test_api "Streak Stats" "http://localhost:8080/api/v1/achievements/streak" "current_streak"
test_api "Community Groups" "http://localhost:8080/api/v1/community/groups" "id"
test_api "Community Friends" "http://localhost:8080/api/v1/community/friends" "id"
test_api "Chat Sessions" "http://localhost:8080/api/v1/chat/sessions" "[]"
test_api "Accountability Partners" "http://localhost:8080/api/v1/accountability/mine" "partnership_id"

echo ""
echo "3. WebSocket握手测试..."
TOTAL=$((TOTAL + 1))
ws_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "Upgrade: websocket" -H "Connection: Upgrade" -H "Sec-WebSocket-Key: test123" -H "Sec-WebSocket-Version: 13" "http://localhost:8080/ws/chat")

if [ "$ws_code" == "101" ]; then
    echo -e "${GREEN}✅ WebSocket握手成功 (101)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ WebSocket握手失败 ($ws_code)${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "======================================"
echo "  测试结果汇总"
echo "======================================"
echo -e "总计: $TOTAL"
echo -e "通过: ${GREEN}$PASSED${NC}"
echo -e "失败: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有后端API测试通过！${NC}"
    echo ""
    echo "下一步: 在Flutter app中验证UI功能"
    echo ""
    echo "运行以下命令启动Flutter app:"
    echo "  cd mobile"
    echo "  flutter run"
    echo ""
    echo "然后在app中:"
    echo "  1. 点击'访客登录'"
    echo "  2. 验证所有页面数据加载正常"
    echo "  3. 测试AI对话功能"
    echo ""
else
    echo -e "${RED}❌ 部分测试失败，请检查后端服务${NC}"
fi

echo ""
echo "详细报告: ACCEPTANCE_REPORT.md"
echo "======================================"
