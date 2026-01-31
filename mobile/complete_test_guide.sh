#!/bin/bash

# Sparkle 完整测试指南
# 使用方法: ./complete_test_guide.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 Sparkle 完整测试流程${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ========================================
# 步骤1: 环境检查
# ========================================
echo -e "${BLUE}步骤1: 环境检查${NC}"
echo "----------------------------------------"

# 检查ADB
export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"

if ! command -v adb &> /dev/null; then
    echo -e "${RED}❌ adb 未找到${NC}"
    echo "请确保Android SDK已安装"
    exit 1
fi
echo -e "${GREEN}✅${NC} adb 已找到"

# 检查模拟器
DEVICE_COUNT=$(adb devices | grep -c "device$")
if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️${NC} Android模拟器未运行"
    echo ""
    echo "请先启动模拟器："
    echo "  1. 打开Android Studio"
    echo "  2. Tools → Device Manager → 启动模拟器"
    echo ""
    echo "或使用命令行："
    echo "  flutter emulators --launch <emulator_id>"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅${NC} 模拟器正在运行"

# 检查Flutter
if ! command -v flutter &> /dev/null; then
    echo -e "${RED}❌ flutter 未找到${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} flutter 已找到"

# 检查Docker服务
if ! docker ps &> /dev/null; then
    echo -e "${RED}❌ Docker 未运行${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} Docker 已运行"

echo ""
echo -e "${GREEN}✅✅✅ 所有环境检查通过！${NC}"
echo ""

# ========================================
# 步骤2: 代码修复确认
# ========================================
echo -e "${BLUE}步骤2: 代码修复确认${NC}"
echo "----------------------------------------"

cd /Users/a/code/sparkle-flutter/mobile

# 检查WebSocket协议转换修复
if grep -q "Converting URL scheme" lib/features/chat/data/services/websocket_chat_service_v2.dart; then
    echo -e "${GREEN}✅${NC} WebSocket协议转换修复已应用"
else
    echo -e "${RED}❌${NC} WebSocket协议转换修复未找到！"
    echo "请确保代码已更新到最新版本"
    exit 1
fi

# 检查401错误处理修复
if grep -q "401 Authentication error detected" lib/features/chat/data/services/websocket_chat_service_v2.dart; then
    echo -e "${GREEN}✅${NC} 401自动刷新修复已应用"
else
    echo -e "${RED}❌${NC} 401自动刷新修复未找到！"
    exit 1
fi

echo ""

# ========================================
# 步骤3: 应用重新部署
# ========================================
echo -e "${BLUE}步骤3: 应用重新部署${NC}"
echo "----------------------------------------"

# 停止应用
echo "1️⃣  停止旧应用..."
adb shell am force-stop com.example.sparkle > /dev/null 2>&1
echo -e "   ${GREEN}✅${NC} 已停止"

# 清除数据（重要！删除旧token）
echo "2️⃣  清除应用数据（删除过期token）..."
adb shell pm clear com.example.sparkle > /dev/null 2>&1
echo -e "   ${GREEN}✅${NC} 已清除"

# 清理构建
echo "3️⃣  清理构建缓存..."
flutter clean > /dev/null 2>&1
echo -e "   ${GREEN}✅${NC} 已清理"

# 获取依赖
echo "4️⃣  获取依赖..."
flutter pub get > /dev/null 2>&1
echo -e "   ${GREEN}✅${NC} 完成"

# 编译安装
echo "5️⃣  编译并安装到模拟器..."
flutter install > /tmp/flutter_install.log 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}❌${NC} 安装失败！"
    echo "查看错误日志:"
    cat /tmp/flutter_install.log
    exit 1
fi
echo -e "   ${GREEN}✅${NC} 安装成功"

echo ""

# ========================================
# 步骤4: 启动应用并监控日志
# ========================================
echo -e "${BLUE}步骤4: 启动应用并监控日志${NC}"
echo "----------------------------------------"

echo "启动应用..."
adb shell am start -n com.example.sparkle/.MainActivity > /dev/null 2>&1
echo -e "${GREEN}✅${NC} 应用已启动"
echo ""

echo -e "${YELLOW}📝 重要提示：${NC}"
echo "1. 请在模拟器中打开应用"
echo "2. 点击登录按钮（使用任意账号）"
echo "3. 登录成功后，发送一条聊天消息"
echo ""
echo "观察以下日志来验证修复："
echo "  ✅ 应该看到: 📍 Original baseUrl: ws://10.0.2.2:8080"
echo "  ✅ 应该看到: 📍 Effective WebSocket URL: ws://10.0.2.2:8080"
echo "  ✅ 应该看到: ✅ WebSocket connected"
echo "  ✅ 应该看到: 📤 Sent: ..."
echo "  ✗ 不应该看到: ❌ Connection error: ...401"
echo ""
echo -e "${BLUE}========================================${NC}"
echo "开始监控日志（Ctrl+C退出）..."
echo -e "${BLUE}========================================${NC}"
echo ""

# 清除旧日志
adb logcat -c > /dev/null 2>&1

# 监控日志并高亮关键信息
adb logcat -v time | grep --line-buffered -E "(flutter|Sparkle)" | while IFS= read -r line; do
    # 去除时间戳和进程信息，只保留内容
    clean_line=$(echo "$line" | sed -E 's/^[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+ [^ ]+ [^ ]+ //')

    # 高亮关键日志
    if echo "$clean_line" | grep -q "Original baseUrl:"; then
        echo -e "${BLUE}🔗 $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Effective WebSocket URL:"; then
        echo -e "${GREEN}🔗 $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Converting URL scheme"; then
        echo -e "${YELLOW}🔄 $clean_line${NC}"
    elif echo "$clean_line" | grep -q "WebSocket connected"; then
        echo -e "${GREEN}✅ $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Sent:"; then
        echo -e "${GREEN}📤 $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Received:"; then
        echo -e "${GREEN}📥 $clean_line${NC}"
    elif echo "$clean_line" | grep -q "401"; then
        echo -e "${RED}⚠️ $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Connection error"; then
        echo -e "${RED}❌ $clean_line${NC}"
    elif echo "$clean_line" | grep -q "Token refreshed"; then
        echo -e "${BLUE}🔑 $clean_line${NC}"
    else
        echo "$clean_line"
    fi
done
