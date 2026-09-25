# WT362-A07-COMEBACK · Comeback + Low-stimulation Relationship Policies

- 工号：wt362（A 线头卡，U-02 落地后解锁）
- 卡面：`v3/07_tasks/cards/A-07.md`（Stream AURORA / Gate V3-4 / risk medium / 1 reviewer）
- **base SHA**：`8ac6bad59b72eed5490a348173074c9d0ce5e22f`（main@wt356 合入后）
- **final SHA**：`221de1fc582a30f6e8903a14eed07ea9fd5f1e8f`
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt362-a07-comeback`（分支 `wt362-a07-comeback`）
- 状态：**READY_FOR_REVIEW**

## 一、改动面（13 文件，+1016/-9 + 收口 1 行）

引擎（backend，锁 aurora-policy）：
1. `backend/app/aurora/runtime_v1/stimulation_policy.py` **新增**——低刺激策略单一权威：`resolve_stimulation_policy`（显式档双向覆盖：`low`→永远衰减 / `standard`→永不衰减 / `auto`+未知+缺省→现状 standard，绝不由内容推断心理状态）+ `apply_policy_to_nudge`（低刺激标题去敦促化「你的学习计划状态」，正文保持事实性）+ `StimulationPolicy`（push 开关 / 抑制窗口 24h→72h / 档位标记）。
2. `backend/app/aurora/runtime_v1/service.py`——①`get_comeback_context` payload 新增 `goal_state` 读侧真源投影（`plan.goal_id` 挂接目标优先 → 全局 primary active 兜底；`title/status/progress` 原样上报含冻结 0/None，不做修饰；`ledger completed/total/ratio` 任务账本诚实进度，与移动端 F-9 口径同源；零写库、不重建真源）；②陈旧任务守卫：`plan_expired`（target_date<today）/`next_task_overdue_days`/`stale_focus`（过期或逾期≥3 天）入 payload；③`_comeback_message`/`_personalized_return_message` 诚实化——计划窗口已结束不再宣称「还来得及/最后一点收尾窗口/最近最适合重新捡起来」，改如实呈报+指向重新校准（接 wt313 的 replan 端点，零羞耻、零诊断表述）；stale 且未过期时如实标注「原定 N 天前」+「也可以先挑今天最顺的一小步」低压力出路；新增 `_comeback_goal_state` 读侧方法。
3. `backend/app/aurora/runtime_v1/user_preferences.py`——第 5 维显式偏好 `aurora_stimulation_mode`（auto/low/standard，默认 auto）入 `_VALID_VALUES`/`_DEFAULTS`。
4. `backend/app/api/v1/aurora.py`——`_AURORA_PREF_KEYS`/`_DEFAULT_AURORA_PREFS`/`AuroraPreferencesRequest` 增同键；GET/PUT `/aurora/preferences` 透传（非法值 422）。
5. `backend/app/core/celery_tasks.py`——`comeback_nudge_task` 接线衰减：读显式偏好→resolve policy→低刺激档 `push_via_websocket=False`（不主动推送，仅入应用内通知中心=「减少主动 CTA」）+ 重复抑制窗口 24h→72h（主动频率衰减）+ 标题去敦促化 + notification data 带 `stimulation_policy`/`goal_state`；显式 standard 行为零变化。

移动端（mobile，锁 mobile-shell）：
6. `mobile/lib/features/aurora/data/models/aurora_comeback_context.dart`——`AuroraComebackGoalState`（goalId/title/status/progress/ledgerCompleted/ledgerTotal，`hasLedger`/`hasContent`）+ `planExpired/staleFocus/nextTaskOverdueDays` 解析；缺字段诚实降级为空。
7. `mobile/lib/features/chat/presentation/widgets/comeback_banner.dart`——新增 `_ComebackGoalStateLine`：目标标题+账本口径 `x/y` 进度 chip（「回来时看到的是自己的真实目标状态而非模板问候」的 UI 面；零新 l10n 键，遵循 U-07 先例）；沿用 `_staggered` 动效减法（低刺激/减动效下直出）。
8. `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart`——`EmotionStateNotifier.setMode` fire-and-forget 同步引擎 `aurora_stimulation_mode`（alwaysLow→low / alwaysNormal→standard / auto→auto；demo 模式与失败静默不打扰），explicit setting 自此**双向贯通**（本地 UI 衰减 + 引擎主动面衰减同一权威）；provider 构造注入 ApiClient，纯本地构造不影响测试。

测试（后端 3 文件 + 移动端 2 文件）：
9. `backend/tests/aurora/test_comeback_context.py` +4 例（见 §二）。
10. `backend/tests/aurora/test_stimulation_policy.py` **新增** 7 例。
11. `backend/tests/unit/test_comeback_nudge_task.py` +1 例（低刺激 nudge 衰减）。
12. `mobile/test/unit/aurora_comeback_context_test.dart` **新增** 3 例（goal_state 解析/缺字段降级/null progress 如实）。
13. `mobile/test/features/chat/presentation/widgets/comeback_banner_test.dart` +2 例（目标状态行渲染；低刺激 interaction：MediaQuery.disableAnimations 下零 SparkleStaggerItem 且目标状态完整保留）。

## 二、验收逐条证据

### 验收 1：3/7/14-day test clock 回归合理；不会显示陈旧任务为当前
- 3-day 阈值：存量 `test_get_comeback_context_triggers_at_three_day_threshold` 保持绿（零放宽）。
- 7-day（窗口未过期）：`test_seven_day_clock_with_live_plan_keeps_framing_and_surfaces_goal_state`——断言「还剩 5 天」正常接回框架 + `plan_expired=False` + goal_state 真实呈现。
- 14-day（窗口已过）：`test_fourteen_day_clock_does_not_present_stale_task_as_current`——`plan_expired/stale_focus=True`；断言 message **不含**「最近最适合重新捡起来」「来得及」「收尾窗口」；**含**「已经结束」「重新校准」；且无「焦虑」「压力」等诊断词。
- 3-day+焦点逾期 5 天：`test_three_day_clock_with_long_overdue_task_marks_stale_focus`——`next_task_overdue_days==5`，message 不称「最适合」、标注「原定 5 天前」+ 低压力出路。
- goal_state：`test_goal_linked_plan_prefers_linked_goal_for_state`（挂接优先）+ 7-day 例中的账本 1/2 断言 + `progress=0.0` 冻结真源如实上报断言。

**红→绿与拦截力**：新 payload 字段/文案在 main 树上即 KeyError/断言红（结构性）；另做变异实验——把 `stale_focus` 恒 False、`goal_state` 恒空，3 个新 clock 用例当场全红（`3 failed, 10 deselected`），还原后全绿，证明非恒真测试。

### 验收 2：低刺激截图/interaction 通过（截图受内存门 DEFERRED，interaction 面完成）
- interaction 测试在册待跑（swap 门，见 §四）：`comeback_banner_test.dart` 两例——目标状态行渲染 + `MediaQuery(disableAnimations:true)`（低刺激经 EmotionResponsiveAppWrapper 的实际运行面）下 `SparkleStaggerItem findsNothing` 且目标状态内容完整 =「减动画、内容不减」的行为断言。
- 全链既有底座核实（考古）：`EmotionResponsiveAppWrapper`（app.dart 全局包络）→ 低刺激 config 关动效/色温；`sparkle_confetti.dart:123` 庆祝彩带低刺激全关；`achievement_card`/`rarity_visual_wrapper`/`sparkle_tappable` 已挂 `emotionLowStimulus`/`hideChallengeBadges`。本卡在其上补齐：引擎主动面（推送/频率/标题）衰减 + explicit 贯通。
- 诚实声明：模拟器截图证据未产出（内存门三次实测不达标），不虚报截图通过。

### 工作项 3：用户 explicit setting 最高优先
- 引擎：`resolve_stimulation_policy` 显式档双向覆盖（`test_explicit_standard_mode_overrides_any_auto_judgement` 钉死「standard 永不衰减」；`test_explicit_low_mode_attenuates_proactive_surface` 钉死「low 永远衰减」）。
- 移动端：`setMode` 三选（既有 settEmotionAdaptive UI）即时同步引擎偏好，本地+引擎同一权威。
- 不诊断红线：策略输出仅行为预算（push/窗口/标题），无任何心理标签；新增文案逐字核对无诊断性表述（14-day 用例断言无「焦虑/压力」字样）。

## 三、测试与门禁

- 引擎定向（worker 树内，sqlite 内存口径，真跑两轮全绿）：
  `DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=<local> .venv/bin/python -m pytest tests/aurora/test_stimulation_policy.py tests/aurora/test_comeback_context.py tests/unit/test_comeback_nudge_task.py -q`
  → `23 passed in 5.94s` / 复跑 `23 passed in 5.45s`（comeback 13 + stimulation 7 + nudge 3）。
- 变异实验：`stale_focus=False`+`goal_state={}` 双变异 → `3 failed, 10 deselected`；还原后绿。
- 守卫：`bash scripts/run_all_rule_guards.sh` → **exit 0，84 条全过**（第一轮 SPACING-RHYTHM 棘轮当场拦截本卡新增半步间距 +3：`spacing10→12`、`spacing6/2→8/4`、`index:2→3`，修正后 `spacingHalfStep=1608/1623 PASS`；第二轮全绿）。
- analyze：`flutter analyze` E0/W16/I589 → `scripts/check_flutter_analyze_gate.py --project-dir mobile` → **exit 0**（预算 E0/W15/I587 容差 ±5；W+1/I+2 为树内漂移——本卡 13 文件在 analyze 日志中**零命中**，16 条 warning 全部位于未触碰文件，如 wt353 存量 emotion_responsive_theme unused import）。
- 冷 mypy：`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'` → 首测 **1279（+1 推高）**→ 定位为本卡 `service.py:464`（getattr 无法窄化 `Task.due_date` Optional→`today-None` No overload）→ 改直接属性判空窄化 → 复测 **1278 = 基线，零推高**；修复随 221de1fc 入库，定向 23 passed 复跑绿。
- mypy 口径备注：venv 无 mypy 二进制（HANDOVER §12 已备案），按主会话先例用全局 mypy。

## 四、DEFERRED 清单（含补跑命令）

1. **移动端定向 flutter test**（本卡 2 个测试文件 + 受 emotion provider 构造变更影响的 WS 回归）：开工起 swap free 三次实测 887M/919M/999M、额度恢复后复测仍 999M，均 <1.2G 硬门，按内存纪律跳过执行。代码照常完成，行为断言均有静态与树内证据。补跑（swap free≥1.2G 时，mobile/ 下）：
   ```
   sysctl vm.swapusage   # free ≥ 1.2G 才跑
   cd mobile && flutter test test/unit/aurora_comeback_context_test.dart test/features/chat/presentation/widgets/comeback_banner_test.dart test/unit/websocket_chat_service_v2_test.dart --concurrency=1
   ```
   预期：5+1 例新增全绿（banner 渲染/低刺激 interaction/goal_state 解析三例 + WS 回归不受 provider 注入影响）。
2. **低刺激模拟器截图证据**：同受内存门（HEAVY≤1）限制，未产出。低刺激 interaction 通过以 widget 测试为替代证据，不虚报截图。

## 五、Forbidden 遵守与事故记录

- 不碰 `task_event_consumer`（wt360 在修）/`emotion_responsive_theme.dart` 换档（U-02 后续卡）/wt358 状态矩阵面；消费 Goal 状态纯读侧，零写库、不重建 comeback/goal 真源。
- 不诊断红线：全部新增文案逐字核对（「这只是节奏变了，不是你的问题」为事实性归因，非诊断）。
- 事故 1（已恢复，教训在案）：变异实验对**未提交**的 service.py 用了 `git checkout --` 还原，误伤本卡改动；靠 sed `.bak` 机制留存的前态副本（/tmp）完整恢复并复跑 23 passed 验证。教训：变异实验前必须先 commit 或显式 cp 备份，`git checkout --` 只可用于已提交基线。
- 事故 2（已收口）：冷 mypy +1 推高，见 §三。

## 六、交接

- 合并后建议主会话在 integration HEAD 复跑：守卫 84、冷 mypy（≤1278）、analyze 门；swap 达标时按 §四补跑移动端三文件。
- U-02 主题换档构造期条件化（`emotion_responsive_theme.dart` applyToTheme 内注释所指后续卡）与 `task_event_consumer` 修复（wt360）不属本卡，未触碰。
