# V4-U03 · 我的理解：项目范围与校准控制 — diff_or_evidence_only

- 卡：V4-U03（implementation · risk normal · 独立审查 1 位 · HEAVY=False）
- 分支：`agent/v4/u03`（worktree wtU03，未 push）；基线 commit：`555346fe`
- 锁：ui-memory（本卡唯一 owner）
- 设计定案：协调方已确认放行（回执面板进既有 /memory/understanding、I06 读面唯一数据源、M-08 变更链、F03 反向面）

## 一句话设计

在既有活界面 `/memory/understanding` 顶部新增「这次的理解」回执面板（新 widget 文件，零路由变更），数据源**唯一**为 V4-I06 读面 `GET /experience/context-receipts/latest`（`context_selection_receipt.v1`：候选集/归因码/why-now 逐条如实投影，unresolved 显式 unattributed，debug note 结构性不进用户面）；UserPersona 活入口去黑话（L1/L2/L3→用户语言、仅此 Goal→仅这个目标、删除→忘记、当前会话中→仅这次对话）并加「这次的理解」活入口按钮；校准动作全部走既有 M-08 变更链，scope 变更前 GET /scope 写前核对，服务端状态漂移→冲突面（F02 `PixelStateBadge(conflict)` + 如实文案，绝不静默覆盖），后端 409 同面；解释缺失 / `budget_exhausted` 归因只作如实说明、绝不禁用更改与忘记。

## 实现面（纯 mobile；零 backend/proto/迁移/生成文件改动）

| 文件 | 性质 | 内容 |
|---|---|---|
| `mobile/lib/features/memory/data/context_receipt_models.dart` | 新（模型面，335 行） | 读面响应封闭解析：版本门 fail-closed（schema_version 非 `context_selection_receipt.v1` → null）、candidates 缺失=candidatesUnknown（合同读侧 unknown 语义，不当空集）、8 归因码/4 角色/4 置信档/2 resolution 词表冻结、`parseMemoryRef`（memory:// 双段）、`calibratableMemories()`（只收 resolved × selected × episodic/preference/goal 三类——消费纪律 §7.1）、note 字段结构性不存在于任何模型 |
| `mobile/lib/features/memory/presentation/providers/context_receipt_provider.dart` | 新（读面 provider，137 行） | 五态分立：loading/offline/modeGated(off·shadow 分 mode)/empty(live 无回执)/unsupported/ready——空态、写先行读未开、断网、版本不支持彼此互斥、诚实呈现 |
| `mobile/lib/features/memory/presentation/widgets/context_receipt_panel.dart` | 新（呈现面，414 行） | 「这次的理解」面板：why-now（statement+审慎档）、选中计数（resolved/unresolved 拆分，unresolved 显式「来源已不可定位」无操作）、rejected 按归因码用户语言分组+「未归因 N 条」显式、budget 说明（明示不影响更改/忘记）、忘记（确认对话框→真实 revoke 链，成功=中性文案，永不成功徽章）、`ScopeConflictBanner`（conflict 徽章+文案+刷新，共用面） |
| `mobile/lib/features/memory/presentation/providers/understanding_overview_provider.dart` | 改 | `MemoryScopeConflictError` + `isScopeConflict`（类型化 + 后端 409）；`_ensureScopeUnchanged` 写前读核对（GET /scope 的 paused 位 + scope 投影逐键比对；核对不可得≠核对通过——不构成阻塞门，交后端行锁+终态 409 兜底）；`_guardedScopeWrite` 统一入口（守卫期与写期冲突同登记 `conflictItemIds`）；state 新增 `conflictItemIds`（load 时清空） |
| `mobile/lib/features/memory/presentation/widgets/understanding_overview_view.dart` | 改 | 条目卡内联冲突面（`ScopeConflictBanner`）；`_actionErrorFeedback`：scope 冲突不再叠加通用错误 toast（冲突面已内联），其余照旧如实 toast |
| `mobile/lib/features/memory/presentation/screens/understanding_screen.dart` | 改 | 顶部接线 `ContextReceiptPanel`（Column：面板+四组视图）；下拉刷新同步刷新回执 |
| `mobile/lib/features/user/presentation/screens/user_persona_screen.dart` | 改 | 快捷入口卡新增「这次的理解」ghost 按钮（`context.push(MemoryRoutes.understanding)`，复用既有活路由，memory 控制开关同门） |
| `mobile/lib/core/network/api_endpoints.dart` | 改 +3 | `experienceContextReceiptLatest = '/experience/context-receipts/latest'` |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + 生成 dart ×3 | 改 | 新增 43 键（contextReceipt*/冲突面/活入口）；黑话清理 9 键（见下） |
| `mobile/test/...`（6 新 + 2 改） | 测试 | 见 test_results.json |

## 黑话清理（卡面「改黑话为来源/这次/这个目标/忘记」逐词对照）

| 黑话（旧） | 用户语言（新） | 位置 |
|---|---|---|
| `L1 用户声明` | 你告诉我的 | UserPersona 分组标题 |
| `L2 协作校准` | 我们校准过的 | UserPersona 分组标题 |
| `L3 系统推断` | 我观察到的 | UserPersona 分组标题 |
| `仅此 Goal` | 仅这个目标 | 理解条目操作（goal 绑定） |
| `删除` | 忘记 | 理解条目/回执面板操作（删除确认链同步：忘记这条内容？/忘记后…/已忘记） |
| `当前会话中` | 仅这次对话 | scope 标签 |
| （来源） | 来源已核对 / 来源已不可定位 / 来源不明 | whyThisSourceTitle 既有「来源」词沿用；回执面板新增 resolved/unresolved 显式面 |

## 不复活已删孤儿界面 / 无第二真源

- 零新路由、零五 Tab 触碰、零 RF-06 冲突面（dashboard_screen/compact_status_bar/task_execution_screen）触碰；回执面板进既有 `/memory/understanding`（V3 U-03 已注册活界面）顶部；UserPersona 入口 push 同一路由。
- 「我的理解」数据真源唯一：I06 回执读面（这次=回执投影）+ 既有 M-08 provenance 读面（完整四组）同屏互补，不另造理解数据源；回执候选的 debug note 不进任何用户可见字段（模型层结构性无该字段，测试钉死）。

## 卡验收对照（必须可失败；每面一正一反）

| 验收 | 落点 | 正例 | 反例 |
|---|---|---|---|
| ① 任何记忆操作可键盘与 200% 字体使用 | 面板 widget 测试 | 200% 字体全面板渲染无异常、忘记按钮可见可走完确认→revoke | 键盘：忘记按钮可聚焦（Focus 可达），Space 激活与点按等效打开确认框（`context_receipt_panel_test` 验收①两测） |
| ② 并发更改 scope 有版本冲突，不静默覆盖 | provider 写前核对 + 409 同面 | 服务端已 paused / scope 漂移 / editable=false → 冲突、PUT 零调用、conflictItemIds 命中；后端 409 → 同面 | 对照：状态一致→PUT 恰一次放行；核对不可得（断网）不设门→放行真实变更链（`calibration_scope_conflict_test` 7 测） |
| ③ 解释次数预算不限制纠正/删除权 | 面板 budget 面 | `budget_exhausted` 归因如实显示 + 明示「不影响更改/忘记」，忘记可点、走完真实 revoke（kind/id 来自回执 ref） | 变异守护：预算面下忘记按钮无禁用态（disabled=false 断言，`context_receipt_panel_test` 验收③正反两测） |

## 协调方验收方向对照

- **理解范围如实呈现**：回执说什么显示什么——选中计数来自服务端（selectedCount/resolvedSelectedCount 原样）、rejected 只显示归因码用户标签（无内容可显示，绝不编内容）、词表外码进「未归因 N 条」、unresolved selected 显式「来源已不可定位」且无操作（模型测试 14 + 面板测试钉死）。
- **校准控制走真实变更链路**：忘记=POST /memory/provenance/items/{kind}/{id}/revoke（后端 revoked=true 诚实契约校验）；scope=pause/resume/link_plan/link_task（写前核对+409）；goal purpose 变更不涉及（本卡不改目标状态机，I07 语义零触碰——无 deliverable/mastery 词进入本卡面）。
- **断网/空回执诚实**：offline 与 modeGated/empty/unsupported 四态分立且互斥（widget 测试两两对照断言），断网绝不渲染成空数据、绝不渲染成功视觉（PixelSuccessBadge findsNothing 三处钉死）。

## 红线自查

- 五 Tab 路由零触碰（仅 `context.push` 既有路由）；RF-06 三文件零 diff；classic 档零差量（标准 DS 组件 + 既有状态徽章族；无 pixel 专属装饰面引入，`PixelProfileTheme` 未涉及）；.env/proto/迁移/`*/gen/` 生成物零触碰（`mobile/lib/gen` 为本机 gitignored 复制实体，未入库）。
- memory 操作永不成功面孔：成功只有中性文案确认，`PixelSuccessBadge` 在面板三态断言 findsNothing（F03 反向面：无 committed 回执不触发成功）。
- 无模型调用（actual_model_and_usage = NOT_APPLICABLE）；无 Mock 冒充（fake 只在测试注入，实现面全走真实 ApiClient/repository）。
- 四棘轮守卫 PASS（ui-tokens/typography/spacing/dl-spec，新文件零新债务）；`flutter analyze` 全绿零 info。
- 附带 1 处格式修复：`test/core/experience/experience_feedback_adapter_test.dart` 一处 expect 加尾逗号（F03 文件，纯格式，断言值零变更——分析器在本地报 require_trailing_commas，为保 analyze 全绿门槛所必需）。

## 差量举证（no_duplicate_rule）

V3 U-03 已交付四组理解面（M-08 provenance 读/改链完整在库）——本卡不重写：四组视图原样保留（仅加内联冲突面与「忘记」文案对齐），V3 任务 ID 与证据不重置。仓库此前无任何 `context_selection_receipt` 的**移动端消费面**（I06 为 backend 权威记录层，读面自 I06 合并起 availability；mobile 侧 grep 零命中），本卡为其首个呈现位。
