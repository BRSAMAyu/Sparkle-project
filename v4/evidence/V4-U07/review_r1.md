# V4-U07 · 一审 receipt（独立审查 wtU07R1）

- 审查会话：wtU07R1（未参与 U07 实现）
- 审查对象：分支 `agent/v4/u07`，实现 commit `d798b321`，基线 `e50107fe`（审查时工作树干净，与实现 commit 一致）
- 审查日期：2026-09-29
- 裁决：**PASS_WITH_CHALLENGES**（实现实质成立；3 项挑战，其中 C-1 为合并前应修正的证据数字勘误，C-2/C-3 为登记类不阻塞项）

## 0. 独立复跑记录（全部亲验，非转抄）

| 命令 | 实测结果 | 与自述对照 |
|---|---|---|
| `flutter test`（7 个新套件全量，含 evidence capture） | **36 passed**（末行 `+36: All tests passed!`） | 一致（34+2） |
| `flutter test test/features/chat test/unit test/core/widgets` | **595 passed + 1 skipped**（末行 `+595 ~1: All tests passed!`，exit 0） | **不一致**：自述 593+1skip，实测多 2（见 C-1） |
| `pytest backend/tests/unit/test_deterministic_lane.py -q` | 49 passed | 一致 |
| `pytest backend/tests/unit/test_semantic_selector.py -q` | 77 passed | 一致 |
| `flutter analyze` | No issues found! | 一致 |
| `bash scripts/run_all_rule_guards.sh --rule UI-TOKENS` | PASS（color=225/275, fontSize=634/727） | 一致（数字逐字同） |
| `flutter gen-l10n` 后 `git status/diff` | **零漂移**（无 U03 类 arb↔gen 漂移） | 一致 |
| `shasum -a 256 ui/`×4 | 与 run_manifest.artifacts_sha256 四条全等 | 一致 |
| classic 零差量对照探针（临时文件，跑完即删，未入库） | 3 项全 PASS（见 §3） | 声明成立 |

## 1. 预登记挑战逐项独立裁决

### R-1 中段阅读无回底入口 → **不属本卡面（挑战成立但出卡）**
按卡文本裁决：objective =「上滑后不自动拉回，保留中断内容」，验收三条均不含「跳最新」入口；规范源 `v4/02_design/SCREEN_FAMILIES.md:7`（「增量不抢滚动；用户上滑后保持位置」）同样未要求显式回底入口。基线本就无该按钮（旧行为是到达即拉回，恰是本卡要移除的），故无回归。limitations L3 已诚实登记。**结论：不阻塞；建议立独立微卡（新组件克制原则下走卡派发，不并入本卡）。**

### R-2 `next.last.role==user` 判显式动作的完备性 → **枚举有漏，影响有界（见 C-2）**
独立枚举 `sendMessage` 全部调用面（`grep -rn "\.sendMessage(" mobile/lib`，24 处）：普通发送/快捷动作/纠正/建议选项/initial prompt/modeling 输出/离线重投（chat_screen.dart:1968 `onRetryDelivery` 走全量追加路径）→ 均追加用户消息 → force 生效。**发现一处漏网**：`retryLastMessage`（chat_provider.dart:2334）→ `sendMessage(reuseLastUserMessage: true)`（chat_provider.dart:2349）——当失败轮把用户消息留在末位（纯连接失败、无部分内容保留）时 `canReuseLastUserMessage=true`（chat_provider.dart:1049），**不追加新用户消息** → messages 监听（chat_screen.dart:248-251）不触发 force。预登记自述「重试…均触发 force 滚动」**对该 reuse 路径不成立**。影响有界：重试按钮挂在上报错误气泡（列表最新端）上，用户能点它时大概率仍在 240px 跟随窗内；且重试应答到达不拉回与「增量不抢滚动」语义一致。会话切换 `jumpTo(0)`（chat_screen.dart:2830）绕过 `_scrollToBottom` 门但经滚动监听把锚复位为跟随（pixels=0 ≤ 240），无悬挂态。

### R-3 「已满足」判定的判别力抽验（本审最重靶）→ **判定成立（mutation 3 发全红）**
对验收 1/2/3 的冻结测试各做一发实现侧 mutation（改后跑、录红、`git checkout` 还原，未留痕）：
- **M1**（验收 1）：`mobile/lib/core/widgets/sparkle_markdown.dart` `_buildMarkdownBody` 返回值包进 `Row(mainAxisSize: min)`（模拟「换行被移除」这一验收防的真实回归类）→ `sparkle_markdown_200_scale_test.dart` **4/6 红**（长中文/代码/公式/表格全抓到；余 2 绿 = 对照 Row 例与…实测 +2 通过）。
- **M2**（验收 2）：`assistant_citation_strip.dart:175-177` `onPressed: documentRoute == null ? null : …` 改为 `? () {}`（未知引用变可点）→ `assistant_citation_honesty_test.dart` **2 红**（两个反例 `onPressed isNull` 断言全触发；正例仍绿）。
- **M3**（验收 3）：`chat_state.dart` `shouldShowPhaseCapsule` 去掉 `&& !isDeterministicLane` → `chat_lane_semantics_test` + `chat_notifier_lane_capture_test` **2 红**（快路轮「反：不进三段胶囊」两断言触发）。
**结论：验收 1/2「既有已满足，差量举证」的冻结测试非恒绿，判定有牙，R-3 关闭。** 附注：200% 套件对照组（无约束 Row）在任意缩放下都溢出，证明的是断言 Harness 抓溢出而非「200% 特异性」；该缺口由 M1（真实产品码 mutation × 200% 场景）补足。

### R-4 快路空白槽是否需中性占位 → **不需（现状可接受）**
三段胶囊对零模型模板轮即「假进度」，正是验收 3 禁止物；空白槽是诚实的直接语义后果。窗口 = 发送→首帧（L4 自述通常 <100ms），期间输入栏发送态在场。中性占位（如无相位语义的微光）属可选打磨，不构成本卡缺陷。**不阻塞。**

## 2. 验收三条对证据核

1. **200% 不破屏**：6 测 = 4 正面（长中文/代码块+横滚消化路径在场断言/公式 LaTeX+无空格长 token/表格混排）+ 对照 Row + 288 紧约束面。真实 360 逻辑宽 × `TextScaler.linear(2.0)`；M1 证明有牙。**核通过。**
2. **引用诚实**：正例真实 GoRouter 导航到 `/tasks/:id` 渲染 `TASK-DETAIL:task-123`；反例×2（外部 url-only / 无目标+伪造 `sparkle://not-a-real-type/xyz`）断言 `onPressed == null` 且摘录在场；M2 证明有牙。ui/ 截图与语义树（「前往文档」节点 isButton=true 由测试钉 onPressed==null，语义树不携带禁用位——测试断言补位，成立）与自述一致。**核通过。**
3. **ack 与首有用内容区分 + 慢任务不循环假思考**：provider 级真实事件流捕获（真 ChatNotifier + 桩仓库：状态帧先行 → lane 捕获 → 等待期 `shouldShowPhaseCapsule=false` → 模板 delta → 终帧消息 rawMetadata 收口 → run 终态清零）；呈现层 marker 正反 4 测（未知形态词不透传）；集合外 lane（`warp_speed`）与无键轮（I09 关）保持旧三段胶囊；慢路胶囊继续走 S18 既有语义（真实状态帧驱动+已等待时长+可取消，非客户端合成循环——本卡 delta 仅快路排除，已核）。词表消费端封闭集与引擎侧逐字一致（`backend/app/agents/standard_workflow.py:1668-1669`、`response_builder.py:1035-1037`、`deterministic_lane.py:52-57`：greeting/acknowledgment/farewell 三值）。**核通过。**

## 3. classic 零差量声明核（对照探针，用后即删）

临时探针（`mobile/test/unit/zr1_u07_classic_zero_delta_probe_test.dart`，跑完 `rm`，未 commit）三断言：
1. 无 lane 状态矩阵上 `shouldShowPhaseCapsule` ≡ 旧表达式 `hasActiveRun && streamingContent.isEmpty`（5 组状态逐值等价）；
2. 无 metadata 帧（null/空 map/仅他键）→ lane/kind 全 null、`isDeterministicLaneReply=false`、state 字段 null；
3. `chat_lane=model`（真模型慢路）→ 胶囊照旧、不标即时回复。
**全 PASS，声明成立。** 产品码 diff 复核：7 文件中 6 文件纯新增；chat_screen.dart 删除 7 行全部是「被门/扩展表达式替换」（`_scrollToBottom()` 三处→force 版、胶囊两处布尔→`shouldShowPhaseCapsule`、方法签名改带参）——「全 additive 或门内扩展」措辞成立。diff 无 backend/proto/迁移/`*/gen/` 手改/.env；`tasks.json` 仅 status/implementation_state 状态位（PENDING→in_progress / REVIEW_READY），沿用既有 state commit 判例。

## 4. 滚动锚行为核

- 4 测中 3 个为真实 reversed ListView + 真实拖拽物理（含卡面核心反例：上滑 600px 后新内容到达 offset 不变、阅读位保留断言到具体像素值）；`chat_screen._handleScroll` 在历史预载 early-return **之前**更新锚（chat_screen.dart:1322-1325），与预载共用 240 档（`position.pixels >= maxScrollExtent - 240`，同值常量）属实。
- 测 4（forceFollow 恢复跟随）偏弱：直接调 `anchor.forceFollow()` 而非经 `_scrollToBottom(force: true)` 全链，且未断言随后的真实滚动——「发送路径」仅语义钉、非端到端。
- L2 豁免（未 pump 完整 ChatScreen）：接线 6 处逐一读 diff 核实在场（chat_screen.dart:42 import、190-193 锚字段、245-251 监听区分、869-872 定位回退 force、972-975 回横幅 force、1319-1325 锚更新、1784-1901 两处胶囊分支、3016-3030 门）。4200 行屏 + 全 provider 栈下豁免理由**成立**，残余风险（未来直接 `animateTo` 绕门不红测）已如实披露；但 L2 自述「grep 钉当前仅 3 处滚动调用点（见 diff_or_evidence_only 红线自证）」**两处失准**：红线自证节并无该 grep；实测 `_scrollToBottom` 调用点 4 处 + `jumpTo(0)` 1 处（见 C-3）。

## 5. 测试质量与数字诚实性（发现 3 处失准，均非实现缺陷）

- **36 分解核对**：14（lane 语义）+3（notifier 捕获）+4（滚动锚）+6（缩放）+4（marker）+3（引用诚实）+2（evidence capture）= 36 ✓，与亲跑一致。
- **C-1（应修正）产品码与回归两个口径不符**：
  - 自述「产品码 6 文件 +201/-7」；实测 `git diff e50107fe..d798b321 --numstat -- mobile/lib/features` = **7 文件 +252/−7**（chat_message_model +44、chat_provider +25、chat_scroll_anchor +44、chat_state +27、chat_screen +37/−7、assistant_lane_marker +63、chat_bubble +12）。任何子集都无法凑出 201；同文档差量表本身列的就是 7 行且行值准确，仅表头与 run_manifest `scope_and_denominator.mobile_product_diff` 口径错。
  - 自述回归「593 passed + 1 skip = 594 collected」；本审在交付树（工作树与 d798b321 一致、探针已删、gen-l10n 零漂移）上同命令实测 **595 passed + 1 skip = 596 collected**。Δ=+2 恰等于 `u07_evidence_capture_test.dart` 的 2 个恒执行测试——疑为该文件补入后未刷新回归口径（test_results.json `totals.regression_tests=720` 同步变 722）。方向是「比声称多、全绿」，非掩盖，但 evidence_required 的 scope_and_denominator 应可复算。
- **C-3（登记类）**：L2「仅 3 处滚动调用点」失准（实为 4+1，且引注悬空）；滚动锚测 4 强度弱于其余三测。
- 其余数字全数对上：I09 49 / I03 77、analyze 0、UI-TOKENS 棘轮数字逐字一致、ui 四件 sha256 全等。

## 6. l10n 一致性

arb×2 各 +4 键（chatInstantReply/chatLaneKindGreeting/chatLaneKindAcknowledgment/chatLaneKindFarewell，中英对齐）；gen×3 为 gen-l10n 产物——本审重跑 `flutter gen-l10n` 后 `git status` 零漂移，无 U03 类 arb↔gen 漂移。**核通过。**

## 7. 裁决与条件

**PASS_WITH_CHALLENGES** —— 四个可失败增量真实、可失败、classic 零差量成立、I09 消费契约两端未漂移、验收 1/2「已满足」判定经 mutation 证实有判别力。

- **C-1（合并前修正，纯证据勘误不动代码）**：将 `diff_or_evidence_only.md` 表头、`run_manifest.json` scope_and_denominator、`test_results.json` totals 的产品码口径改为 7 文件 +252/−7、回归口径改为 596 collected（595+1skip，或复核后给出实际数）；或在 receipt 附更正说明并由集成方在销账 commit 落账。
- **C-2（登记类，不阻塞）**：R-2 reuse 路径重试不 force 滚动——登记进 limitations 或后续微卡（可选一行修复：`_beginRun` reuse 分支后由 screen 侧对「同轮重发」补 force；亦可接受现状，因其与「增量不抢滚动」一致）。
- **C-3（登记类，不阻塞）**：修正 L2「3 处滚动调用点」表述与悬空引注；滚动锚测 4 与接线 bypass 守卫（grep 型守卫或 scroll API 白名单）列后续候选。
- R-1 建议：立独立「回到底部/跳最新」微卡走卡片库派发，不并入本卡。

审查期间产生的 mutation 与探针均已还原/删除；本 commit 仅新增本 receipt，未触碰实现与既有证据文件，未 push。
