# V4-U13 · 一审 receipt（独立审查 wtU13R1）

- 审查人：wtU13R1（未参与实现，只读审查 + mutation 探针，探针用后即删、工作树已还原干净）
- 审查对象：`agent/v4/u13` @ `6725a8d6`（链 `d3ec17ad` backend → `2138a121` mobile → `6725a8d6` 证据；基线 `799e145e`），工作树干净。
- 材料：卡标准 `Sparkle-project/v4/04_tasks/tasks.json#V4-U13`（normal 风险，1 独立审查）+ 证据五件套 + 三截图/语义树。
- **裁决：PASS_WITH_CHALLENGES**——三条验收独立复验全部成立且可失败（mutation 亲验反例钉会红）；CH-1~CH-7 逐项裁决如下，全部非阻塞；5 条观察登记（OBS-1~OBS-5），不要求返工，随集成复验与后续卡消化。

## 1. 逐验收独立下判（可失败性亲验）

### 验收① 所有百分比/样本/时间窗有真实定义 — PASS

- 三类卡 fact 模板逐个核（zh/en arb 亲读）：friction「最近 {days} 天记录到 {count} 次」=窗口+样本；helped「观察到的 {observed} 次记录中，{positive} 次伴随正向结果」=分子分母随行；goal「已完成 {completed} / 共 {total} 项」=账本口径。三族模板零 `%` 字符（CH-3 亲扫）。
- helped 卡样本定义行三数（去重后/raw/重放丢弃）正反两测亲跑绿（raw=3 去重 2 → 整行如实；0 样本无行不虚构）。
- 报告面掌握度定义行（0–100 证据融合值 + 样本＝N 节点 + delta 百分点）与雷达图内定义行语义树亲验在册；`UserNodeStatus.mastery_score` 列契约亲查确为 0–100（`backend/app/models/galaxy.py:247`），文案忠实。
- 认知卡观察档由真实 frequency 派生（4 档正例 + 0.99 置信不上屏反例钉亲跑绿）。
- **OBS-2（登记）**：`reportTrendDeltaPoints`（delta `%`→百分点）代码改动正确但无测试钉——趋势指标需上一份报告才渲染，现有测试未覆盖该面；delta 定义已由关键指标定义行文案覆盖（该行有测）。半句「反例钉」对 delta 面属过度声明，不阻塞。

### 验收② 无数据/不足/撤回分别呈现 — PASS

- backend 三测亲跑绿（`SECRET_KEY=<proc-env> pytest tests/services/test_evidence_insight_withdrawn_exclusion.py` → 3 passed）：显式零基线 / 撤回计数=1 不静默 + refs 恒洁净 / 全撤回无卡 + 诚实空态 note。回归 18 passed（D05 呈现契约 9 + evidence-cards API 6 + 本卡 3）。
- 三态正反测抽验亲跑绿（affected 套件 53 passed）：no_data 显式行（区级 + 卡级 band 双层）；incomplete 双口径（censored/missing 分列 + 合并行）；词表外档位无行；unsupported 与 no_data 互斥两向钉死（card_test 改写 + 新增各一）。
- CH-1 边界裁决：**按 D05 R-C5 同判例——PASS**。`withdrawn_refs_excluded` 只覆盖软删来源（lifecycle `deleted_at` / 软删 Task），D03 retraction 引擎 insight 面执行体仍归债务台账（#14）；本卡 depends_on 不含 D03，不越权接线、不造第二撤回语义。fact 分子分母零改动经代码亲读（`not_deleted_filter` 既有权威未动）+ 测试断言（exposures 3→2 仅由既有过滤产生）确认；无复活路径（D05 `exclude_withdrawn_refs` 整串身份匹配 + 软删身份绝不进 refs 钉）。**OBS-3（登记）**：该测试文件 docstring「只经既有生产入口驱动写路径」过度声明——`_soft_delete_exposure` 直接改行 `deleted_at`（lifecycle 事件的生产软删入口尚不存在，恰是 D03 债务本身）；被测读路径是生产服务，判定不受影响。
- CH-2 裁决：**PASS（接受该权衡）**。unsupported 是契约态不是数据态，给「无数据」文案会伪造「尚未形成结论」的前提；与 no_data 互斥两向钉死。登记的升级路径（1 l10n 键 + 1 分支）留作需要时的增量，不构成本卡缺陷。

### 验收③ 图表标签不像素糊化，低刺激色觉模式等价 — PASS

- 雷达轴标签 bodySmall（`mastery_radar_chart.dart:123` 亲读）+ 非 Pixel 字族断言亲跑绿； painters 全矢量。
- 双编码亲读确认：掌握度行 `_masteryIcon` 三档不同图标 + `_masteryLabel` 定性词（报告面），图例文字 chip 承载读数——颜色非唯一载体。
- CH-5 裁决：**PASS_WITH_NOTE（接受验证口径）**。「同构渲染 + 图标/文字双编码 + 语义令牌槽」widget 钉对 normal 风险卡充分；真实色觉滤镜矩阵缺失已如实登记为基建缺口（limitations #12）而非本卡豁免，判归后续基建卡，不阻塞。

## 2. 最重靶：夸大门继承 — PASS（mutation 亲验）

- **mutation 探针 A（呈现面亲放）**：临时改 `evidence_insight_card.dart` 在不确定性块注入 `关联提升 N%`（模拟绕过 D05 契约层直喂原始比值）→ `evidence_insight_u13_presentation_test` 夸大门组**红**（「整树写不出因果百分比」断言命中，`%`+因果措辞双通道均触发）→ 已还原。
- **mutation 探针 B（认知卡）**：临时把 `_observationTierLabel` 换回 `置信 ${(confidenceScore*100)}%` → tier 测 4 例**全红**（反例钉「置信值再高也不得上屏为百分比」命中）→ 已还原。两次探针后 `git status` 干净，实现零改动。
- 「2/3 关联卡无 67%」grep 亲验：三读面 arb 模板与 widget 代码零硬编码百分比；feed 层 `meta.presentation_gate_dropped` 绝不进 cards（模型无复活路径，结构保证 + 钉测）。后端 D05 契约层（`insight_presentation.py`）零改动亲核（diff 只含 service 与新测试）。

## 3. 其余靶

- **假精确治理（靶4）**：PASS。`pattern_list_screen` 置信徽章移除、frequency 四档 + 相邻「出现 N 次」徽章承载计数（360dp 溢出修复为同卡窗口内勘误、自身新键修订、已如实登记——亲 diff 核实仅 `cogPatternTierRepeated` 一处，非既有键）。confidence_score 模型/后端保留（CH-6b 亲读 `behavior_pattern_model.dart` + 测试种子 0.99）。M-10 判例同向（V3 667001e6 已删 PredictiveInsightsCard 置信% 族先例）。**OBS-4（登记，卡外面）**：`prism_behavior_card.dart:272` 仍有裸 `N%` 置信 chip（仅 chat `agent_message_renderer` 消费）与 `understanding_snapshot_card.dart:63`「可信度 N%」（experience 面）——均在 U13 objective（insights/cognitive/report 三读面）之外，归后续 M-10 清扫卡，非本卡阻塞。
- **深链（靶5）**：PASS。`?node_id=` 由**既有** `_resolveReportDeepLinkUri`（基线 `799e145e` 已在）重写为 `/galaxy/node/<id>`（与真实路由 `GalaxyRoutes.knowledgeDetail = '/galaxy/node/:id'` 同形）；wiring 测试用真路由形注册并断言 `NODE_OK node-1` 落地；后端 `query_mastery_scores` 确发 `node_id`/`related_error_count`；node_id 缺失回落星图首页（不编造地址）。测试路由为 test-local（非 app 全 router），normal 风险下足够。
- **测试数字（靶6）**：37 新测分解亲核=12(feed)+12(呈现)+4(tier)+6(报告定义)+2(capture)+1(card_test 净增，5→6)；backend 3 新测亲跑绿。mypy 59 亲跑复现（≤77 棘轮）；`flutter analyze` 亲跑零 issue；抽批亲跑 53（affected）+93（experience+home widgets）全绿——全量 3127 未整跑（按抽批口径）。Q03-VISUAL 探针还原亲核：`git status/diff v3-output/` 空，与 HEAD 逐字节一致。受影响套件清单自述 52、本轮亲跑 53（capture 测在勘误窗口 +1，manifest 数字略滞后于 HEAD，无碍）。**OBS-1（登记）**：报告面证据 PNG/语义树为**计数动画中间帧**——`_MetricCard` TweenAnimationBuilder count-up 未收口（总掌握度 43% 实为 72%×~0.6、知识点数 2 实为 4×0.5、雷达图例 80/74/57/69 为终值 82/76/58/71 的 ~97.5% 进度插值）；定义行（静态文本）准确且正是测试断言对象，重采集亲跑与在库文件逐字节一致（可复现），但中间帧数值可能被误读为真实读数——建议后续采集在 `pumpAndSettle` 后落盘，本卡证据结构性主张不受影响。
- **合并落差（靶7）**：PASS。`git merge-tree --write-tree HEAD f898b465` → exit 0、零冲突标记；双方面交集仅 l10n 5 文件 + tasks.json（自动合并干净），insight/report/cognitive 逻辑面与 main 侧零交集亲核（`comm` 交集为空）。

## 4. CH-4/CH-6/CH-7 补充裁决

- **CH-4：PASS_WITH_NOTE**。0–100 列契约与 G-01 语义无出入；`round()` 显示偏差 ≤0.5 个百分点，定义文案未宣称未取整，可接受。**OBS-5（登记）**：error-record fallback 派生路径（`report_tools._derive_mastery_from_error_records`）为启发式 18–58 带宽且无 node_id——该路径下「证据融合值」措辞偏松、深链正确降级回落；属既有后端口径，非本卡引入，登记给报告线后续卡。
- **CH-6：PASS**。(a) M-10/SCREEN_FAMILIES 支持移除而非保留加定义（黑盒 AI 置信不盖章）；(b) 数据零丢失（模型+后端保留 confidence_score）；(c) 360dp@100% 有钉 + 溢出修复真实（非放宽断言）；200% 字体归 Q03-VISUAL 探针域并已登记 limitations #14——责任面划分成立。
- **CH-7：PASS**。22 键 zh/en 集合逐一相等（脚本亲核）；既有键零漂移（diff 仅闭行位移）；gen-l10n 再生与 analyze 零 issue 互证；平台通道 mock 仅存在于测试文件亲核。

## 5. 红线抽核

RF-06 三冲突面（dashboard_screen/compact_status_bar/task_execution_screen）零 diff；proto/迁移/gen 产物零触碰；backend `app/api/` 零改动；l10n 14 文件 = 5 insights + 3 report + 1 cognitive + 5 l10n（与 manifest 一致）。证据六件 SHA256 与 run_manifest 逐一相符（亲算）。

## 6. 裁决汇总

| 项 | 裁决 |
|---|---|
| 验收① | PASS（OBS-2 delta 无钉登记） |
| 验收② | PASS（CH-1 边界按 D05 R-C5 判例维持；OBS-3 测试 docstring 措辞登记） |
| 验收③ | PASS（CH-5 基建缺口已披露，接受） |
| 夸大门继承 | PASS（mutation 双探针红→已还原） |
| 深链 | PASS |
| 测试数字 | PASS_WITH_NOTE（OBS-1 中间帧、OBS-2、52→53 滞后） |
| 合并落差 | PASS（merge-tree 干净） |
| **整体** | **PASS_WITH_CHALLENGES（全部非阻塞；implementation_state=REVIEW_READY 维持，按 integration_reverify 清单在集成 SHA 复验后闭账）** |

探针记录：两处 mutation 均当场还原，本 receipt 提交时工作树仅含本文件。
