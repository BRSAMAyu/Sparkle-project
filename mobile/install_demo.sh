#!/bin/bash
# 真机演示安装脚本
# 用于安装app到真机并配置正确的后端IP

# 获取Mac的IP地址
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

if [ -z "$MAC_IP" ]; then
    echo "❌ 无法获取Mac的IP地址"
    exit 1
fi

echo "🔧 检测到Mac IP: $MAC_IP"
echo "📱 将安装app并连接到后端: http://$MAC_IP:8080"
echo ""

# 检测设备类型
DEVICE_ID=$(flutter devices | grep -v "Wireless" | grep -m 1 -oE "[a-z0-9]{12,}")

if [ -z "$DEVICE_ID" ]; then
    echo "❌ 未检测到连接的设备"
    echo "请确保已连接真机或模拟器"
    flutter devices
    exit 1
fi

echo "✅ 检测到设备: $DEVICE_ID"
echo ""
echo "🚀 开始构建并安装..."

# 构建并安装，指定API_BASE_URL
flutter build apk --debug \
  --dart-define=API_BASE_URL=http://$MAC_IP:8080 \
  --dart-define=IOS_DEVICE_URL=http://$MAC_IP:8080 \
  --dart-define=ANDROID_DEVICE_URL=http://$MAC_IP:8080

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo ""
echo "📲 安装到设备..."

flutter install --debug -d $DEVICE_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 安装成功！"
    echo ""
    echo "📋 测试清单："
    echo "1. 点击「演示账号登录」"
    echo "2. 确认看到数据库中的真实数据（42个任务、11个胶囊等）"
    echo "3. 测试LLM聊天功能是否正常"
    echo ""
    echo "🔍 如果看不到数据，请检查："
    echo "- 后端是否在 http://$MAC_IP:8080 运行"
    echo "- 数据库中chat_test账号是否有数据"
    echo "- App日志中的API请求地址"
else
    echo "❌ 安装失败"
    exit 1
fi
