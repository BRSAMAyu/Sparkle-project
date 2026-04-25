# Reviewer B — C16: 导航死路检查（完成页/庆祝页/建模完成后）
Timestamp: 2026-04-25T21:20:00Z
Chain Index: 7

## Chain Flow Summary
检查三个关键 "完成态" 页面的导航安全性：

**Sprint Completion**（`sprint_completion_screen.dart`）：冲刺完成后显示庆祝动画+confetti。3 个 CTA："分享"、"记录考试结果"（push 到 `/exam-sprint/review`）、"查看学习档案"（`context.go()` 到 portfolio）。左上角关闭按钮使用 `RouteResilience.popOrGo()` 智能导航，回退到 portfolio。PopScope 处理系统返回键。

**Milestone Celebration**（`milestone_celebration_screen.dart`）：成就解锁后显示。2 个 CTA："分享这一刻"（系统分享面板）、"继续学习"（→ `/home`）。关闭按钮 → `/achievements`。RouteResilienceScope 回退到 achievements。三个出口，不会困住用户。

**Modeling Chat**（`modeling_chat_screen.dart`）：建模对话完成后自动触发计划生成（75s 超时）。成功时自动 `context.go()` 到 `/plans/{planId}`。错误时显示 "重试生成计划" 和 "稍后再说"（→ `/home` 或 `/chat`）。"跳过" 按钮在 AppBar 右上角。RouteResilienceScope 回退到 `/onboarding/persona`（见 Critical Issue）。

## Critical Issues 🔴

**`modeling_chat_screen.dart:80-82` — RouteResilienceScope 回退路由错误 → 用户被送回 onboarding**
- Expected: 系统返回键回退到 `/home`（与 "稍后再说" 行为一致）
- Actual: `RouteResilienceScope(fallbackRoute: UserRoutes.personaOnboarding)` — 回退到 `/onboarding/persona`。建模完成后如果用户按系统返回键（而非点 "稍后再说"），会被送回 onboarding 页面而非首页，造成困惑或循环
- Evidence: `modeling_chat_screen.dart:80-82` `fallbackRoute: UserRoutes.personaOnboarding`；对比 `_finish()` 方法（lines 615-625）导航到 `/home` 或 `/chat`
- Impact: 新用户完成建模后按返回键，回到 onboarding 而非进入主应用。修复仅需改一行：`fallbackRoute: HomeRoutes.home`

## Major Issues 🟡

**`sprint_completion_screen.dart` — 无 "返回首页" CTA**
- Expected: 完成冲刺后可直接返回首页
- Actual: 仅有 "分享"、"记录考试结果"（→ review）、"查看学习档案"（→ portfolio）。关闭按钮回退到 portfolio 而非 home。用户需额外步骤才能回到首页
- Evidence: lines 300-316 三个按钮均不导航到 home；`_closeScreen()` line 161 回退到 `PlanRoutes.learningPortfolio`

**`modeling_chat_screen.dart:649-662` — 计划生成失败后无自动超时恢复**
- Expected: 计划生成失败后，一段时间后自动恢复到可用状态
- Actual: 错误状态要求用户手动点击 "重试" 或 "稍后再说"。如果用户不操作，界面停留在错误状态无超时退出机制
- Evidence: lines 872-944 错误状态仅有 "重试生成计划" 和 "稍后再说" 按钮，无 Timer 或自动跳转

## Minor Issues 🟢

**`sprint_completion_screen.dart` — 庆祝动画后无自动过渡**
- Confetti 动画播放完毕后界面静止，用户可能出现 "然后呢？" 的短暂困惑。没有自动跳转到下一个逻辑页面（如学习档案或首页）

## Working Well ✅

1. **三个页面均有 RouteResilienceScope** — 即使导航栈为空也有回退路由，不会白屏
2. **三个页面均有明确的关闭/退出按钮** — 左上角 close icon，不会困住用户
3. **Sprint completion 使用 RouteResilience.popOrGo()** — 智能判断：有栈 pop，无栈 go fallback
4. **Milestone celebration "继续学习" → /home** — 清晰的下一步引导
5. **Modeling 自动导航到计划页** — 成功路径无摩擦，用户无需手动操作
6. **PopScope 处理系统返回键** — 三个页面都正确处理了 Android 返回手势

## Files Examined

- `mobile/lib/features/plan/presentation/screens/sprint_completion_screen.dart` (lines 157-163, 165-178, 186-189, 192-194, 214-225, 300-317)
- `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart` (lines 218-230, 243-247, 275-293)
- `mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart` (lines 80-82, 87-92, 181-197, 560-625, 649-662, 741, 872-944)
- `mobile/lib/app/routes.dart` (route definitions for achievements, modeling, plans)

## Confidence: High — 三个页面全部读取，导航目标、按钮行为、回退路由通过代码确认。Critical bug 通过比对 RouteResilienceScope fallback 和 _finish() 方法确认
