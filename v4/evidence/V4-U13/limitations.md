# V4-U13 · limitations

## 1. 范围限制（按卡保守侧执行并如实登记）

1. **撤回排除计数 ≠ D03 撤回引擎接线**。本卡的 `withdrawn_refs_excluded` 只覆盖**软删来源**（lifecycle 事件 `deleted_at` / 软删 Task）的呈现面诚实计数。D03 `retraction.recompute.v1` 的 insight 派生面重算执行体（INFERENCE_RETRACTED/RESULT_RETRACTED 按依赖索引影响洞察卡）仍按其债务台账（KNOWN_CODE_DEBT_LEDGER #14）归后续消费卡接线——本卡 depends_on 不含 D03，不越权接线、不造第二撤回语义。若 outcome 撤回引擎落地后产生「撤回但未软删」的行，本计数字段需该卡扩展。
2. **goal_progress 的撤回计数口径 = 软删任务数**。目标卡的账本分子分母（D-05 权威）零改动，`withdrawn_refs_excluded` 只随行如实声明；「已删目标本身」的场景由卡不存在（无 active goal → 无卡）自然覆盖。
3. **friction/helped 卡的撤回计数 = 窗口内软删 exposure 数**，非「曾出现在某次呈现里后被撤回」的差集——本服务是无状态读时计算，不落陈旧快照，无法也无须知道历史呈现内容（纠正即更新语义）。
4. **报告面撤回呈现走深链不复制语义**：掌握度真源（`UserNodeStatus.mastery_score`）的撤回重算状态（`stale_recomputing` 等）由星图读门权威呈现；报告面通过 node_id 深链把用户送达权威面，不在报告面另立撤回标记（避免双份相矛盾成长语义）。报告 payload 本身不含撤回标记字段——如审查认为报告面需要内联 stale 标记，属后端 payload 契约增量，应归 D03 线卡。
5. **趋势 delta 的窗口定义沿用后端 `_build_trend_overview` 现状**（上一份报告对比）；本卡只纠正了单位口径（百分点 vs 增长率），未新增窗口元数据字段——「样本/时间窗真实定义」在该处以「与上一份报告相比」+ 报告生成时点呈现，窗口天数后端未发、移动端不编造。
6. **认知定式卡的时间窗未新增**：`last_observed_at` 在模型中已有但卡面未呈现（增量最小化；观察档 + 频次徽章已满足「样本真实定义」）。如需「最近观察于…」可作后续小增量。

## 2. 实现口径说明

7. **`exclude_withdrawn_refs` 的契约消费是防御性的**：候选 refs 与撤回集合在正常路径不相交（查询已过滤软删行），契约调用保证删除竞态窗口内 refs 恒洁净（确定性落入 excluded）。该路径由正测钉（refs 恒不含软删身份），「竞态即排除」分支无独立并发测试（sqlite 测试环境无并发注入面；函数本体已有 D05 契约层测试）。
8. **unsupported 契约门 = 静默隐藏（有意为之）**：旧后端/未知 schema 下整区隐藏，与 no_data 显式行互斥（测试钉死两态）。未给 unsupported 做显式用户文案——仪表盘区块的「版本不支持」文案对用户是噪音；若审查裁决需要显式降级文案，是一处 l10n+一分支的增量。
9. **证据截图为 Ahem 方块字形**（flutter_test 无 CJK 字体，U03/F04 同先例）：布局/结构以 PNG 为准，文案以同名 `_semantics.txt` 为准。
10. **`meta.presentation_gate_dropped` 不上用户面**：D05 语义是「响亮失败登记」（meta 级），用户面只见合规卡；移动端只透传计数进 feed 模型（测试钉 gate_dropped 绝不渲染为卡）。若审查认为需要用户可见提示，需裁决文案与位置。
11. **回访记录（revisit）已解析入模型但未上卡面**：七态词表/`proves_relevance`/零惩罚后果在 feed 模型层全部钉测；卡面呈现（如「上次建议后来验证相关」行）留作后续增量——本卡验收面不含它，避免单卡过载。
12. **低刺激等价的验证口径**：以「同一 widget 树在 StimulationLevel.low 主题下同构渲染 + 文本/图标双编码存在 + 颜色来自语义令牌槽」为等价定义（widget 测试钉）；未做真实色觉模拟器矩阵（deuteranopia 等滤镜截图比对）——本仓无该测试基建，登记为基建缺口而非本卡豁免。

## 3. 测试环境注记

13. mobile 测试对平台通道做了 mock（secure_storage 空 / shared_preferences 空库 + 里程碑预置解锁）。mock 只存在于测试文件（实现面全走真实通道），但意味着报告面全屏测试不覆盖「庆祝对话框弹出→交互」路径（该路径由其自有测试域覆盖）。
14. 全量套件运行会顺带重写 `v3-output/WT401-Q03-VISUAL/*probe*.json`（既有行为，l10n 键数变化使 text_widget_count ±2）——本卡已 `git checkout` 还原，不属本卡证据；Q03-VISUAL 归其卡主。
15. 本卡 l10n 中途修订过一处本卡新增键（cogPatternTierRepeated 去重复计数占位，修复 360dp 溢出），属实现窗口内勘误；既有键零改动。
