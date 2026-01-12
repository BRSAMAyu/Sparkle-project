# Claude Code API 配置对齐指南

此指南旨在说明 `ccsw` 脚本如何将 Claude Code CLI 与不同的 API 后端进行对齐配置。

## 1. 设计逻辑
Claude Code CLI 通过修改 JSON 配置文件实现无需手动编辑的“一键切换”：
- `~/.claude/settings.json`: 存储环境级别变量 (`env`)。
- `~/.claude.json`: 存储全局状态（如 Thinking mode 开关）。

## 2. 配置对照表

| 配置项 | 原生 (Native) | MiMo (Flash) | DeepSeek (Official) |
| :--- | :--- | :--- | :--- |
| **API Base URL** | 默认 (Anthropic) | `https://api.xiaomimimo.com/anthropic` | `https://api.deepseek.com/anthropic` |
| **Auth Token** | 系统存储 | MiMo Key | DeepSeek Key |
| **默认模型** | 系统自动分配 | `mimo-v2-flash` | `deepseek-chat` |
| **Thinking 模式** | 支持 (可开关) | **强制关闭** | **强制关闭** |
| **稳定性备注** | 极高 | 高 (具备容错) | 一般 (严格校验) |

## 3. 模式说明

### 3.1 MiMo 模式 (`ccsw m`)
使用 MiMo 提供的增强端点。该端点对 Claude Code 的兼容性较好，能够自动处理一些非法的空内容消息块，适合日常高频使用。

### 3.2 DeepSeek 官方模式 (`ccsw d`)
直接连接 DeepSeek 官方 Anthropic 兼容端点。
> **⚠️ 警告**: 官方端点对消息格式要求极严。若在复杂 Session 中遇到 `400 (all messages must have non-empty content)` 错误，说明当前的上下文包含空块，建议切换至 MiMo 模式。

## 4. 使用指令汇总

在终端任何位置输入以下极简指令：

- **`ccsw d`**: 切换到 **DeepSeek 官方 API**。
- **`ccsw m`**: 切换到 **MiMo 模式 (Flash)**。
- **`ccsw n`**: 切换回 Claude 原生模式。

---
*注：脚本位于 `/usr/local/bin/ccsw`，已自动配置到系统 PATH。*