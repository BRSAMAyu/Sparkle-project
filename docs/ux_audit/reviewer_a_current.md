# Reviewer A — D07: 设置/隐私控制——用户能控制数据流向吗
Timestamp: 2026-04-26T02:25:00+08:00
Chain Index: 13

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。关键验证：(1) `privacy.py` 只有 `redact_pii()` 和 `laplace_noise()` 工具函数，无用户偏好读取；(2) `prompts.py` 中 `privacy` grep 仅命中 kill_switch import（line 39），prompt 组装不检查隐私设置；(3) `planning.py:809` 读取 `privacy_boundaries` 但仅用于 Aurora 建模 tension 过滤；(4) `transparency_settings_screen.dart` 是 AI 透明度 UI 设置，非数据收集控制。

## Chain Flow Summary

审查用户隐私控制能力：用户能否在设置中关闭某项数据收集？关闭后该数据是否真的不再发送到 LLM？kill switch 是否影响对应功能？`backend/app/aurora/privacy.py` 提供 PII 脱敏工具，`backend/app/core/kill_switch.py` 提供三态功能开关，`transparency_settings_screen.dart` 提供 AI 透明度设置，但**三者互不关联**——没有一个统一的"数据收集偏好"系统。

## Critical Issues 🔴

None found.

## Major Issues 🟡

**1. 无统一的用户数据收集偏好系统——PII 脱敏是自动的，但用户无法选择性关闭特定数据流**

现状分析：
- `privacy.py` 的 `redact_pii()` 自动脱敏 email/phone/CN_ID/bank_card（line 24-30），**无需用户设置即生效** — 这是好事
- `kill_switch.py` 提供三态开关（off/shadow/live），但这是**运维工具**，控制的是功能启停，不是用户数据偏好
- `transparency_settings_screen.dart` 控制的是 AI 回答的**展示方式**（透明模式、纯净模式），不是数据收集范围
- `planning.py:809` 的 `privacy_boundaries` 仅用于建模阶段跳过特定 tension 域，不影响 prompt assembly

Expected: 用户应能在设置中看到"我有哪些数据被 AI 使用"并选择性关闭（如"不使用我的日历数据"、"不使用我的社群活动"）。Actual: 没有这样的用户界面。所有数据流由系统自动决定，用户无法干预。

**2. `prompts.py` 不检查任何隐私偏好——所有用户数据无条件进入 prompt assembly**

`prompts.py` 是 prompt 组装的核心文件（3000+ 行）。grep `privacy|privacy_bound|redact` 仅命中 `kill_switch` import（line 39）。这意味着：
- 用户的日历数据（如果 stage40 kill switch 为 live）无条件进入 prompt
- 用户的社群活动（social_signal_bridge）无条件进入 dashboard
- 用户的专注记录无条件进入 context
- 没有任何机制让用户说"不要把我的 X 数据发给 AI"

Expected: prompt assembly 应查询用户偏好，跳过用户关闭的数据维度。Actual: 所有启用的数据维度无条件组装到 prompt。

## Minor Issues 🟢

None found.

## Working Well ✅

**PII 自动脱敏** (`privacy.py:24-30`):
- 自动脱敏 email、手机号、中国身份证号、银行卡号
- 使用正则匹配，覆盖常见格式
- 在 LLM 调用前统一应用

**差分隐私噪声** (`privacy.py:33-56`):
- `laplace_noise()` 实现差分隐私
- epsilon 和 sensitivity 参数可配置
- 用于 mastery 分数等统计值的隐私保护

**Kill switch 三态控制** (`kill_switch.py`):
- off/shadow/live 三态
- Redis 持久化 + settings.py fallback
- Prometheus gauge 暴露状态
- 每个功能独立控制

**Aurora 建模隐私边界** (`planning.py:807-810, 882-883`):
- `privacy_boundaries` 列表可跳过特定建模域
- 匹配到的域被标记为 `status = "dropped"`，不会被追问
- 当前机制存在但前端无 UI 控制它

**AI 透明度设置** (`transparency_settings_screen.dart`):
- 全局开关（enabled/disabled）
- 展示模式选择（折叠悬浮/底部抽屉/仅详情页）
- 纯净模式（隐藏卡片和反馈组件）
- 自动折叠 + 允许单轮关闭

**Profile transparency API** (`backend/app/api/v1/profile_transparency.py`):
- 提供数据使用透明度端点
- 列出各数据类别（focus_sessions、error_book、achievement_signals 等）
- 用户可查看哪些数据被系统使用

## Files Examined

1. `backend/app/aurora/privacy.py` (全文 57 行 — PII redaction + Laplace noise)
2. `backend/app/core/kill_switch.py` (KillSwitchBinding dataclass + read_mode)
3. `backend/app/orchestration/prompts.py` (line 39, grep: no privacy checks in prompt assembly)
4. `backend/app/aurora/runtime_v1/planning.py` (lines 807-810, privacy_boundaries in hard bounds; 882-883, dropped domains)
5. `mobile/lib/features/settings/presentation/screens/transparency_settings_screen.dart` (AI display settings, not data collection)
6. `backend/app/api/v1/profile_transparency.py` (read-only transparency API)
7. `backend/app/services/aurora_stage40_calendar_kill_switch_service.py` (calendar kill switch — ops tool)

## Confidence: High — 系统有隐私保护基础（PII 脱敏、kill switch、差分隐私），但缺少用户可控的数据收集偏好。当前设计是"系统决定一切，用户只能看"模式。profile_transparency API 提供可见性但不提供控制权。
