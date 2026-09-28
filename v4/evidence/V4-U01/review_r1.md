# V4-U01 · 独立审查 receipt（一审）

- 审查 agent：wtU01R1（未参与 U01 实现）
- 审查对象：`agent/v4/u01` @ `e7caa89c`（基线 `e50107fe`），审查开始时工作树干净
- 卡标准：`v4/04_tasks/tasks.json` → `V4-U01`（normal / 独立审查 1 位 / locks: ui-home）
- 裁决：**PASS_WITH_CHALLENGES**（R1-1 勘误要求见下；无实现阻断）

## 0. 独立复验命令与结果（全部亲跑）

| 项 | 命令（wtU01 根） | 结果 |
|---|---|---|
| RF-06 三冲突面零 diff | `git diff e50107fe..e7caa89c --stat \| grep -E "dashboard_screen\|compact_status_bar\|task_execution_screen"` | 无匹配（exit 1）= 零触碰；`routes.dart`/`design_system`/`theme_manager` 同零 diff |
| 合并演练 vs main | `git merge-tree $(git merge-base HEAD main) HEAD main`（main=4622efe8，含 b1cec7c2） | 产品代码**零冲突**；l10n 五文件 changed-in-both 全部自动合并干净；唯一冲突 `v4/04_tasks/tasks.json`（状态文件，销账协调解决，预期内）。实现者「仅 app_zh.arb 1 key 重叠」属实且偏保守 |
| 全量测试 | `cd mobile && flutter test` | **+2912 ~23 -1**，exit 1。唯一失败 `websocket_chat_service_v2_a2_offline_queue_test`（`IsarError: instance has already been closed`）——U01 零接触文件（不在 diff 内）；隔离重跑 `flutter test test/features/chat/data/services/websocket_chat_service_v2_a2_offline_queue_test.dart` → +3 全绿。**负载型 flake 复现，与实现者中间轮 3-flake 披露同族互证**；2912+1=2913 与自述分母精确吻合 |
| analyze | `cd mobile && flutter analyze` | No issues found! |
| 四棘轮 | `python3 scripts/guards/check_{ui_design_tokens,typography_rhythm,spacing_rhythm,dl_spec}_ratchet.py` | 4/4 PASS，数字与 test_results.json 逐字一致（color=225/275, fontSize=634/727; sub12=232/234, W800=0/0, W900=6/6; spacingHalfStep=**1591/1623**——1591<1623 佐证「改 4pt 栅格未刷基线」）；dl-spec 15 项不升 |
| 截图 sha256 | `shasum -a 256 v4/evidence/V4-U01/u01_resume_*` | 4/4 与 run_manifest.json artifacts 逐字一致 |
| 语义互斥 | grep 两份 *_semantics.txt | ready：eyebrow+Last time(y≈333)+Next(y≈354)+Continue this step(y≈409)；stale：**0 处** Last time/Next，out-of-date 单行 + Start Here(y≈449)。截图亲视（Ahem 字形披露属实） |
| 存量测试改动 | `git diff e50107fe..e7caa89c -- mobile/test/widget/a11y_u08_state_semantics_test.dart`、cockpit 测试 | a11y 纯增量（override+桩，断言零改动）；`today_cockpit_card_test.dart` 零 diff、9 testWidgets 亲数吻合 |
| tasks.json 增量 | `git diff e50107fe..e7caa89c -- v4/04_tasks/tasks.json` | 仅本卡 status/implementation_state/evidence_pointer/summary/progress_note，零触碰他卡 |
| TTL 常量 | `grep DEFAULT_RESUME_VIEW_TTL_SECONDS backend/app/services/episode_resume_service.py` | `30*60`（limitations #1 的 30min 属实）；服务端每次请求现算（`build_resume_view` 无缓存）→「装载重算」真实 |

## 1. 预登记 6 挑战逐项独立裁决

### CH-1 receipt 角色门（selection_role=='resume_view'）——**门方向正确；但发现 R1-1 可用性事实**

- 契约依据亲读：`backend/app/core/context_selection_receipt.py:60-68` `SELECTION_ROLES` 四值封闭词表，注释「这次选择在哪生效」；B05 合同 §2 同义。`chat_context` 回执记录的是 **chat 装配**的选择，拿来当接续依据 = 归因错置——实现者推理成立，且角色词表移动端投影 `context_receipt_models.dart:40-45` 与后端四值 1:1，**无漏角色**（反向挑战不成立）。
- 测试判别力：mutation M1（删角色门）→ `episode_resume_provider_test` 反例 2 红（亲跑）。
- **但（R1-1，见 §3）**：全仓检索证实**当前后端没有任何 `resume_view` 角色回执的生产者**——唯一生产链 `context_pack.py:2159` 硬编码 `selection_role="chat_context"`（`context_receipt_assembly.py:70` 默认同）；I01 端点只校验 ref scheme 不生产回执（`episode_resume_service.py:122-130`）；`latest_receipt` 不分角色返回最新一条（`context_selection_receipt_service.py:288-308`）。⇒ 真实环境即使 receipt mode=live，latest 回执恒为 chat_context → 接续条**永不可现**。limitations #2「mode=live 后自动生效」必要不充分，属过claim。

### CH-2 stale 不判 memory_epoch——**接受（披露如实，窗口窄）**

- 亲核：客户端子集只判 `expires_at`（`episode_resume_models.dart:313-321`）；`memory_epoch_changed` 需当前 epoch 真源，移动端读侧确无（epoch 由写侧 bump）。I01 契约本身把 `current_memory_epoch` 设为可选参（`episode_resume_view.py:294-327`），重算权威出口在服务端——每次请求现算（service 无缓存，`expires_at = now + 30min`）→「TTL+装载重算兜底」真实。
- 可感知窗口 = 同会话内 provider（依赖 receipt/growth 变化才重算）在「epoch 已 bump 且 TTL 未过」时仍显示原视图；但视图核心内容（last_confirmed_step/pending_human_step）来自 task 权威行而非 memory 行，epoch bump 主要由记忆删除/纠正触发——窗口内误导伤害窄，且任一新回执（下一轮对话）即触发重算。limitations #1 披露充分。不构成阻断。

### CH-3「可调整」无显式控件——**按卡文本裁决：满足**

- 卡验收原文「回归有真last_step/可调整」未要求新增控件；MASTER_DESIGN L15「一个主动作」「若目标已变或记录过期，先说明不确定性而不是强行接续」直接支持「可调整 = 不强制接续」口径。既有 ghost 次级入口（/tasks 账本）保留即调整路径可达；新增显式「换个任务」CTA 反与「首屏唯一 primary」张力。非降阈值。

### CH-4 D01 mark_seen 不接线——**裁决正确**

- 亲读 `experience_event_service.py:128-152,266-285`：曝光投影唯一入口 `record_rendered_exposure(record: InterventionRecord,…)`，需 decision_id 权威回执，缺失即 `no_authoritative_receipt` 降级（I2）。首页接续条非 intervention record、无 InterventionRecord 可指——接线即需造 record/ref（假曝光，违 I2）。不接线是契约正确解。F03 消费面就绪亲核：`resume_available` 在封闭词表（`backend/app/core/experience_event.py:66` + `mobile/lib/core/experience/experience_event.dart:32`）。

### CH-5 off/shadow 桩盲区——**无盲区（live 探针用后即删）**

- 探针（临时文件，已删）：纯 harness 默认（零 extraOverrides）pump `TodayCockpitCard` → `episode-resume-strip`/`stale-line` findsNothing、零 `Last time:` 文案、`_UnreachableApiClient` 未触发（零触网）→ 存量基线「接续条如实缺席」成立、无测试误依赖默认。新增 24 测全部显式 live override（集成/证据测试文件亲读：`resumeOverrides` 后写胜出）。既有 cockpit 9 测零改动经全量佐证。

### CH-6 卸载重挂等价性——**接受（实际比声明更强）**

- 亲读测试：`pumpCockpit` 每次经 `buildDashboardWidgetHarness` 新建 ProviderScope → 卸载重挂实为**容器销毁级**重启，强于真实「退出重进（容器可能存活）」。容器存活场景（FutureProvider 非 autoDispose 返回缓存）由渲染时刻 `episodeResumeStaleReason(now: DateTime.now())` 现判兜底（strip 每帧 build 现判，`episode_resume_strip.dart:34`）；TTL 过期即转 stale 只说明。review_receipt CH-6 披露与实现一致。

## 2. 验收三条对证据核

1. **「360宽首屏有主CTA，不靠滚动」**：`today_cockpit_resume_integration_test.dart:365-402` 钉 `physicalSize=Size(360,800)`/dpr 1.0，经 `buildDashboardTestHarness` 渲染**真实 DashboardScreen**（harness L105 亲读）；滚动前 `ctaRect.bottom ≤ 800 && top ≥ 0`（load-bearing）+ ensureVisible 后仍在视口；语义证据 CTA y≈409-425。断言强度足够。反例：stale 主 CTA 照旧 Start Here（改写即红）。
2. **「新用户零假历史；回归有真last_step/可调整」**：反例×3（回执 off→缺席零占位、view=null→缺席、无任务→hidden 零请求）+ CH-5 探针；正例 fresh 视图原文渲染真 last_step。「可调整」裁决见 CH-3。
3. **「退出/重进不强制自动播放」**：卸载重挂断言零导航/零 Dialog/SnackBar/内容纯静态复现成立；`transientCallbackCount==0` 的断言真实性**打折**——见 R1-2。主防线是结构事实（亲读 strip/provider：纯静态文本、无 Timer/无 AnimationController/无导航调用）——成立。

## 3. Mutation 抽查（3 处，均亲跑后还原，工作树已复原干净）

| # | 产品代码变异 | 预期 | 实测 |
|---|---|---|---|
| M1 | `episode_resume_provider.dart` 删 `selectionRole != 'resume_view'` 门 | 角色反例红 | **红** ✓（provider 反例 2 failed） |
| M2 | `episode_resume_models.dart` `episodeResumeStaleReason` 恒 null | stale 面红 | **红** ✓（models 过期判定 + 集成 stale 两测 failed） |
| M3 | `episode_resume_strip.dart` 注入 `LinearProgressIndicator()`（不定动画） | 卸载重挂 transientCallbackCount==0 红 | **存活**（测试仍绿）→ R1-2 |

**R1-2（挑战）**：harness `TickerMode(enabled: false)`（`dashboard_test_harness.dart:240-243`，存量行为）冻结一切 ticker → muted ticker 不调度帧 → `transientCallbackCount==0` 对 ticker 驱动的动画/转场**空洞真**；「零自动播放已被 transientCallbackCount==0 钉死」（test_results/diff_md/tasks.json progress_note 三处表述）强度过claim。结构论证（零动画代码路径）才是主防线且成立。建议：措辞降级为「结构零动画路径 + 静态重挂断言」，或在 tickerEnabled:true 下补一条钉。

## 4. 3-flake 披露可信性

本审查全量跑独立复现同族 flake 1 例（`websocket_chat_service_v2_a2_offline_queue_test`，Isar 实例生命周期竞态；该文件基线即存在、U01 零接触），隔离重跑全绿。实现者「中间一轮 3 failed 日志截断未定位 → 完整日志重跑全绿、如实披露不归因」与本证据一致，可信；非本卡回归，不列条件。建议 fleet 对该 Isar 家族 flake 另立登记（超出本卡范围）。

## 5. 裁决与条件清单

**PASS_WITH_CHALLENGES**——实现契约正确（fail-closed 解析、五门派生、stale 只说明不接续）、验收三条全部有真实可失败证据、RF-06 红线亲验零触碰、合并落差零产品冲突、数字诚实性全面吻合（含对己不利的中间轮披露）。以下挑战不阻断，但销账/二审须处理：

- **R1-1（勘误要求）**：limitations #2 与 tasks.json `evidence_summary`/`progress_note` 的「mode=live 后自动生效」须勘误为「live **且** 后端接续流存在 resume_view 角色回执生产者后方可见」（当前唯一生产者 `context_pack.py:2159` 恒 chat_context；`latest_receipt` 不分角色）。并登记集成依赖：接续流 receipt 生产 = 后续 contract-owner 卡；本卡真实环境演示面前接续条不可现（证据测试桩 live 举证的口径 limitations #2 已含，但归因须从「读面开关」改为「生产者缺位」）。
- **R1-2（措辞要求）**：「transientCallbackCount==0 钉死零自动播放」按 §3 R1-2 降级措辞（三处）；可选增强：tickerEnabled:true 下复验钉。
- **R1-3（登记建议）**：Isar 负载型 flake 家族（本审查复现 1 例）另立 fleet 登记，不计本卡。

## 6. 审查过程留痕

- 变异探针与 CH-5 探针均用后即删；全量跑产生的 `v3-output/WT401-Q03-VISUAL/*` 运行时产物已 `git checkout --` 还原；审查结束工作树干净 @ `e7caa89c`。
- 本 receipt 提交于 `agent/v4/u01`（不 push、不动实现 commit）。
