# V4-U13 · 洞察报告：让分析可理解 — diff_or_evidence_only

执行：wtU13（worktree `../wtU13`，分支 `agent/v4/u13`，自 main@`799e145e` 开出）· 2026-09-29 · backend 服务最小增量 + mobile 三读面呈现增量，零 HEAVY，零模型调用，无迁移，无 proto/生成文件改动。实现 commit：`d3ec17ad`（backend 撤回排除）+ `2138a121`（mobile 三读面）+ 证据/勘误随本提交。不 push。

## 1. 一句话设计

洞察三读面（D07 证据洞察区 / 学习报告 / 认知定式卡）**消费 D05 `insight.presentation.v1` 契约出口**把「原始数值」与「推断」拆开：移动端 feed 模型过 `presentation_schema` 版本门（fail-closed），`understanding` 档驱动 **无数据/证据不足分呈现**、后端服务最小增量把软删来源计数 `withdrawn_refs_excluded` 经契约 `exclude_withdrawn_refs` 如实随行（**撤回不静默消失**）、样本量挂真实定义（去重后/原始/重放丢弃三数随行）、信封零惩罚宣称 fail-closed；报告面掌握度百分比挂真实定义（证据融合值 0–100 + 样本＝N 个能力节点 + delta 百分点口径）且节点行经既有深链解析跳星图原始记录；认知卡「置信 N%」假精确改 frequency 真实计数派生的定性观察档（M-10 同律）；图表（雷达/趋势）标签保持现代排版令牌并钉测低刺激档等价。

## 2. 卡面 → 真实路径绑定（path_policy：先绑定既有面，不造第二权威）

| 卡面词 | 真实路径 | 本卡动作 |
|---|---|---|
| 洞察（insights） | `GET /insights/evidence-cards`（insights.evidence_cards.v1 + D05 呈现契约出口）→ `backend/app/services/evidence_insight_service.py` → mobile `EvidenceInsightFeedData`（`mobile/lib/features/insights/data/models/evidence_insight_card.dart`）→ `EvidenceInsightSection`/`EvidenceInsightCardWidget` | 消费 D05 出口 + 撤回排除计数 + 三态呈现；零新路由 |
| 报告（report） | `GET /learning-reports`（`backend/app/services/report/learning_report_agent.py`，mastery 真源=`report_tools.query_mastery_scores` → `UserNodeStatus.mastery_score`）→ mobile `LearningReportScreen`/`MasteryRadarChart` | 百分比定义随行 + node_id 深链跳星图（既有 `/galaxy?node_id=` 解析，U-07 语义）；零新路由 |
| 认知（cognitive） | `behavior_patterns`（confidence_score/frequency）→ mobile `PatternListScreen` | 假精确清理（置信% → frequency 观察档）；零路由/零模型改动 |
| 依赖核验 | depends_on = V4-F02、V4-D05 | F02（认知读面契约）与 D05（`1e626998` 呈现契约层）均已在 main；锁 ui-insights 本卡持有 |

## 3. 实现面（真实路径）

### backend（服务层最小增量，`backend/app/services/evidence_insight_service.py` +29/−4）

- `_withdrawn_exposure_ids_by_tag` / `_withdrawn_exposure_ids_by_signature`（新增）：窗口内软删 exposure 的 decision_id 分组（真实计数源；`deleted_at IS NOT NULL`）。
- 三类卡的 `uncertainty.withdrawn_refs_excluded`：friction（按 tag）/ helped（按 signature）/ goal_progress（软删任务计数）——**fact 分子分母零改动**（D-05 账本权威不动），撤回排除只是呈现面诚实声明。
- 候选引用过 D05 契约 `exclude_withdrawn_refs`（import 期消费，单一权威）：查询窗口与软删读之间的删除竞态，被撤回身份确定性落入 `excluded`，绝不进呈现 refs。
- 无新路由（`/insights/evidence-cards` 签名零变化，response_model=dict）、无迁移、无契约/词表改动；`understanding` 门、夸大门、样本去重全为 D05 既有出口原样消费。

### mobile（呈现增量，19 文件 +2025/−59）

| 文件 | 内容 |
|---|---|
| `insights/data/models/evidence_insight_card.dart` | `EvidenceUnderstandingBlock`（band 封闭四值，词表外 fail-closed=unknown）/`SuggestionEnvelope`（`zeroPenaltyRejectable` 只在 `user_can_reject && reject_penalty=="none"` 成立）/`EvidenceRevisitRecord`（七态封闭词表）/`EvidenceInsightFeedData`（版本门 fail-closed：schema 非 `insight.presentation.v1` → unsupported；合法零卡 → no_data 显式态；`meta.presentation_gate_dropped` 计数随行、绝不进 cards） |
| `insights/data/repositories/evidence_insight_repository.dart` | `getEvidenceFeed`：显式拆 `{data, meta}` 双层（unwrapMap 会丢 meta）→ feed |
| `insights/presentation/providers/evidence_insight_provider.dart` | `evidenceInsightFeedProvider`（替代 cards-only provider，唯一数据源不变） |
| `insights/presentation/widgets/evidence_insight_section.dart` | 三态分呈现：no_data → 显式「还没有可分析的记录」行；unsupported/加载/出错 → 隐藏（与无数据互斥，不互相冒充） |
| `insights/presentation/widgets/evidence_insight_card.dart` | 不确定性块追加：撤回排除行 / 样本量真实定义行（去重后+raw+丢弃）/ 理解档行（无数据/证据不足-删失/证据不足-不可定位/双口径/仅定性）；行动含义块追加零惩罚可拒绝行（信封契约漂移 → 不渲染） |
| `report/data/models/learning_report.dart` | `LearningMasteryDatum` 增 `nodeId`/`relatedErrorCount` 解析（空串→null 不编造） |
| `report/presentation/screens/learning_report_screen.dart` | 关键指标定义行（掌握度定义+样本 N 节点+delta 百分点口径）/ 维度行点按提示 / 明细 sheet 定义行（含关联错题计数）+ `node_id` 在册时经既有 `?node_id=` 深链解析直达 `/galaxy/node/<id>`（跳原始记录），否则回落星图首页 / hero delta 改「±N 分」百分点口径（不伪装增长率） |
| `report/presentation/widgets/mastery_radar_chart.dart` | 图内定义行（0–100 证据融合读数；样本＝当前绘制节点数）；标签保持 bodySmall 现代排版 |
| `cognitive/presentation/screens/pattern_list_screen.dart` | 「置信 N%」假精确移除（M-10 同律）→ `_observationTierLabel`：frequency 真实计数派生定性档（暂无观察/单次观察/观察到 2 次/多次观察到），计数由相邻「出现 N 次」徽章承载（360dp 无溢出） |
| l10n（zh/en + 生成 dart ×3） | 双语各 22 键纯增量（arb 顺序保持，gen-l10n 再生 diff 纯追加，languageVersion 3.0 下零既有键改动） |

## 4. 差量判定（no_duplicate_rule）

- **未重建 V3/D05**：五要素卡契约、`understanding` 门、夸大门、样本去重、回访词表全部为 D05 已合并出口原样消费（`git diff` 显示 service 只增 withdrawn 三查询+计数；insight_presentation.py 零改动）。
- **已满足面的差量举证**：证据深链跳转（D07 已有，本卡测试钉）/ 图表现代标签（雷达/趋势已用 bodySmall 令牌，本卡钉测防像素化回潮）/ 无数据不出卡（后端已有，本卡补移动端显式呈现）。
- **本卡首个面**：`presentation_schema` 版本门的移动端消费（grep 全库此前零命中）、`understanding.band` 移动端消费、`withdrawn_refs_excluded`、报告面 node_id 深链（此前模型直接丢弃该字段）、认知卡观察档。

## 5. 与验收逐条对照（可失败 = 每条一正一反）

### 验收① 所有百分比/样本/时间窗有真实定义 — PASS

- 正例：样本量定义行 `样本＝去重后方向观察 2 条（原始投递 3 条，重放重复 1 条不计入样本量）`（`evidence_insight_u13_presentation_test`）；报告定义行 `掌握度＝星图能力节点的证据融合值（0–100）…样本＝4 个能力节点；与上次报告相比的变化按掌握度分（百分点）计`（`learning_report_u13_definition_test` 关键指标测）；雷达图定义行 `图上每个轴是一条 0–100 的证据融合掌握度读数；样本＝当前绘制的 3 个能力节点。`；认知观察档由真实 frequency 派生（tier 4 测）。
- 反例钉：无方向观察 → 无样本定义行（不虚构样本）；D-07 卡整树渲染断言 `%` 零出现（卡契约禁百分比，呈现面不引入）；`'样本＝去重后方向观察'` 反例（0 样本无行）；delta 不再渲染 `+X%` 增长断言（`reportTrendDeltaPoints` 百分点口径）。

### 验收② 无数据/不足/撤回分别呈现 — PASS

- **无数据**：feed 合法 schema 零卡 → `no_data` 显式态，区头 + 「这个窗口还没有可分析的行为记录，尚未形成任何结论。」（`evidence_insight_card_test` V4-U13 两测；不再是静默隐藏）；卡级 `band=no_data` → 「还没有可分析的数据，无法得出结论」。
- **不足**：`band=incomplete_evidence` → 双口径如实成行「证据不足：1 条结果未到期、2 条来源已不可定位，先不下充分结论」；understanding 门 D05 权威，词表外档位 → 无行（不臆测）。
- **撤回**：软删 exposure → `withdrawn_refs_excluded=1` 如实随行 + 卡面「已排除 1 条已删除或撤回的来源记录」（backend `test_evidence_insight_withdrawn_exclusion` 三测：显式零基线/撤回计数/全撤回无卡无结论；移动端正反两测）；合法其他来源不连坐（fact 分子分母零改动断言）。

### 验收③ 图表标签不像素糊化，低刺激色觉模式等价 — PASS

- 正例：雷达轴标签显式 `textTheme.bodySmall`（现代排版），断言无像素字族（`learning_report_u13_definition_test` 低刺激测）；掌握度档以 **图标+文字双编码**（`_masteryIcon` 三档不同图标 + `_masteryLabel` 定性词——颜色非唯一载体，低刺激/色觉模式信息等价）；低刺激档（`StimulationLevel.low` 主题）下雷达定义行与图例读数同构渲染。
- 反例钉：`SparkleScreenFamilies`「不能用 pixel 阶梯线捏造台阶趋势」——趋势图无像素阶梯装饰（Chart painters 全矢量线，标签 Text 令牌渲染）；D-07 卡 `GraphiteCardSurface` 断言（无像素装饰面引入）。

### 协调方铁律对照

- **夸大表述门继承反例钉**：`evidence_insight_u13_presentation_test` 夸大门组——3 例只有 2 例关联的真实计数卡，整树写不出「67%」/「提升/有效/因此/导致」族（D05 门语义在呈现面继承）；feed 层 `meta.presentation_gate_dropped` 登记的违例卡绝不作为卡渲染（`evidence_insight_u13_feed_test`）。
- **评测 FAIL 不标 PASS**：本卡证据 PASS 仅就上述可失败验收面成立；「无数据不造结论」由三态呈现+空态 note 原样随行钉死。
- **参考图=提案非批准；UI 消费 core/design 令牌**：全部新增 UI 走 DS/context.colors/context.typo（`GraphiteCardSurface` 断言钉）；零参考图直译。
- **RF-06 三冲突面只读**：dashboard_screen/compact_status_bar/task_execution_screen 零 diff（`git status` 佐证）。
- **不造第二权威**：数据面只读既有读面（evidence-cards/learning-reports/behavior_patterns）；撤回排除计数不改账本口径；理解档/信封/回访词表全部 D05 权威透传。

## 6. 红线自查

- RF-06 三冲突面零 diff；五 Tab 路由零触碰（仅 sheet 内 `context.push` 既有路由）；`backend/app/api/` 零改动（无 OpenAPI/BA-ROUTES 机械门触发面）；proto/迁移/`*/gen/` 生成物零触碰（mobile `lib/l10n/app_localizations*.dart` 为 gen-l10n 声明产物、仓库现行约定随分支入库，本次再生纯追加零既有键改动）。
- 无权限/跨用户/删除复活/假成功变更：backend 只读查询带 user_id 属主过滤；撤回行不进任何 fact（既有 `not_deleted_filter` 权威不动）；零惩罚宣称只在后端冻结常量成立时渲染（fail-closed）。
- 零 HEAVY、零模型调用：backend 测试 sqlite 隔离；mobile 测试无网络（noop ApiClient + 平台通道 mock），`actual_model_and_usage = NOT_APPLICABLE`。
- 不动 sparkle-cosmos 仓；不 push（本地银行领先 origin，本分支仅本地提交）。
- 附带勘误：证据采集过程发现 `pattern_list_screen` 观察档首版文案（含重复计数）在 360dp 溢出（RenderFlex overflow 34px）——缩短为「多次观察到」（计数由相邻频次徽章承载）并有 widget 测试钉 360dp 无溢出、无「置信」字样。
