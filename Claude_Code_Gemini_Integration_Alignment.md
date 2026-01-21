# Claude Code Gemini 接入对齐文档

## 1. 项目目标
在 macOS 全局 `ccsw` (Claude Code Switcher) 脚本中集成 Google Gemini 系列模型，实现一键无感切换，并自动处理环境依赖与代理启动。

## 2. 支持模型列表
| 简写命令 | 模型完整 ID | 说明 |
| :--- | :--- | :--- |
| `ccsw gm` | `gemini-1.5-pro` | Gemini 1.5 Pro 稳定版 |
| `ccsw g2` | `gemini-2.0-flash-exp` | Gemini 2.0 Flash 实验版 |
| `ccsw g3p` | `gemini-3-pro-preview` | Gemini 3 Pro 预览版 (最新旗舰) |
| `ccsw g3f` | `gemini-3-flash-preview` | Gemini 3 Flash 预览版 |

## 3. 已实现的技术方案
- **全自动 LiteLLM 启动**：脚本自动检查 `litellm[proxy]` 环境，缺失则自动安装。
- **环境隔离**：使用 `env -i` 启动代理进程，隔离当前项目环境变量。
- **进程管理**：切换模型前自动结束旧的 LiteLLM 进程，确保端口 (4000) 不冲突。
- **配置同步**：自动更新 `~/.claude/settings.json` 和 `~/.claude.json` 以适配本地代理。

## 4. 遇到的问题及解决方案

### 问题 A：LiteLLM 启动失败 (Missing dependency: backoff)
- **现象**：日志提示 `ModuleNotFoundError: No module named 'backoff'`。
- **原因**：默认 `pip install litellm` 不包含代理模式所需的依赖。
- **解决**：修改脚本自动执行 `pip install 'litellm[proxy]'`。

### 问题 B：API Key 配置无效
- **现象**：LiteLLM 报错不支持 `--api_key` 参数。
- **原因**：新版 LiteLLM CLI 仅通过环境变量读取 Key。
- **解决**：在启动命令前显式 `export GEMINI_API_KEY="..."`。

### 问题 C：数据库冲突 (Prisma/DATABASE_URL Error)
- **现象**：日志显示 `Unable to connect to DB. DATABASE_URL found in environment`。
- **原因**：当前项目 `.env` 中的 `DATABASE_URL` 被 LiteLLM 误识别为需要开启数据库日志模式。
- **解决**：使用 `env -i` 强制清空环境变量，并切换到 `/tmp` 目录启动，同时增加空配置文件 `--config`。

### 问题 D：404 错误 (Model Not Found)
- **现象**：`gemini-3.0-pro` 返回 404。
- **原因**：模型名称不符合预览版规范。
- **解决**：更新模型 ID 为 `gemini-3-pro-preview` 和 `gemini-3-flash-preview`。

## 5. 当前状态与后续工作
- [x] 脚本逻辑修复与 Gemini 3 支持。
- [x] 本地环境隔离与自动启动验证。
- [ ] **待处理**：彻底消除日志中的 Prisma 警告（虽然目前不影响基本对话功能，但会导致启动耗时增加）。
- [ ] **待处理**：验证 Gemini 3 预览版在特定地区的 API 可用性。

---
**对齐日期**：2026-01-21
**执行人**：Cline (AI Agent)
