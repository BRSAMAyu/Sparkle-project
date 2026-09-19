# C-02 R2 深层验收回执（DeepAudit）

- 审计人：V3 Fleet R2（DeepAudit 路线）
- 审计对象：wt9 @ db652302 之上的 C-02 交付（READY_FOR_REVIEW）
- 主仓参照：Sparkle-project main @ 1ea854c9（M-03 已合入）
- 审计时间：2026-09-19；环境：sparkle-cosmos/backend/.venv（只读借用），sqlite/mock，主仓只读
- **总 Verdict：CHANGES**（架构方向成立、核心机制可用；两处 P1 返修后再合入）

---

## 一、逐风险面 Verdict

### 风险面 1 · 信号形状未冻结 — **FAIL（P1，F1）**

**事实**：同一个 `SOURCE_SCHEMA_VERSION = "context_sources.v1"`（context_sources.py:65）盖在两个形状不同的 manifest 上：

| 面 | 顶层 key | sections 内 key |
|---|---|---|
| pack 侧（context_pack.py:1839-1847 `_build_source_manifest` return） | schema_version, sections, **item_category_counts**, overrides, **seed_or_demo_items_total** | enabled/adapter/keys/item_count/token_estimate/seed_or_demo/seed_or_demo_items/note/**decision_items**（无 category/items/compaction） |
| orchestrator 侧（context_sources.py:887-897 `build_payload_source_manifest`；SourceSection.to_dict :290-306） | schema_version, sections, overrides, **unclassified**, **user_is_seed_or_demo**, **late_stage_writers**, **control_keys**, **event_schema_version**（无 item_category_counts/seed_or_demo_items_total） | category/enabled/adapter/keys/**items**/item_count/token_estimate/seed_or_demo/seed_or_demo_items/compaction/note（无 decision_items） |

telemetry 侧再派生第三份（context_pack.py:1698 `memory_counts["sources"] = sources_manifest["sections"]`，pack 形状子集）。

**为什么是缺陷**：后续 D-CTX 卡按 "context_sources.v1" 消费时，`manifest["item_category_counts"]` 在 orchestrator 面 KeyError、`sections[x]["decision_items"]` 同理；`sections[x]["category"]` 在 pack 面 KeyError。这正是 C-01 R2 的教训（value 形状钉死断言）在 manifest 层重演——本卡交付物本身就是契约层。两张测试文件都没有把任一 manifest 的完整 key 集钉进断言（test_context_pack_sources.py:96-126、test_context_sources.py:242-271 均只断言个别 key 存在）。

**返修建议**：给两个面分别钉契约测试（顶层 key 集与 section key 集的精确相等断言），并二选一：(a) 两个面收敛为同一形状（补齐缺失 key）；(b) 版本串区分（`context_sources.pack.v1` / `context_sources.payload.v1`）并在 docstring 写明。趁零消费者时改，成本最低。

### 风险面 2 · M-03 接口漂移 — **PASS（接口实证兼容）+ P2 残留（F4）**

**逐参核对（主仓 @1ea854c9 `memory_retrieval_prefilter.py`）**：
- `prefilter_candidates(candidates: Iterable, ctx: RetrievalContext) -> PrefilterResult`（:601）— C-02 调用 `module.prefilter_candidates(items, module.RetrievalContext(**ctx_kwargs))`（context_sources.py:558）位置参数匹配 ✓
- `RetrievalContext` 字段 user_id/purpose/now/goal_ids/task_ids/plan_ids/domain_keys/task_type/session_id（:238-251）— C-02 ctx_kwargs（:539-555）全为合法子集，kwargs 名逐一相同 ✓
- `purpose="llm_context"` ∈ `RETRIEVAL_PURPOSES`（:158）✓；`result.allowed`/`result.rejections`/`MEMORY_PREFILTER_VERSION="memory-v3.m03.v1"`（:73）全部匹配 ✓
- **post-merge 实证**（本审计把主仓真模块+新版 business_metrics.py 临时复制进 wt9 模拟合入后状态）：
  `prefilter_applied: True, version: memory-v3.m03.v1, allowed:['m1','m2'], rejections:1 (user:wrong_user)`；全 kwargs 调用（plan_ids/task_ids/domain_keys/task_type/session_id）亦通过。

**P2 残留（F4）**：
- **死代码+双义名**：`app.orchestration.context_sources.apply_memory_prefilter` 在 `backend/app` 内 **0 个生产调用点**（grep 证实；仅测试经 fake module 调用）。主仓 M-03 自己导出了同名 `apply_memory_prefilter`（async、DB-aware、经 `build_retrieval_context` 载入 permissions）。REPORT §9「M-03 合入后自动生效」表述误导：生效的只是"可委托"，没有任何路径调用它。后来者 grep 同名函数极易接错版本。
- **fail-open 语义**：C-02 wrapper 手工构建 RetrievalContext、**不传 permissions**（user_memory_settings）——若未来被接线，用户 `blocked_pref_keys` / `allow_episodic=false` 等隐私设置将被静默绕过（默认全放行）。这与 M-03 的 purpose 维度设计相悖。
- **漂移吞噬**：`except Exception → pass-through`（:559-561）实测会吞真实故障（本审计第一次模拟中真 ImportError 被吞、静默 passthrough，仅 loguru warning，无 metric）——任何未来接口漂移都会无声变成"预筛从未生效"。

**返修建议**：要么删除该 wrapper（等真接线时直接用 M-03 的 `build_retrieval_context` + `prefilter_candidates`），要么改名（如 `prefilter_or_pass`）并让委托路径走 `build_retrieval_context` 以继承 permissions。

### 风险面 3 · 双路径静默分歧 — **部分 FAIL（P2，F5）**

- 两条 manifest 挂不同对象（pack.metadata["sources"] vs payload["context_sources"]），无直接值冲突；但**没有任何测试同时钉两条路径**（确认：两测试文件互不引用另一面）。
- **后写盲区（实测链路）**：manifest 在 `_build_user_context` 尾部附加（context_builder.py:1058），此后 orchestrator 仍向 payload 写 key：
  - `use_document_context` / `document_filter` / `selected_document_ids` / `conversation_settings`（orchestrator.py:2277-2280）
  - `aurora_planning_sidecar`（orchestrator.py:538）
  这些 key **永远不进任何 manifest**：`control_keys` 在生产环境恒空（KEY_CATEGORY_MAP 的 control 语义只在测试 fixture 里成立），`unclassified` 告警也看不见它们（manifest 已建完）。"新增 key 必须登记否则告警"的防线只覆盖 manifest 附加前的写入。
- merge 后 metering 反映 local 值而非获胜的 grpc 值（override 事件有登记，section token_estimate 未更新）——metadata 面可接受，记录在案。
- manifest 随 payload 进 120s 用户上下文缓存（context_builder.py:70,1591）→ decision_records/registration_source 计量最长陈旧 120s（P3，F7）。

**返修建议**：在 `_build_full_context` 的 control-key 写入后重建/增补 manifest（或把 manifest 附加挪到 `_build_full_context` 尾部），并给两条路径加一个同请求一致性测试（哪怕只钉 schema_version 与 sections 四键存在）。

### 风险面 4 · 封闭词表击穿 — **PASS**

- `SOURCE_CATEGORY_BY_ITEM_TYPE` 未知 type → KeyError 显式失败（context_sources.py:184-186），有测试（test_context_sources.py:166-168）。
- payload 未知 key → unclassified + warning（context_sources.py:798-799, 880-885），有测试（:286-290）。
- `set(SOURCE_CATEGORY_BY_ITEM_TYPE) == set(DECISION_ITEM_TYPES)` 集合相等断言（test :157-163）——C-01 冻结面 ↔ 四类投影的封闭性钉住 ✓。
- `decision.recorded`：主仓 event_registry.py:181-187 确认存在（status="reserved"，producers="v3: decision_records read projection"——本卡即该读投影首个消费方）；`is_registered_event_name`（:395-396）为词表成员检查；撤名 → LookupError → 适配器降级 note（context_sources.py:212-213, 740-742），不静默换名 ✓。`EVENT_SCHEMA_VERSION`（"event.v1"）仅作 manifest 信息性盖章（context_sources.py:896），无版本戳击穿面。E-05 教训未重演。

### 风险面 5 · grpc merge / pref_key 折叠红测 + late_stage_writers — **FAIL（P1，F2/F3；部分 P3）**

- 红**不是** xfail/skip（两测恒绿跑）——但它们是**同义反复测试**：`test_red_flat_dict_merge_silently_drops_local_value`（test :38-52）与 `test_red_preference_records_same_key_collapse`（:55-72）的函数体是测试文件里手写的 plain dict update / dict comprehension，**从不调用** `_merge_user_contexts` 或 pack 真实代码。产品代码怎么改它们都绿。是文档，不是锁定（P2，F3）。
- **三处接线零钉住（变异实验证明，P1，F2）**：
  1. 删除 pack 折叠接线（context_pack.py:1344 `detect_preference_key_overrides` 调用改为空列表）→ 34 测试全绿；
  2. 删除 orchestrator manifest 附加调用（context_builder.py:1058-1063）→ 34 测试全绿；扩大到 tests/unit/orchestrator/ 全目录 155 测试仍全绿；
  3. 禁用 grpc merge 检测 + history attach 接线（context_builder.py:1607/1675 区域）→ 34 测试全绿。
  即：**本卡的两个安装面（orchestrator manifest、无静默覆盖）可整体删除而全部测试仍绿**。纯函数有测试，接线没有——M-03 R2-F1（守卫钉不可达分支）的镜像形态：分支可达，但无测试走到。
- `late_stage_writers` 是静态表（context_sources.py:148-156），不随 stage34/39 实际写序重算，也无守卫测试对照真实写序；写序腐化时无人看得见（P3，F8）。测试只钉 active_goals/cognitive_context 两键（test :300-302），其余 5 键可任意改动不红。

**返修建议**：(a) 红 characterization 改为调用真实 `_merge_user_contexts` / 真实 pack 非 resolver 分支（sqlite 集成已有现成基建）；(b) 为三处接线各加一条最小 wiring 测试（mock mixin host 走 `_build_full_context` 或 sqlite pack 造同 key 双记录断言 `metadata["sources"]["overrides"]` 非空）。

### 风险面 6 · trace 写入退化 — **PASS（附边界说明）**

- 主仓 `normalize_memory_counts`（understanding_depth_metric_service.py:60-69）只对已知 ("preferences","goals","episodic") int 键求和，新 "sources" dict 键被忽略；wt9 sqlite 测试（test_context_pack_sources.py:167-173）钉住该断言 ✓。
- JSONB 每 run INSERT 覆盖（非 append），sections 固定 key 集 + seed_or_demo_items 受注入条数上界约束——无长程膨胀。旧行 NULL / 新行带值的边界由 `sources["memory"]["item_count"]` 类 SQL 可查（REPORT §6 SQL 已验）。
- 未见其他 memory_counts 读者受影响（主仓 grep：仅 telemetry service 写入 + normalize 读）。

### 风险面 7 · 测试语义（变异实验） — 见风险面 5；7 组变异结果见下表

### 风险面 8 · 长程/并发 — **PASS（附观察）**

- `SourceRegistry`/四 adapter 均为每次调用新建实例，模块级无可变全局（context_sources.py 全文核对）；`importlib.import_module` 走 Python 导入缓存，线程安全；settings 开关经属性动态读，无竞态面。
- 观察（P3，F10）：`build_payload_source_manifest` 对全 payload 逐值 json.dumps + tiktoken 编码计量 token——O(payload) 热路径成本（document/galaxy 大载荷时显著），已有 `[LATENCY] source_manifest` 计时面可见，但无回归门。
- 观察（P3，F7/F11）：manifest 进 120s 缓存（见风险面 3）；`SourceSection.to_dict` 同时输出 `"items"` 与 `"item_count"` 同值冗余键（context_sources.py:296-297），未来去掉任一即 breaking——趁零消费者钉死一个。

---

## 二、发现分级汇总

| # | 级 | 发现 | 一句话 |
|---|---|---|---|
| F1 | **P1** | 同版本双形状 | `context_sources.v1` 盖在 pack/orchestrator 两个不同形状的 manifest 上，无契约测试钉 key 集，下游消费即 KeyError（C-01 教训重演于 manifest 层） |
| F2 | **P1** | 接线零钉住 | 变异实验证明：三处安装面接线（pack 折叠登记、orchestrator manifest 附加、grpc/history 接线）可整体删除而全部测试仍绿 |
| F3 | P2 | 红测同义反复 | 两个 RED characterization 测试只复现测试体内手写的 dict 语义，从不触碰产品代码，锁定力为零 |
| F4 | P2 | M-03 死代码+fail-open | `context_sources.apply_memory_prefilter` 零生产调用点、与主仓 M-03 同名 async 函数构成双义名；wrapper 不传 permissions（隐私设置被绕）；except-Exception 静默 passthrough 吞接口漂移（实测复现） |
| F5 | P2 | manifest 后写盲区 | orchestrator 在 manifest 附加后仍写 5 个 payload key（含 control 面 4 键），生产环境 control_keys 恒空、unclassified 告警不可见——登记防线的写序盲区 |
| F6 | P2 | 交付树不可复现 | `app/gen` 被收工清理删除后，交付树上本卡自己的新测试、mixins 127 测试、contract 15 测试全部无法 collect（ModuleNotFoundError: app.gen）；REPORT 验证主张在交付形态不可复现（临时恢复 gen/ 后本审计复跑全绿，主张本身成立） |
| F7 | P3 | manifest 缓存陈旧 | manifest 随 payload 进 120s 用户上下文缓存，decision_records/seed 标记最长陈旧 120s |
| F8 | P3 | 静态写序表可腐 | LATE_STAGE_WRITERS 静态表无守卫测试对照 stage34/39 真实写序，5/7 键不被测试钉住 |
| F9 | P3 | 类别映射部分钉 | KEY_CATEGORY_MAP 逐 key 判定仅 fixture 覆盖键被钉（~27/37），无 golden-map 相等断言；"preferences"=state(payload) vs "preference"=memory(pack) 同名异义是共享版本号下的消费者陷阱 |
| F10 | P3 | 热路径计量成本 | 每次上下文构建对全 payload 做 json.dumps+tiktoken 编码，O(payload) 成本，有 LATENCY 计时无回归门 |
| F11 | P3 | 冗余形状键 | SourceSection.to_dict 输出 items 与 item_count 同值双键，未来移除任一即 breaking |

**已验证为良好的面**（非发现）：封闭词表显式失败（KeyError/unclassified）；decision.recorded 注册名/盖章/降级语义；normalize_memory_counts 读侧兼容 + JSONB 有界；无全局可变并发状态；grpc merge 白名单无法伪造 manifest；prompt 渲染按键取值、manifest 不泄漏进 LLM prompt（`_render_user_context_content` 核对）；wt9×main@1ea854c9 三交叠文件文本合并 0 冲突、语义级 post-merge 委托实测通过。

---

## 三、变异实验清单（全部已还原，diff 校验一致）

| # | 变异 | 结果 | 结论 |
|---|---|---|---|
| M1 | SourceRegistry.register 覆盖登记禁用（`if False and previous...`） | 2 红（registry_detects_cross_category / registry_warns） | 登记机制已钉 ✓ |
| M2 | 未知 payload key 静默归 state（`.get(key, "state")`） | 1 红（unknown_keys_do_not_silently_land） | unclassified 防线已钉 ✓ |
| M3 | 删除 pack 折叠登记接线（context_pack.py:1344 → 空列表） | **0 红（34 全绿）** | 接线未钉 ✗ |
| M4 | 删除 `_attach_source_manifest` 调用（context_builder.py:1058-1063） | **0 红（34 全绿）** | 接线未钉 ✗ |
| M4b | 同 M4，扩大到 tests/unit/orchestrator/ 全目录 | **0 红（155 全绿）** | 全仓无测试钉此接线 ✗ |
| M5 | 禁用 grpc merge 检测 + history attach 接线 | **0 红（34 全绿）** | 接线未钉 ✗ |
| M6 | KEY_CATEGORY_MAP recent_tool_usage events→state | 1 红（categories_and_metering） | fixture 覆盖键已钉（未覆盖键除外，F9） |
| M7 | attach_conversation_history 把 history 泄入 state 节 | 1 红（updates_events_channel_only） | 铁律已钉 ✓ |

还原校验：`diff` 与备份逐一比对相同；`git status` 恢复为交付原状（3 M + 4 ??）；/tmp 备份与 pytest 缓存已清；临时复制的 app/gen、memory_retrieval_prefilter.py 已删、business_metrics.py 已还原。

---

## 四、回归验证记录（R2 自跑）

| 套件 | 结果 | 备注 |
|---|---|---|
| tests/unit/test_context_sources.py | 30✓ | 交付树需先恢复 app/gen（F6） |
| tests/unit/test_context_pack_sources.py | 4✓ | sqlite，同上 |
| tests/unit/orchestrator/mixins/ | 111✓ | 同上（REPORT 称 127，跑 tests/unit/orchestrator/ 全目录=125✓，计数口径差异，全绿） |
| tests/contract/test_decision_context_contract.py | 15✓ | 同上 |
| tests/contract/test_event_registry_contract.py | 1✗ 35✓ | 该✗为 REPORT §9 已声明的 D-01 守卫误报（state_aggregator 注释），与本卡改动无关，核验属实 |
| tests/unit/test_rule_as_guard.py | ✓ | 新附件 `# rule-as: ignore` 登记生效 |
| tests/unit/test_context_pack*.py 家族 + test_context_manager + test_context_pruner | 20✓ 8 skipped | skip 为环境性，预存 |
| post-merge 语义模拟（真 M-03 模块 + 新 business_metrics） | 委托成功 | prefilter_applied=True / version=memory-v3.m03.v1 / wrong-user 拒绝 / 全 kwargs 通过 |
| 合并冲突 dry-run（git merge-file × settings/context_pack/context_builder） | 0 冲突 hunk | 文本可自动合并；语义以模拟为准 |

**未验证项**（如实声明）：生产 dev DB 上的 telemetry SQL 只读查询未在本轮复跑（REPORT §6 声称已实测，本审计以 sqlite 集成测试同构覆盖）；`_attach_source_manifest` 在真实有 DB 环境的 provider 读路径（registration_source 正常值/decision_records 正常返回）仅有降级路径单测覆盖，正常路径无单测（与 F2 同根）；C-01 `why_included` 词面未被本卡改动（未复核 C-01 全量契约，归 C-01 面）。

---

## 五、总 Verdict：**CHANGES**

理由：架构方向（四分词表、来源标注、覆盖显式化）正确且大部分机制实测有效；M-03 前向兼容经真实模块实证；封闭词表与 telemetry 读侧无击穿。但两处 P1 均属"测试全绿而产品契约/防线不成立"级：(1) 同一版本号下两个 manifest 形状，本卡交付物即契约层，形状歧义必须在任何消费者出现前消除；(2) 三处安装面接线被变异实验证明零钉住——本卡自己的验收证据结构对最核心的接线是空心的。二者返修量小（契约测试 + 三条 wiring 测试 + 形状收敛决策），不构成 REJECT。P2 四项（红测同义反复、M-03 死代码处置、后写盲区、交付树恢复 gen/ 后再交）应在合入前或紧随其后处理。
