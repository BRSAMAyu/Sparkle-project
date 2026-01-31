#!/bin/bash

echo "========================================"
echo "🔧 Sparkle WebSocket 修复脚本"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd /Users/a/code/sparkle-flutter/mobile

echo -e "${BLUE}1. 检查代码修改...${NC}"
echo "----------------------------------------"

# 检查 _applyWebSocketSchemeForEnvironment 方法
if grep -q "Converting URL scheme" lib/features/chat/data/services/websocket_chat_service_v2.dart; then
    echo -e "${GREEN}✅${NC} WebSocket协议转换修复已应用"
else
    echo -e "${RED}❌${NC} WebSocket协议转换修复未找到"
    exit 1
fi

# 检查调试日志
if grep -q "Original baseUrl:" lib/features/chat/data/services/websocket_chat_service_v2.dart; then
    echo -e "${GREEN}✅${NC} 调试日志已添加"
else
    echo -e "${RED}❌${NC} 调试日志未找到"
    exit 1
fi

echo ""
echo -e "${BLUE}2. 重新编译应用...${NC}"
echo "----------------------------------------"

# 停止旧应用
echo "停止旧应用..."
adb shell am force-stop com.example.sparkle > /dev/null 2>&1

# 清理构建缓存
echo "清理构建缓存..."
flutter clean > /dev/null 2>&1

# 获取依赖
echo "获取依赖..."
flutter pub get > /dev/null 2>&1

echo -e "${GREEN}✅${NC} 编译准备完成"
echo ""

echo -e "${BLUE}3. 安装应用到模拟器...${NC}"
echo "----------------------------------------"

# 检查模拟器是否运行
if ! adb devices | grep -q "device$"; then
    echo -e "${RED}❌${NC} Android模拟器未运行，请先启动模拟器"
    exit 1
fi

# 安装应用
flutter install > /tmp/flutter_install.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC} 应用安装成功"
else
    echo -e "${RED}❌${NC} 应用安装失败，查看日志："
    cat /tmp/flutter_install.log
    exit 1
fi

echo ""
echo -e "${BLUE}4. 清除应用数据（重要！）...${NC}"
echo "----------------------------------------"

# 清除应用数据以删除旧的token
adb shell pm clear com.example.sparkle > /dev/null 2>&1

echo -e "${GREEN}✅${NC} 应用数据已清除（旧token已删除）"
echo ""

echo -e "${BLUE}5. 启动应用...${NC}"
echo "----------------------------------------"

adb shell am start -n com.example.sparkle/.MainActivity > /dev/null 2>&1

echo -e "${GREEN}✅${NC} 应用已启动"
echo ""

echo -e "${BLUE}6. 监控日志（Ctrl+C退出）...${NC}"
echo "----------------------------------------"

echo -e "${YELLOW}📝 请在应用中重新登录，然后观察以下日志：${NC}"
echo ""
echo "✓ 应该看到: 📍 Original baseUrl: ws://10.0.2.2:8080"
echo "✓ 应该看到: 📍 Effective WebSocket URL: ws://10.0.2.2:8080"
echo "✓ 应该看到: ✅ WebSocket connected"
echo "✗ 不应该看到: ❌ Connection error: ...401"
echo ""

# 监控Flutter日志
adb logcat -c  # 清除旧日志
adb logcat | grep --line-buffered -E "(flutter|sparkle)" | while read line; do
    # 高亮关键日志
    if echo "$line" | grep -q "Original baseUrl:"; then
        echo -e "${BLUE}$line${NC}"
    elif echo "$line" | grep -q "Effective WebSocket URL:"; then
        echo -e "${GREEN}$line${NC}"
    elif echo "$line" | grep -q "WebSocket connected"; then
        echo -e "${GREEN}$line${NC}"
    elif echo "$line" | grep -q "401"; then
        echo -e "${RED}$line${NC}"
    elif echo "$line" | grep -q "Converting URL scheme"; then
        echo -e "${YELLOW}$line${NC}"
    else
        echo "$line"
    fi
done
