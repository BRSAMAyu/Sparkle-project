# V4-S03 — diff_or_evidence_only

## 结论一句话

haptic-policy 锁面按「缺失面最小增量落地 + 既有满足面差量举证」完成：新增 `core/design/semantic_haptics.dart`（能力探测封闭表 + 乐谱触觉列四槽 → HapticFeedback **官方 API** 一枚映射 + 六序纯门裁决[偏好→能力→重播→相位→native双震→同槽去重窗]，每抑制面一个具名原因）；F03 适配器默认出口 `SensoryFeedbackSink` 触侧升格接线到锁面派发器（声侧零变化继续走既有服务 `enableHaptic: false`——声/触各只有一条物理出口，无第二震动路径）；22 个新测试每验收面一正一反（关闭偏好钉 / 去重窗反例钉 / pending·unknown 反例钉 / 重播钉 / nativeHandled 钉 / 源码棘轮）+ F03×真方法通道集成面（模拟器只认调用证据的口径面）；`flutter analyze` 全库零 issue，受影响域 design 261 / experience 19 / services 98 / 消费方 20 / q03+home 139 全绿，88 条治理守卫过；真机触感舒适度未测，全量记 DEVICE_UNVERIFIED（归 Q06 真机面）。

## 差量明细（相对 base c3baf168 = 开卡时 main HEAD）

产品码（1 新 + 1 改；RF-06 三冲突面、`app/routes.dart`、backend/、proto/、迁移、gen 产物、l10n arb 零触碰）：

- `mobile/lib/core/design/semantic_haptics.dart`（新，+389/−0）—
  **haptic-policy 锁面单一权威**：
  - 能力探测：`resolveSparkleHapticCapability(TargetPlatform)` 纯函数封闭表——iOS/Android 判支持；macOS/windows/linux/fuchsia 保守判**不支持 → 静默保持文本**（乐谱「不支持则不震，不能拿蜂鸣替代」；macOS 触控板留真机面证实后再入表，取「少震」不取「无证据触觉承诺」）。
  - 离散语义触觉：`SparkleSemanticHapticSlot` 封闭四槽（selection/lightImpact/success/warning）↔ `kSparkleSemanticHapticPatterns` 每槽映射 **Flutter `HapticFeedback` 官方 API 恰一枚**（selectionClick / lightImpact / successNotification / warningNotification——乐谱「系统success一次」「system warning一次」的官方语义载体；iOS 引擎侧 UISelectionFeedbackGenerator/UINotificationFeedbackGenerator，Android 侧 HapticFeedbackConstants）。**不造自定义震动语言**：无组合脉冲、无原始波形、无 amplitude 调制（源码棘轮测试钉死：禁 `Future.delayed`、禁 `SystemSound`、禁原始通道字符串直调）。
  - 相位门：`SparkleHapticPhase` 五相 + `kSparkleHapticSlotPhases` 封闭表——**pending/unknown 不在任何槽的放行集**（卡验收 2 结构面），success 槽恒 `{terminalSuccess}`（有 committed 回执的终态），warning 槽恒 `{terminalFailure}`（明确操作失败）。
  - 纯门 `SparkleSemanticHapticGate.decide` 六序裁决，每面一个具名 `SparkleHapticSuppression`：`userPreferenceOff`（U14 偏好面唯一权威）→ `platformUnsupported` → `eventReplay`（恢复重放不重复震；F03 event_id 抑制之外的触觉通道第二道防线）→ `phaseNotHapticEligible` → `nativeFeedbackAlready`（调用点声明框架/平台此处已有系统触觉——Material enableFeedback、日期/时间选择器滚轮、文本选择、长按菜单——避免双震）→ `dedupedWithinWindow`（同槽 500ms 短窗，同类事件不重复触发；按压/成功是不同槽不受合并——乐谱「两者不可合并」由槽位分离保证）。
  - `SemanticHapticDispatcher`：唯一震动出口 `SparkleHapticChannel`（默认实现=官方 HapticFeedback API；测试注入记录器）+ 去重窗状态（可注入时钟）+ 可观测计数（firedCount / firedByPattern / suppressedBy）。偏好读取默认直连 `SensoryFeedbackService.isHapticEnabled`（U14 写入门控的同一持久键单源——不造第二权威，无装配=读真权威）。
- `mobile/lib/core/experience/experience_feedback_adapter.dart`（改，+50/−5）—
  默认出口 `SensoryFeedbackSink` 触侧从「委托既有服务（声触合一）」升格为：声侧 `SensoryFeedbackService.emit(…, enableHaptic: false)`（S02 音频策略面零变化）+ 触侧 `SemanticHapticDispatcher.instance.dispatch(...)`（成功槽恒 terminalSuccess / 选择槽 userInitiated / 警示槽 terminalFailure——相声明强制显式，无默认终态）。适配器仍是唯一事件入口：声、触各只有一条物理出口。库头注释同步改写（F03 原「触经既有服务」路径由本出口升格接管）。注入型测试（F03 既有 19 用例）不受影响，全绿复证。

测试（1 新文件，22 用例；每验收面一正一反 + 通道级集成）：

- `test/core/design/semantic_haptics_s03_test.dart`（22）—
  A± 偏好门（验收 1）：U14 开→1×successNotification；**关→0 通道调用+具名 userPreferenceOff**（默认读取器=SensoryFeedbackService 同键单源的真实性自证；关→开翻转后立即可震，钉门序语义）。
  B± 重播门：首派放行；**isReplay=true→0 调用+eventReplay**（恢复重放不重复震）。
  C± 相位门（验收 2）：终态成功/失败各归 successNotification/warningNotification；**pending×4 槽全拒 / unknown×4 槽全拒 / 成功槽配 userInitiated 相拒**（success pattern 不可误用的反例钉）。
  D± 能力门：iOS/Android 支持；**桌面/web 四平台全拒+pattern=null**（不支持不蜂鸣替代）；纯函数全表断言。
  E± native 双震门：nativeHandled=false 放行；**true→0 调用+nativeFeedbackAlready**。
  F± 去重窗：窗外再发放行（去重≠禁震）；**窗内同槽二次抑制（共 1 次）**；跨槽不合并（selection 后窗内 success 都放行——按压/成功不可合并）。
  G 映射与棘轮：四槽↔官方模式表逐键断言+每槽恰一枚；相位表 pending/unknown 零放行集结构性钉；**源码棘轮**（锁面文件剥注释禁 `Future.delayed`/`SystemSound`/原始通道字符串直调）。
  H 集成面（F03 适配器 × 默认出口 × SystemChannels.platform 真方法通道 mock——**模拟器调用证据**）：committed 任务事件→通道恰一次 `HapticFeedback.vibrate:HapticFeedbackType.successNotification`；**同 event 重播→0 新增调用**；**版本未知→0 调用**；**U14 关闭→视觉照常（presentSuccess）但触觉 0 调用**（通道级反例钉）。

## 验收逐条自证（卡面原文 → 机器证据）

1. **「无用户同意/已关闭/重播=0触觉调用」** — 已关闭：A−（门级，偏好=false→0 调用）+ H-偏好关（通道级：committed 事件视觉照常、`hapticCount==0`、instance 计数 userPreferenceOff=1）；无用户同意=同一门（偏好未开启即无同意，fail-safe 同向）。重播：B−（isReplay 位→0）+ H-重播（通道级：适配器 replaySuppressed→0 新增通道调用）。反例钉：A+（开→1 调用）与 B+（正常首派→1）证明断言非恒真。
2. **「pending/unknown不误用success pattern」** — C− 反例钉（pending/unknown×四槽全拒+成功槽相错配拒）+ G 相位表（pending/unknown 不在任何槽放行集——结构面）+ H-版本未知（通道级 0 调用）。正例：C+（terminalSuccess→successNotification / terminalFailure→warningNotification）。
3. **「模拟器调用正确与真机舒适度分开出具结论」** — 模拟器/测试环境结论=**调用级正确**（本套件 22 用例：门控/模式选择/通道调用计数全绿）；真机触感舒适度=**DEVICE_UNVERIFIED**（本环境无物理设备，未测；归 Q06 真机面，乐谱明文「模拟器可测调用/去重/静音，不能证明硬件触感舒适」）。两层结论在 run_manifest.json `evidence_scope` 与 limitations.md 分开出具，不互相冒充。

## 目标三件事自证（objective → 机制）

- **封装系统能力探测**：D 组（探测纯函数封闭表+派发器接线+四平台反例）。
- **离散语义触觉（平台惯例映射，不造自定义震动语言）**：G 组（表值=官方七 API 枚举直引、每槽恰一枚）+ 源码棘轮（无组合脉冲/无蜂鸣/无原始通道调）。
- **native已有反馈避免双震；不支持时静默保持文本；事件重播不震**：E 组（nativeHandled 具名钉）+ D 组（不支持→0 调用且 pattern=null，无任何声音替代）+ B/H 组（重播 0 调用）。

## 既有满足面差量举证（no_duplicate_rule）

- 偏好门控本体（`sensory_feedback.haptic_enabled` 持久键+设置面开关）= U14 已落（`accessibility_provider.dart` → `SensoryFeedbackService.setHapticEnabled`），本卡**不重写不另立**，只把锁面读取器直连该权威并补通道级反例钉。
- 事件级重播抑制（event_id 去重集合）= F03 已落，本卡保留为第一道门，锁面 `isReplay` 位为触觉通道第二道独立防线（防御纵深，非替代）。
- V3 UI 词表触觉映射与成就双脉冲 = V3 已 DONE 快照继承（卡 rollback 条款「保留 V3 路径」），本卡不重写；V4 语义面（experience_event 呈现链）一律经本锁面。
- 动效节奏归 S01（motion-policy）、音频归 S02（audio-policy）、偏好键归 U14（ui-settings）——本表面零跨界改动（与在航 S02 的 sensory_feedback_service.dart 音频区改动零文件交集，merge 面仅适配器触侧出口一处语义衔接）。

## 红线自证（diff 逐面）

- **RF-06 三冲突面零触碰**：`git status --short` = 1 新产品码 + 1 新测试 + 1 适配器改；dashboard_screen / compact_status_bar / task_execution_screen / app/routes.dart / backend/ / proto/ / 迁移 / gen 产物零命中。
- **l10n 零触碰**：本卡无文案面（触觉无 UI 字；不支持=静默保持文本）；arb/生成物零 diff（S01 同例）。
- **不另立第二权威**：偏好键零新增（直连 U14 同键）；官方模式表是 haptic-policy 唯一映射权威且唯一消费点为 F03 默认出口；V3 服务触觉物理出口不动（V3 路径向后兼容）；物理震动出口在 V4 语义面只有 `SparkleHapticChannel` 一处。
- **参考图=提案非批准**：本卡零视觉资产消费；REFERENCE_ONLY.jpg 零引用。
- **classic 零差量声明**：本卡零像素组件调用点。

## 复跑清单（全绿实录见 run_manifest.json / test_results.json）

`flutter analyze --no-pub`（No issues found!，全库）；新套 22/22；`flutter test test/core/design/` 261/261；`flutter test test/core/experience/` 19/19；`flutter test test/core/services/` 98/98；消费方 6 套 20/20；`flutter test test/goldens/q03_visual_qa/ test/features/home/` 139/139；`bash scripts/run_all_rule_guards.sh` 88 规则全过。
