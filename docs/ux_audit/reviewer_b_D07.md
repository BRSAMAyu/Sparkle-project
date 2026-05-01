# Reviewer B — D07: 设置/隐私控制——用户能控制数据流向吗
Timestamp: 2026-04-26T11:45:00+08:00
Chain Index: 32 (Round 4 — E-chain audit)

## Chain Flow Summary
用户隐私控制涉及三层：(1) Mobile 设置页 `transparency_settings_screen.dart` 提供全局 transparency toggle 和"纯净模式"（隐藏卡片），但无 per-feature 数据收集开关；(2) Backend `aurora/privacy.py` 提供 PII 红脱（email/phone/CN ID/bank card），但只在 prompt 级别工作，不控制数据收集；(3) Kill switch（`kill_switch.py`）是管理员 tri-state 控制（off/shadow/live），用户无法自行切换。`context_manager.py` 收集 6 维上下文（calendar/social/galaxy/preferences/error/achievement）时不检查用户隐私偏好。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`mobile/lib/features/settings/presentation/screens/transparency_settings_screen.dart` + `backend/app/core/context_manager.py`**: 用户无法按维度控制数据收集。Transparency settings 只有全局 toggle（transparency enabled/disabled）和纯净模式（隐藏 UI 卡片），无 per-feature 隐私开关（如"禁止 Aurora 读取我的日历"、"禁止 Aurora 看到社交数据"、"禁止收集学习行为数据"）。Expected: 用户能选择哪些数据流入 Aurora prompt。Actual: 用户只能全局开关 transparency（UI 展示层），不影响后端数据收集。Context manager 的 `_get_calendar_context`、`_get_social_context_v1` 等方法不检查用户 preference，始终收集并返回数据（仅受 kill switch 控制）。Kill switch 是管理员设置（Redis/环境变量），用户无法操作。Evidence: `transparency_settings_screen.dart` 仅有 `enabled` 和 `pureModeEnabled` 两个 toggle；`context_manager.py` 的 calendar/social/galaxy 收集方法无 preference 检查。

## Minor Issues 🟢
**`backend/app/aurora/privacy.py:24-30`**: PII 红脱仅覆盖 4 种类型（email/phone/CN ID/bank card），不覆盖姓名、学校名、住址等。但这些通常不直接出现在 prompt 中（由 structured data 传入），影响有限。

## Working Well ✅
- **`backend/app/aurora/privacy.py:24-30`**: PII 红脱实现正确——正则匹配 email/phone/CN ID/bank card，替换为 `[REDACTED_*]` 标记。
- **`backend/app/core/kill_switch.py:27-65`**: Tri-state 实现完善——off/shadow/live 三态，normalize_mode 夹值，mode_value 数值化（0/1/2），Prometheus gauge 暴露。
- **`kill_switch.py:95-116`**: `read_mode` 有 Redis fallback → settings fallback → fallback_mode 三级降级。
- **`backend/app/orchestration/prompts.py:3276`**: Stage33 social mode 正确检查 kill switch（D08 发现默认 shadow）。
- **`backend/app/core/context_manager.py:516`**: Calendar context 有 kill switch 检查。

## Files Examined
- `mobile/lib/features/settings/presentation/screens/transparency_settings_screen.dart` (lines 1-80)
- `backend/app/aurora/privacy.py` (lines 17-33)
- `backend/app/core/kill_switch.py` (lines 10-116)
- `backend/app/core/context_manager.py` (lines 516, 295-302, 413-420)

## Confidence: High — 用户隐私控制缺失已通过 mobile settings 和 context_manager grep 确认。
