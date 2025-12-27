# Claude Code API 配置对齐指南

此指南旨在说明 `ccsw` 脚本如何将 Claude Code CLI 与不同的 API 后端（原生、MiMo、DeepSeek、智商隔离模式）进行对齐配置。

## 1. 设计逻辑
Claude Code CLI 主要通过两个文件进行持久化配置：
- `~/.claude/settings.json`: 存储环境级别变量 (`env`) 和工具权限。
- `~/.claude.json`: 存储用户全局状态（如是否完成 onboarding 和 Thinking mode 开关）。

`ccsw` 脚本通过 `jq` 工具精准修改这些 JSON 文件，实现无需手动编辑文件的“一键切换”。

## 2. 配置对照表

| 配置项 | 原生 (Native) | MiMo (Flash) | DeepSeek (Chat) | 智商隔离 (Isolation) |
| :--- | :--- | :--- | :--- | :--- |
| **API Base URL** | 默认 (Anthropic) | `.../anthropic` | `.../anthropic` | `.../anthropic` |
| **Opus 位模型** | 系统自动分配 | `mimo-v2-flash` | `deepseek-chat` | **`deepseek-reasoner`** |
| **Sonnet 位模型** | 系统自动分配 | `mimo-v2-flash` | `deepseek-chat` | **`deepseek-chat`** |
| **Haiku 位模型** | 系统自动分配 | `mimo-v2-flash` | `deepseek-chat` | **`mimo-v2-flash`** |
| **Thinking 模式** | 支持 (可开关) | **强制关闭** | **强制关闭** | **强制关闭** (需手动开启) |
| **超时时间** | 默认 | 默认 | `600000ms` | `600000ms` |
| **流量优化** | 关闭 | 关闭 | `1` (禁用非必要) | `1` (禁用非必要) |

## 3. 模式说明

### 3.1 智商隔离模式 (Isolation)
这是最高效的模式，通过分层调度实现性能与成本的最佳平衡：
- **Haiku (低档)**: 由 `mimo-v2-flash` 担任。负责 `ls`, `cat`, 环境检查等极速任务。
- **Sonnet (中档)**: 由 `deepseek-chat` (V3.2) 担任。负责日常代码编写、补全和常规逻辑。
- **Opus (高档)**: 由 `deepseek-reasoner` (R1) 担任。负责解决疑难 Bug 和架构设计。

### 3.2 Thinking mode 联动
由于非原生后端对 Claude Code 原生“思考块”的处理可能存在兼容性问题，脚本在切换到 MiMo、DeepSeek 或隔离模式时，会**自动将 `Thinking mode` 设为 `false`**。

> **注意**: 如果您在隔离模式下需要 Opus 执行深度思考，请在 CLI 中输入 `/config` 手动开启 Thinking mode，并在完成后关闭，以避免 Haiku 档位报错。

## 4. 使用指令汇总

在终端任何位置输入以下极简指令：

- **`ccsw iso`**: 切换到 **智商隔离模式** (推荐)。
- **`ccsw d`**: 切换到 DeepSeek 模式。
- **`ccsw m`**: 切换到 MiMo 模式。
- **`ccsw n`**: 切换回 Claude 原生模式。

---
*注：脚本位于 `/usr/local/bin/ccsw`，已自动配置到系统 PATH。*