# wt277-value-signal · 价值信号接线补完（N47 落地）+ 转化卡 chat 扩挂载

> 卡号 wt277-value-signal（A 线·转化系统补完，S-M 级）｜ 2026-09-22 ｜ worktree **wt277-value-signal**（分支同名）
> 依据：`v3-output/A-SPEC8B-ONBOARDING/REPORT.md` §3 G2 辩论（采纳）+ §4 N47「价值信号接线令（禁预留常量悬空）」+ §5 改造 #1
> 性质：产品代码改造（mobile）。改前基线：价值信号只接线 1/3（仅 firstTaskCompleted），转化卡仅挂 home。

---

## ① 两信号接线点与依据

### firstDiagnosisOutput（首次诊断/规划类 AI 输出）
- **接线点**：`chat_notifier_actions.dart` 的 `_handlePlanReviewWidget`（chat_provider 库的 part），在 `pendingPlanReview` 落态之后调用 `recordValueSignal(GuestValueSignal.firstDiagnosisOutput)`。
- **为什么是这里**：
  - 服务 docstring 自注释的「pattern 首产出回调」在客户端不可直达——行为定式由引擎异步聚合产出，mobile 侧只有拉取面（cognitive_provider.loadPatterns，恰是 docstring 警告「勿在空态/入口误挂」的入口），A-SPEC8B 辩论亦确认「接线点在引擎侧时序里不易抓」。
  - 按卡面指示改接「chat/modeling 诊断产出落点」：**引擎 `requires_review` metadata（execution_engine.py:2637）→ PlanReviewWidgetEvent → PlanReviewCard** 是聊天内规划类 AI 输出的唯一引擎级标记落点，访客可直达（访客跳过 modeling，主聊天是其唯一可触达的诊断/规划产出面），也是 N39「开始首次诊断」prompt 路径的自然产出口。
  - modeling_chat_screen 的 `modeling_complete` 落点**未接线**：该面注册用户专属（访客 onboarding 自动置 completed 跳过 modeling），而 `recordValueSignal` 对注册用户恒 no-op——接了即死代码，故留待产品侧真有访客 modeling 路径时再接。
- **形制**：完全照 task_execution_screen.dart:293-297 既有样板——`unawaited(ref.read(guestConversionControllerProvider.notifier).recordValueSignal(...))`，只记录不展示，展示时机全归派生可见性；未发明任何新机制。

### firstMemoryReferenced（AI 回复引用记忆）
- **接线点**：`chat_provider.dart` `finalizeRun` 内，AI 消息落态（`state = state.copyWith(messages: [...])`）之后，以 `_receiptReferencesMemories(accumulatedRawMetadata)` 判据触发。
- **为什么是这里**：
  - 服务 docstring 自注释「memory_reference_receipt 首渲染回调」：渲染处是 chat_bubble 内联的 `ContextReceiptBar` → `AuroraReceiptChip(kMemoryReferenceReceiptType)`，但 widget build 会随重建多次执行，而 `recordValueSignal` 计数只增不去重——按渲染帧计数会重复累加。改为在**每轮回复唯一收口**（finalizeRun，`sawTerminalEvent` 守门恰发一次）检测同一数据源（`rawMetadata['memory_reference_receipt']`，引擎 `response_builder._build_memory_reference_receipt` 产出，空引用返回 None）。
  - 判据要求 `referenced_memories` 非空（兼容 dict / JSON 字符串两种下发形态，与 memory_reference_receipt.dart 解析口径一致）——「AI 确实引用了记忆内容」才记，不是「收到空 receipt」就记。
  - 消息未送达（流中断、`shouldPreserveMessage == false`）不记——价值动作以「用户收到」为准。
- **形制**：同上既有样板；守门（仅访客/点掉挂起/同会话一次/无进行中任务）零改动、全复用。

## ② 改动清单

| 文件 | 改动 |
|---|---|
| `mobile/lib/features/chat/presentation/providers/chat_provider.dart` | ① 新增 `_receiptReferencesMemories()` 库级判据（dict/JSON 字符串双形态解析 + 非空 referenced_memories 校验）；② `finalizeRun` AI 消息落态后接 firstMemoryReferenced（N47 注释）；③ import `guest_conversion_service.dart`（provider 侧经既有 `auth.dart` 导出，不重复 import） |
| `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart` | `_handlePlanReviewWidget` 落态后接 firstDiagnosisOutput（N47 注释） |
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | 转化卡第二挂载点：`chatHeaderPanels` 事件横幅槽（既有「出现即有实际事件、无事件零面积」区），追加 `!chatState.isSending && !chatState.hasActiveRun` 本面「非流式中」守卫；import guest_conversion_card |
| `mobile/lib/core/services/guest_conversion_service.dart` | 三枚举 docstring 从「预留常量」更新为实际接线点（文档诚实性）；逻辑零改动 |
| `mobile/lib/features/auth/presentation/providers/guest_conversion_provider.dart` | 挂载点注释 home → home + chat；逻辑零改动 |
| `mobile/lib/features/auth/presentation/widgets/guest_conversion_card.dart` | 形制注释同步（挂载点 + chat 非流中守卫）；逻辑零改动 |
| `mobile/test/features/chat/presentation/providers/chat_value_signal_test.dart` | **新增**，5 用例（见③） |

守门红线核验：派生可见性四条（仅访客/已有价值信号/未被点掉/无进行中任务）未动一字；「禁弹窗形态」遵守（chat 落点为内联卡于既有横幅槽，非弹窗非 overlay）；「永不打断」双保险（provider 级无进行中任务 + chat 级非流式中）。

## ③ 测试 / analyze 结果

**新增 `chat_value_signal_test.dart`（5/5 PASS，单文件单进程）**——触发路径测试：从聊天流真实事件驱动 `ChatNotifier.sendMessage` 全链（fake repository harness，形制照 `test/unit/chat_notifier_stream_test.dart`），断言到 `GuestConversionService` 持久层：
1. 访客收到 PlanReviewWidgetEvent → signalCount=1、lastSignalKey=`first_diagnosis_output`、持久层落盘、派生可见性成立、pendingPlanReview 照常（触发点行为未被接线改变）；
2. 访客收到 memory_reference_receipt（MetaEvent）→ signalCount=1、lastSignalKey=`first_memory_referenced`、消息照常落态且 receipt 可渲染；
3. 普通回复（负路径）→ 不记录；
4. receipt 空引用（负路径）→ 不记录；
5. 注册用户两信号同屏投喂 → 全程 no-op（免费闭环零变化）。

**回归（全部 PASS）**：guest_conversion_provider_test 5、guest_conversion_service_test 3、guest_conversion_card_test 5、chat_notifier_stream_test 8（同 harness 先例）、chat_screen_basic_test 24（chat 挂载渲染回归）。

**analyze**：7 个改动文件定向 analyze，新增问题 **0**（余留 65 条均为既有：chat_screen 既有 info 群、chat_provider:30 directives_ordering 与 :359-360 discarded_futures、chat_notifier_actions:687/744——均已用 git diff hunk 比对确认不在本次改动行）。

**环境补齐**：`flutter pub get` + `buf generate --template buf.gen.dart.yaml`（gen/ 重生成，不入库项）；gen-l10n 重排已按卡令 `git checkout -- mobile/lib/l10n/` 还原，未入库。

## ④ 资源峰值

- 测试错峰合规：每次 flutter test 前 swap 空闲 1.2G+（1.42G/1.29G/1.21G 三次实测）、`pgrep` 确认无并行 flutter test、`--concurrency=1` 单进程。
- 内存：纯 dart test 无模拟器/gradle/浏览器实例，未触发 HEAVY 门。
- 磁盘：开工时 / 剩 9.2G；收工已删 `mobile/build`（123M）与 `.dart_tool`（132K）；/tmp 无本卡产物（`sparkle_engine.log` 等为其它进程产物，未动）。

## ⑤ 交接建议

1. **A/B 数据面**：`lastSignalKey` 已可区分三类价值信号的最后触点；后续做转化漏斗时建议在 guest_upgrade 提交事件里带上「注册前最后一个信号 key」，即可量化「诊断产出 vs 记忆引用 vs 任务完成」谁的转化话术最强（N48 A/B 的素材）。
2. **modeling 落点留白**：若未来开放访客建模路径（如 N49 破冰令把建模访谈对话化），firstDiagnosisOutput 需在 modeling_chat_screen 的 `modeling_complete` 处补第二个触发点——判据与形制已备好，3 行接线。
3. **首渲染语义的强化余地**：当前 firstMemoryReferenced 以「回复送达」为准；若产品要严格对齐「用户看见了 receipt 芯片」（受透明度设置 showMemoryReferenceReceipts 门控），可在 ContextReceiptBar 挂载处加去重守卫后前移——收益存疑（关掉 receipt 的用户本就选择了低透明度），不建议现在做。
4. **转化卡 chat 挂载的曝光面**：chatHeaderPanels 槽上限 20% 视口高，卡完整可显；若后续数据表明 chat 面曝光过度（访客高频停留 chat），可加「每会话 chat 面最多渲染一次」的会话内去重，改动点仅在挂载处。
5. **合入注意**：改动手过 chat_provider/chat_screen 两个热点文件，apply --3way 后建议重跑 `chat_value_signal_test.dart` + `chat_notifier_stream_test.dart` + `chat_screen_basic_test.dart` 三件（对比法）。

## 收工核查

- [x] 主仓只读未动；无 push/stash/reset/clean（l10n 纯格式还原按卡令执行 `git checkout -- mobile/lib/l10n/`）
- [x] 分支本地 commit（不 push）；import 修改全走 Read+Edit
- [x] mobile/build、.dart_tool 已删；/tmp 无自产物；无模拟器/浏览器实例
- [x] 测试全部单文件单进程、错峰执行；交付物 = 本 REPORT.md + changes.patch + worktree 本地 commit
