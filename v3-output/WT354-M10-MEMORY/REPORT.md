# M-10 REPORT — Memory/Aurora UI 全链集成（wt354）

- **Worker**: wt354（卡 M-10，stream=MEMORY，gate=V3-4，risk=high，resource=HEAVY，reviewers=2，lock=memory-ui）
- **Worktree**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt354-m10-memory`
- **Base SHA**: `f9f0ae7a`（发车时 main）/ **Final SHA**: 见本分支 `wt354-m10-memory` 提交
- **Status**: **READY_FOR_REVIEW**（定向 flutter test 因 swap 门 DEFERRED，见 §6）
- **前序依赖**: M-08（cbd7e44d，后端 provenance API，双证已合并）/ U-03（295fd59a+8c6797fc，理解面五动作，已合并）/ M-09（7d1eedd3，评测套件，已合并）
- **纪律声明**: 主仓只读；gen 三件套按 `-L` 只读复制（mobile/backend/gateway，gitignored 不入 patch）；零模拟器/零 Gradle/零浏览器；`flutter test`/`pytest` 未跑（前者 swap 门未开、后者本卡零后端改动无跑点）；mock 仅存在于测试替身（合法），产品链路全部真实端点。

---

## 0. 接缝缺口盘点（动手前完成，两个前序交付的 seam）

| # | 缺口 | 证据 | 本卡处置 |
|---|---|---|---|
| G1 | chat 引用回执（`memory_reference_receipt.dart`）只有快捷"不对"（旧 `/memory/correct` lower_confidence），**无任何入口进入 U-03 权威理解面**。U-03 报告 §8.3 明示"chat 流内回执深链属 chat 卡"=本卡 | 该文件 `_markWrong` 走 `memoryApiService.correctMemory` | 已接：每条引用行新增「为什么有这条」→ 弹 U-03 why-this receipt（真实 `POST /memory/provenance/why-this`），内含来源/选中原因/治理历史 + 真实纠正环（supersede→失效链→全个性化面重算） |
| G2 | home「Sparkle 懂我」面板与 chat 理解抽屉**都无入口**到 `/memory/understanding` 完整视图 | 两文件无任何导航边 | 已接：面板底部「查看完整理解」固定入口；缺省 `context.push(MemoryRoutes.understanding)`；模态 sheet 场景（chat 抽屉）由调用方传先关 sheet 再导航的闭包 |
| G3 | **诚实性红线缺口**：U-03 的 `_syncAfterMutation` 只 invalidate home/chat 理解快照一个 provider；dashboard 理解快照卡（experience 面，`UnderstandingSnapshotCard` 上屏于 dashboard_screen:1005）与 persona/透明档案/推断偏好（profileContext/transparentProfile/inferredPreferences）**删改后继续展示旧个性化** | experience_provider.dart:5、persona_view_provider.dart:4、profile_context_provider.dart:3 三个 provider 均不在 U-03 失效链内 | 已接：mutation 同步链扩为五面全失效（§2） |
| G4 | chat 两处回执行的置信**百分比黑话**（`chatMemoryConfidencePercent(91%)`）与 U-03 黑话移除决定相悖（模块文档「不是数据库管理器」） | memory_reference_receipt.dart:329、aurora_receipt_chip.dart:876 | 已改：定性层级词（高置信/中置信/低置信），阈值与后端 `_confidence_label` 同口径（0.75/0.45）；死键 `chatMemoryConfidencePercent` 五文件外科手术移除（wt350 死键收割同款手法，实跑 gen-l10n 会引入 ~430 行格式噪声故手工） |
| G5 | Gateway 侧 `/memory` 为纯鉴权代理（proxy_routes.go:1043-1048 `registerREST(memory,"/*path")`），无记忆缓存——GJ08/GJ09 的网关腿=透传零存储 | 代码定位 | 报告声明，无需改动 |

## 1. Work 1 — 接 U-03 到真实 API + chat/home why receipt 深链

- **chat 引用回执 → 对应理解**：`_MemoryReceiptRow` 新增 `_openUnderstanding()`——按 C-01 `memory://<kind>/<id>` 方案从引用行构造最小真源指针（kind 缺省 episodic 与后端 `_parse_kind` 域一致），先关回执 sheet 再经根 navigator 上下文打开 `unawaitedWhyThis`（复用 U-03 `why_this_receipt_sheet`，零新真源）。条目已被删除/跨用户时后端 404/422 → sheet 显示诚实的 whyThisLoadFailed，绝不本地编造回执。该 sheet 内「这不对」→ `updateItem`（真实 supersede）→ 走 §2 全量同步链。
- **home 面板/chat 抽屉 → 完整理解**：`UnderstandingPanel` 新增 `onOpenFullUnderstanding` 回调 + 底部固定入口；缺省直接 push 权威路由；`ChatUnderstandingDrawerButton` 的 sheet 传「pop 后 push」闭包。home dashboard 用缺省路径，**dashboard_screen.dart 零改动**（避开 wt353 shell 面）。
- 语义统一：入口文案复用 U-03 既有 `understandingActionWhy`（"为什么有这条"），全产品同一句话指同一真源——用户无需理解 Memory 内部结构。

## 2. Work 2 — 修改/删除后自动重算当前个性化（acceptance 红线）

`understanding_overview_provider._syncAfterMutation` 扩展为五面全失效（cascade）：

1. `understandingSnapshotProvider`（home/chat「Sparkle 懂我」面板，U-03 既有）
2. `experience.understandingSnapshotProvider`（dashboard 理解快照卡；两 provider 同一后端路径 `/experience/understanding-snapshot`，但都是独立客户端缓存，**都**必须失效）
3. `profileContextProvider`（persona/画像面 `/profile/context`）
4. `transparentProfileProvider`（透明档案 `/profile/transparent`）
5. `inferredPreferencesProvider`（推断偏好 `/profile/inferred-preferences`）

**诚实性论证（删除后当前/未来个性化正确变化）**：
- **当前（客户端呈现）**：五面失效重取=用户在任何 surface 看到的个性化都是删除后的新态；provider 级测试钉住（§5）。
- **未来（引擎侧）**：M-07/M-08 既有权威链在变更事务内 bump `memory_epoch`+发 `memory.invalidated`+DEL derived cache（profile_context/inline_snapshot/prefs_center/aurora self_model/context snapshot），读侧 epoch 门兜底——下一次 ContextPack/decision 必然新数据（M-08 21 定向测+变异 A/B/C 必红已双证，非本卡重建）。
- **发现并如实登记（不改）**：chat 快捷"不对"（lower_confidence）按 epistemic contract（`EPOCH_BUMP_CORRECTION_ACTIONS` 钉死不含 lower_confidence，test_memory_epistemic_contract.py:180）是**有意的软信号**（置信微调不 bump epoch 不 DEL 缓存）。本卡不弱化该契约，而是让权威纠正环（supersede/revoke，全失效链）从回执直接可达——快捷旗标保留为降噪审计信号，真实纠错走深链入口。

## 3. Work 3 — 视觉与 copy 终审

- 置信百分比黑话两处清除（G4）；层级词复用 `understandingConfidenceHigh/Medium/Low`（零新键）。
- 新键仅 1 个：`understandingPanelOpenFull`（zh「查看完整理解」/en「See the full understanding」），arb+三生成物五文件同步，锚点与插入序均按 gen-l10n 输出形态（L10N-PARITY 守卫绿实证）。
- UI 全 owner 组件/DS token（TextButton.icon/Icons.arrow_outward_rounded 既有用量先例），零裸组件，未碰 design owner 与令牌（wt353 战区零触碰：main 增量 21 文件与本卡 14 文件零交集，已 comm 核验）。

## 4. 变更清单（14 文件）

产品（5）：memory_reference_receipt.dart / aurora_receipt_chip.dart / understanding_drawer.dart / understanding_panel.dart / understanding_overview_provider.dart
l10n（5）：app_zh.arb / app_en.arb / app_localizations.dart / app_localizations_zh.dart / app_localizations_en.dart（增 1 键删 1 死键，净 -1 info）
测试（4）：understanding_overview_provider_test.dart（+M-10 五面同步测试+计数客户端扩 3 路径）/ memory_reference_receipt_test.dart（+深链测试+copy 测试+why-this 假客户端）/ aurora_receipt_chip_test.dart（+copy 测试）/ understanding_panel_copy_test.dart（+回调入口测试+真路由 push 测试，断言新入口存在）

## 5. 验证与证据

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **exit 0（83 条，基线口径；主仓已升 84 条系 wt351 GOFMT-GW 合入，合并态以 84 复跑）** |
| `flutter analyze`（worktree，pub get 后全量） | **E0 / W15 / I586**（预算 E42/W16/I594±5；基线 I587，净 -1 来自死键移除；两处 inference_failure 警告为主仓 understanding_panel_copy_test.dart:30-31 预存同款，行号平移非新增） |
| `check_flutter_analyze_gate.py --project-dir mobile`（TOLERANCE=5） | **PASSED** |
| 冷 mypy（rm -rf .mypy_cache → venv mypy app） | **1278 = 棘轮基线零推高**（后端零改动，同数自证环境一致） |
| 定向 pytest | 不适用（本卡零后端代码改动；后端失效链证据=M-08 已合并测试 test_memory_provenance_api.py 1171 行 + test_memory_epistemic_contract.py 契约钉） |

## 6. DEFERRED（内存门，附补跑面）

- **swap 现场实测**：开工 894M→收工 926M free（门=1.2G），load 4.4-6.3；全程三次探测均未开门，按纪律不跑。
- **补跑命令**（swap free≥1.2G 时，主会话整合管线 §5-4 或 reviewer 执行；`--concurrency=1` 串行）：
  ```bash
  cd <wt>/mobile && flutter test test/features/memory/presentation/providers/understanding_overview_provider_test.dart --concurrency=1
  flutter test test/features/chat/presentation/widgets/memory_reference_receipt_test.dart --concurrency=1
  flutter test test/features/chat/presentation/widgets/aurora_receipt_chip_test.dart --concurrency=1
  flutter test test/widget/understanding_panel_copy_test.dart --concurrency=1
  ```
  回归面（既有批，按余量选跑）：memory 面系列（panel_v2/evidence_cards 46 例等）。
- **已做代偿**：四测试文件 analyzer 0 错误（类型/引用/装配静态可证）；测试断言文案逐条与 arb 键值/源码渲染行核对（whyThisSheetTitle/whyThisInUse/understandingActionWhy/understandingConfidence* 逐一 grep 实值）。残余风险=widget 运行时行为（tap 后 sheet 叠栈/路由跳转），已在断言设计上取最保守形态。
- **GJ08/GJ09 三端**：引擎+网关腿=既有证据（M-08 失效链测试、网关纯代理定位）；移动端 API/状态层=本卡测试（DEFERRED 待跑）；**模拟器端到端腿（GJ08 纠正→下一会话适配 / GJ09 删除→缓存失效→不复活的可视走查）按 HEAVY 门 DEFERRED，候窗口，不静态阅读宣称 UX 通过**。

## 7. 合并态须知（给主会话）

1. 本分支 fork 于 f9f0ae7a；main 已前进至 45896c5d（wt348/351/352/353/357）。**与本卡 14 文件零交集**（comm 核验），apply --3way 预期零冲突；但 wt353 动了 core/design（本卡 UI 的依赖面），合并态需复跑 analyze 门+定向测试（§12-8 精神）。
2. 守卫数基线已 83→84（GOFMT-GW），合并态复跑按 84。
3. worktree 内 `.dart_tool` 保留（补跑 DEFERRED 测试即取即用）；`.mypy_cache` 已删（防未来冷测被热缓存污染）。

## 8. 诚实申报

1. 定向 flutter test 与模拟器证据 DEFERRED（§6）——不因 DEFERRED 宣称"测试全绿"；树内静态可证部分（analyze/mypy/守卫/l10n 奇偶）全部实跑。
2. 快捷"不对"（lower_confidence）与权威纠正环并存是**产品现状**（A-06/wt311 设计+epistemic contract 钉死），本卡未改其语义，只把权威环变得可达；若产品判定快捷旗标也须走全失效链，应立新卡改契约（牵动 test_memory_epistemic_contract 钉）。
3. home 面板的 correctClaim（experience 自模型纠正通道）与 provenance 通道是两个真源域（self-model 假设 vs 记忆记录），本卡只接记忆域深链，未合并两域（合并=重建真源，Forbidden）。
4. experience 理解快照卡（UnderstandingSnapshotCard）语义标签仍有 "可信度 X%" 文案（另一黑话点）——不在本卡锁（features/experience）且其屏消费面属 dashboard；登记为后续 copy 卡输入，未越锁改动。
