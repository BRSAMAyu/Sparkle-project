#!/bin/bash

# ccsw: Claude Code Switcher
SETTINGS_FILE="$HOME/.claude/settings.json"
CLAUDE_JSON="$HOME/.claude.json"

# API Keys
MIMO_API_KEY="sk-cs8vwdveohdg59yv88gsw9q13nnmr0zwwj6rgztt9yak22i4"
DEEPSEEK_API_KEY="sk-4b5e3a76c151494cb79b04e6cb4ecfd3"
YINLI_API_KEY="sk-hvB4UdkdoX6PrCPopBa9IozMhbeYNIG1belcVqdRAJnOFp1D"
GLM_API_KEY="e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt"
GEMINI_API_KEY="AIzaSyCW0TamEl0p2z7C8Bl_U6zlpPOX8G6Al_Q"

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo "错误: 未找到 jq 命令，请先安装 jq (例如: brew install jq)"
    exit 1
fi

show_usage() {
    echo "用法: ccsw [选项]"
    echo "  m / mimo:    切换到 MiMo API (mimo-v2-flash)"
    echo "  d / deepseek:切换到 DeepSeek 官方 Anthropic 兼容 API (deepseek-chat)"
    echo "  r / reasoner:切换到 DeepSeek Reasoner API (deepseek-reasoner)"
    echo "  y / yinli:   切换到引力云 API (yinli.one)"
    echo "  g / glm:      切换到智谱清言 API (open.bigmodel.cn)"
    echo "  gm / gemini:  切换到 Google Gemini API (gemini-1.5-pro)"
    echo "  g2 / gemini2: 切换到 Google Gemini 2.0 Flash (gemini-2.0-flash-exp)"
    echo "  g3p / gemini3p: 切换到 Google Gemini 3.0 Pro (gemini-3.0-pro)"
    echo "  g3f / gemini3f: 切换到 Google Gemini 3.0 Flash (gemini-3.0-flash)"
    echo "  n / native:  切换回 Claude 原生 API"
}

update_thinking_mode() {
    local enabled=$1
    if [ -f "$CLAUDE_JSON" ]; then
        jq ".alwaysThinkingEnabled = $enabled | .thinking = $enabled" "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    fi
}

start_litellm() {
    local model=$1
    echo "正在配置 LiteLLM 代理 ($model)..."
    
    # Check if litellm is installed AND if the proxy dependencies (backoff) are present
    if ! command -v litellm &> /dev/null || ! python3 -c "import backoff" 2>/dev/null; then
        echo "未检测到完整 LiteLLM 环境 (缺少 proxy 依赖)，正在安装..."
        pip install 'litellm[proxy]'
    fi

    # Kill existing litellm instances
    pkill -f litellm || true
    
    echo "启动 LiteLLM..."
    # Start in background, detached
    # Passing API key via environment variable as CLI argument is not supported
    export GEMINI_API_KEY="$GEMINI_API_KEY"
    
    # Force unset DB related env vars to prevent LiteLLM from trying to connect to them (e.g. Prisma errors)
    # Using 'env -u' to ensure they are removed from the child process environment
    
    # Run in a completely isolated directory to avoid picking up any .env files
    LITELLM_RUN_DIR="/tmp/litellm_isolated_run"
    rm -rf "$LITELLM_RUN_DIR"
    mkdir -p "$LITELLM_RUN_DIR"
    cd "$LITELLM_RUN_DIR"
    
    # Use 'env -i' and also ensure no .env file exists in the current or parent dirs of the process
    (
        LITELLM_PATH=$(command -v litellm)
        # Force ignore all potential DB env vars and any other problematic ones
        # Using a heredoc to run a clean python script that unsets and then calls litellm might be safer
        # but let's try this first. We explicitly clear out DATABASE_URL in the env -i call.
        
        # FINAL STRIKE: We define our own config file that is empty to force litellm into a clean state
        CONFIG_FILE="/tmp/litellm_config_clean.yaml"
        echo "model_list: []" > "$CONFIG_FILE"

        nohup env -i \
            HOME="$HOME" \
            PATH="$PATH" \
            USER="$USER" \
            GEMINI_API_KEY="$GEMINI_API_KEY" \
            LITELLM_LOG=INFO \
            "$LITELLM_PATH" --model "$model" --port 4000 --config "$CONFIG_FILE" > /tmp/litellm.log 2>&1 &
    )
    
    # Return to original directory
    cd - > /dev/null
    
    # Wait for it to initialize
    sleep 2
    
    if pgrep -f "litellm" > /dev/null; then
        echo "✅ LiteLLM 已在后台启动 (PID: $(pgrep -f litellm | head -n 1))"
    else
        echo "❌ LiteLLM 启动失败，请检查日志: /tmp/litellm.log"
    fi
}

switch_to_mimo() {
    echo "正在切换到 MiMo API (mimo-v2-flash)..."

    jq --arg key "$MIMO_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://api.xiaomimimo.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2-flash",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "mimo-v2-flash",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2-flash"
    } | .alwaysThinkingEnabled = true' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode true

    echo "✅ 已切换到 MiMo API (Thinking mode 已自动启用)。"
}

switch_to_deepseek() {
    echo "正在切换到 DeepSeek 官方 API (deepseek-chat)..."

    jq --arg key "$DEEPSEEK_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-chat",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-chat",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-chat",
        "ANTHROPIC_MODEL": "deepseek-chat",
        "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-chat",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已切换到 DeepSeek 官方 API (Thinking mode 已自动禁用)。"
}

switch_to_deepseek_reasoner() {
    echo "正在切换到 DeepSeek Reasoner API (deepseek-reasoner)..."

    jq --arg key "$DEEPSEEK_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-reasoner",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-reasoner",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-reasoner",
        "ANTHROPIC_MODEL": "deepseek-reasoner",
        "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-reasoner",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = true' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode true

    echo "✅ 已切换到 DeepSeek Reasoner API (Thinking mode 已自动启用)。"
}

switch_to_yinli() {
    echo "正在切换到引力云 API (yinli.one)..."

    jq --arg key "$YINLI_API_KEY" '.env = {
        "ANTHROPIC_BASE_URL": "https://yinli.one",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已切换到引力云 API (可使用 /model 切换模型)。"
}

switch_to_glm() {
    echo "正在切换到智谱清言 GLM API (open.bigmodel.cn)..."

    jq --arg key "$GLM_API_KEY" '.env = {
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
        "API_TIMEOUT_MS": "3000000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已切换到智谱清言 GLM API。"
}

switch_to_gemini() {
    echo "正在切换到 Google Gemini API (gemini-1.5-pro)..."
    start_litellm "gemini/gemini-1.5-pro"
    
    # 假设使用本地 LiteLLM 代理，默认端口 4000
    # LiteLLM 将作为 Anthropic 兼容服务器
    jq --arg key "sk-any-token" '.env = {
        "ANTHROPIC_BASE_URL": "http://localhost:4000",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini/gemini-1.5-pro",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini/gemini-1.5-pro",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini/gemini-1.5-flash",
        "ANTHROPIC_MODEL": "gemini/gemini-1.5-pro",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini/gemini-1.5-flash",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 1.5 Pro (http://localhost:4000)。"
}

switch_to_gemini_2() {
    echo "正在切换到 Google Gemini 2.0 Flash API (gemini-2.0-flash-exp)..."
    start_litellm "gemini/gemini-2.0-flash-exp"
    
    # 假设使用本地 LiteLLM 代理，默认端口 4000
    # LiteLLM 将作为 Anthropic 兼容服务器
    jq --arg key "sk-any-token" '.env = {
        "ANTHROPIC_BASE_URL": "http://localhost:4000",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini/gemini-2.0-flash-exp",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini/gemini-2.0-flash-exp",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini/gemini-2.0-flash-exp",
        "ANTHROPIC_MODEL": "gemini/gemini-2.0-flash-exp",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini/gemini-2.0-flash-exp",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 2.0 Flash (http://localhost:4000)。"
}

switch_to_gemini_3_pro() {
    echo "正在切换到 Google Gemini 3.0 Pro API (gemini-3-pro-preview)..."
    start_litellm "gemini/gemini-3-pro-preview"
    
    jq --arg key "sk-any-token" '.env = {
        "ANTHROPIC_BASE_URL": "http://localhost:4000",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini/gemini-3-pro-preview",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini/gemini-3-pro-preview",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini/gemini-3-flash-preview",
        "ANTHROPIC_MODEL": "gemini/gemini-3-pro-preview",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini/gemini-3-flash-preview",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 3.0 Pro (gemini-3-pro-preview) (http://localhost:4000)。"
}

switch_to_gemini_3_flash() {
    echo "正在切换到 Google Gemini 3.0 Flash API (gemini-3-flash-preview)..."
    start_litellm "gemini/gemini-3-flash-preview"
    
    jq --arg key "sk-any-token" '.env = {
        "ANTHROPIC_BASE_URL": "http://localhost:4000",
        "ANTHROPIC_AUTH_TOKEN": $key,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini/gemini-3-flash-preview",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini/gemini-3-flash-preview",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini/gemini-3-flash-preview",
        "ANTHROPIC_MODEL": "gemini/gemini-3-flash-preview",
        "ANTHROPIC_SMALL_FAST_MODEL": "gemini/gemini-3-flash-preview",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
    } | .alwaysThinkingEnabled = false' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    jq '.hasCompletedOnboarding = true' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" && mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
    update_thinking_mode false

    echo "✅ 已配置为 Gemini 3.0 Flash (gemini-3-flash-preview) (http://localhost:4000)。"
}

switch_to_native() {
    echo "正在切换到 Claude 原生 API..."

    jq 'del(.env)' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    echo "✅ 已切换到 Claude 原生 API。"
}

case "$1" in
    m|mimo)
        switch_to_mimo
        ;;
    d|deepseek)
        switch_to_deepseek
        ;;
    r|reasoner)
        switch_to_deepseek_reasoner
        ;;
    y|yinli)
        switch_to_yinli
        ;;
    g|glm)
        switch_to_glm
        ;;
    gm|gemini)
        switch_to_gemini
        ;;
    g2|gemini2)
        switch_to_gemini_2
        ;;
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
