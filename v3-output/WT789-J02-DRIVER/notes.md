# WT789 · J-02 专属 dart 集成测试驱动 notes

- 工号：wt789 ｜ 日期：2026-09-27 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt789-j02driver`
- 分支：`agent/node-b/wt789/j02driver` ｜ **base = main@`5833639a`**（轮#276，含 `docs(j02): wt784` 88ff9e45，WT784-J02PREP 在位——正确基线已核）
- 性质：wt784 缝隙③（checklist §6 G5「J-02 专属 dart 驱动不存在」）的销项——**只写代码 + 静态/单测验证，绝不在真机/模拟器上跑**。门后（day7 终门 2026-09-28 08:00 之后）执行会话拿本驱动 + wt784 runbook 即可开跑。
- 纪律：未 flutter run、未启动模拟器、未触碰运行栈（docker/:50051/:8000/:8080 全程未连）、未碰 `/tmp/northstar_ns001_real_drive_state.json`、未 push、未改台账（DYNAMIC_ISSUES.md 零触碰，新发现见 §5）。

---

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `mobile/integration_test/j02_fastpath_journey_test.dart` | J-02 快车道旅程驱动：Leg R（注册端 R0-R9 主判据 ≤180s）/ Leg G（游客端 G1-G3 + 打印 `J02_GUEST_USER` 供 G4 探针）/ Leg U（升级端 U1-U3 原位翻转）；5 persona 差异化（PX1-PX5，J-01 同常量）；`J02_MARK`/`J02_SUMMARY` 打点；`j02_timings.json`/`steps.json`/`proposals.json` 产物落盘；runbook §3 命名逐字的截图族 + `9x-*-timeout.png`/TEXTDUMP 失败留证 |
| `mobile/test/unit/j02_driver_contract_test.dart` | 驱动纯函数面契约钉（9 用例）：persona 集合、J02_MARK 行形制（orchestrator verdict 正则咬合）、秒表预算 180000ms、timing-key schema、产物文件名、截图 canon、F3 两两非同文规则、密码字面量 |
| `v3-output/WT789-J02-DRIVER/notes.md` | 本文件 |

产品代码零改动（`git diff` 仅两个新增文件，l10n 生成物 whitespace churn 已 checkout 还原不入 patch）。

## 2. 路径决策（含否决记录）

1. **驱动文件名 = `j02_fastpath_journey_test.dart`（runbook §2.2 / first3minutes.sh 指定），否决任务建议的 `first3_j02_value_before_profile_test.dart`**：`v3-output/WT784-J02PREP/first3minutes.sh` 把 `DART_DRIVER="mobile/integration_test/j02_fastpath_journey_test.dart"` 写死且 `run_journey()` 有存在性守卫（`die "dart 驱动不存在"`）——用任何其他文件名都会让门后编排脚本第一跑就 FATAL。runbook §2.2 的 flutter test 命令行同此路径。**取规格权威，弃我卡建议名**。
2. **新增可选 dart-define `J02_LEGS`（默认 `R,G,U`）**：runbook §2.2 命令只给 `J02_PASS`/`J02_SHOT_DEST` 两个 define，默认值保证不传该 define 时三腿全跑（编排命令零改动）；`J02_LEGS=R` 供执行会话单腿重放。属驱动侧便利开关，不改编排契约。
3. **截图落 `<passId>/NN-<step>.png` 子目录**（J-01 同法）：runbook §3 命名逐字保留在文件名段；`J02_PASS=0..4` 每 persona 独立进程写同一 `J02_SHOT_DEST` 时平面命名会互相覆盖，子目录是唯一不覆盖方案。
4. **JSON 产物落 `J02_SHOT_DEST` 的父目录**（当 basename == `screenshots` 时）：对齐 runbook §8 模板（`j02_timings.json`/`steps.json`/`proposals.json` 与 `screenshots/` 平级）；dest 不叫 screenshots 时原位写（J-01 兼容形制）。
5. **Leg G/U 打点用 `ms_since_leg_t0`，Leg R 用 `ms_since_pass_t0`**（对 runbook §4 形制的有意偏离，见 §5-2 裁定请求）：first3minutes.sh `verdict()` 按 `pass=(\S+)` 分组取 `ms_since_pass_t0=(\d+)` 最大值判 180s——A2 会话稳定腿没有 3 分钟预算，若同样喂 `ms_since_pass_t0`，G/U 的 LLM 耗时会污染 Leg R 秒表判定造成假 FAIL。
6. **worktree 构建面**：`flutter pub get --offline` 一步到位（pub cache 全命中）；`make proto-gen` 补 gitignored `gen/`（buf host toolchain，docker 回退仅告警）。此后 `flutter analyze` = No issues found。macOS xcconfig shims（runbook §1.2）属门后执行面，本卡未做（不跑桌面通道）。

## 3. 规格映射表（runbook 条目 → 驱动代码位置）

| runbook 条目 | 驱动落点（`j02_fastpath_journey_test.dart`） |
|---|---|
| §2.1 macOS wipe 语义 / F1 fresh install | `main()` 开头 `wipeLocalState()`（secure storage + prefs，J-01 同款）在 `app.main()` 之前；`J02_PASS=<i>` 单 persona 单进程 = 真 cold start；`all` 模式 pass 2-5 走 `resetToLoginBetweenPasses`（warm，如实标注） |
| §3 R0 首屏 + F2 CTA 无滚动可见 | `legRRegistered` R0 段：`fullyVisible(tester, SparkleButton '登录')` + `welcome_subtitle_present`（"AI 陪你"）+ `01-first-surface.png`；recordStep `r0_first_surface` |
| §3 R1 注册链（tap flaky ×3） | R1 段：`还没有账号？` reveal→tap ×3，以 `确认密码` 字段/RegisterScreen 出现为准；`02-register.png` |
| §3 R2 四字段+双 tile（`j02px<i><ss>`、`J02-Passw0rd!`） | R2 段：TextFormField ×4 顺序填 + CheckboxListTile 整行 tap；`03-register-filled.png`；账号名 `j02px<index><ms后6位>` |
| §3 R3 软墙 + O3 fallback | R3 段：SparkleButton 祖先过滤定位 `注册`（AppBar 标题陷阱，O3 复盘注释在位）；期望 Dashboard+Resume 卡；弹回则 `04b-register-bounce.png` + `register_ui_bounce=true` + `fallbackApiRegisterAndUiLogin`（真实 API 注册→UI 登录→provider 登录，逐级披露，`t_route_done_fallback` 另列不计入 ≤3min）；`04-home-softwall.png` + `r3_softwall_resume_card`（A2a 面） |
| §3 R4 resume 卡继续引导 | R4 段：`继续引导`（SparkleButton）→ `PersonaOnboardingScreen`；`05-persona-step1.png` |
| §3 R5 空目标 CTA 不在（wt764 判据）+ 非空 CTA/hint 出现 | R5 段：typing 前 `j02-fast-path-cta` 缺席断言（`r5_cta_negative_gate`）→ enterText persona goal → key+`只回答目标这一个问题` 等待；`06-goal-typed-fastpath.png` |
| §3 R6 modeling + 四问延后 | R6 段：tap key → `ModelingChatScreen`；`deferred_questions_not_asked`（persona 屏已不在 ∧ modeling 在）；`07-modeling-deferred.png` |
| §3 R7 modeling 跳过 → onboardingCompleted=true | R7 段：AppBar `跳过`（SparkleButton text 档）→ 等 ChatScreen/DashboardScreen；**实测落点如实记录**（见 §5-1 分歧）；非 home 时走 shell 首页 tab（真实用户路径）→ FirstActionCard 生成入口；`07b-post-skip-*.png` + `08-home-first-action.png` |
| §3 R8 秒表核 ≤180,000ms + F5 loading>500ms 反馈 + 诚实失败面 | R8 段：tap `生成我的第一步` → 6×150ms 内探 `CircularProgressIndicator`（`r8_loading_feedback`）→ 等 proposal 三字段+`开始这一步`/`这个不合适`（120s，失败照 `09b-action-error.png` + 卡内 `重试` 一次再等 120s）；`t_action_ready_ms`/`within_3min_budget` 对 `j02BudgetMs`；`09-action-proposal.png`；proposal 文本进 `proposals.json` |
| §3 R9 确认 = useful action 终点 | R9 段：tap `开始这一步` → 等 `第一步已在任务账本里`；`t_confirm_ms`/`total_ms`；`10-action-confirmed.png` |
| §3 G1 游客折回 + A2b session 稳定 | `legGGuest`：`以访客身份继续` → Dashboard，+3s 仍 Dashboard ∧ 无 persona 屏（`g1_guest_session_stable`）；`11-guest-home.png`；**打印 `J02_GUEST_USER=<username>`** 供编排 DB 探针 |
| §3 G2 种子可见 + 示例标识（缺失=测量数据） | G2 段：种子词/示例标识/conversion 卡三布尔，缺失照录不粉饰；`12-guest-seed-scan.png` |
| §3 G3 demo 轮对话（V3-FIX-258 短路的 UI 面） | G3 段：`对话` tab → ChatScreen 输入框 enterText → `TextInputAction.send`（fallback send 图标）→ 等 Aurora 回复（90s）；`13-guest-demo-chat.png`；G4 DB 探针归编排（`db_probe_owner: orchestrator` 写进 summary） |
| §3 U1 转化入口 + U2 原位翻转（V3-FIX-205 实机面）+ U3 persona 可达 | `legUUpgrade`：`注册并同步进度`（GuestConversionCard）优先，缺失降级 login 注册链并如实记 `card-visibility claim=false` → 注册表单提交 → 断言**不落 LoginScreen** ∧ 回 Dashboard ∧ `registrationSource != 'guest'`（`u2_upgrade_submit`）→ resume 卡 `继续引导` → PersonaOnboardingScreen（`u3_persona_reachable`）；`14/15/16-*.png` |
| §3 5 persona 差异化 / F3 | `j02Personas`（PX1-PX5 与 J-01 逐字同常量）；R8 捕获 proposal 文本入 `proposals.json`；`proposalsPairwiseDistinct` 进程内判定（all 模式），单 pass 跨 run 对比归执行会话 |
| §3 横切断言：超时留证 / 错误不回空白页 | `waitUntilTracked`：任何等待超时 → `9x-<step>-timeout.png` + `J02_TEXTDUMP` + `J02_STEP_FAIL`；不删 run、不静默吞 |
| §4 打点形制 | `j02MarkLine`（纯函数，契约单测钉死）：`J02_MARK pass=<PX*> leg=<R|G|U> mark=<step> ms_since_pass_t0=<n> clicks=<c>`（R 腿）/ `ms_since_leg_t0`（G/U 腿，理由见 §2-5）；进程末 `J02_SUMMARY {json}` + `j02_timings.json`（per-pass 六权威键 = `requiredTimingKeys`） |
| §7 判据映射（F2/F4/F5 + A1a/A1b/A2 实机面） | F2=R0 段；F4=`j02_timings.json` + `within_3min_budget`（编排 verdict 消费 J02_MARK）；F5=`r8_loading_feedback` + 超时截图族；A1a=Leg R 全步；A1b=G 腿 + J02_GUEST_USER（活栈探针归编排）；A2=R3 软墙/G1 折回/U1-U3 原位翻转 |
| §8 产物命名模板 | 截图名 canon = `j02ScreenshotNames`（§3 逐字 18 个，含 04b/09b 失败面）；`j02ArtifactNames` = j02_timings/steps/proposals 三件；db_probes.jsonl/run_manifest 归编排不越权 |
| §6 失败留证 | O3 fallback 段（§6-2 逐字落实）；failures 非空 → `expect(failures, isEmpty)` 令 test 红，产物先行落盘（§6-1 不删 run 的驱动侧对应） |

## 4. 验证实录（全部静态/单测，零设备）

```
基线确认   git log --oneline -2 @ Sparkle-project
           → 5833639a（含 88ff9e45 docs(j02): wt784）+ WT784-J02PREP/ 四件在位
worktree   git worktree add -b agent/node-b/wt789/j02driver
             /Users/brsama/code/GitHub/Sparkle-sysrev/wt789-j02driver main → OK
构建面     flutter pub get --offline → Got dependencies!（离线全命中）
           make proto-gen → ✅（host toolchain；gen/ gitignored 不入 patch）
基线 analyze（proto-gen 后）→ No issues found!（消除 25 个 gen/ 缺失既有 error，
           使"零新增"可严格判定）
写驱动     两文件落地后逐轮 analyze 修至零：
           18 → 4 → No issues found!
analyze    cd mobile && flutter analyze → No issues found! (ran in 7.6s)
单测       flutter test test/unit/j02_driver_contract_test.dart
           → 00:00 +9: All tests passed!
churn 处理 flutter 工具链重排 l10n 生成件空白（app_localizations*.dart -90 行），
           git checkout -- mobile/lib/l10n/ 还原；再跑 analyze 仍 No issues found，
           git status 仅两个新增文件 —— 生成物 churn 不入 patch
终态       git status --short：
           ?? mobile/integration_test/j02_fastpath_journey_test.dart
           ?? mobile/test/unit/j02_driver_contract_test.dart
           ?? v3-output/WT789-J02-DRIVER/notes.md
```

驱动本体编译面另有实证：契约单测相对导入整个驱动文件（含 main.dart/全部 screen 依赖图）在宿主 VM 完整编译通过——`main()` 不被调用，无设备绑定副作用。

## 5. 新发现（按纪律只写本 notes；grep 复核 V3-FIX-533 空闲，最新已用 532）

| # | 发现 | 性质 | 证据 | 处置建议 |
|---|---|---|---|---|
| V3-FIX-533 | **R7 post-skip 落点：runbook §3 R7 期望「回 /home」，代码事实是快车道（R6 带 post_onboarding_message）经 `_finish()` 落 `/chat`**（`modeling_chat_screen.dart:767-772`：`firstMessage` 非空 → `context.go('/chat', extra: initial_ai_message)`，仅无消息才 `/home`）。规格与实现分歧，非必然产品缺陷（带 AI 首条消息进 chat 可辩为设计），但门后执行若按 runbook 逐字判 R7 会误记 FAIL | 规格-实现分歧（待集成裁定改 runbook 表或改产品） | base 5833639a `modeling_chat_screen.dart` `_finish()` 亲读；runbook §3 R7 行对照 | 驱动已兼容两态：落点如实记 `post_skip_route`，非 home 时走 shell 首页 tab 真实用户路径续 R8；集成会话裁定后回填 runbook §3 R7（建议改「/chat（带 post-onboarding message）或 /home」） |
| —（notes 级事实，非缺陷） | runbook §3 R8/R9 按钮字「开始/不合适」与实际 l10n 全文「开始这一步/这个不合适」为截断形制；驱动按全文定位（textAny 兼容） | 文案精度 | app_zh.arb :15728/:15729 | 无动作；执行会话看 screenshot 时勿误判 |
| —（notes 级事实） | GuestConversionCard 可见性受 `guestConversionVisibleProvider` 价值信号门（卡头注释自述）；U1 若卡未显，驱动降级走 login 注册链并如实记 `claim=false` | 既有设计（N40），非新缺陷 | guest_conversion_card.dart :21-26 | 门后 G3 demo 轮先行（价值信号）可提高卡显现率——执行顺序 R→G→U 已内置 |

## 6. 门后执行会话接手指引（三行）

```bash
# 1) worktree 一次性 setup（runbook §1.2）：make proto-gen + macos xcconfig shims
# 2) 每 persona 一进程（真 cold start）：
cd mobile && flutter test integration_test/j02_fastpath_journey_test.dart -d macos \
  --dart-define=J02_PASS=<0..4> \
  --dart-define=J02_SHOT_DEST=<worktree>/v3-output/WT784-J02-SIM/evidence/<run_id>/screenshots
# 3) 日志抓 J02_GUEST_USER → J02_GUEST_USER=<user> bash first3minutes.sh db_probes；J02_MARK 供 verdict
```

驱动不触碰 docker/DB/运行栈（探针权归编排脚本），不 push，不自称完成——本卡交付 READY_FOR_REVIEW 口径，验收依独立未参与会话审查。
