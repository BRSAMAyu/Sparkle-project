# WT772 · J-02 独立审查 receipt

- 审查工号：wt772（独立未参与会话，未参与 wt764 实现）｜ 日期：2026-09-27
- 审查对象：V3 卡 **J-02 · Onboarding：Value Before Profile**（`v3/07_tasks/cards/J-02.md`），交付 wt764（commit `787bc973`，base `3cbeb4a7`，均已入 main）
- 审查环境：独立 worktree `agent/node-b/wt772/j02rev` @ **main integration HEAD `81976d55`**（轮#261 补正）；主仓只读，无模拟器/运行栈触碰
- 性质：独立执行关键验收（复跑 + 变异咬合抽验 + 前人交付核对 + 卡面对账）

---

## 1. 结论：**PARTIAL**（不销账）

工程交付面合格，唯一缺口 = 卡面 Required evidence 明列的 **integration/simulator 实测证据**（wt764 的 ≤3min 为验算非实测，卡面证据要求未满足，按卡面判 PARTIAL 不放宽）。其余全部对账通过（§3-§5）。

## 2. 独立复跑（integration HEAD `81976d55`，本人执行）

| 面 | wt764 声称 | wt772 实测 | 判 |
|---|---|---|---|
| fast-path（`mobile/test/features/user/persona_onboarding_fast_path_test.dart`） | 4/4 | **4/4 过** | ✅ 一致 |
| persona 回归 draft_resume | 8/8 | **7/7 过** | ⚠️ 全绿但计数失实（§6） |
| persona 回归 submit_feedback | 3/3 | **1/1 过** | ⚠️ 同上 |
| 相邻面 first_run_value_subtitle | 3/3 | **3/3 过** | ✅ 一致 |
| 相邻面 onboarding_resume_card | 5/5 | **4/4 过** | ⚠️ 同上 |
| router_smoke（三端 session 三角） | 10/10 | **10/10 过**（含新增 guest 折回 home + 升级端 persona 可达两用例） | ✅ 一致 |
| 后端 `tests/unit/test_j02_minimal_goal_capture.py` + `test_j02_seed_memory_namespace.py` | 4/4 | **4/4 过**（sqlite 内存库 + SECRET_KEY 测试变量） | ✅ 一致 |

后端 4 例独立核读：goal-only 恰 1 行 memory_goals + 偏好中心四键零写 + first_message 回包；全量载荷对照锚不受影响；`seed_guest_user_data` 后 memory_goals/episodic_memories 恒 0 行；V3-FIX-258 demo 轮短路 + demo_skipped 观测点递增。服务端 `submit_onboarding`（`backend/app/api/v1/profile_transparency.py` :1319 起）逐字段条件写入为既有行为，本卡只钉未改——未弱化任何守卫。

## 3. 变异咬合力抽验（本人执行）

- 变异：注释 `persona_onboarding_screen.dart` 快车道 CTA 空目标守卫行（`return const SizedBox.shrink();`，:238）→ CTA 恒显。
- 结果：fast-path 用例 1「CTA stays hidden until the goal has text」**转红**（`+0 -1 [E]`），其余 3 例不受影响。
- 回退后：**4/4 复绿**，`git status` 干净。测试对实现有真实咬合力，非恒绿装饰。

## 4. 前人交付核对

- **wt282 增量面**：commit `cd154f03` 实在（首跑字幕 N48 zh+en、persona 草案 8 字段 debounce+clamp 续存、注册硬跳移除 + OnboardingResumeCard、dashboardSections 挂载），`mobile/lib/app/routes.dart` 软墙与 `onboarding_resume_card.dart` 在当前 main 均可核。✅
- **wt759 缺口⑤（GuestConversionCard 盲区）确已过时**：wt287 两 commit（`2f27dd2a`、`e387f380`）实在；`dashboard_screen.dart:1150` GuestConversionCard 挂 `dashboardSections`、:1123-1130 注释与实况一致（hasNoGoals 分支不渲染 growthSections 的盲区已修）。wt764「本卡零工作」判断成立。✅

## 5. 卡面对账

**Acceptance**
1. 「fresh user ≤3min 到 useful action」——验算（notes §5，≈5 taps + 55-70s，留 >100s 余量）**非实测**；FIRST_3_MINUTES「Automated simulator acceptance」清单一节明确 fresh install + 3 分钟脚本 + 视觉 Reviewer 截图打分，属模拟器/设备证据。**未满足 → PARTIAL 主因**。
2. 「seed 不进入真实 Memory」——后端 4 例独立复绿 + V3-FIX-258 分支首次获得测试覆盖。✅（widget/服务端级证据充分）
3. 「注册/游客/升级三端 session 稳定」——router_smoke 三角复绿（注册软墙既有 + 新增 guest 折回 + 升级端可达）。router 级 ✅；实机三端走查随 §6-1 残差。
4. 「五问零裁减只延后」语义核实：draft `maxStep=4`（5 步）未动；全量 primary 提交路径（`_submitting`，:598-648 全字段）未动——快车道纯增量；goal-only → `onboardingCompleted` 推断（settings_provider :1018-1034，依赖 study_time_preference/knowledge_level/response_style 任一）保持 false → OnboardingResumeCard 入口留存；`deferredAt(1)` 步进到第一个延后问、目标不重填；后端全量对照锚复绿。**语义成立：零裁减、只延后、可达。** ✅

**Forbidden**
- 不得重建已存在的权威真源——只钉既有裁决（258/257/142）+ 增量 UI，未重建。✅
- 不得用 mock/seed 冒充真实行为——测试 fake 属标准 widget 测试手法；≤3min 未被当作实测宣称。✅
- 不得只通过静态阅读宣称用户体验通过——wt764 明示不勾验收框、留 Reviewer/首飞，**诚实声明属实**。✅
- 不得弱化既有安全/幂等/隔离/审计守卫——commit 全文件复核为纯增量（屏/arb/l10n/测试），零守卫改动。✅

**Required evidence**：base/final SHA ✅（`3cbeb4a7`/`787bc973`，均为 main 祖先，已验 ancestry）；targeted tests ✅（本人复跑）；**integration/simulator evidence ❌（缺口）**；review receipt ✅（本文件）。

## 6. 残差裁定

| # | 残差 | 裁定 |
|---|---|---|
| 1 | **设备/simulator 实测**（fresh install ≤3min 到 Action 秒表核 + 三端实机走查 + 截图视觉核） | **J-02 销账前置**。卡面 Required evidence 明列，审查方无权豁免。闭合路径：持有模拟器/真机的后续会话在 integration HEAD 按 FIRST_3_MINUTES「Automated simulator acceptance」清单执行并存证（截图+秒表）入 v3-output；或由 fleet owner 显式裁决豁免并转 HUMAN_INBOX 首飞清单（豁免须记账，非默认）。 |
| 2 | review receipt | **本轮已闭合**（本文件即 wt772 receipt），不再是残差。 |
| 3 | N49 首聊破冰（访客首聊零问询） | **转 post-RC 独立跨层卡**（A-SPEC8B 明示跨层，wt759 未列入 J-02 缺口）。非 J-02 销账前置。 |
| 4 | **（wt772 新发现）notes §7 回归计数失实**：声称 draft_resume 8/8、submit_feedback 3/3、resume_card 5/5，实际 **7/1/4**（subtitle 3/3 正确）。测试文件自 wt764 commit 至 main 字节级一致（`git diff 787bc973 main` 零差异），属 notes 笔误非代码缺陷；全部用例实际全绿，不构成虚假通过宣称，但证据计数应准确。 | 轻量更正项：J-02 销账前在 WT764-J02 notes 追加更正注记（或在台账注记），不单独占卡。 |

## 7. 销账建议

1. J-02 **维持 PARTIAL，不销账**，缺口唯 §6-1 一项。
2. wt764 工程交付面（fast-path + 后端 pin + router 三角 + l10n）**判定合格**，无需返工；变异咬合与语义核实均过。
3. 补证完成后（simulator 证据入 v3-output + notes §7 更正注记），J-02 可由该会话按验收模型申请销账，引用本 receipt。
4. N49 按 §6-3 转 post-RC 跨层卡登记。

## 8. 审查动作记录

- 独立 worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt772-j02rev`（分支 `agent/node-b/wt772/j02rev`，不 push）
- 测试执行：flutter test 串行（--concurrency=1），后端 pytest sqlite 内存库（复用主仓 venv 解释器，主仓零写入）；gen 目录自主仓 `cp -RL`（gitignored 编译依赖，wt764 同法）
- 本 receipt 随 worktree 提交：见分支 HEAD commit

*—— wt772 审查完毕，PARTIAL（工程面合格，simulator 实测证据缺口项销账前置）。*
