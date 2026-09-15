#!/bin/bash
# MIMO API 验证脚本
# 直接使用 curl 测试 MIMO API 调用和联网搜索功能

set -e

# 从 .env 文件读取配置
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep -E '^(XIAOMI|LLM_TIER)' | xargs)
fi

API_KEY="${XIAOMI_MIMO_API_KEY:-}"
BASE_URL="${XIAOMI_MIMO_BASE_URL:-https://api.xiaomimimo.com/v1}"
MODEL="${XIAOMI_CHAT_MODEL:-mimo-v2-flash}"

if [ -z "$API_KEY" ]; then
    echo "XIAOMI_MIMO_API_KEY is not set; refusing to run a live provider check."
    exit 1
fi

echo "============================================================"
echo "  MIMO API 验证"
echo "============================================================"
echo ""
echo "配置信息:"
echo "  API Key: configured"
echo "  Base URL: $BASE_URL"
echo "  Model: $MODEL"
echo ""

# 1. 测试基础聊天
echo "============================================================"
echo "  1. 测试基础聊天（无联网搜索）"
echo "============================================================"

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"你好，请用一句话介绍你自己。\"}],
    \"temperature\": 1.0,
    \"max_tokens\": 100
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否有错误
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "❌ 基础聊天测试失败"
else
    echo "✅ 基础聊天测试成功"
fi
echo ""

# 2. 测试联网搜索
echo "============================================================"
echo "  2. 测试联网搜索功能"
echo "============================================================"

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"今天北京的天气怎么样？请搜索最新信息。\"}],
    \"tools\": [{\"type\": \"web_search\"}],
    \"temperature\": 1.0,
    \"max_tokens\": 500
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否有 annotations（联网搜索引用）
if echo "$RESPONSE" | grep -q '"annotations"'; then
    echo "✅ 联网搜索测试成功 - 找到搜索引用"
elif echo "$RESPONSE" | grep -q '"error"'; then
    echo "❌ 联网搜索测试失败"
else
    echo "ℹ️  响应中没有找到 annotations（可能是模型没有触发搜索）"
fi
echo ""

# 3. 测试思考模式
echo "============================================================"
echo "  3. 测试思考模式"
echo "============================================================"

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"计算 123 * 456 等于多少？请详细说明计算过程。\"}],
    \"thinking\": {\"type\": \"enabled\"},
    \"temperature\": 1.0,
    \"max_tokens\": 500
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否有 reasoning_content（思考链）
if echo "$RESPONSE" | grep -q '"reasoning_content"'; then
    echo "✅ 思考模式测试成功 - 找到思考链内容"
elif echo "$RESPONSE" | grep -q '"error"'; then
    echo "❌ 思考模式测试失败"
else
    echo "ℹ️  响应中没有找到 reasoning_content（可能是模型没有返回思考过程）"
fi
echo ""

# 4. 测试流式响应
echo "============================================================"
echo "  4. 测试流式响应"
echo "============================================================"

echo "发送流式请求..."
curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"用一句话介绍 Python 编程语言。\"}],
    \"tools\": [{\"type\": \"web_search\"}],
    \"thinking\": {\"type\": \"enabled\"},
    \"temperature\": 1.0,
    \"stream\": true,
    \"max_tokens\": 200
  }" 2>&1 | head -50

echo ""
echo "✅ 流式响应测试完成"
echo ""

echo "============================================================"
echo "  验证完成"
echo "============================================================"
