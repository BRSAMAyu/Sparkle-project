# C-02 R2 返修 Delta 复核回执（REVIEW_RECEIPT_3）

- 审计人：V3 Fleet R2（DeepAudit，与 R2 首轮同手法复验）
- 对象：wt9 @ 42180162 之上的 C-02 返修交付（REPORT §11 + 再生成 changes.patch，8 文件）
- 方法：R2 原始变异手法全量重跑（不信任自报）+ 禁用/改名形态加严 + F1 形状变异 + F4 真模块对接审计 + rebase 完整性
- 环境：sparkle-cosmos/backend/.venv 只读借用；sqlite/mock；主仓只读；/tmp 克隆已清理；未 commit/push；无 stash/reset/clean
- **总 Verdict：ACCEPT（合入）**——附 3 条 P3 边界登记（不阻塞）

---

## 一、逐项复核结果

### 1. 变异重跑（R2 原始手法，10/10 全红，与自报逐条一致）— **PASS**

| # | 变异（R2 原始形态） | 红 | 锁定测试 | 自报 | 判定 |
|---|---|---|---|---|---|
| M1 | registry 覆盖登记禁用（`if False and previous`） | 2 | registry_detects_cross_category / registry_warns | 2 | ✓ |
| M2 | 未知 payload key 静默归 state（`.get(key,"state")`） | 1 | payload_manifest_unknown_keys_do_not_silently_land | 1 | ✓ |
| M3 | pack 折叠登记接线 → 空列表（**新调用点**形态适配） | 2 | **W1（sqlite 行为级）+ W1b（AST）** | 2 | ✓ |
| M4 | 删 `_attach_source_manifest` 调用 | 1 | W2 | 1 | ✓ |
| M4b | 同 M4 + 全目录联合跑（orchestrator/ + 3 文件） | 1（174 pass 之外唯一红） | W2 | 1（174 pass） | ✓ |
| M5 | 禁用 grpc merge 检测（remove 赋值）+ history 附加（`if False and` 守卫） | 1 | **W3（剪枝后命中——R2 时此形态全绿，盲区已闭合）** | 1 | ✓ |
| M6 | recent_tool_usage events→state | 2 | categories_and_metering + **key_category_map_golden** | 2 | ✓ |
| M7 | attach_conversation_history 把 history 泄入 state 节 | 1 | attach_conversation_history_updates_events_channel_only | 1 | ✓ |

R2 的完成标准（M3/M4/M4b/M5 转红、M1/M2/M6/M7 保持红）全部达成。

### 2. 禁用/改名形态加严（接续员 `_live_call_names` 剪枝修复独立复验）— **PASS**

- M4d（`if False:` 包 `_attach_source_manifest` 调用）→ W2 红 ✓（自报 1 红，复现）
- W4d（`if False:` 包 process_stream 的 4 键 post-manifest 登记）→ W4 红 ✓（自报 1 红，复现）
- W4-sidecar（`if False:` 包 `_attach_aurora_planning_sidecar` 内的登记，R2 未测的第二接线点）→ W4 红 ✓
- 改名形态（调用改 `_attach_source_manifest_renamed`，方法保留）→ W2 红 ✓
- **剪枝语义单元证明（9/9）**：`if settings.X:` / `if not conflict_enabled:` / `if enabled:` 不被剪枝（合法 kill-switch 零误杀，else 分支可达）；`if False:` / `if False and X:` / `if 0:` / `while False:` 的 body 全部剪枝；`if False or X:` 正确不剪（body 生死由 X 决定）。基线绿本身也是无误杀证据——W1b 在 `if not conflict_enabled:` 守卫下命中。
- **运行时 monkeypatch 绕过残留（如实、有界，确认）**：实测在 `ChatOrchestrator.__init__` 注入类级 no-op 补丁 → 171 测试全绿（W2/W3/W4 均不红）。该残留与自报一致，危害有界：(a) 绕过需要显式源码补丁（评审可见，非意外回归形态）；(b) W1 是真实 sqlite 路径行为级测试，pack 面不受此向量影响；(c) 保护等级与仓库既有 AST 治理守卫（Rule AS）同型。**接受为已知边界。**

### 3. F1 形状收敛（两面 key 集）— **PASS**

- 常量冻结：`MANIFEST_TOP_LEVEL_KEYS`（10 键）/`MANIFEST_SECTION_KEYS`（11 键）（context_sources.py:247-273）；序列化唯一权威 `assemble_manifest`/`normalize_section`（:276-334），`SourceSection.to_dict`/`SourceManifest.to_dict` 均委托之——pack 面（context_pack.py `_build_source_manifest` 尾部 assemble_manifest）与 orchestrator 面（build_payload_source_manifest 尾部）同构，面间不适用值为 None/{}。
- 契约测试四面齐钉：payload 面顶层/分节 + pack 面顶层/分节（test_context_source_contract.py:108-131）+ 常量字面钉死（:134-164，防"同时改常量与实现"绕道）。
- **变异实证**：F1a（pack 面单独加分节 key `bogus_pack_only_key`）→ `test_manifest_section_keys_frozen_pack_face` 红 ✓；F1b（只给冻结常量加 `bogus_constant_key`）→ 3 红（两面 + 字面钉）✓。
- 附带确认：F11（`items` 冗余键）已随形状收敛删除——`MANIFEST_SECTION_KEYS` 无 `items`，两面同钉。

### 4. F4 真模块直调 — **PASS**

- 树内 M-03（`backend/app/services/memory_retrieval_prefilter.py`）与主仓 @42180162 **逐字节一致**（diff 验证）。
- `prefilter_memory_candidates_for_llm_context`（context_sources.py:638-689）逐项核对：
  - **签名**：kwargs 与 M-03 `build_retrieval_context(db, *, user_id, purpose, plan_id, goal_ids, task_ids, domain_keys, task_type, session_id, ...)` 全对齐，`purpose=PURPOSE_LLM_CONTEXT` 常量取自 M-03；
  - **权限**：context 经 `build_retrieval_context` 组装（user_memory_settings best-effort 载入）——sqlite 实测 `allow_episodic=False` → 全拒（purpose 维度 1），R2 的 fail-open 缺口已闭合；
  - **不吞错**：函数体无 try/except，接口漂移异常上抛（monkeypatch `_broken` → RuntimeError 传播，实测）；
  - **metric 透传**：返回 `result.to_metric_payload()` 原样（version/input/allowed/dimension/reason，e2e 断言）。
  - e2e（真模块 + sqlite）：wrong-user 拒绝、allowed==[own]、metric 计数正确。
- 双义名死代码删除有钉：`test_no_dual_name_dead_code_left_behind` 断言旧 `apply_memory_prefilter`/`PrefilterOutcome` 不存在（防回潮）。
- pack 面 provenance 集成真实：`build()` 内 M-03 接线（context_pack.py:1281-1310）落 `metadata["memory_prefilter"]`，`_build_source_manifest` 消费之并在有砍除时生成 memory 节 note（"M-03 prefilter cut N candidate(s)"）——不是假集成。
- 备注（不阻塞）：该委托入口当前仍无生产调用方（服务 D-03+ 后续卡），但与 R2 的差异在于：命名防接错、权限正确、异常可见、e2e 钉住、REPORT 不再声称"自动生效"——前向入口的合格形态。

### 5. F3 / F5 / F6 / F8 / F9 — **PASS**

- **F3**：RED characterization 改调真实 `_merge_user_contexts`（`_MergeHost` 最小宿主，test_context_sources.py:48-63）——锁定"值替换语义在合并函数、检测层在调用方"的分层事实；pack 折叠面由 W1（真实 sqlite 双记录）+ W1b 钉。同义反复测试已删。
- **F5**：`register_post_manifest_writes`（control→control_keys、未 mapped→unclassified+WARNING、copy-on-write、幂等、manifest 缺失静默降级——四性质各有测试）；5 个后写 key 两处接线（orchestrator.py:540-544 sidecar、:2286-2299 process_stream 4 键）；`aurora_planning_sidecar` 入 KEY_CATEGORY_MAP(control)。W4 双接线点 AST 钉住且禁用形态红（上表）。
- **F6**：`backend/app/gen/` 保留在交付树（本轮全部验证即在该形态跑通：C-02 50✓ / orchestrator 125✓ / contract 15✓+event_registry 35✓1✗ 全部可 collect）。
- **F8**：`LATE_STAGE_WRITERS` 整表 golden（7/7 键，test:220-230）。
- **F9**：`KEY_CATEGORY_MAP` 整表 golden（42 键含新增 sidecar，test:172-217）+ 模块 docstring 命名陷阱澄清（preferences/state vs preference/memory 按面取义）。

### 6. Rebase 完整性 — **PASS**

- wt9 HEAD = 42180162 = 审计时点 origin/main；树内 M-03 与主仓逐字节一致。
- `changes.patch` 对 42180162 `git apply --3way --check` **干净**；对主仓当前 head **ee885386**（B-03 已合入，42180162 之后无 C-02 文件交集）同样干净——两次确认。
- orchestrator 全目录 125✓（含 M-03 rebase 后回归）；contract+rule_guard 50✓1✗（✗为 R2 已录的 state_aggregator 守卫误报，预存、非本卡）；context_pack 家族 37✓（36+manager_community 1，与自报分毫吻合）。

---

## 二、边界登记（P3，不阻塞合入）

1. **运行时 monkeypatch 绕过（已证实的残留）**：W2/W3/W4 为源码级 AST 钉，类级运行时重绑定可绕过（实测 171 全绿）。有界性论证见 §一.2；建议后续卡若需要更强保证，为 `_build_user_context` 补一条 W1 同型的行为级 sqlite 测试（当前仅 pack 面有行为级）。
2. **F5 类残留后写 key（3 个）**：`plan_context`（context_builder.py:1636，post-manifest 写入 payload）、`document_context` / `document_context_retrieval`（orchestrator.py:1993-1994，deep-graph 文档注入点）未走 `register_post_manifest_writes`——manifest 完整性缺口（metadata-only）。机制已就位，登记是三行式跟进；`document_context_retrieval` 连 KEY_CATEGORY_MAP 都未登记（若登记会落 unclassified 可见）。
3. **overrides 条目形状未冻结**：`SourceOverride.to_dict` 的 `contenders` 键条件出现（有折叠参选才有），契约测试只钉顶层/分节 key 集，不钉 override 条目形状；消费方需按 `override.get("contenders", ())` 取。另：两处 `register_post_manifest_writes` 调用包在 `contextlib.suppress(Exception)` 里——函数自身 bug 会静默降级（metadata-only 面，可接受，知悉即可）。

---

## 三、复核中跑过的全部命令结果汇总

| 验证 | 结果 |
|---|---|
| 3 个 C-02 测试文件基线 | 50✓ |
| tests/unit/orchestrator/ | 125✓ |
| contract（decision_context+event_registry）+ rule_guard | 50✓ 1✗（预存） |
| context_pack 家族 11 文件 | 37✓ |
| 变异 M1/M2/M3/M4/M4b/M5/M6/M7（R2 原始手法） | 2/1/2/1/1/1/2/1 红 |
| 变异 M4d/W4d/W4-sidecar/rename | 各 1 红 |
| F1a/F1b 形状变异 | 1 红 / 3 红 |
| 剪枝 helper 语义单元证明 | 9/9 |
| 运行时 monkeypatch 绕过演示 | 171 全绿（残留证实，有界） |
| patch --3way --check vs 42180162 / vs ee885386 | 干净 / 干净 |
| 树内 M-03 vs 主仓 diff | 逐字节一致 |

**未验证项**（如实声明）：真实 LLM 调用（全程 0 次，与自报一致，未复验有无——静态审计未见网络调用面）；dev DB telemetry SQL 只读查询（REPORT §6 声称，本轮未复跑，sqlite 集成同构覆盖）；black/ruff（改动文件 lint 未由本轮复跑——静态阅读未见格式异常，非判定依据）。

还原与清理：4 个被变异文件与 /tmp 备份逐字节 diff 一致；`git status` 恢复交付原状（4 M + 4 A + v3-output）；/tmp 克隆与备份、.pytest_cache 已清；未 commit/push。

---

## 四、总 Verdict：**ACCEPT**

R2 两处 P1（F1 同版本双形状、F2 接线零钉住）与四处 P2（F3/F4/F5/F6）全部闭环且经本轮独立变异复验：10/10 变异红（含 R2 盲区形态 M5 与加严形态 M4d/W4d）、两面 key 集变异红、真模块直调三性质（权限/不吞错/metric）实测成立、rebase 后回归全绿、patch 对基线与当前 main head 均干净。接续员对前任半成品的盘点处置（保留合格工作、只修 W 系盲区）与 R2 首轮记录交叉印证一致。剩余三条 P3 边界已登记（运行时绕过残留有界、3 个 F5 类后写 key、override 条目形状），均可跟进卡处理，不构成合入障碍。
