# 07 R2 修复波·Wave1 — 移动长尾面修复档案

> 对应复审报告：`round2/07-r2-mobile-features.md`｜工作树 wt7 @ ca86bda8（冻结基线，本波未提交）
> 修复员：07｜日期：2026-09-18

## 修复总览

| 项 | 状态 | 红-绿证明 |
|----|------|-----------|
| ★第 0 批棘轮守卫 `UI-TOKENS` | ✅ 落地 | 基线绿（color 275/275, fontSize 727/727）→ 注入违规红（exit=1）→ 移除后绿 |
| R2-01 记忆设置读失败静默回退默认值（P0） | ✅ 修复 | 新用例 5xx 红（回退默认值、无错误态）→ 绿（错误态+重试）；404 用例钉住"仅 404 用默认值" |
| R2-03 专注会话假保存/数据丢失（P0） | ✅ 修复 | 新用例 2 个在改动前代码上 0/2 红 → 修复后 2/2 绿 |
| F7-09 Radio deprecated API 定时炸弹 | ✅ 修复 | 冷启动问卷套件 4/4 绿（含交互式选择→提交断言，实测 RadioGroup 迁移） |
| F7-15 机械批（33 unused_import + 11 空 catch） | ✅ 修复 | analyze warnings 37 → 2（仅剩报告预期保留的 chat unused_element + feed_post_card 参数项） |

---

## 1. ★第 0 批：棘轮守卫（硬前置，已完成于一切修复之前）

**落地方式**（与现有守卫机制一致：`scripts/guards/` + `rule_guard_manifest.tsv`）：

- 新增 `scripts/guards/check_ui_design_tokens_ratchet.py`：扫描 `mobile/lib/features/**.dart`，统计 `Color(0x`（硬编码颜色）与 `fontSize:\s*[0-9]`（硬编码数字字号；`fontSize: DS.fontSizeSm` 等令牌不计），逐文件对照冻结基线 `scripts/guards/ui_design_tokens_baseline.json`，**新增即红、只许下降**；`--update-baseline` 供燃烧批降基线。
- 注册：`scripts/rule_guard_manifest.tsv` 新增 `UI-TOKENS` 行。

**基线计数（ca86bda8 实测，脚本口径）**：color **275** 处 / fontSize **727** 处（203 个文件含硬编码）。
> 注：与报告 §3.4 的 243/884 存在口径差（报告按行/可能含令牌计；脚本按出现次数、剔除注释行、仅数字字号计）。棘轮钉的是脚本自身口径，防回灌目标不变。

**红-绿证据**：
```
$ python3 scripts/guards/check_ui_design_tokens_ratchet.py
[ui-tokens-ratchet] PASS — ratchet holds at color=275/275, fontSize=727/727 (203 files ...)
$ printf '...Color(0xdeadbeef...fontSize: 99...' > mobile/lib/features/tmp_ratchet_probe.dart
$ python3 scripts/guards/check_ui_design_tokens_ratchet.py; echo exit=$?
[ui-tokens-ratchet] FAIL — 1 ratchet violation(s) ...
  NEW FILE mobile/lib/features/tmp_ratchet_probe.dart: color=1 fontSize=1 (baseline: none)
exit=1
$ rm .../tmp_ratchet_probe.dart && python3 scripts/guards/...py
[ui-tokens-ratchet] PASS — ratchet holds at color=275/275, fontSize=727/727 ...
$ bash scripts/run_all_rule_guards.sh --rule UI-TOKENS
all rule guards passed (1 rules)
```
全部修复落地后复跑：仍 PASS（275/275、727/727，本波零新增）。

---

## 2. R2-01（P0）：记忆设置读失败静默回退默认值 → 保存即覆盖服务端真实设置

**修法（报告 §3.3 ②，含服务层同族问题一并闭环）**：

- `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart`
  - 删除 `loadSettings` 两处 `catch (_) → 默认值` 回退；改为 `on DioException` 仅 `statusCode == 404`（服务端确认无配置）时才以默认值填充，其余一律 rethrow → 既有整页错误态 + `重试` 按钮（本屏已具备，`errorKind: load`）。
  - 默认值常量随迁至 notifier（服务层不再私藏假数据）。
- `mobile/lib/core/services/memory_api_service.dart`
  - 删除 `_shouldUseLocalFallback`（401/403 → 默认值/假回显）及 `_defaultMemorySettings`/`_defaultPushSettings`：读失败全部上抛（memory_detail_screen 自有 try/catch 天然兼容，且从"静默假设置"变为显式错误提示）；**写失败不再把入参 echo 回来冒充保存成功**。服务层回归薄 API 层（符合分层边界）。

**红-绿**：`test/widget/memory_settings_screen_test.dart` 新增 2 用例：
1. 5xx 读失败 → 断言渲染 `重试`、不渲染表单（`自我记忆`/`保存设置` 均不存在）、无保存发生 —— 改前红（旧行为回退默认值直接渲染表单），改后绿；
2. 404 → 默认值填充可保存 —— 钉住"仅 404 允许默认值"的绿灯面。
套件 **3/3 绿**（含原 renders-and-saves 用例）。

## 3. R2-03（P0）：专注会话假保存 / 失败即销毁可恢复会话

**修法（报告 §3.3 ①）**：

- `mobile/lib/features/focus/presentation/providers/focus_statistics_provider.dart`
  - `saveSession`：`if (_localRepo == null) return null;` → `throw StateError('local focus repository unavailable — focus session NOT saved')`。null 语义收敛为"已落 Isar、同步待重试"，杜绝"哪里都没存却提示已离线保存"。
  - `build()`：`FocusStatisticsRepository(db.isar)` → `db.isarOrNull`（Isar 初始化失败时统计面降级 API-only，477 的抛错分支成为可达的真实故障路径，而非仅在 build 阶段崩溃）。
- `mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart` `stop()`
  - 失败路径**不再** `_clearPersistedSession()` + 重置 state：`_timer/状态/SharedPreferences 快照` 的清理整段移入 `!saveFailed` 才执行；快照保留供 `_restoreSession()` 下次启动恢复重试；`loggingError` 不再被覆盖性销毁（同时 `isLoggingSession: false` 防止按钮卡在提交态）。
- `mobile/lib/features/tools/presentation/widgets/focus_timer_tool.dart`（第二调用方）
  - `_handleSessionComplete` 对 `saveSession` 增加 try/catch：失败发 `focusSaveFailed` 通知并提前返回，不再走"已记录"成功通知。

**红-绿**：新增 `test/features/focus/presentation/providers/focus_save_r2_03_test.dart`（2 用例）：
1. 无本地仓库时 `saveSession` 抛 `StateError`（改前返回 null → 红）；
2. 端到端恢复链：预置快照 → 构造 notifier 断言 `_restoreSession` 恢复 → `stop()` 保存失败 → 断言 `savedLocally == false`、文案含 `保存失败`、**快照仍在**、会话仍活跃可重试（改前：假"已离线保存"文案 + 快照被清 → 红）。
临时回退两个修复点复跑：**0/2 红**；恢复修复后 **2/2 绿**。`test/features/focus` 全套 **5/5 绿**。

## 4. F7-09：Radio deprecated API → RadioGroup（定时炸弹拆除）

- `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart`：`RadioListTile.groupValue/onChanged`（Flutter 3.32+ 废弃）迁移为 `RadioGroup<String>` 祖先（`groupValue`/`onChanged` 上提，tile 仅持 `value`）。`flutter analyze` 的 2 条 deprecated 警告清零。
- 配套：`test/widget/coldstart_questionnaire_test.dart` 基线即红（4 用例从未展开折叠面板、submitting 用例未先作答）。修复测试侧：展开后再断言/交互 + 先作答再保存。**4/4 绿**，其中 "collects answers" 用例实测了迁移后 RadioGroup 的选择→提交链路。

## 5. F7-15：机械批

- **33 处 unused_import** 删除（按 `dart analyze --format machine` 逐条定位，28 个文件；calendar/chat/cognitive/community/home/insights/memory/mirofish/photon/seed_library/theater/tools/translation/user）。
- **11 处空 `catch (_) {}`**（R1 F7-15 清单逐项核对，`accountability_invite_flow.dart` 实际路径在 `presentation/utils/`）逐处加一行"为何安全"注释；其中 9 处补 `debugPrint`（observability），2 处纯注释（mock 数据集缺失回复目标、可选 overview 刷新失败回落缓存）——涉及 `aurora_core_session_sheet`×2、`aurora_telemetry_service`、`mock_community_repository`、`accountability_invite_flow`、`translator_tool`、`knowledge_integration_service`、`translation_history_provider`、`modeling_chat_screen`、`visual_element_card`×2；4 个无 foundation 导入的文件补 `import 'package:flutter/foundation.dart'`。

---

## 6. 验证汇总（资源纪律：全部 `--concurrency=4`、单命令串行）

| 检查 | 结果 |
|------|------|
| `flutter analyze --no-pub lib/features` warnings | **37 → 2**（33 unused_import 清零、2 deprecated Radio 清零；余 2 = chat `_safeDouble`（归 6 号切片）+ `feed_post_card` 参数项，均为报告预期保留项）；errors 0 |
| `flutter test test/widget/memory_settings_screen_test.dart` | 3/3 绿（含 R2-01 新增 2 用例） |
| `flutter test test/features/memory` | 48/48 绿 |
| `flutter test test/features/focus` | 5/5 绿（含 R2-03 新增 2 用例） |
| `flutter test test/widget/coldstart_questionnaire_test.dart` | 4/4 绿（基线红已修复 + RadioGroup 迁移验证） |
| `flutter test test/features/tools` | 1/1 绿 |
| `run_all_rule_guards.sh --rule UI-TOKENS` | PASS（棘轮 275/275、727/727） |

## 7. 本波未排产 / 新发现记档

- **未做（按任务书列余量清单）**：R2-02（focus errorMessage 死端）、R2-04（mergeServerSessions 死代码）、R2-05（restore 竞态）、R2-06（plan 刷新扇出）、R2-10（portfolio 下拉刷新红测试）、F7-11/12、Demo 模式指示器、243/727 令牌燃烧批（守卫已就位，按 §3.4 分批策略推进）。
- **新发现（本波修复中顺带核实）**：
  1. `memory_api_service.dart` 服务层 401/403 静默回退（读→假默认值、写→假回显）是 R2-01 的同族问题且在更底层，已随 R2-01 一并修复（见 §2）。
  2. `test/widget/coldstart_questionnaire_test.dart` 基线即红（4/4，从未被执行过红-绿校验），已随 F7-09 修复并转绿。
  3. `MindfulnessStopResult`（savedLocally/message 等）目前无任何 UI 消费方（`confirmExit` 为 unawaited fire-and-forget），R2-03 修正后的语义（false + 保存失败文案）要真正触达用户需在 mindfulness_mode_screen 补结果提示，建议随 R2-02 一并排产。

*修复波：R2·Wave1｜切片：移动长尾面｜基线 ca86bda8（未提交，产物见同目录 07-r2-fixes.patch）*
