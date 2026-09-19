# M-03 Scope/TTL/Purpose 确定性预筛 — 执行报告

worktree: `Sparkle-sysrev/wt4`，base = main @ `43942d23`（X-01 ACCEPT merge 后）
gate: V3-2 ｜ stream MEMORY ｜ risk high ｜ reviewers_required 2 ｜ locks: memory-retrieval
禁 commit/push（已遵守）。改动全文见 `changes.patch`（返修轮后 11 文件，+1983/-6）。

> **接续说明**：前任 worker 初始开发基于 `6f488636`（D-01 merge 后）因额度中断；本 worker
> 接续后确认 6f488636..43942d23（E-01/X-01 两次 merge）与 M-03 改动文件零重叠，已将全部
> 未提交改动整体迁至 `43942d23`（checkout 携带，无冲突），并在新基上**全量复验**：红→绿
> 重证、单测/集成/回归重跑、lint 重查、changes.patch 重新生成（reverse-apply 校验一致）。
> 前任的实现经逐行代码评审后全部沿用（纯函数核心/M-01 委派/封闭词表/接线点设计均合格），
> 仅修复模块 docstring 一处拼写（`classify_episemic_class`→`classify_episodic_class`）。

## 0. 六句总结

预筛器形态：单一权威模块 `backend/app/services/memory_retrieval_prefilter.py`——纯函数核心
`prefilter_candidates(candidates, ctx)`（零 I/O，任何候选源可复用）+ 唯一异步适配器
`build_retrieval_context`（best-effort 读 user_memory_settings）。scope lattice 以封闭常量
`SCOPE_LEVELS × {unconstrained, match, mismatch}` 兼容矩阵为单一真源，session 级 fail-closed、
无锚点 scoped 记录按 user-global 放行、global 恒过。红绿证据：基线（未接预筛）5/5 集成测试
失败——superseded 行/expired 承诺（due_at+7d）穿越 SQL 实漏、wrong-user/revoked 候选无级守卫、
user_memory_settings 读侧零执行；接入后同测试集 5/5 通过。接入点两处：
`context_manager._get_past_session_memory`（重排前）与 `context_pack.build`（rank/语义门控前，
pref_history 保持不过滤供冲突消解）。filter reason metrics：每维度+每原因计数随返回值携带、
loguru 落日志、Prometheus `sparkle_memory_prefilter_rejections_total{dimension,reason}`、
pack.metadata["memory_prefilter"] 结构化输出（供 D-06/O-02）。**新基 43942d23 复验**（接续
worker 重跑）：单测+集成 58/58 通过；红→绿重证（stash 接线 → 集成 5 failed，恢复 → 5 passed）；
定向回归 22 文件 153 测试 152 通过，唯一失败 `test_two_consecutive_sessions_prompt_
includes_inferred_memory` 经全量 stash 基线对照在新基重证为预存（demo-mode LLM 路由环境性
失败）。black/ruff clean，patch reverse-apply 校验一致。
**双评审返修轮（R1+R2 均 CHANGES → Leader 裁决随卡修 5 项全部完成）**：R2-F1 未知 scope
level 由静默提升 global（fail-open）改为 fail-closed（`scope:unknown_level` 砍+指标）并加
M-01 词表 parity 守卫；R2-F2 求值顺序以实现为准统一 docstring 并把全部 5 个相邻对钉进
归因测试；R1-F1 修 context_manager I001；R1-F2 stage34 `context_builder.
_attach_stage34_memory_context`（主聊天链 payload → prompts.format_user_context 渲染进
系统提示词【近期相关记忆】段）接预筛，红（stash 接线 2 failed：superseded/expired 泄入
payload、allow_episodic=false 泄入）→绿；routing_engine:2530 与 aurora/signal_aggregator:
99-110 按 R2 裁决不接线（喂确定性路由非 LLM prompt，M-04 域），登记 §6.4/§7。返修轮
M-03 套件 68/68（61 单测+7 集成）+ 定向回归全绿。

## 1. 问题与目标

任务卡：LLM 前用确定规则砍掉不合法 Memory——user/status/revoked/scope/TTL/purpose/sensitivity
七维过滤 + goal/domain/task_type/global/time-window 兼容定义 + filter reason metrics。
验收：wrong-user/revoked/expired candidate 在 semantic retrieval 前为 0；单测覆盖 scope lattice
与 today-only。硬约束：不新增迁移（scope 派生自现有列）；预筛是既有检索链（importance/
confidence 重排）**之前**的 L0 硬层，不是替代；不改 LLM 调用本身。

### 勘察发现的实质缺口（基线实证，非理论）

1. **superseded 行实漏**：`list_recent_episodic` SQL 过滤 deleted/archived/retracted/revoked，
   但**不过滤 `superseded_by_id`**（M-01 加列后无读侧消费者）——被冲突消解替换的行照常进入
   LLM 上下文（红测实证）。
2. **expired 承诺无消费者**：`due_at+7d`（承诺类时敏记忆，memory_inferred_write_lane 写入）
   在 D4 账本已登记"仍无消费者"——过期承诺永久滞留检索池（红测实证）。
3. **superseded 偏好版本参与注入竞争**：`list_preference_records` 返回全版本链（含
   replaced_by_id 已置的旧版本），旧版本与链头一起进 rank/预算竞争（红测实证：2 个候选）。
4. **user_memory_settings 只在写侧执行**：`allow_episodic=false`/`blocked_pref_keys` 的用户，
   读侧（context_manager/context_pack）完全不查设置——用户关掉的照常注入 LLM（红测实证）。
   这正是 MEMORY_V3 §3 步骤 3 "purpose & permission" 的缺口。
5. **跨 plan 目标越界**：pack 构建带 plan_id 时，锚定其他 plan 的 goal 照常进入（scope 维度
   红测实证）。
6. **候选边界无级守卫**：wrong-user/revoked 行一旦越过 SQL（未来向量检索、working memory
   整合、或 SQL 回归），无任何二级防线（stage 级红测实证）。

## 2. 设计（核心决策）

### 2.1 单一权威模块 + 依赖方向

`app/services/memory_retrieval_prefilter.py`（`MEMORY_PREFILTER_VERSION = "memory-v3.m03.v1"`）：

- **纯函数核心**：`prefilter_candidates(candidates, ctx) -> PrefilterResult`——不碰 DB/Redis，
  供任何候选源（SQL 拉取、向量检索、整合管线）作硬层复用；
- **M-01 为真源，M-03 只加语义**：status 用 `derive_status(record, now)`（优先级
  revoked>superseded>retracted>archived>expired>resolved），scope 派生用 `derive_scope(record)`
  提升（lift）为类型化 `MemoryScopeDescriptor`，inferred 判定用 `classify_episodic_class`
  （HYPOTHESIS 即推断层）——本模块不重复定义任何 M-01 语义；
- **维度求值顺序固定** user→status→ttl→scope→purpose→sensitivity（**实现顺序即契约**，
  R2-F2：与 MEMORY_V3 §3 文档顺序 identity/status/purpose/scope/TTL 不同——廉价列派生砍
  在前、lattice 次之、settings 快照检查最后；docstring 已如实注明差异，顺序由
  `test_filter_dimensions_order_is_pinned` + 5 个相邻对归因测试钉死，reorder 必红且必须
  bump `MEMORY_PREFILTER_VERSION`），首个失败维度独占拒绝归因（指标确定性）；
- **保守放行与 fail-closed 的分界**：goal/domain/task_type 在检索上下文**未约束**该维度时
  放行（相关性是语义层职责，合法性与否才归 L0）；identity（wrong user/无 user_id）、
  session 越界、未知 scope level（**含派生路径**——R2-F1 返修：`scope_of_record` 保留未知
  level 原样进 descriptor，由 `scope_compatible` fail-closed，不再静默提升 global；
  M-01 `derive_scope` 词表 ⊆ `SCOPE_LEVELS` 有 parity 守卫，M-01 加新 level 此处必红）、
  TTL 窗口**无条件砍**。

### 2.2 scope lattice（封闭数据结构 + 单一真源）

```
SCOPE_LEVELS = (global, goal, domain, task_type, session)
SCOPE_COMPATIBILITY[(level, ctx_state)] -> bool    # 15 格全矩阵
ctx_state ∈ {unconstrained, match, mismatch}
LEVEL_ANCHOR_KEYS = goal→(goal_id,task_id,plan_id)  domain→(domain_key,)
                    task_type→(task_type,)          session→(session_id,)  global→()
CTX_ANCHOR_VALUES                                    # ctx 侧锚值唯一映射
```

| level \ ctx_state | unconstrained | match | mismatch |
|---|---|---|---|
| global    | pass | pass（不可达，恒真保险格） | pass（同左） |
| goal      | pass | pass | **cut** |
| domain    | pass | pass | **cut** |
| task_type | pass | pass | **cut** |
| session   | **cut** | pass | **cut** |

三条关键语义：
- **unconstrained 的两种含义**：ctx 未约束该维度，或记录在该维度**无锚点**（无锚点的
  scoped 记录不自我限制，按 user-global 放行）；
- **session fail-closed**：瞬态/工作记忆永不跨会话泄漏（MEMORY_V3 §2），ctx 无 session
  约束也砍；
- **与 C-01 对齐**：goal≈plan/task 锚、domain≈user-subject、global≈global、session≈session
  （DECISION_SCOPES 词汇对映，本卡不改动 C-01 冻结面）。
- task_type 是 MEMORY_V3 §1 的任务形态轴——现有存储无来源（派生为 None），仅显式
  descriptor 可用（未来写方），兼容矩阵仍覆盖（防三处散定义的验收点）。

### 2.3 TTL 规则（naive-UTC，time_utils 规范）

- `due_at+7d` 承诺类：`now > due_at + 7d` → `ttl:expired`（补上 D4 账本的"无消费者"）；
- **today-only**：`decay_policy ∈ {1d, today}` → 仅在 `created_at` 的 UTC 日有效，
  `now.date() != anchor.date()` → `ttl:today_only_expired`（边界：23:59:59 过、次日 00:00 砍，
  单测锁定）；写方今天只需按既有 decay_policy 约定写 `"1d"`，零迁移；
- `valid_from > now` → `ttl:not_yet_valid`（descriptor 通道，未来写方）；
- goals.expires_at 走 M-01 状态机报 `status:expired`（列背书的过期归 status 维度，不双计）；
- **半衰期策略（7d/30d/60d/90d）明确不是硬 TTL**：软衰减归每日 decay job（archived_at →
  status 维度），本层不越权（单测断言 90 天前的 7d 记录不被砍）。

### 2.4 purpose 与 sensitivity（不发明产品政策）

- purpose 封闭词表 `{llm_context, personalization, analytics, export, governance}`；
  现有列无 per-record allowed_purposes → 记录默认全允许，descriptor 通道已留（未来写方）；
  **已落地的真实权限层**：user_memory_settings（enabled/allow_preferences/allow_goals/
  allow_episodic/allow_inferred_episodic/blocked_pref_keys/blocked_sources）——写侧已执行、
  读侧本卡首次执行（reason 前缀 `purpose:`）。缺设置行/读失败 → 全允许（与写侧
  `_is_user_disabled` 语义一致，best-effort 不阻塞上下文组装）。
- sensitivity 封闭有序词表 `{normal:0, sensitive:1}` + ctx 上限（默认 normal）+ 软件级强制
  执行点；**现有列无 sensitivity 来源 → 全部派生 normal，live 行为零变化**。将
  person_mention/relationship 判为 sensitive 属产品决策（Aurora 社交链路正在消费），
  本卡不做，见 §7 已登记边界。

### 2.5 接入点（三处，均在语义阶段之前；第三处为双评审返修 R1-F2 新增）

1. `context_manager._get_past_session_memory`：SQL 拉取后、importance/confidence/created_at
   重排**之前**（含 get_user_context 缓存命中路径的刷新调用）；
2. `context_pack.build`：三族候选拉取后、rank_items/语义门控/预算裁剪**之前**；
   `pref_history`（冲突消解输入）刻意不过滤——supersede 消解合法需要全版本链
   （MEMORY_V3 §3 步骤 6 在步骤 1-5 之后）；
3. `orchestration/context_builder._attach_stage34_memory_context`（R1-F2 返修）：主聊天链
   :1038 调用，payload["episodic_memories"]（top5）与 cognitive_context 同键——
   `prompts.format_user_context` 将其渲染进系统提示词【近期相关记忆】段；预筛接在
   `list_recent_episodic(limit=12)` 之后、correction/importance 排序之前。**刻意不接线**
   （R2 裁决，登记 §6.4）：`routing_engine.py:2530`（SignalAggregator 快照只喂确定性
   decision fns——detect_escalation/decide_backbone_route，非 LLM prompt，属 M-04 域）与
   `app/aurora/signal_aggregator.py:99-110`（`_collect_memory` 同上）。

### 2.6 metrics 与可观测

- Prometheus：`sparkle_memory_prefilter_rejections_total{dimension,reason}`（business_metrics，
  与 MEMORY_WRITE_TOTAL 同域）；计数失败静默（指标永不破坏检索）；
- loguru：每次有砍除时 info 汇总 input/allowed/dims/reasons；
- `PrefilterResult.to_metric_payload()`：结构化（version/input/allowed/dimension_counts/
  reason_counts），pack 侧写入 `metadata["memory_prefilter"]["sections"][...]`（D-06/O-02 消费）。

## 3. 与相邻卡的边界

- **E-05（semantic_cache）对齐**：本卡不改任何缓存键；预筛改变的是注入**内容**而非键结构。
  内容失效通道是 M-01 epoch（破坏性记忆变更 bump 已接线）；**settings 变更（如新拉黑一个
  pref_key）不 bump epoch** → 5 分钟 context 快照 TTL 内可能短暂注入旧集合——已登记 M-07
  （context compiler）接入时把 settings 变更纳入 epoch/失效触发（见 §7）。
- **M-01**：status/scope 派生与 inferred 判定全部委托，未重复定义；守卫测试模式沿用。
- **M-04（写方治理）/M-06（EXPERIENCE 投影）**：descriptor 的 allowed_purposes/sensitivity/
  task_type 通道即为其预留接口，无需迁移。
- **既有检索链**：context_ranker 权重、冲突消解、Self-ReCheck、预算裁剪零改动——预筛只
  是其之前的 L0。

## 4. 证据（红→绿 + 回归，均在 base 43942d23 复验）

### 守卫红→绿（同一测试集 `tests/unit/test_memory_prefilter_integration.py`）

**RED**（基线 43942d23 + 新测试，接线代码 git stash 剥离，`5 failed`——接续 worker 在新基重证；
前任在 6f488636 亦实证同样 5 failed）——六类泄漏全部实证：
```
assert 'SUPERSEDED-episodic' not in [... 'EXPIRED-COMMITMENT', 'SUPERSEDED-episodic', ...]  # SQL 实漏
assert 'WRONG-USER' not in ['REVOKED', 'WRONG-USER', 'STAGE-LEGAL']                        # 边界无守卫
episodic memory injected despite allow_episodic=False                                       # 读侧权限缺口
only the chain head may compete ... got [(2, head), (2, head)]  # superseded 版本进入 rank 输入
assert 'GOAL-OTHER-PLAN' not in ['GOAL-OTHER-PLAN', 'GOAL-UNLINKED', 'GOAL-THIS-PLAN']      # 跨 plan
'depth_preference' not in {'curiosity_preference', 'depth_preference': blocked-key}         # 黑名单键注入
```
**GREEN**（接线后）：`5 passed`（合法候选 FRESH-COMMITMENT/LEGAL-episodic/GOAL-THIS-PLAN/
GOAL-UNLINKED/head-new 均存活——保守放行不误伤）。

### 返修轮红→绿（stage34 面，R1-F2；base 43942d23）

**RED**（stash `context_builder.py` 接线，仅跑集成 → `2 failed`）：
```
AssertionError: superseded row leaked into stage34 prompt payload:
    ['STAGE34-EXPIRED', 'STAGE34-SUPERSEDED', 'STAGE34-LEGAL']
AssertionError: episodic memory reached the stage34 prompt payload despite allow_episodic=False
```
**GREEN**（接线后）：7 passed（含两条 stage34 新守卫：payload 面 + `format_user_context`
渲染面双重断言——非法候选在渲染出的系统提示词文本中为 0）。

### 单测（`tests/unit/test_memory_retrieval_prefilter.py`，61 passed）

- lattice 全矩阵 parity：15 格逐格构造 (descriptor, ctx) 并断言求值器与表一致 + 矩阵键集 ==
  全叉积（封闭结构验收）+ 无锚点 scoped 记录 / global 恒过 / session fail-closed / 未知 level
  fail-closed；
- today-only：同 UTC 日 23:59 过、次日 00:00 砍（naive-UTC 边界锁定）；
- 七维逐维：wrong_user（含无 user_id fail-closed）、status×5 列 + goal expires_at + revoked>
  superseded 优先级、TTL（due_at+7d 界内/界外、today-only、not_yet_valid、软衰减不砍）、
  scope（task/plan 双锚）、purpose（memory_disabled/type_disabled/inferred_episodic/
  blocked_pref_key/blocked_source/not_allowed）、sensitivity（超限砍/提权过/live 默认不砍）；
- metrics：dimension_counts/reason_counts/to_metric_payload 形状 + 求值顺序归因；
- **返修轮新增（R2-F1/F2）**：未知 level 在**派生路径** fail-closed（monkeypatch derive_scope
  返回假设的 "subject" → descriptor 保留原值 → `scope:unknown_level` 砍+计数，不再是死分支）；
  M-01 词表 parity（inspect 静态扫描 `derive_scope` 真实源码的 level 字面量 ⊆ SCOPE_LEVELS——
  M-01 加新 level 此处必红，双向防漂移；扫描不到字面量时 fail-loud 提示更新守卫）；
  `FILTER_DIMENSIONS` 顺序钉死 + 5 个相邻对（user/status、status/ttl、ttl/scope、scope/
  purpose、purpose/sensitivity）各构造恰好双违例记录断言前维独占归因——reorder 必红。

### 回归（定向串行，基线 stash 对照甄别；新基 43942d23 复验）

- **直接影响域+邻接域合并 153 测试：152 passed**（22 文件：context_manager(含 community)/
  ranker/context_pack×6/past_session_ranking/M-01 守卫(epistemic_contract+migration_sqlite)/
  h6 aurora/memory_service_reads/governance/revival_slim/social_namespace/inferred_write_lane/
  context_focusing(C-01 decision_context 契约)/understanding_depth + M-03 新测试 58）。
- **唯一失败 `test_two_consecutive_sessions_prompt_includes_inferred_memory` 全量 stash 基线
  对照在新基重证为预存**（stash 全部 M-03 tracked 改动后同样失败；失败点为 LLM 路由
  demo-mode 环境性，M-01 报告已登记同类）。
- **测试夹具适配（4 个既有测试，非守卫弱化）**：test_context_manager / h6 scenario4 /
  past_session_ranking / context_builder_mixin 的 mock 候选行补上 `user_id`（真实 DB 行必有；
  预筛对无主行 fail-closed 是本卡语义；第 4 个为返修轮 stage34 接线所触发的同型适配）。
  past_session_ranking 同时把 `user_id=None` 调用改为真实 UUID。

### lint

新文件 black + ruff clean（返修轮复验）。**R1-F1**：context_manager.py 的 I001（本卡首版
新引入）已修——memory_retrieval_prefilter 移到 memory_service 之前，ruff 复查该文件 clean；
context_builder.py 的新 import 同样按序插入。**stash 基线对照披露**：context_builder.py
存在 2 处**基线预存** I001（顶层 `app.core.time_utils` 混在 stdlib 导入间 + :865 局部导入块）
与 black 预存重排噪音（test_context_builder_mixin.py 文档字符串空行同类）——均非本卡引入，
未顺手重排版以保持 patch 聚焦；context_manager.py 的 black 噪音（`_sanitize_context` 长行）
亦为基线预存。

## 5. 交付物清单

- 新增 `backend/app/services/memory_retrieval_prefilter.py`（含模块级设计说明）
- 新增 `backend/tests/unit/test_memory_retrieval_prefilter.py` /
  `backend/tests/unit/test_memory_prefilter_integration.py`（返修轮各加 R2-F1/F2 守卫与
  stage34 红绿两条）
- 修改 `backend/app/core/business_metrics.py`（+MEMORY_PREFILTER_REJECTIONS_TOTAL）
- 修改 `backend/app/core/context_manager.py`（_get_past_session_memory 接入 + R1-F1 import 序）
- 修改 `backend/app/core/context_pack.py`（build 接入 + metadata 观测面）
- 修改 `backend/app/orchestration/context_builder.py`（R1-F2：stage34 接线，
  `_attach_stage34_memory_context` 排序前预筛）
- 修改 4 个既有测试文件（夹具 user_id 适配，见 §4）
- `v3-output/M-03/changes.patch`（针对 base 43942d23 的 `git diff` 全文快照——**精确文件
  列表导出**，未用 `git add -A`；`git apply --check --reverse` 在 wt4 校验一致；未 commit）

复现命令（backend/ 下，SECRET_KEY 为测试专用）：
```
SECRET_KEY="test-secret-key-for-pytest-only-0123456789abcdef" python3.11 -m pytest \
  tests/unit/test_memory_prefilter_integration.py tests/unit/test_memory_retrieval_prefilter.py -q
# RED 复现 A（指定路径两接线，新基已验证）：
#   git stash push -- app/core/context_manager.py app/core/context_pack.py
#   → 仅跑集成 → 5 failed（原两守卫面）
# RED 复现 B（stage34 接线，返修轮已验证）：
#   git stash push -- app/orchestration/context_builder.py
#   → 仅跑集成 → 2 failed（stage34 payload + prompt 渲染面）
# git stash pop 恢复 → 68 passed
```
注：wt4 无 backend/app/gen（buf 产物不入库）——测试经符号链接借用主仓生成物（gitignored，
收工已撤除）。

## 6. 风险与限制（如实）

1. **sensitivity 无 live 数据来源**（§2.4）：机制+词表+强制点已就绪并测试，但今日零行为
   变化；政策数据（哪些 subject_type 敏感）是产品决策，留给写方治理卡。
2. **task_type 层无存储来源**：lattice 覆盖 + descriptor 通道，现无记录可派生。
3. **settings 变更的缓存时效**（§3）：≤300s context 快照窗口 + semantic cache 依赖 E-05
   knowledge_version/epoch；settings 变更纳入失效触发登记为 M-07 前置项。
4. **其他读侧消费者未接线**（刻意，完整清单）——本卡只锁 LLM 注入面（三处：context_manager
   pull / context_pack.build / stage34 prompt 注入）：
   - **喂确定性路由/决策、非 LLM prompt（M-04 域，R2 裁决本卡不接线）**：
     `orchestration/routing_engine.py:2530`（SignalAggregator → stage4 路由 snapshot，budget
     4000 tokens）与 `app/aurora/signal_aggregator.py:99-110`（`_collect_memory`：goals/
     preferences/recent_episodic——SQL 均不过滤 revoked/superseded；kill-switch
     `aggregator_enabled` 默认 live）。被撤销的目标/偏好会继续影响路由/唤醒决策，
     M-04 接线时**必须**覆盖这两处（按 purpose 词汇表 personalization/analytics）。
   - **不同消费目的（analytics/governance/export）**：state_aggregator/
     router_context_reader/task_reflection/memory_eval/治理透明 API
     （profile_transparency/user_persona_batch）、memory_admin/export/list API——M-04 按
     purpose 词表逐个接线。
5. 每 context 构建多一次 user_memory_settings 点查（唯一索引，行级；权限正确性优先；
   stage34 接线后主聊天链每次组装为 1 次——stage34 与 context_manager 各 1）。
6. **goal_id 锚语义褶皱（R1-F3 注记，今日零影响）**：`scope_of_record` 把 goal 级记录的
   `linked_task_id` 同时填入 descriptor.goal_id 与 descriptor.task_id（两字段同值）——
   `LEVEL_ANCHOR_KEYS["goal"]` 的 `goal_id` 键今日比对到的实际是 **task** 锚。当前无任何
   调用方传 goal_ids（context_pack 只传 plan_id，context_manager 不传锚）；M-04 接线
   goal-id 约束前必须先裁决该字段语义（改名或补真 goal 锚），已登记 §7。
7. **today-only 的本地日错位（R2-F4 → M-07 裁决）**：切日按 naive-UTC——目标用户（UTC+8）
   本地"今天"在本地 08:00 结束；且 `_get_past_session_memory` 每次 get_user_context 重跑
   （缓存命中路径也刷新）→ 单次聊天跨 00:00 UTC（北京 08:00）时第 N 轮还在、第 N+1 轮
   消失，无用户动作。与 time_utils 全库 naive-UTC 规范一致；改本地日需 schema 里不存在的
   用户时区输入（用户档案时区 or 固定 Asia/Shanghai），登记 M-07/M-04 裁决。
8. **settings 读失败 fail-open 不对称（R2-F5 → M-04）**：`build_retrieval_context` 对
   settings 点查 `except Exception` → 全默认（全允许）；写侧 `_is_user_disabled` 无捕获
   （fail-closed）。settings 查询失败而候选拉取成功的窗口内，allow_episodic=false/
   blocked_pref_keys 用户该次请求被注入；唯一痕迹是 warning 日志（无计数器）。当前
   settings 语义是用户舒适/隐私偏好非安全边界，封顶 P2 登记；M-04 方向：llm_context
   目的读失败视作 memory_disabled（上下文组装仍成功）或最低限度加
   `settings_load_failures_total` 计数器。
9. **plan-only ctx 过砍 task 锚 goal（R2-F3，零 live 行，M-04 写方守则）**：
   `linked_task_id` 置位而 `linked_plan_id` 为 NULL 的 memory_goals 行，在 ctx 只约束
   plan 时因 task 锚永不可匹配被 `scope:mismatch` 砍（即使该 task 属于该 plan）。今日
   grep 证实无调用方写 linked_task_id；M-04/M-06 启用任务锚定时需 ctx 侧补 task_ids 或
   按"仅有次级锚"判 unconstrained，且与真跨 plan 砍在指标上不可区分需注意。

## 7. 登记的后续项

- M-07 前置：user_memory_settings 变更纳入 epoch bump / 缓存失效触发（本卡 §3/§6.3）；
  today-only 时区语义裁决（§6.7，R2-F4）；滚动部署期旧版缓存 ≤300s 窗口建议 bump 缓存
  key 或接受并记录（R2-F7）。
- M-04：其余读侧消费者按 purpose 词表接线（**必含 §6.4 前两项：routing_engine:2530 与
  aurora/signal_aggregator:99-110**，默认 live 喂确定性路由）；写方落 allowed_purposes/
  sensitivity；goal_id 锚语义正名（§6.6，R1-F3）；plan-only ctx 的 task 锚守则（§6.9，
  R2-F3）；settings 读失败方向（§6.8，R2-F5）。
- 决策遗留：person_mention/relationship 是否标 sensitive（Aurora 消费链影响面大，需产品
  裁决）；`mentioned_entity_owner_user_id` 跨用户实体可见性归 C-03/C-07 隐私边界。

## 8. 双评审返修轮处置记录（R1: CHANGES + R2: CHANGES → Leader 裁决范围）

| 发现 | 级别 | 处置 |
|---|---|---|
| R2-F1 未知 scope level 静默提升 global（fail-open，探针实证） | P1 | **随卡修**：`scope_of_record` 删除归一化，未知 level 原样进 descriptor → `scope:unknown_level` fail-closed 砍+指标；monkeypatch 派生路径守卫 + inspect 静态扫描 `derive_scope` 真源码的词表 parity 守卫（M-01 加 level 必红） |
| R2-F2 求值顺序三处矛盾 / 5 相邻对仅钉 1 | P2 | **随卡修**：docstring 改为实现顺序 + 差异理由（§2.1）；`test_filter_dimensions_order_is_pinned` + 5 相邻对参数化归因测试（reorder 必红） |
| R1-F1 context_manager.py I001 | 轻微 | **随卡修**：import 两行互换（memory_retrieval_prefilter 先于 memory_service）；context_builder 同序 |
| R1-F2 stage34 `context_builder._attach_stage34_memory_context` 绕过预筛（主聊天链渲染进系统提示词） | 中等 | **随卡修（Leader 裁决）**：接线 + 红（stash → 2 failed）→绿（7 passed）；payload 面 + `format_user_context` 渲染面双断言 |
| R1-F2/R2-F6 routing_engine:2530、aurora/signal_aggregator:99-110 未披露 | P2 | **登记不接线（R2 裁决：喂确定性路由非 LLM prompt，M-04 域）**：§6.4 完整清单 + §7 M-04 必含项 |
| R1-F3/R2-F3 附 descriptor.goal_id 实为 task 锚别名；plan-only ctx 过砍 task 锚 goal | P3/P2 | **注记 + 登记**：§6.6/§6.9 → M-04（正名 / ctx 补 task_ids） |
| R2-F4 today-only UTC 切日对 UTC+8 用户本地 08:00 失效 + 跨午夜当轮消失 | P2 | **登记**：§6.7 → M-07 时区裁决 |
| R2-F5 settings 读失败 fail-open 与写侧 fail-closed 不对称 | P2 | **登记**：§6.8 → M-04（方向或计数器） |
| R2-F7 混部窗口旧缓存 ≤300s | P3 | **登记**：§7 → 部署时 bump 缓存 key 或接受并记录 |
| R2-F8 gen 符号链接合并纪律 | P3 | **遵守**：patch 以精确文件列表导出（未用 `git add -A`），符号链接收工撤除 |

返修轮复验（base 43942d23 不变）：M-03 套件 68/68（61 单测 + 7 集成）；stage34 红绿独立
重证；定向回归（含 stage34/context_builder 邻接 6 文件 + 原 22 文件集）除已知预存
demo-mode 失败外全绿；black/ruff clean。
