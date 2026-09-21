# U-03 REPORT — Aurora/Memory「Sparkle 对我的理解」核心交互

- **Worker**: U-03（stream=UX, risk=high, gate=V3-4, locks=mobile-profile+memory-ui）
- **Worktree**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt66`
- **Base SHA**: `76847722`（U-01 Step 3）/ **Final SHA**: 见回执（本文件同目录交付）
- **Status**: **READY_FOR_REVIEW**
- **纪律声明**: HEAVY 唯一（本卡）；零模拟器（端到端留主会话）；flutter test 全程 `--concurrency=1` ≤2 文件/批；批间 swap 检查（最低 1304M，未触发 <1G 熔断）；主仓/wt67 只读未动；未 commit/push；零真实 LLM、零 mock 冒充真实数据。

---

## 1. API 契约摸底（真实端点，全部来自 M-08 已合入代码）

权威文件：`backend/app/api/v1/memory_provenance.py`（handler）→ `backend/app/services/memory_provenance_service.py`（user-language projection，`PROVENANCE_BUCKETS = {told, observed, uncertain, effective}`，`BUCKET_LABELS` 用户语言文案，置信只给 tier 不给原始参数，honest-unknown 契约 `source_known/reason.known`）。

| 端点 | 语义（后端持有） | 移动端接线 |
|---|---|---|
| `GET /memory/provenance/items` | 四组列表（bucket/bucket_label/source_label/confidence_tier_label/scope/actions 服务端投影；`has_more`/`scan_capped` 诚实分页） | `MemoryProvenanceRepository.listItems` |
| `GET /memory/provenance/items/{kind}/{id}/source` | 来源（何时/何源/证据计数/治理历史） | `getSource` |
| `GET /memory/provenance/items/{kind}/{id}/scope` | scope 读（paused/editable/supported_updates） | `getScope` |
| `PUT /memory/provenance/items/{kind}/{id}/scope` | **暂时不用**（pause）、**恢复**（resume）、**仅此 Goal**（link_plan/link_task，仅 goal；plan/task 归属校验，跨用户/缺失同报 404） | `updateScope` |
| `POST /memory/provenance/items/{kind}/{id}/update` | **修改/纠正**：episodic→supersede 链（M-02 存储门+fork 收敛 P2-4）；preference→版本链；goal→字段白名单 | `updateItem` |
| `POST /memory/provenance/items/{kind}/{id}/revoke` | **删除**：委托 M-07 原语（epoch bump + `memory.invalidated` + derived-cache DEL，原子）；ARCHIVED 先解档再撤（P1-1 防复活）；响应 `revoked=true` 仅在真实终态 | `revokeItem` |
| `POST /memory/provenance/why-this` | **Why-this receipt**（M-05/C-01 回执结构）：why_included/internal_only 冻结词表翻译，`known=false` 诚实未知，`receipt_version_known=false` 标 stale，superseded 旧 id 带替代指针；响应内嵌 correction 三端点指针 | `whyThis` |

辅助真实语义：
- `GET /experience/understanding-snapshot` + `POST .../corrections`（understanding_router.py）：home/chat「Sparkle 懂我」面板数据源与纠正入口（既有，直接复用）。
- `PlanRepository.getActivePlans()`（走 apiClientProvider 鉴权链）：仅此 Goal 的真实 plan 选择器。
- **未发现缺口需要新建后端语义**——M-08 验收项全部可用，无平行真源。

## 2. 四组理解视图 + Why-this receipt（工作 1）

新文件（`mobile/lib/features/memory/`）：
- `data/memory_provenance_models.dart` — 与后端 `_item_payload`/`get_source`/`why-this` 形状一一对应；`UnderstandingBucket` 冻结词表镜像；scope.level→用户语言。
- `data/memory_provenance_repository.dart` — 薄 API 层（走 `ApiClient` 既有鉴权链），读失败原样上抛。
- `presentation/providers/understanding_overview_provider.dart` — 总览状态：分组、pendingActionIds、`lastEffect`（真实 memory_epoch/superseded_id 回执）、纠正后同步链（见 §3）。
- `presentation/widgets/understanding_overview_view.dart` — 四组视图（embedded/完整双模式）：你告诉我的 / 我从你的行动中观察到的 / 我还不确定的 / 对你有效过的方法（bucket_label 服务端文案优先，客户端兜底同文案）；每卡：内容 + 来源 · 置信层级 · 范围 · 日期 + 状态徽标（已暂停/已被新内容替代）+ 操作条（按服务端 `actions` 白名单渲染：修改/暂时不用/恢复/仅此 Goal/删除/为什么有这条）。
- `presentation/widgets/why_this_receipt_sheet.dart` — Why-this receipt 底部抽屉：现行状态（在用/已暂停/已被修改/已删除）、来源（含诚实「来源不明」）、当时被选中的原因（服务端翻译 + 「原因说明暂缺」honest-unknown）、未说出口的原因（internal_only）、最近使用、旧版回执提示，底部「这不对」直接进修改（correction loop，MEMORY_AURORA_UI.md Correction experience）。
- `presentation/screens/understanding_screen.dart` + 路由 `/memory/understanding`（memory_routes.dart，barrel 已登记）。

设计令牌合规：全部使用 owner 组件（SparkleButton/SemanticPill/EmptyState/CustomErrorWidget/GraphiteScaffold/SparkleRefreshIndicator/LoadingIndicator/DS token）；**未改任何 design owner 组件**（无 wt67 冲突；SparkleButton 仅用既有构造参数）。

## 3. 真实语义接线 + 纠正后同步（工作 2 / acceptance ②）

操作链（全部真实端点，无 mock）：
- 修改 → `POST .../update`：supersede 返回新条目原位替换；UI 即时反映 + 列表重取。
- 删除 → `POST .../revoke`：仅接受真实 `revoked=true`；列表重取后条目消失（服务端对非 ACTIVE 隐藏）。
- 暂时不用/恢复 → `PUT .../scope` pause/resume：卡片状态徽标即时变化。
- 仅此 Goal → `PUT .../scope` link_plan（真实 plan_id，后端归属校验）。
- 「这不对」（receipt 内）→ 复用 update 通道，`reason=why_this_correction`。

同步链（验收②：纠正/删除后界面与下一次 decision 同步变化）：
1. **服务端保证**：M-07 失效链在变更事务内 bump `memory_epoch` + 发 `memory.invalidated` + DEL derived cache → 下一次 ContextPack/decision 必然使用新数据（后端测试已覆盖，M-08 交付）。
2. **客户端界面**：mutation 成功后 `_syncAfterMutation()` 重取 provenance 列表（四组视图即时重排）。
3. **decision 呈现面**：`ref.invalidate(understandingSnapshotProvider)` → home「Sparkle 懂我」/chat 理解抽屉立即重取快照。
   provider 级测试 `correction invalidates understandingSnapshotProvider` 用计数型 ApiClient 断言 invalidate 后重取真实发生。

诚实申报（缺失语义面，如实登记不 mock）：
- `link_task`（绑定到任务粒度）后端已支持，但移动端缺现成 task-picker，本卡只接 `link_plan`（plan-picker 复用 PlanRepository）。未伪造 task 选择。
- Why-this 依赖 memory_use_receipt（pack_id/why_included 等在 chat 流内）；理解面入口按条目 ref 构造最小回执（服务端接受并返回 still_in_use/来源/治理历史）。chat 流内回执的深链入口属 chat 面卡片，不在本 lock 内。

## 4. 黑话移除清单（工作 3 / acceptance ①）

| # | 位置 | 移除的黑话 | 替换 |
|---|---|---|---|
| 1 | home「Sparkle 懂我」面板副标题（understanding_panel.dart + arb） | `{count} 条判断 · {ratio}% 高置信`（即卡面所指 "5 correctable claims / 75%"） | `understandingPanelPlainSubtitle`「这些是 Sparkle 目前的判断，每一项都可以纠正。」 |
| 2 | chat 理解抽屉副标题（understanding_drawer.dart + arb） | `{count} 条可纠正判断` | 「Sparkle 目前的判断，都可以纠正」（去 count 参数） |
| 3 | arb key `understandingPanelSubtitle` | 整键删除（zh/en），生成物同步 | — |
| 4 | claim 无障碍标签 | `(confidence*100)%` 百分比 | 定性层级词（把握程度：高/中/低） |
| 5 | 记忆面板 V2 主呈现（memory_panel_screen.dart） | 类型/证据双排筛选 chips（「偏好/目标/经历/OK/缺失/已隐藏」数据库管理器式分类）、「N 条」计数、重要性/置信度数值排序 | 四组理解视图（服务端 bucket_label 用户语言）+ 每卡来源/层级/范围一行 |
| 6 | V2 死代码 | MemoryEntry/MemorySort/MemoryViewMode/筛选条/条目排序器共 ~370 行删除 | — |
| 7 | 空态 | 计数式空态 | 「Sparkle 还不了解你」+ 引导一句话（全空时保留既有「记忆面板还没有内容/开始对话」引导，非计数） |

测试内断言：`memory_panel_v2_test`、`understanding_overview_view_test`（「条判断/%/0 memories findsNothing」）、`understanding_panel_copy_test`（面板副标题与百分比移除断言）。

## 5. 测试统计（全部 --concurrency=1 串行，≤2 文件/批）

**新增（17 例，全绿）**：
- `test/features/memory/data/memory_provenance_repository_test.dart` — 5：请求形状与 M-08 契约逐字段对齐（list 查询串/update body/scope 三动作/revoke body/why-this receipt 结构）。
- `test/features/memory/presentation/providers/understanding_overview_provider_test.dart` — 5：四组分组、update 原位替换+重取、revoke 移除、pause 真实 epoch 回执、**纠正后 understandingSnapshotProvider 失效重取（验收② provider 级）**。
- `test/features/memory/presentation/widgets/understanding_overview_view_test.dart` — 7：四组渲染用户语言、黑话移除断言、空态、编辑接线、删除接线、暂停接线、**Why-this receipt 渲染（含 honest-unknown 与「这不对」入口）**。
- `test/widget/understanding_panel_copy_test.dart` — 1（可并入上行计数）：home 面板黑话移除。

**既有回归（本卡触碰面，最终全绿）**：memory 面板系列（panel_v2/panel_screen×2/governance/correction/explain/auto_memory/settings/scene_recent_summary）、evidence_cards(46 例含 badge 组)、unresolved_conflicts、subject_type_filter、chat memory_reference_receipt(2)、aurora freeform correction(2)、aurora preferences(5)、aurora core session sheet、working_memory_card、user_state_profile_context_fallback、profile_transparent —— 逐批通过。

**测试基线修复（harness-only，不削弱断言，逐一申报）**：
1. `test/shared/i18n_test_helper.dart`：`testMaterialApp` 默认挂 `SparkleThemeExtension.light()`——owner 组件（SemanticPill/SparkleRefreshIndicator）构建即读 `context.sparkle`，未注册即断言失败。与仓库内 galaxy/profile 测试同款存量修复先例。基线影响：memory 面至少 8 例因此红（基线预存，Step 3 报告同类申报「harness 预存」）。
2. `test/widget/memory_panel_screen_test.dart`：自带 MaterialApp.router 补挂 theme（同款修复）。
3. `test/widget/aurora_freeform_correction_dialog_test.dart`：harness 补挂 l10n delegates + 显式 EN locale（对话框源码 `AppLocalizations.of(context)!`，原 harness 未挂 delegates 构建即 null 崩溃；测试原断言英文按钮，locale 对齐原意）。
4. `evidence_cards_test` MemoryEvidenceBadge 组 5 例：断言从已删除的 Chip 形状迁到 owner `SemanticPill`（状态→文案/tone 映射 + 计数前缀，强度不降）。根因=U-01 Step 3 已把 badge 迁 owner 但未同步该组断言（badge 在本卡 lock 内）。

**基线预存红（未触碰、如实申报，不计入本卡回归）**：
- `test/core/services/memory_api_service_test.dart` 2 例：测试期望 401 时回落默认设置，与现行 R2-01 契约（鉴权失败必须传播、绝不伪造用户设置，服务内注释明示）相反——陈旧测试，修复属 R2-01/memory-settings 所有者，本卡不改语义。
- `test/widget/user_persona_screen_test.dart` 1 例：persona readable summary 富文本管线渲染断言（rich-text 归属 persona 面，非本卡改动；与基线完全一致）。
- l10n 生成噪声：`flutter gen-l10n` 对三个 `app_localizations*.dart` 产生纯格式重排（本地工具链 dart 风格差异），已并入本 patch 并申报。

## 6. Acceptance 映射

| Acceptance | 证据 |
|---|---|
| ① 用户 30 秒解释 Sparkle 知道什么/为什么/怎么改 | 四组视图进入即见（组名即回答"知道什么"）；每卡来源/层级/范围/时间一行（"为什么"）；「为什么有这条」receipt 给完整来源+选中原因；操作条第一眼可见修改/删除/暂时不用/仅此 Goal（"怎么改"）；顶部一句 intro 说明。黑话计数全部下线（§4），主呈现零内部参数。widget 测试断言结构可达。 |
| ② 纠正/删除后界面与下一次 decision 同步变化 | 服务端 M-07 epoch/invalidated/derived-cache 链 + 客户端列表重取 + `understandingSnapshotProvider` 失效重取；provider 级测试计数断言；UI 级 update/revoke/pause 后状态即时断言（view 测试 + panel 测试）。 |
| ③ A/B visual issues=0 | 零模拟器（本卡约束），采用「B-04 截图基线 + 代码级视觉审计」对照，结论见 §7；端到端实机 A/B 留主会话（工具已就绪：`/memory/understanding` 路由 + V2 面板直出）。 |

## 7. A/B 视觉对照（对照 backup/2026-09-21/B-04-final/ 只读基线）

B-04 `memory__panel_main` canonical（Q0.66 场景卡 + 待处理承诺 + completed 卡 + 双排筛选 chips）vs 本卡 V2 目标结构：

- **不引入新问题**：主呈现从 3 层筛选/计数变为四组列表；所有新 UI 走 owner 组件与 DS token（无裸 Chip/裸 spinner/裸错误态）；卡片密度与既有 Card/ListTile 体系一致； 新增状态徽标只用 SemanticPill 既有 tone（success/info/neutral/warning）。
- **V20（memory 条目 "completed…" 原始事件文案）**：数据级 copy 问题（上游 episodic summary 生成），本卡未修——但新四组视图把它归入「对你有效过的方法/我还不确定的」等语义分组并带来源行，可读性不再以裸标题堆叠呈现；**未恶化**。属上游 copy-review 卡输入。
- **V21（待处理承诺毫秒时间戳）**：`pending_commitments_section.dart` 本卡未触碰，维持基线现状；**未恶化**（B-04 遗留，非新增）。
- B-04 正向基线项「筛选 chips 设计合理、Q 值徽标直观」：Q 徽标（最近场景卡）保留未动；筛选 chips 的移除是 MEMORY_AURORA_UI.md「不是数据库管理器」+ 黑话移除的明确设计指令，与本正向项冲突处按 must_read 文档优先。
- 遗留声明：实机截图 A/B（before/after 同状态截图 + 目检）需模拟器，按纪律留主会话端到端；本卡以 widget 测试（1440×2200 大 surface pumpAndSettle 无溢出异常）+ token 审计作为过程证据。

## 8. 诚实申报汇总

1. **冲突预警核查结果**：未动任何 design owner 组件（SparkleButton/EmptyState/SemanticPill 等），wt67 无冲突。
2. `link_task` 未接（缺 task-picker，如实登记，见 §3）；其余四动作全部真实接线。
3. 为什么入口按条目 ref 构造最小 receipt；chat 流内 receipt 深链属 chat 卡。
4. 两处基线预存红（memory_api_service_test/persona）与基线完全一致，未修复也不属于本卡（原因见 §5）。
5. l10n 生成物格式噪声（3 文件）随 patch 交付。
6. gen/ 代码 27 文件按纪律从主仓只读复制（gitignored，不入 patch）。
7. 测试基线修复 4 项均为 harness-only/陈旧断言迁移，逐条见 §5。
8. `/tmp` 中间产物已清理；worktree 内 `.dart_tool`/build 收工清理。
