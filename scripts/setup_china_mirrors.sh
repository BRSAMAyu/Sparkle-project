#!/bin/bash
#
# setup_china_mirrors.sh
# One-click setup script for China network mirrors
#
# This script configures mirrors for:
# - Python (pip)
# - Flutter/Dart
# - CocoaPods (macOS only)
#
# Usage: bash scripts/setup_china_mirrors.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Sparkle Project - China Network Mirror Setup              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# 1. Python pip configuration
echo -e "${GREEN}[1/4] Configuring Python pip mirror...${NC}"
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF
echo "   ✅ pip configured to use Aliyun mirror"
echo "      Config file: ~/.pip/pip.conf"
echo ""

# 2. Flutter/Dart environment
echo -e "${GREEN}[2/4] Configuring Flutter/Dart mirrors...${NC}"

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
fi

if [ -n "$SHELL_RC" ]; then
    # Remove old entries if exists
    sed -i.bak '/PUB_HOSTED_URL/d' "$SHELL_RC" 2>/dev/null || true
    sed -i.bak '/FLUTTER_STORAGE_BASE_URL/d' "$SHELL_RC" 2>/dev/null || true
    sed -i.bak '/# Flutter\/Dart mirrors for China/d' "$SHELL_RC" 2>/dev/null || true

    # Add new entries
    echo "" >> "$SHELL_RC"
    echo "# Flutter/Dart mirrors for China network" >> "$SHELL_RC"
    echo 'export PUB_HOSTED_URL="https://pub.flutter-io.cn"' >> "$SHELL_RC"
    echo 'export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"' >> "$SHELL_RC"
    echo "   ✅ Flutter/Dart mirrors added to $SHELL_RC"
else
    echo -e "   ${YELLOW}⚠ Unknown shell. Please manually add:${NC}"
    echo "      export PUB_HOSTED_URL=\"https://pub.flutter-io.cn\""
    echo "      export FLUTTER_STORAGE_BASE_URL=\"https://storage.flutter-io.cn\""
fi
echo ""

# 3. CocoaPods configuration (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${GREEN}[3/4] Configuring CocoaPods...${NC}"

    # Check if CocoaPods is installed
    if command -v pod &> /dev/null; then
        # Remove trunk repo if exists (use CDN instead)
        pod repo remove trunk 2>/dev/null || true
        echo "   ✅ CocoaPods configured to use CDN (cdn.cocoapods.org)"
        echo "      The Podfile already includes CDN source configuration"
    else
        echo -e "   ${YELLOW}⚠ CocoaPods not installed. Skipping...${NC}"
    fi
else
    echo -e "${GREEN}[3/4] Skipping CocoaPods (not macOS)${NC}"
fi
echo ""

# 4. Gradle configuration (already in build.gradle.kts)
echo -e "${GREEN}[4/4] Gradle mirrors...${NC}"
echo "   ✅ Already configured in:"
echo "      - mobile/android/build.gradle.kts (Aliyun Maven)"
echo "      - mobile/android/settings.gradle.kts (Aliyun Maven)"
echo "      - mobile/android/gradle/wrapper/gradle-wrapper.properties (Tencent Cloud)"
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. ${BOLD}Restart your terminal${NC} or run:"
echo "   source $SHELL_RC"
echo ""
echo "2. ${BOLD}Verify Flutter mirrors:${NC}"
echo "   echo \$PUB_HOSTED_URL"
echo "   echo \$FLUTTER_STORAGE_BASE_URL"
echo ""
echo "3. ${BOLD}Install dependencies:${NC}"
echo "   cd mobile && flutter pub get"
echo "   cd mobile/ios && pod install"
echo "   cd mobile/android && ./gradlew build"
echo ""
echo "4. ${BOLD}Install Python dependencies:${NC}"
echo "   pip install -r backend/requirements.txt"
echo "   # Or with uv:"
echo "   uv pip install -r backend/requirements.txt"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Note: Firebase and Google Sign-In require Google servers.${NC}"
echo -e "${YELLOW}Use VPN for first-time download of these dependencies.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
