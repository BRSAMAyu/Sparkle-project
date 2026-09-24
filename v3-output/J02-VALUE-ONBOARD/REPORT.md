# J-02 · Onboarding: Value Before Profile（价值先于画像）落地报告

> 卡：wt282-j02-value-onboard（A 线·V3 剩余卡）｜2026-09-22｜worktree **wt282-j02-value-onboard**（分支同名，基于 main @ e4d795e1）
> 性质：S-M 级产品落地卡。研究依据：`v3-output/A-SPEC8B-ONBOARDING/REPORT.md`（G1/G3/G7 + 改造 #2/#3 + N48/N50）；**不推翻研究任何结论，本卡是其三处采纳项的施工**。
> 范围声明：仅前端（mobile）；auth 守卫安全面零触碰；无 proto/迁移/引擎改动。

---

## 0. 三项落地情况（回执要素①）

| # | 改造 | 状态 | 说明 |
|---|---|---|---|
| a | **首启副标题具象化**（研究改造 #2 / N48） | ✅ 做了 | 两键两语言全换具象文案，零布局改动；A/B 双候选见 §4 |
| b | **persona 进度 resume**（研究改造 #3 / N50 前半） | ✅ 做了 | 步数 + 全部 7 项已填内容 per-user 持久化；恢复钳位；跳过/提交成功清除。比研究最低要求（只存步数）多做内容恢复，因 G7 痛点原文是「已填内容全丢」 |
| c | **注册墙软化**（G1 裁决「改写采纳」的保守档） | ✅ 做了 | 全域硬重定向撤除 + home「继续引导」入口卡；「不动 auth 安全面」遵守——未登录→login、已登录→出 auth 的守卫原样保留 |

**留报告不做**：N49 访客首聊破冰（跨层卡，需引擎 extraContext 配合）、N50 后半 skip 视觉升档（涉及两屏 golden 重录，本卡测试预算已满，建议 V 系列首飞卡捎带）、G5 modeling 回退环（研究已裁「转台账待实测」——注：本卡撤除硬重定向后该环**理论上自然消解**，fallback 到 home 不再被弹回 persona，待首飞确认）。

## 1. 改动清单（回执要素②）

**产品代码（5 文件 + 2 新建）**
| 文件 | 改动 |
|---|---|
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` | welcomeSubtitle、splashSubtitle 换具象文案（N48）；新增 homeOnboardingResumeTitle/Summary/Cta 三键（双语同步） |
| `mobile/lib/l10n/app_localizations*.dart`（3 生成文件） | `flutter gen-l10n` 重生成，diff 仅含本卡键，无格式重排 |
| `mobile/lib/app/routes.dart` | 撤除「非 guest && completed==false → 弹回 persona」全域硬重定向分支（原 217-224）；`isOnModelingChat` 变量随之删除；completed/guest 在 persona 页弹回 home 的分支保留 |
| `mobile/lib/features/home/presentation/widgets/onboarding_resume_card.dart`（新建） | OnboardingResumeCard：可见性守门（已认证 && 非 guest && completed==false；null 未决不可见对齐 M6-07），SparkleCard 内联形制照 GuestConversionCard |
| `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` | 挂载点在 dashboardSections（首目标空态之后）**而非 growthSections**——新注册用户无目标时走 hasNoGoals 分支、growthSections 整体不渲染，挂 growthSections 会错过主受众（与 GuestConversionCard 同款的既有盲区，本卡新卡规避之） |
| `mobile/lib/features/user/presentation/providers/persona_onboarding_draft.dart`（新建） | PersonaOnboardingDraft（8 字段 JSON 模型 + clamp 钳位）+ PersonaOnboardingDraftStore（per-user key `onboarding_persona_draft_$userId`，SharedPreferences.getInstance() 形制照 settings_provider） |
| `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart` | initState 恢复草稿（clamp 后 setState）；所有字段变更统一走 `_onFieldMutated`（预览防抖 + 存稿防抖 400ms）；步进立即落盘；skip 与提交成功清除草稿 |

**测试（3 新建 + 2 修改）**
| 文件 | 内容 |
|---|---|
| `test/features/auth/first_run_value_subtitle_test.dart`（新建，a） | zh/en × 两键含「期末/备考/提分(拿回)/final/point」断言 + 禁回退旧口号 |
| `test/features/user/persona_onboarding_draft_resume_test.dart`（新建，b） | store 往返/损坏 JSON 降级/clamp/clear 四单元 + 屏恢复断点步与已填内容 + 步进即落盘 + skip 清除并进建模访谈 |
| `test/features/home/presentation/widgets/onboarding_resume_card_test.dart`（新建，c） | 注册未完成可见且 CTA 跳 persona / completed 隐藏 / null 未决隐藏 / guest 隐藏（N40 互斥） |
| `test/app/router_smoke_test.dart` | 「未完成引导弹回 persona」测试改写为软墙语义：/home + DashboardScreen 在场 + PersonaOnboardingScreen 不在场 |
| `test/features/home/dashboard_test_harness.dart` | 加 onboardingCompletedProvider 静态 override（钉 completed=true）——防真实 notifier 测试环境落 false 令 ResumeCard 混入存量结构断言 |

**语义红线自查**：注册表单 7 项与 persona 五问零裁减（TV-G3 既辖）；转化卡禁弹窗形制未破；免费闭环行为零变化；诚实性无涉（无数据面）。

## 2. 测试与 analyze（回执要素③）

- 定向测试（单文件单进程，--concurrency=1）：
  - a `first_run_value_subtitle_test.dart`：**+3 全过**；
  - b `persona_onboarding_draft_resume_test.dart`：**+7 全过**（store 单元 4 + 屏 widget 3）；
  - c `onboarding_resume_card_test.dart`：**+5 全过**（可见性三态 + CTA 导航 + guest 互斥）。
- 受影响面回归（与本卡改动直接相邻的存量测试）：
  - `persona_onboarding_submit_feedback_test.dart`：**过**；
  - `router_smoke_test.dart`：+7 -1，失败项 `navigates shell routes…` 在 `/tmp/j02-baseline`（HEAD 克隆）**同样 +7 -1** —— 存量环境性失败，非本卡引入（本卡改写的软墙用例在 +7 内）；
  - `dashboard_screen_structure_test.dart`：+2 -3，失败集与基线 **diff 为空（IDENTICAL_FAILURES）** —— 存量环境性失败。
- `flutter analyze` 改动文件与 `/tmp/j02-baseline`（HEAD 克隆，舰队纪律允许的基线法）逐条比对：routes/dashboard/persona/harness/router_smoke 五个存量文件 **info 集与基线完全同集（仅行号平移）**；四个新建文件（draft store、resume card、三个新测试）**零 issue**。
- arb 双语键同步：gen-l10n 后 diff 干净，zh/en 键集合一致。

## 3. 资源峰值（回执要素④）

- 本卡全程 LIGHT（无模拟器/Gradle/浏览器）；flutter analyze 数轮、flutter pub get ×2（本树 + /tmp 基线克隆）、buf generate ×2（本树 gen/ 缺失需补齐）、定向 flutter test 6 轮（串行单文件单进程）。
- swap 门禁：开工时 free 711M < 1.2G，轮询等待错峰约 10 分钟后门禁开（1251M）；每轮测试前复核。load 全程 <6。

## 4. A/B 候选文案（N48 要求留档，主会话/首飞定稿）

| 键 | A（本卡落地） | B（备选） |
|---|---|---|
| welcomeSubtitle (zh) | 期末备考提分，AI 陪你把该拿的分拿回来 | 期末周，把该拿的分拿回来 |
| welcomeSubtitle (en) | Prep for finals and raise your grade with AI at your side | Finals week: win back every point you can |
| splashSubtitle (zh) | 期末一周，星火陪你备考，把该拿的分拿回来。 | 备考期末，每一分都算数。 |
| splashSubtitle (en) | One week to finals — Sparkle helps you win back every point you deserve. | One week to finals — make every point count. |

## 5. 交接建议（回执要素⑤）

1. **首飞补测**：注册新号走「注册→home（应见继续引导卡）→先聊一轮→回卡进 persona→中途杀进程→重进续步→skip→建模→完成」全链，顺带确认 G5 回退环消解。
2. **skip 视觉升档（N50 后半）**留 V 系列：persona appbar 跳过现为 ghost、modeling 为 text 档，升级需重录两屏 golden。
3. **GuestConversionCard 挂载盲区**（新发现，非本卡范围）：growthSections 在 hasNoGoals 时整体不渲染，访客新号同样看不到 N40 转化卡——建议单开小卡核实并比照本卡挪挂载点。
4. harness 钉 completed=true 只为保存量布局基线；后续 home 结构变更卡若断言「未完成引导」态，需自行 override。
5. 收工清理已执行：mobile/build、.dart_tool、/tmp/j02-baseline*（基线克隆与探针 txt）全删，worktree 回落 399M；分支本地 commit 未 push。
