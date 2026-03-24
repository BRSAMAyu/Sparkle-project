#!/bin/bash
# MIMO v2-pro 集成验证脚本（简化版）
# 使用 curl 直接调用 MIMO API

set -e

# 从 .env 文件读取配置
source .env 2>/dev/null || true

API_KEY="${XIAOMI_MIMO_API_KEY}"
BASE_URL="${XIAOMI_MIMO_BASE_URL:-https://api.xiaomimimo.com/v1}"
MODEL="${XIAOMI_PRO_MODEL:-mimo-v2-pro}"

echo "=============================================="
echo "  MIMO v2-pro 集成验证"
echo "=============================================="
echo ""
echo "配置信息:"
echo "  API Key: ${API_KEY:0:10}..."
echo "  Base URL: $BASE_URL"
echo "  Model: $MODEL"
echo ""

# 1. 测试基础聊天
echo "=============================================="
echo "1. 测试基础聊天（不带联网搜索）"
echo "=============================================="

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"你好，请用一句话介绍你自己。\"}],
    \"max_tokens\": 100
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否有错误
ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
if [ -n "$ERROR" ]; then
    echo "❌ 基础聊天失败: $ERROR"
    exit 1
fi

echo "✅ 基础聊天成功"
echo ""

# 2. 测试联网搜索
echo "=============================================="
echo "2. 测试联网搜索功能"
echo "=============================================="

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"今天北京的天气怎么样？请搜索最新信息。\"}],
    \"tools\": [{\"type\": \"web_search\"}],
    \"max_tokens\": 500
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否有错误
ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
if [ -n "$ERROR" ]; then
    echo "❌ 联网搜索失败: $ERROR"
    exit 1
fi

# 检查 annotations（联网搜索引用）
ANNOTATIONS=$(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msg = d.get('choices', [{}])[0].get('message', {})
anns = msg.get('annotations', [])
print(f'找到 {len(anns)} 个搜索引用' if anns else '无搜索引用')
for i, a in enumerate(anns[:3], 1):
    print(f'  {i}. {a.get(\"title\", \"N/A\")}')
" 2>/dev/null)

echo "联网搜索引用: $ANNOTATIONS"
echo "✅ 联网搜索测试完成"
echo ""

# 3. 测试思考模式
echo "=============================================="
echo "3. 测试思考模式"
echo "=============================================="

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"请解释一下什么是递归，并给出一个例子。\"}],
    \"thinking\": {\"type\": \"enabled\"},
    \"max_tokens\": 500
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查 reasoning_content
REASONING=$(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msg = d.get('choices', [{}])[0].get('message', {})
rc = msg.get('reasoning_content', '')
print(f'思考链长度: {len(rc)} 字符' if rc else '无思考链内容')
" 2>/dev/null)

echo "思考链: $REASONING"
echo "✅ 思考模式测试完成"
echo ""

# 4. 测试流式响应
echo "=============================================="
echo "4. 测试流式响应"
echo "=============================================="

echo "发送流式请求..."
curl -s -N -X POST "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"请数到5\"}],
    \"stream\": true,
    \"max_tokens\": 50
  }" 2>&1 | head -20

echo ""
echo "✅ 流式响应测试完成"
echo ""

echo "=============================================="
echo "  🎉 MIMO v2-pro 集成验证完成"
echo "=============================================="
