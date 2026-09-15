#!/bin/bash
#
# setup_flutter_mirrors.sh
# Configure Flutter/Dart mirrors for China network
#
# This script adds the following environment variables to your shell config:
# - PUB_HOSTED_URL: Dart package mirror
# - FLUTTER_STORAGE_BASE_URL: Flutter SDK storage mirror
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Flutter/Dart Mirror Setup for China Network ===${NC}"
echo ""

# Determine shell config file
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.bash_profile"
    fi
else
    echo -e "${YELLOW}Warning: Unknown shell. Please manually add the following to your shell config:${NC}"
    echo ""
    echo 'export PUB_HOSTED_URL="https://pub.flutter-io.cn"'
    echo 'export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"'
    exit 0
fi

echo "Shell config file: $SHELL_RC"
echo ""

# Check if already configured
if grep -q "PUB_HOSTED_URL" "$SHELL_RC" 2>/dev/null; then
    echo -e "${YELLOW}Flutter mirrors already configured in $SHELL_RC${NC}"
    echo "Current configuration:"
    grep "PUB_HOSTED_URL\|FLUTTER_STORAGE_BASE_URL" "$SHELL_RC"
    echo ""
    read -p "Do you want to update the configuration? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping..."
        exit 0
    fi
    # Remove old entries
    sed -i.bak '/PUB_HOSTED_URL/d' "$SHELL_RC" 2>/dev/null || true
    sed -i.bak '/FLUTTER_STORAGE_BASE_URL/d' "$SHELL_RC" 2>/dev/null || true
    # Remove empty Flutter mirror comment lines
    sed -i.bak '/# Flutter\/Dart mirrors for China/d' "$SHELL_RC" 2>/dev/null || true
fi

# Add new configuration
echo "" >> "$SHELL_RC"
echo "# Flutter/Dart mirrors for China network (added by setup_flutter_mirrors.sh)" >> "$SHELL_RC"
echo 'export PUB_HOSTED_URL="https://pub.flutter-io.cn"' >> "$SHELL_RC"
echo 'export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"' >> "$SHELL_RC"

echo -e "${GREEN}Configuration added to $SHELL_RC${NC}"
echo ""
echo "Added:"
echo '  export PUB_HOSTED_URL="https://pub.flutter-io.cn"'
echo '  export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"'
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart your terminal, or run: source $SHELL_RC"
echo "2. Verify: echo \$PUB_HOSTED_URL"
echo "3. Run: cd mobile && flutter pub get"
echo ""
echo -e "${GREEN}Alternative mirrors (if flutter-io.cn is slow):${NC}"
echo "  - Tsinghua:    https://mirrors.tuna.tsinghua.edu.cn/dart-pub"
echo "  - SJTU:        https://mirror.sjtu.edu.cn/dart-pub"
echo "  - Aliyun:      https://mirrors.aliyun.com/dart-pub"
