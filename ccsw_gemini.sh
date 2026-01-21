#!/bin/bash

# ccsw: Claude Code Switcher - Gemini Only Edition
SETTINGS_FILE="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"

# Gemini API Key
GEMINI_API_KEY="AIzaSyCW0TamEl0p2z7C8Bl_U6zlpPOX8G6Al_Q"

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo "错误: 未找到 jq 命令，请先安装 jq (例如: brew install jq)"
    exit 1
fi

show_usage() {
    echo "用法: ccsw [选项]"
    echo "  g3p / gemini3p: 切换到 Google Gemini 3 Pro (gemini-3-pro-preview)"
    echo "  g3f / gemini3f: 切换到 Google Gemini 3 Flash (gemini-3-flash-preview)"
    echo "  n / native:     切换回 Claude 原生 API"
}

update_thinking_mode() {
    local enabled=$1
    if [ -f "$CLAUDE_JSON" ]; then
        jq ".alwaysThinkingEnabled = $enabled | .thinking = $enabled" "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    fi
}

switch_to_gemini_3_pro() {
    echo "正在切换到 Google Gemini 3 Pro (gemini-3-pro-preview)..."

    jq --arg key "$GEMINI_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini-3-pro-preview",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini-3-pro-preview",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini-3-pro-preview",
        "ANTHROPIC_MODEL": "gemini-3-pro-preview",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini-3-pro-preview",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 3 Pro 直连模式 (gemini-3-pro-preview)。"
    echo "⚠️  注意：使用的是 Google 官方的 OpenAI 兼容端点。"
}

switch_to_gemini_3_flash() {
    echo "正在切换到 Google Gemini 3 Flash (gemini-3-flash-preview)..."

    jq --arg key "$GEMINI_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini-3-flash-preview",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini-3-flash-preview",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini-3-flash-preview",
        "ANTHROPIC_MODEL": "gemini-3-flash-preview",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini-3-flash-preview",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 3 Flash 直连模式 (gemini-3-flash-preview)。"
    echo "⚠️  注意：使用的是 Google 官方的 OpenAI 兼容端点。"
}

switch_to_native() {
    echo "正在切换到 Claude 原生 API..."

    jq 'del(.env)' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    echo "✅ 已切换到 Claude 原生 API。"
}

case "$1" in
    g3p|gemini3p)
        switch_to_gemini_3_pro
        ;;
    g3f|gemini3f)
        switch_to_gemini_3_flash
        ;;
    n|native)
        switch_to_native
        ;;
    *)
        show_usage
        exit 1
        ;;
esac