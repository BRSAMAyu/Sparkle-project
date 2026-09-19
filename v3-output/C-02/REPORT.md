# C-02 · State/Memory/Knowledge/Events 四分适配层 — 执行报告

- 基线：main @ db652302 交付（C-01✓ / M-01✓ / D-01✓；M-03 当时待合入）→ R2 返修
  后 rebase 至 **origin/main @ 42180162**（M-03 已在树，见 §11.2）
- worktree：wt9；锁：context-builder；禁 commit/push（未做）
- 状态：READY_FOR_REVIEW（R2 返修完成，见 §11；待 R2 delta 复核）

## 1. 解决的真实问题

ContextBuilderMixin 装配的 user_context payload 把 profile（state 域）、stage34 记忆
（memory 域）、galaxy/种子库（knowledge 域）、工具使用/校准回执（events 域）混成一个
无来源标注的平铺 dict，且存在三个**后写静默覆盖面**：`_merge_user_contexts` 的 grpc
覆盖、pack 非 resolver 分支的 `{pref_key: pref_value}` 折叠、以及任何 stage 适配器对
base 同名 key 的后写——覆盖发生时无检测、无登记、无告警。USER_WORLD_MODEL.md 的
"四类对象不可混"在装配面没有执行机制。

## 2. 适配层形态（核心设计）

新模块 **`backend/app/orchestration/context_sources.py`**（schema
`context_sources.v1`），四个 install 面：

1. **封闭四类词表** `SOURCE_CATEGORIES = (state, memory, knowledge, events)` +
   `SOURCE_CATEGORY_BY_ITEM_TYPE`：C-01 冻结的 6 个 item type 封闭投影到四类
   （goal/plan/user_state_signal→state：USER_WORLD_MODEL §1 把 Goal 归 Current State，
   存储在 MemoryGoal 表不改变语义类别；preference/episodic_memory→memory；
   document_chunk→knowledge）。**不改 C-01 冻结面**（ref scheme/why_included/字段集
   原样），events 条目不进冻结 items——走本层 manifest（扩展 items 需 C-01 契约
   bump + 双 reviewer，本卡不越权）。
2. **四类 adapter**（`StateSourceAdapter` / `MemorySourceAdapter` /
   `KnowledgeSourceAdapter` / `EventSourceAdapter`）：各自独立 settings 开关
   （`ENABLE_CONTEXT_SOURCE_{STATE,MEMORY,KNOWLEDGE,EVENTS}`，默认 True）+ token/项数
   计量 + seed/demo 标记。
3. **`SourceRegistry`**：按写序登记 (category, key)；同名 key 后写 → `SourceOverride`
   显式登记 + loguru WARNING + namespaced key（`memory/X` vs `state/X`）四类并存。
4. **`KEY_CATEGORY_MAP`**：ContextBuilderMixin payload 全部 33 个 key 逐一登记类别
   （判据逐条写在 map 注释）；请求参数/kill-switch 归显式 `control` 桶（不硬塞四类）；
   未登记 key 落 `unclassified` + 告警（防新增 key 再度无来源混装）。

### seed/demo 标记（与 registration_source 口径对齐）

- 用户级：`registration_source ∈ {seed, system, guest}`（guest_seed_service="seed"、
  simulation_runner="system"、guest_cleanup="guest" 的既有写方口径）。
- 条目级：memory `source_type == "startup_seed"`（guest_seed_service 落的记忆）；
  种子库 few-shot（`seed_library`）恒标 seed（内容本身即种子）。
- manifest 输出 `user_is_seed_or_demo` + 每类 `seed_or_demo` 计数与 `seed_or_demo_items`
  key 列表，消费方可直接过滤。

### Events 走 D-01 词表

`event_name_for_decision_record` → 注册名 **`decision.recorded`**（EVENT_REGISTRY 中
status=reserved、producers 即 "v3: decision_records read projection"——本适配器是该读
投影的首个落地消费方）；经 `is_registered_event_name` 校验 + `EVENT_SCHEMA_VERSION`
盖章；registry 撤名时抛错并降级标记，绝不静默换名。

### Memory 走 M-03 预筛接口（前向兼容，零撞卡）

`apply_memory_prefilter(candidates, *, user_id, purpose="llm_context", ...)` 按 M-03
REPORT §2.1 接口编程（`prefilter_candidates` + `RetrievalContext`，lazy import）：
模块未在 main 时透传 + `prefilter_applied=False`；wt4 合入后零改动生效。单测注入
fake 模块验证委托调用（purpose/plan_ids 传参断言）。**不碰** M-03 的三个接线点：
context_pack.build 拉取行、context_manager._get_past_session_memory、stage34 预筛
（M-03 返修负责）——本卡对 stage34 只做来源类别标注（KEY_CATEGORY_MAP + manifest，
stage34 函数体零改动）。

## 3. D-CTX 收敛进度（本卡落地的迁移路径第一步）

- **pack 侧（契约面）**：`ContextPackBuilder._build_source_manifest` →
  `pack.metadata["sources"]`（四类分节：item_count/token_estimate/enabled/seed 计数/
  note；decision items 逐条封闭投影计数 `item_category_counts`——"每 item source type
  正确"的机器验证面）。knowledge/events 在 pack 中显式 0 计量 + channel note（文档/
  决策记录/历史走 orchestrator 侧与 ContextBudgetManager），不留静默空缺。
- **orchestrator 侧（平行路径降级）**：`_attach_source_manifest` 在 stage39 之后给
  payload 附加 `context_sources` manifest（provider 读：registration_source +
  decision_records 最近 3 条；读失败只降级该输入，测试覆盖无 DB 降级路径）。stage
  适配器自此成为**带来源标签的数据源**——这是 D-CTX 冻结迁移路径的落地起点；
  payload 既有 key 的值零改动（manifest 纯 metadata 面，消费面不变）。
- 尚未做（后续卡）：orchestrator 直接消费 ContextPack 替换本地装配、prompt 按
  manifest 分节渲染。本卡把两条路径的**来源语义**统一到同一词表/同一 manifest
  结构，为替换铺平。

## 4. 无静默覆盖保证（红→绿证据）

**红（characterization，锁定缺陷现状，永久保留）**：
- `test_red_flat_dict_merge_silently_drops_local_value`：grpc 后写覆盖 local
  active_plans，值消失且无任何登记面；
- `test_red_preference_records_same_key_collapse`：同 pref_key 两记录 dict 折叠，
  后写胜出无痕。
- 首次运行红态：`ModuleNotFoundError: No module named 'app.orchestration.context_sources'`。

**绿（机制）**：
- `SourceRegistry`：四类同名 key → 3 次覆盖登记 + WARNING 日志 + 4 个 namespaced
  key 并存（`test_registry_detects_cross_category_same_key_overrides`）；
- `detect_merge_overrides` 接入 `_build_full_context`（grpc 合并面，copy-on-write
  并入 manifest，值语义不变）；
- `detect_preference_key_overrides` 接入 context_pack.build 非 resolver 分支
  （`last_write_wins_visible`；注：`list_preference_records` 上游已按 M-01 版本链
  按 key 去重，此为装配表达式的防线，非当前热路径）；
- `LATE_STAGE_WRITERS`：stage34/39 晚写的 7 个 payload key 静态写序显式入 manifest
  （`late_stage_writers`，provenance 标注）。

## 5. history 语义（仅最近必要消息 + compaction，不替代 state）

现状核查：ContextPruner 已实现 recent window（4 条）+ summary 阈值（30 条）压缩。
本卡最小收敛：`_build_full_context` 把 pruner 结果（messages/original_count/
pruned_count/summary_used/recent_window）经 `attach_conversation_history` 记入
manifest **events 通道**（message sent 属事件域）+ history token 计量；铁律由结构
保证——state 通道没有 conversation_history 写入点
（`test_state_source_adapter_never_consumes_history` +
`test_attach_conversation_history_updates_events_channel_only` 断言 state 节不受
历史附加影响）。不重写会话管理（pruner 零改动）。

## 6. trace 可观测（验收②）

- **pack 侧**：`context_pack_runs.memory_counts` JSONB 附加 `"sources"` 键（既有读者
  `normalize_memory_counts` 只按已知 key 求和，不受影响——测试断言）。验证 SQL
  （已在 dev DB 只读实测，旧行 NULL、新行带值）：

```sql
SELECT created_at, intent,
       memory_counts->'sources'->'state'->>'item_count'    AS state_items,
       memory_counts->'sources'->'state'->>'token_estimate' AS state_tokens,
       memory_counts->'sources'->'memory'->>'item_count'   AS memory_items,
       memory_counts->'sources'->'memory'->>'token_estimate' AS memory_tokens,
       memory_counts->'sources'->'knowledge'->>'item_count' AS knowledge_items,
       memory_counts->'sources'->'events'->>'item_count'   AS events_items
FROM context_pack_runs ORDER BY created_at DESC LIMIT 20;
```

- **orchestrator 侧（主聊天链路，无 pack telemetry 表）**：两条结构化 INFO：
  `C-02 context sources user=...: state=Ni/Nt memory=... knowledge=... events=...
  seed_demo_user=... overrides=N`（`_attach_source_manifest`）与
  `C-02 conversation history (events channel): messages=... original=...
  summary_used=... tokens=...`（`_build_full_context`）；pack 构建同型日志
  `C-02 context pack sources pack_id=... item_categories=...`。

## 7. 测试与验证证据

新增 `tests/unit/test_context_sources.py`（30 tests）+ `tests/unit/test_context_pack_sources.py`
（4 tests，sqlite 集成）；回归：contract `test_decision_context_contract.py` 15✓、
`test_event_registry_contract.py`（1 个**预存失败**，见 §9）、context_pack 全家族
（budget/conflicts/ranking/personalized_ranking/rollout/feedback/budget_manager/
focusing）45✓、orchestrator mixins 目录 127✓、`test_context_pruner`、
`test_rule_as_guard`✓（新增 `context_sources` 附件以 `# rule-as: ignore` 登记——
metadata-only 面，无 prompt/routing 消费方属设计而非缺失）。lint：改动文件
black(120) + ruff 全过。运行环境：借用 sparkle-cosmos/backend/.venv
（PYTHONDONTWRITEBYTECODE=1 只读），SECRET_KEY 测试值内联。

## 8. 改动清单

- 新增 `backend/app/orchestration/context_sources.py`（四分适配层，~640 行含设计注释）
- 新增 `backend/tests/unit/test_context_sources.py`、`tests/unit/test_context_pack_sources.py`
- `backend/app/core/context_pack.py`：pack 侧 manifest + telemetry `memory_counts.sources`
  + preference 折叠显式化（telemetry 块移至 decision_ctx 之后统一落账，pack_id 供
  manifest 日志关联；行为等价，telemetry/contract 测试回归✓）
- `backend/app/orchestration/context_builder.py`：`_attach_source_manifest` +
  `_build_full_context` 的 grpc 覆盖检测与 history 附加（stage34/39 函数体零改动）
- `backend/app/config/settings.py`：4 个独立开关（附带 black 对既有注释对齐的归一）

## 9. 边界与遗留

- **预存失败（非本卡引入，clean tree db652302 复现）**：①`test_event_registry_contract
  ::test_truth_path_modules_never_read_client_telemetry[state_aggregator/service.py]`——
  D-01 守卫把 state_aggregator 注释里的 "stream:tracking_events" 字样当引用（守卫
  误报，属 D-01/state_aggregator 维护方）；②RB-06 flush 测试在本机连 dev DB 密码
  失败（环境性）；③rule guards K/Z/BG 在无生成物的新 worktree 失败（BG 缺 Go/Dart
  生成物；K/Z 同类，clean tree 复现）。
- **Rule AS 守卫的标签 bug**（预存）：context_builder 附件的违规打印成
  profile_context_service 路径（f-string 硬编码），不影响判定，建议守卫维护方修。
- knowledge/events 在 pack 侧为 0 计量 + channel note：文档正文计量在
  ContextBudgetManager（既有），决策记录/历史在 orchestrator 侧 manifest——四类
  全量计量需等 D-CTX 后续卡把 orchestrator 切到 ContextPack 后自然合并。
- M-03 合入后：读侧预筛委托入口为 ``prefilter_memory_candidates_for_llm_context``
  （R2 返修后直调真模块，见 §11/§11-F4；原文「apply_memory_prefilter 自动生效」
  表述有误导，R2-F4 已纠正）；其 pack 侧 ``metadata["memory_prefilter"]`` 已在
  manifest memory 节以 note 透传（rejected 计数可见）。

## 10. 收工清理

删除 `backend/app/gen/`（主仓只读拷贝）、`__pycache__`/`.pytest_cache`、/tmp 探针
diff；无进程/模拟器/浏览器；venv 只读借用未写入；未 commit/push。
（R2 返修注：本轮 gen/ 保留在交付树——R2-F6 要求交付树可 collect 测试；gen/ 属
gitignored 生成物，不进 patch/repo。）

## 11. R2 返修记录（含接续盘点）

- 审计依据：`v3-output/C-02/REVIEW_RECEIPT_2.md`（R2 DeepAudit，Verdict: CHANGES；
  P1 F1/F2 + P2 F3-F6 + P3 F7-F11）
- 返修执行：两段接续。前任返修员（15:52 额度阵亡，~19 分钟）完成主体实现；
  本段接续盘点其半成品、修复一处 wiring 测试盲区、完成基线对齐与全部验证。
- 基线：rebase 至 **origin/main @ 42180162**（自 d21d1579 前移 2 个 doc-only 提交，
  autostash 逐字保留工作树 diff）；M-03 真模块（1ea854c9）在树内。
- 状态：READY_FOR_REVIEW（R2 delta 复核）

### 11.1 接续盘点（前任半成品 → 判定）

| 前任产物 | 对应 | 判定 | 处置 |
|---|---|---|---|
| `context_sources.py`：`MANIFEST_*_KEYS` 冻结 + `assemble_manifest`/`normalize_section` 唯一序列化权威 + `build_payload_source_manifest` 收敛 | F1 | 完成（合格） | 保留；仅 black 归一 |
| `context_pack.py` `_build_source_manifest` 全量改经 `normalize_section`/`assemble_manifest`（两面同 key 集，面间不适用值 None/{}） | F1 | 完成（合格） | 保留；black 归一（sum 推导式/token_estimate 两处） |
| `test_context_source_contract.py`：两面 key 集精确相等断言 + 常量字面钉死 + W1(sqlite)/W1b/W2/W3/W4 接线钉 + F9/F8 golden map | F1/F2/F9/F8 | **部分**（W2/W3/W4 为纯调用名存在性 AST——对 M5 的"禁用"变异形态盲） | 接续段修复：`_live_call_names` 常量假守卫剪枝（见 11.3-F2） |
| `context_sources.py`：删本地 `apply_memory_prefilter`/`PrefilterOutcome`，新增 `prefilter_memory_candidates_for_llm_context`（真模块直调 + `build_retrieval_context` 权限 + 异常上抛 + metric 透传） | F4 | 完成（合格） | 保留 |
| `test_context_sources.py`：RED characterization 改真实 `_merge_user_contexts`；M-03 e2e/permissions/no-swallow 三测；`register_post_manifest_writes` 两测 | F3/F4/F5 | 完成（合格） | 保留；ruff SIM300（Yoda 反转）修回原序 |
| `orchestrator.py`：`process_stream` 4 键 + `_attach_aurora_planning_sidecar` sidecar 共 5 个后写 key 经 `register_post_manifest_writes` 补登记 | F5 | 完成（合格） | 保留 |
| `test_context_pack_sources.py`：pack 面 None/{} 断言 + 同 key 双记录折叠真实 characterization | F1/F3 | 完成（合格） | 保留 |
| `detect_preference_key_overrides` 增 `final_values` winner 回溯 + `contenders` 全记录登记 | F2/F3 加严 | 完成（合格） | 保留（rank 重排下登记与事实一致） |
| REPORT.md R2 返修记录 / changes.patch 再生成 / rebase 42180162 | 收尾 | 未动 | 本段完成 |
| F7/F10 边界登记 | P3 | 未动 | 本段补（见 11.4） |

原则执行情况：无删除/重写前任合格工作；本段实质改动仅 3 处——W 系 AST 剪枝修盲、
lint 归一、REPORT/patch 收尾。

### 11.2 基线对齐（rebase）

`fetch origin && rebase --autostash origin/main`：d21d1579 → **42180162**（仅
`86f3ed6d` Ledger 文档 + `42180162` AGENTS 文档两个提交，无代码冲突面）。autostash
回放后 `git diff` 与 rebase 前逐字节一致（diff 校验）；untracked 交付物原样保留。
R2 提示的 event_registry/context_pack 冲突面在本区间不存在（均为 doc-only 提交）。

### 11.3 返修清单逐项处置

- **F1（P1）manifest 同版本双形状 → 收敛为单一形状（方案 a）**：
  `MANIFEST_TOP_LEVEL_KEYS`（10 键）与 `MANIFEST_SECTION_KEYS`（11 键）冻结为
  模块常量；两面序列化唯一权威 `assemble_manifest`/`normalize_section`（构造保证
  形状）；面间不适用值为 `None`/`{}`（orchestrator 面 `item_category_counts=None`
  ——恒 key 不误导为 0；pack 面 `user_is_seed_or_demo=None`/`late_stage_writers={}`）。
  契约测试（test_context_source_contract）把**两条路径**的顶层/分节 key 集对冻结
  常量做 `set(...)==set(...)` 精确相等断言，常量内容本身再被字面 tuple 钉死
  （同时改常量与实现的绕道也不可行）。telemetry 派生面（memory_counts.sources =
  sections 子集）不变。
- **F2（P1）三处接线零钉住 → W1-W4 + 变异实证**：
  - W1（行为级，sqlite）：同 pref_key 双记录 → `metadata["sources"]["overrides"]`
    非空，winner 与实际胜出值一致（final_values 回溯），contenders 全记录可见；
  - W1b/W2/W3/W4（AST）：pack build 调折叠检测+manifest 构建、`_build_user_context`
    调 `_attach_source_manifest`、`_build_full_context` 调 merge 检测+history 附加、
    orchestrator 两处调 post-manifest 登记。
  - **接续段修盲（本段核心增量）**：原 W2/W3/W4 是调用名存在性检查——R2-M5 的
    变异是"禁用"（`if False:` 守卫）而非删除，接续段变异复测 M5 仍全绿（盲区实
    证）。修复：`_live_call_names` 把常量假守卫（`if False:` / `if False and X:`）
    的 body 剪枝为不可达，settings 开关（合法 kill-switch）不受影响——删除与禁用
    两种变异形态都必红；复测 10/10 变异全红（见 11.5）。
- **F3（P2）红测同义反复 → 真实代码 characterization**：
  `test_red_real_merge_user_contexts_replaces_local_value` 经最小 mixin 宿主调用
  真实 `_merge_user_contexts`（锁定"合并函数本身无痕替换，检测层在调用方"的分层
  现状）；pack 折叠面由 sqlite 集成锁定（test_context_pack_sources 双记录测试 +
  W1）。原手写 dict 复现测试删除。
- **F4（P2）M-03 死代码 → 直调真模块**：
  删本地 `apply_memory_prefilter`/`PrefilterOutcome`（有 no-dead-code 断言测试钉
  死防回潮）；委托入口 `prefilter_memory_candidates_for_llm_context` 与 M-03 的
  async `apply_memory_prefilter` **刻意不同名**（防接错版本）；context 经 M-03
  `build_retrieval_context` 组装（`user_memory_settings` permissions 随 db 载入，
  `allow_episodic=False` 实测拒绝）；委托异常上抛（无静默透传，接口漂移以失败
  可见）；`PrefilterResult.to_metric_payload` 原样透传。三测：真模块 e2e（wrong-user
  fail-closed + metric 断言）、permissions 生效、no-swallow。
- **F5（P2）manifest 后写盲区 → 显式登记闭合**：
  5 个后写 key 全部补登记——`process_stream` 的 use_document_context/document_filter/
  selected_document_ids/conversation_settings（4 键）与 `_attach_aurora_planning_
  sidecar` 的 aurora_planning_sidecar（KEY_CATEGORY_MAP 增 control 映射）经
  `register_post_manifest_writes`（copy-on-write，幂等，manifest 缺失降级静默；
  未登记 key 落 unclassified+WARNING——未来后写四类 key 也可见）。生产环境
  control_keys 不再恒空；W4 AST 钉住两处调用接线。
- **F6（P2）交付树可复现**：`backend/app/gen/`（gitignored 生成物）保留在交付树，
  不再收工删除——本卡测试/mixins/contract 全部可 collect（本轮全部验证即在该形态
  下运行）。
- **F9（P3）**：KEY_CATEGORY_MAP 整表 golden 相等断言（37/37 键，此前仅 ~27 被
  fixture 钉）；模块 docstring 增"命名陷阱澄清"：payload `"preferences"`（复数，
  profile 画像）= state，pack 面 DecisionItem type `"preference"`（单数，memory
  记录）= memory——按（面, 词形）取义。
- **F11（P3）**：`SourceSection` 双键收敛为仅 `item_count`（"items" 冗余键删除，
  两面同形状下由契约测试钉死，未来移除/新增即红）。
- **F8（P3，加严）**：`LATE_STAGE_WRITERS` 整表 golden 断言（7/7 键，此前 2/7）；
  stage 写序变化必须同步改表与测试（否则红）。
- **F7/F10（P3）→ 登记为已知边界（不改行为）**：
  - F7：manifest 随 payload 进 120s 用户上下文缓存（FT-LAT-3），decision_records/
    registration_source 计量最长陈旧 120s——缓存语义与 payload 同生命周期，属
    设计边界，非缺陷；
  - F10：`build_payload_source_manifest` 对全 payload json.dumps+tiktoken 计量为
    O(payload) 热路径成本，已有 `[LATENCY] source_manifest` 计时面可观测，无回归
    门（载荷极大时的量化阈值留待 D-CTX 后续卡）。

### 11.4 变异实验（接续段复测，10/10 红；含还原校验）

| # | 变异 | 红 | 锁定测试 |
|---|---|---|---|
| M1 | registry 覆盖登记禁用（`if False and previous`） | 2 | registry_detects_cross_category / registry_warns |
| M2 | 未知 payload key 静默归 state | 1 | payload_manifest_unknown_keys_do_not_silently_land |
| M3 | pack 折叠登记接线 → 空列表 | **2** | W1（行为）+ W1b（AST） |
| M4 | 删 `_attach_source_manifest` 调用 | **1** | W2 |
| M4b | 同 M4 + tests/unit/orchestrator/ 全目录 | **1** | W2（174 passed 之外唯一红） |
| M5 | 禁用 grpc merge 检测 + history 附加（`if False` 守卫） | **1** | W3（接续段剪枝修复后才红——原 AST 对禁用形态盲，已实证并修复） |
| M6 | recent_tool_usage events→state | 2 | categories_and_metering + key_category_map_golden（golden 加严后比 R2 时的 1 红更强） |
| M7 | history 泄入 state 节 | 1 | attach_conversation_history_updates_events_channel_only |
| M4d | 加严：M4 的"禁用"形态（`if False:` 包调用） | 1 | W2 |
| W4d | 加严：orchestrator post-manifest 登记禁用形态 | 1 | W4 |

对照完成标准：M3/M4/M4b/M5（原全绿四组）全部转红；M1/M2/M6/M7 保持红。每轮变异
后文件与备份逐字节 diff 校验还原一致；`git status` 恢复交付原状。

### 11.5 回归验证（rebase @ 42180162 + 返修后）

| 套件 | 结果 | 备注 |
|---|---|---|
| test_context_sources.py + test_context_source_contract.py + test_context_pack_sources.py | **50✓** | 原 34 + 新增 16（契约 4 + golden 2 + W 系 5 + M-03 三测 + post-manifest 两测等） |
| tests/unit/orchestrator/ 全目录 | 125✓ | |
| tests/contract/ decision_context + event_registry + test_rule_as_guard | 50✓ 1✗ | ✗为 REPORT §9 既录的 D-01 守卫误报（state_aggregator），预存、与本卡无关 |
| context_pack 家族（pack/conflicts/feedback/personalized_ranking/ranking/rollout/budget_manager/budget_scheduler/focusing/context_ranker/manager_community） | 37✓ | |
| tests/test_context_pruner.py | 8 skipped | 环境性 skip，预存（与 R2 记录一致） |
| lint（black 26.3.1 + ruff） | 过 | 新文件全绿；modified 文件 hunk 干净（orchestrator/context_pack 基线本存 black 26.x 漂移，非本卡引入、不在本卡 hunk 内不整理） |
| 真实 LLM | 0 次 | 全程无外部模型调用 |

环境：sparkle-cosmos/backend/.venv 只读借用（PYTHONDONTWRITEBYTECODE=1），
sqlite/mock，dev DB 未触碰，主仓只读，未 commit/push。

### 11.6 交付物

`changes.patch` 已再生成（8 文件：4 M settings/context_pack/context_builder/
orchestrator + 4 新 context_sources + 3 测试文件；3035 行）。
