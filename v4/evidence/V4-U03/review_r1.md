# V4-U03 · 独立审查 receipt（一审 R1）

- 审查人：wtU03R1（独立会话，未参与 U03 实现）
- 审查对象：worktree `wtU03`，分支 `agent/v4/u03`，commit `01e63308`（base `555346fe`）
- 卡：V4-U03（implementation · normal · 1 位独立审查）
- 审查日期：2026-09-28
- 方式：只读审查 + 本机复跑；未 push

## 总裁决：PASS（附 4 条非阻塞 CHALLENGED 登记，见下）

三条卡验收全部独立复跑通过且可失败；八项审查靶全部核验；红线零触碰；
无第二真源、无夸大、无假成功（U03 自有面）。发现项均为非阻塞残留，
已逐条给出裁决与去向建议。

## 复跑记录（本机亲验）

| 项 | 命令 | 结果 |
|---|---|---|
| 新测+受影响面 | `flutter test test/features/memory/` | +117 passed / 0 failed |
| 全量套件 | `flutter test`（mobile） | +2817 passed / ~23 skipped / 0 failed（与交付声明逐字一致） |
| 静态分析 | `flutter analyze` | No issues found |
| 四棘轮 | ui-tokens / typography / spacing / dl-spec | 全 PASS（新文件零新债务） |
| 环境核对 | `flutter --version` | 3.41.3 stable（与 run_manifest 一致） |

测试实数核对：**本卡新增测试实为 46 个**（模型 14 / 读面 provider 6 / 冲突守卫 7 /
面板 12 / 黑话+入口 5 / 证据采集 2）——test_results.json 与 tasks.json
evidence_summary 写 45（面板 11）。声称方向保守（少报 1），不影响验收门槛
（45+），但证据元数据与实数差 1，登记为 CH-R3，集成前顺手订正。

## 八项审查靶逐条核验

### 1. 不造第二真源 — PASS

- 模型层（`context_receipt_models.dart`）为 I06 `context_selection_receipt.v1`
  读面纯投影：8 归因码 / 4 角色 / 4 置信档 / 3 候选态 / 2 resolution 词表与
  `backend/app/core/context_selection_receipt.py` 冻结词表**逐字对齐**（本人比对
  一致）；版本门 fail-closed（`schema_version` 不符 → unsupported，不当数据渲染）。
- 无本地推导改写：选中计数来自服务端字段/服务端候选集（`resolved_selected_count`
  语义经 backend `experience_readouts.py` 核实 = resolved ∧ selected 的服务端计数；
  面板 `selectedCount - resolvedSelectedCount` 的差值仅为两个服务端权威数字的
  算术投影，语义正确）。无缓存改写、无兜底编造。
- resolution=unresolved 显式「来源已不可定位（可能已被你删除或修改）」，且
  **无操作**（`calibratableMemories()` 只收 resolved × selected × 三类 kind；
  面板测试钉死 unresolved-only 回执「忘记 findsNothing」——防对不可定位对象误删）。
- note（debug-only）结构性不入用户面：`ReceiptCandidateView` 无 note 字段
  （字段清单断言）+ payload 带 `note:'DEBUG_GATE'` 渲染后 `findsNothing`（双钉）。
- 词表外归因码不猜标签、不静默丢弃 → 显式「未归因 N 条」；
  candidates 缺失 → 「这次回执暂缺候选明细」，不当空集渲染为「没有引用」。

### 2. 不夸大验收（归因逐码如实直译）— PASS

逐码对照（zh）：`out_of_scope_memory`→不在这次的范围里；
`stale_epoch`→已删除或已被新内容替代；`utility_gate_rejected`→这次判断帮助不大
（直译不美化）；`conflicts_confirmed_preference`→与你确认过的偏好不一致；
`permission_denied`→你设置过不让使用（如实归于用户自己的设置）；
`budget_exhausted`→这次能带上的内容有限；`duplicate`→和其他内容重复；
`expired`→已过时效。unattributed 显式。语义 dump（ready 态）逐行核对与
代码/词表一致。`unavailable` 候选并入「没用上的原因」分组呈现——语义成立
（确实没用上），不虚构成「用过」。

### 3. 校准链路 — PASS

- 忘记 = 真实 `revokeItem`（POST revoke），且客户端强制后端诚实契约：
  `result['revoked'] != true` 即按失败处理——不把中间态当成功。
- scope 三写（pause/resume/link_plan/link_task）统一走 `_guardedScopeWrite` →
  `_ensureScopeUnchanged`（GET /scope 的 paused 位 + editable + scope 投影
  level/plan_id/task_id 逐键比对）→ 漂移即抛 `MemoryScopeConflictError`、
  **PUT 零调用**（测试断言 putCalls==0，非静默覆盖实证）。
- 后端 409 同面：`isScopeConflict`（类型化 + DioException 409）→ 冲突登记
  `conflictItemIds` → 内联 `ScopeConflictBanner`（`PixelRunState.conflict` 徽章，
  非成功视觉）+「这次修改已停止，未做任何覆盖」；不叠加通用 toast。backend
  409 出口在库（`memory_provenance.py:191,223` ConflictError→409）。
- 核对不可得（断网）**不设门**：放行真实变更链，交后端行锁+终态 409 兜底
  （反例测试钉死 putCalls==1）——裁决：方向正确，「核对不到即停」会把网络故障
  变成删除/纠正权的新闸，违反验收③方向；且非静默覆盖由后端终态 409 保底。
- budget_exhausted 只作如实说明（「只是当时的选择空间，不影响你随时更改或忘记
  任何内容」），预算面下忘记 `disabled==false` 断言（变异守护）+ 走完真实 revoke。

### 4. 去黑话 — PASS（有残留，见 CH-R1/CH-R2）

四映射 zh+en 双语核实（arb diff 旧值→新值）：L1 用户声明→你告诉我的 /
L2 协作校准→我们校准过的 / L3 系统推断→我观察到的；仅此 Goal→仅这个目标；
删除→忘记（按钮+确认链+toast 同步）；当前会话中→仅这次对话。
en 同步无漂移（What you told me / Forget / Only for this goal /
Only in this conversation）。面板新文案全用户语言（「这次用了 N 条，其中 N 条
来源可核对」「没用上的原因」「为什么现在用它（把握较高）」）。

### 5. F03 反向面 — PASS（U03 自有面）；V3 残留见 CH-R4 裁决

面板 forget 成功 = 中性文案「已忘记」，失败 = 「没有成功：…」如实文本；
`PixelSuccessBadge findsNothing` 三处钉死；忘记失败（404）测试在库。
**未发现 U03 新增任何成功面孔。**

### 6. 红线 — PASS

- 零路由变更：`memory_routes.dart` 零 diff；`/memory/understanding` 为 V3 既有
  活路由；UserPersona 入口仅 `context.push` 同一路由；五 Tab 零触碰。
- RF-06 冲突面（dashboard_screen / compact_status_bar / task_execution_screen）
  零 diff（逐文件核对）。
- classic 零差量：`core/design` 零 diff，面板全用标准 DS 组件 +
  既有 `PixelStateBadge` 状态族，无 pixel 专属装饰面。
- backend / proto / 迁移 / `*/gen/` 零触碰；无 WIP/TODO/debugPrint 残留
  （新增 lib 行全量扫描零命中）。

### 7. 复跑与断点合并完整性 — PASS

- 单 commit `01e63308`，工作树干净；两会话合并无半途残留：diff 全量扫描无
  TODO/FIXME/WIP/print/临时占位；`v4/04_tasks/tasks.json` 状态诚实推进
  （in_progress/REVIEW_READY，review_receipt.json PENDING）。
- 锁外文件 1 处（`experience_feedback_adapter_test.dart`）：纯格式（expect 加
  尾逗号），CH-3 互钉 sha256 字面量 `949757da…` 逐字未动——与 limitations #8
  登记一致，断言强度零变更，放行。
- 附带说明：本审查复跑 q03 visual probe 后 `v3-output/WT401-Q03-VISUAL/*.json`
  出现时间戳抖动（manifest known_side_effects 预登记过的同类噪声），已按先例
  `git checkout --` 还原，未入任何 commit。

### 8. I06 读面档位降级 — PASS

backend 默认 `CONTEXT_SELECTION_RECEIPT_MODE=shadow`（settings.py:935），
读面 off/shadow → `receipt:null`（已读 backend 端点核实三态语义）；mobile
五态分立且互斥：off→「理解回执尚未开启」、shadow→「记录中，展示尚未开启」、
词表外 mode→原样透传、live 无回执→诚实 empty、版本不符→unsupported、
断网→offline+重试（绝不渲染为空数据/成功视觉，widget 测试两两对照 + offline
语义 dump 在库）。开箱即 shadow 档时面板呈现诚实降级态，非崩溃非空集。

## CHALLENGED（4 条，全部非阻塞）

- **CH-R1（F03 反向面残留，需跟踪）**：同屏 V3 四组视图的 memory 操作成功反馈
  仍为 `AppFeedback.success`（`understandingToastUpdated/Paused/Resumed/Scoped/
  Deleted` 六处，understanding_overview_view.dart:357-488）——其实现含 success
  语义色 + check 图标 + `SensoryFeedbackEvent.success` 声触，**不属中性文本**。
  为 base `555346fe` 既有行为（U03 diff 零触碰、未引入未恶化），且 CH-4 预登记
  在案。裁决：按设计定案「memory 操作永不成功面孔」，该残留与本纪律在同屏不一致，
  **不得以「toast=中性」口径销账**；因非本卡增量、本卡自有面已合规，不计阻塞，
  但须立 follow-up（V3 四组视图成功 toast → 中性文案，与面板同口径），建议由
  协调方开小卡或并入 U 线收尾。
- **CH-R2（同屏词汇不一致）**：`understandingViewIntro`（understanding_overview_view.dart:103
  渲染，两份语义 dump 均在案）仍为「…也可以修改或删除。」——「删除」未随
  卡面「删除→忘记」映射对齐，与紧邻其上的回执面板词汇冲突。词汇残留非黑话
  本体、无诚实性问题，非阻塞；建议 l10n 键顺手订正（一词）。
- **CH-R3（证据元数据差 1）**：新增测试实数 46（面板文件 12），证据写 45（11）。
  少报方向保守、无验收影响；集成前订正 test_results.json / tasks.json
  evidence_summary。
- **CH-R4（卡外残留，登记）**：memory panel（`memory_panel_screen.dart`）的
  `memoryGovDelete`=「删除」/`memoryGovDeleted`=「已删除该记忆…」等治理面词汇
  未对齐「忘记」；chat working-memory 抽屉「Current session」为 chat 域既有文案。
  均在卡面/设计定案点名范围之外（U03 点名=UserPersona 入口+理解面），不判违规；
  登记给词汇 owner 作后续统一。

## 预登记挑战（CH-1..6）回应

- CH-1 TOCTOU：属实且已在 limitations #1 如实登记；「可见漂移必冲突 + 409 必
  冲突面 + 绝不静默覆盖」的断言在本卡落地范围内成立；expected_version 乐观锁
  归 contract-owner，本卡已收敛 `isScopeConflict` 单点。接受。
- CH-2 断网放行：接受实现方向（不设新闸保删除权；后端终态 409 兜底），反例
  测试已钉死放行路径。
- CH-3 unresolved 无操作：核实通过（模型过滤 + 面板 findsNothing 双钉）。
- CH-4 成功面孔：U03 自有面合规；V3 残留见 CH-R1 裁决（不销账，立 follow-up）。
- CH-5 共享 l10n 键更新：核实为文案钉值更新（删除→忘记 tap 定位），revoke 全链
  断言原样保留；「仅此 Goal findsNothing」类断言保留；en/zh 无漂移。
- CH-6 Ahem 字形：语义 dump 携带真实文案（本审查逐行核对 ready/offline 两份），
  按 F04 先例口径接受「截图+语义 dump」组合。

## 结论

V4-U03 实现与证据可信：数据单源、逐码如实、校准走真实 M-08 链且冲突不静默、
预算不禁权、红线零触碰、全量复跑与本机亲验一致（+2817 全绿 / analyze 零 issue /
四棘轮 PASS）。**一审 PASS**。4 条 CHALLENGED 均非阻塞：CH-R1 需立 follow-up
（V3 成功 toast 与 F03 反向面纪律对齐），CH-R2/R3 建议集成前一词/一数订正，
CH-R4 登记备案。集成复验按 review_receipt.json 所列（全量 test + analyze +
四棘轮）在集成 SHA 执行。

— wtU03R1
