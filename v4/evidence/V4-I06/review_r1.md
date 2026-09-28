# V4-I06 · 独立审查 receipt（一审 R1）

- 审查会话：**wtI06R1**（未参与 I06 实现；只读审查 + 本 receipt 提交，不 push）
- 审查锚：分支 `agent/v4/i06` @ **`a9a59a9e`**（基线 `a616f27f`）
- 卡：V4-I06（implementation · risk normal · 独立审查 1 位）；契约：`v4/evidence/V4-B05/contract_receipt_min.md` §2 `context_selection_receipt.v1`
- 日期：2026-09-28
- 合并落差声明：主检出 main 已前进至 `67b3c558`（I09/I10/D01/I02/I01 均已合并，均不含本审查分支的改动）；本审查全部复跑在分支锚点 `a9a59a9e` 上完成，合并落差面用 `git merge-tree` 实测（见靶 7）。

## 总裁决：**PASS_WITH_CHALLENGES**

分支本体（契约、落库、来源验证、红线、测试）审过；66 新测 + 187 受影响面 + 813 闭包亲跑全绿，红线可失败性亲验成立。**1 项 C 级挑战（C1）为合并交互缺陷**：本分支上不可达（无 I02 代码），但与 main 已合入的 I02 接线组合后在效用门 bypass 路径产生**回执误归因**——必须在合并时（或紧随 fix commit）落修复，否则回执在该路径违反「服务器权威记录确实发生了什么」的契约根本语义。不阻塞本卡销账进入集成；C1列为集成必落动作。

---

## 靶 1 · 契约逐条比对（与 B05 §2 逐字）——PASS

| 契约项 | B05 §2 权威值 | 实现（core/context_selection_receipt.py） | 判定 |
|---|---|---|---|
| schema_version | `context_selection_receipt.v1` | 同值常量 + 冻结测试 `test_contract_schema_version_frozen` | ✅ |
| receipt_id | `csr_<ulid>`，幂等键 | `csr_` + 26 位 Crockford Base32（48bit 毫秒+64bit 随机）；单调性不承诺已登记 limitations#8 | ✅ |
| selection_role | 4 值封闭 | frozenset 精确集合相等测试 | ✅ 无私扩 |
| candidates[].status | `selected\|rejected\|unavailable` | 同 3 值精确集合相等 | ✅ 无私扩 |
| reason_code | **8 码**：`out_of_scope_memory\|stale_epoch\|utility_gate_rejected\|conflicts_confirmed_preference\|permission_denied\|budget_exhausted\|duplicate\|expired` | `REJECTION_REASON_CODES` 8 值**逐字一致**，`test_rejection_reason_codes_frozen` 精确集合相等钉死 | ✅ **无私扩码** |
| why-now confidence_band | `high\|medium\|low\|unknown`（§4 R1-C2 口径） | `WHY_NOW_CONFIDENCE_BANDS` 同 4 值；statement≤200、basis_refs⊆selected（C1 投影）、expires_at 位齐 | ✅ 无私扩词 |
| note | ≤140 debug-only | `CANDIDATE_NOTE_MAX_LEN=140` 构造层截断 + pydantic max_length | ✅ |
| ref scheme | 复用 `ACTION_SOURCE_REF_SCHEMES`（11 scheme）不复制 | 直接 import + `ref_in_closed_schemes` 机器判定；测试断言与 action_plan 权威同源 | ✅ |
| input_versions | null=未读取，不得 0/"" 冒充 | selector_version 非空校验（空串=ValidationError）；其余显式 None 合法（`test_unknown_semantics_null_not_zero`） | ✅ |
| budget | `{candidate_scan_limit, selected_max, clarifications_used}` | 三键齐；scan/selected 记**实际读数**（token 预算面无整数上限，limitations#5 如实登记） | ✅ |
| 字段面 I1 | 无权限语义字段 | `test_payload_fields_frozen_no_permission_semantics`：键集冻结为 8 键 + 禁词集 | ✅ |

**候选集「被扫描全集逐条归因」完备性**：`assemble_pack_receipt` 对 input_records（prefilter 前、build 已扫描全集）逐条判定，归因判定序冻结（prefilter 拒用 > surfaced > selfcheck > 冲突 suppressed > deny-quiet > budget），每条恰落一个出口；缺口兜底 `budget_exhausted` + `unattributed_downstream` note（不悬空）。**不可解析锚的记录不入册也不计扫描数**——这是声明性规则（构造悬空 ref 违 I3），非凭空消失，已在模块 docstring 与 diff 文档登记，接受。「凭空出现」面：gate 只覆盖既有候选、从不构造（`test_gate_never_creates_dangling_ref_for_unknown_id`）；重复 ref 由 validate 拒。反例三件（`fabricated_ref_scheme`/`empty_candidates_rendered_as_has_evidence`/`why_now_without_basis`）全部有契约级断言。

## 靶 2 · fail-closed + 幂等落库——PASS（语义与声明一致）

**语义澄清**（审阅确认两处 "fail" 方向不同且实现一致）：
- **契约违例 → fail-closed 不落库**：`record_receipt` 落库前过 `validate_contract`，违例返回 None + WARN（`test_record_fail_closed_on_contract_violation`：构造 `astro://` selected 违例 → 不落库 → latest 为空）。
- **基建失败（DB 挂/约束冲突）→ 降级不阻断主链**：build 接线将装配+落库整体包 try/except，失败 WARN + `context_receipt=None`，pack 照常返回（docstring「装配失败只降级，绝不阻断 pack 主链路」与实现一致）。IntegrityError 同样被该 except 吸收为主链降级。
- ⚠️ 无显式「DB 挂」注入测试（靠 except 可见性保证）；非阻塞，登记 O6。

**幂等**：`receipt_id` 唯一约束（`uq_context_selection_receipts_receipt_id`）+ 落库前存在性预查；重放同 id 不重复计数（`test_build_produces_and_persists_receipt_in_shadow_mode` 断言重放后仍 1 行）。预查+插入非原子，并发同 id 竞态 → commit 抛 IntegrityError → 接线 except 吸收降级，不会产生双行；无并发测试（O6）。

**迁移 `i06_20260928` 单头**：`down_revision=wt598_20260927`。**重点核过**：main（`67b3c558`）相对基线 **零新增迁移文件**（`git diff a616f27f main -- backend/alembic/versions/` 为空），且 main 树中无任何文件以 `wt598_20260927` 为 down_revision（I06 是唯一子）；全部活跃 fleet 分支（d02/i03/f01/fix558/fix559）亦无竞争迁移。权威工具 `alembic heads` = **`i06_20260928` 单头**；守卫脚本 `scripts/guards/check_alembic_single_head.py` 亲跑 ✅。合并后单头保持。真库 upgrade/downgrade/upgrade 为实现方 scratch 库自证（manifest #77），本审未重跑真库（sqlite 不适用该迁移验证），接受其命令记录。

## 靶 3 · 来源验证双门——PASS（抽测断言真实）

- **第一重 scheme 门**：`parse_ref_scheme` + `ACTION_SOURCE_REF_SCHEMES` 封闭集；畸形/无 scheme/集合外 → `unresolved/unknown`。
- **第二重 join 门**：episodic/preference/goal/plan/task/goal/document 各 join 真实存储行 **且 `user_id == 当前授权用户`**（I3 属主过滤）；`user_state/profile/chat/decision/run` 无单行属主表 → 如实 unknown（不伪造可点定位，limitations#6）。
- **抽测核断言**（读测试源码 + 亲跑通过）：`test_cross_user_and_missing_refs_are_unknown`（other 用户验 owner 的 ref → `unknown`，与不存在同判，不区分泄漏）✅；`test_deleted_source_reads_unresolved_after_delete`（软删后读时验证 → `unresolved/deleted`）✅；`test_selected_refs_join_real_storage`（resolved + 泄漏探针断言验证结果无正文）✅；`test_why_now_basis_refs_are_verified`（basis_refs 进验证面）✅。
- **不编 quote/时间**：验证 entry 仅 `ref/resolution/status_code/detail`（detail 为 kind 或固定短语），无任何正文/时间构造；读面断言 `"quote" not in entry`。
- 「删除后旧 receipt 更新」= 读时验证语义（回执行只读不改写，每次读面现场 join）——与卡验收第 2 条相容，limitations#7 如实登记该口径选择。
- 观察 O3：deleted preference 走查询内 `deleted_at.is_(None)` 过滤 → 返回 `unknown` 而非 `deleted`（episodic 则为 `deleted`）——细分粒度按 kind 不对称，均 unresolved，不影响验收；后续可统一。

## 靶 4 · 开关红线（亲验可失败性）——PASS

- **默认 shadow**：`settings.CONTEXT_SELECTION_RECEIPT_MODE: str = "shadow"`（off|shadow|live）；`normalize_mode` 复用 kill_switch 词表，无第二组常量 ✅。
- **off=V3 零变化**：`test_build_mode_off_produces_no_receipt`——off 下 `pack.context_selection_receipt is None` + 零落库行。
- **回执不进 prompt 面**：`test_receipt_never_leaks_into_prompt_face`（live 模式下逐候选断言 ref/note 不在 `to_prompt_context()` 输出）；且接线侧为**结构性不进入**（回执只挂 `ContextPack.context_selection_receipt` 尾字段，`to_prompt_context` 无该键）。
- **亲验可失败性**（scratch 反转法，会话内临时测试文件，跑完即删、未提交）：① off 模式下反向断言「receipt 在场」→ **红**；② monkeypatch `to_prompt_context` 注入候选 ref 后原红线断言 → **红**。两条红线均真实可失败（2/2），非永绿断言。
- 读面门：`test_read_face_mode_gate`——off/shadow → `receipt: None`（B05 §8 shadow 写先行默认读关），live → 全量+验证。方向正确可失败。
- 观察 O7：开关为 settings-only（未注册 `KillSwitchBinding`/Redis 运维面）——与 I02 的 `ENABLE_MEMORY_UTILITY_GATE` 同款风格，B05 §8「登记进既有 kill-switch manifest」以复用 `normalize_mode` + settings 常量方式满足最低要求；live 推广时若需 Redis 动态切换需补 binding（非本卡阻塞）。

## 靶 5 · I02 接线落差——自报已过时（合并即生效），但发现 C1

实现方自报「I02 合入后接线需写 to_metric_payload() 进 metadata 才生效」。**核实：该动作已由 main 侧 I02 接线天然完成**——main 的 `context_pack.py`（I02 hunk，合并后 ~:1639）在 `ENABLE_MEMORY_UTILITY_GATE` 开启时写入 `metadata["memory_utility_gate"] = utility_gate_meta`，其值即 `UtilityGateResult.to_metric_payload()`（含 `decisions:[{item_id,selected,score,reasons}]` 冻结形状）+ 附加键；I06 侧鸭子类型只读 `decisions`，形状吻合。**merge-tree 实测合并后该键在生产点（~:1639）与消费点（~:2151）同文件共存，接口自动生效，无需 Leader 额外接线。**

**但由此发现 C1（见挑战节）**：main 侧 bypass 路径（required-memory 全拒回退）仍带着全拒 decisions 的 metadata 落键（仅加 `bypassed=True` 标记），I06 接线无条件透传 → bypass 时回执误归因。

## 靶 6 · 复跑（全部亲跑，`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，借主检出 venv py3.11.15）

| 套件 | 结果 | 对照 manifest |
|---|---|---|
| 66 新测（48 契约+10 装配/接线+8 来源） | **66 passed** (7.67s) | ✅ 一致 |
| 187 受影响面（context pack 全家+M-03+C-01+读面） | **187 passed** (22.09s) | ✅ 一致 |
| 闭包（tests/contract 全套 + experience_readouts + tests/api） | **813 passed, 5 skipped** (444s) | ✅ 一致 |
| mypy 改动 7 文件 | 30 errors 全部位于**既有依赖闭包文件**（notification_push_service 等）；grep 证实 **I06 改动文件 0 error** | ✅ 与「零漂移」声明一致（基线总数未另行复核，非承重项） |
| `alembic heads` | 单头 `i06_20260928` | ✅ |
| `check_alembic_single_head.py` | ✅ 单头: i06_20260928 | ✅ |
| 红线可失败性 scratch 探针 | 2/2 反转即红（文件已删，未入库） | 新增证据 |

## 靶 7 · 合并落差预警（merge-tree 实测 `main` × `agent/v4/i06`）

**冲突面（实测）**：
1. **`backend/app/config/settings.py` — 唯一内容冲突**。I02 块（`ENABLE_MEMORY_UTILITY_GATE` 等，main :922-）与 I06 块（`CONTEXT_SELECTION_RECEIPT_MODE`）同在 `ENABLE_MEMORY_USE_SELFCHECK` 之后相邻插入。**解法：两块都留，无语义互斥**（git 取双方即可）。
2. `backend/app/core/context_pack.py` — **文本自动合并成功**（已 AST 校验合并结果语法成立；I02 hunk ~:1600 与 I06 hunks ~:1425/:2135 不重叠），**但语义交互即 C1**。
3. `v4/04_tasks/tasks.json` — 自动合并成功。
4. 迁移：main 无新增迁移、无竞争头 → 合并后 `i06_20260928` 单头保持。
5. 测试文件：main 新增（memory_utility_gate/episode_resume_view/v4_i10 等）与 I06 新增文件名零碰撞；`backend/tests/conftest.py` main 未动。

**建议解决序**：
1. Leader 集成时以 main 为基准合入 `agent/v4/i06`；`settings.py` 冲突取双方块。
2. **同一合并（或紧随 fix commit）落 C1 修复**（见下），并补 bypass 路径回执回归测试。
3. 合并树复跑：66+187+813 与 I02 测试族（`test_memory_utility_gate*.py`）同跑一次集成闭包 + alembic 单头守卫（预期 `i06_20260928`）。
4. 其余 fleet 分支（i03/f01/d02/fix55x）当前均无迁移与 `context_pack.py` 写权竞争；后续若有卡改 `context_pack.py`，需在 context-receipt 锁协调（I06 持锁）。

---

## CHALLENGED 列表

### C1（合并必落）：效用门 bypass 路径回执误归因——surfaced 被翻为 `utility_gate_rejected`

- **位置**：合并后 `context_pack.py`——生产点 main 侧 bypass 块（`ranked_episodic` 回退全量后**仍写** `metadata["memory_utility_gate"]`，仅加 `bypassed=True`/`verdict=required_memory_recall_miss_bypass`）× 消费点 I06 侧 `raw_gate = metadata.get("memory_utility_gate")` 无条件透传 `apply_utility_gate_metadata`（分支 :2099/:2160 附近）。
- **触发条件**：`ENABLE_MEMORY_UTILITY_GATE=true` 且 required-memory 场景门全拒（`passed=False` → bypass）。分支本体不可达（无 I02 代码）；默认旗标关时不可达。**合并后即成为可达的真实生产路径。**
- **后果**：bypass 时调用方已回退全量 ranked（被门拒的条目**实际进了 prompt**），但回执按门 decisions 把同 id 的 surfaced 候选覆盖为 `rejected/utility_gate_rejected`——回执与真实依据面相反，违反「回执=服务器对确实发生了什么的权威记录」与 C1 精神（呈现引用面 ⊆ selected 的可信根基）。
- **佐证**：分支侧冻结测试 `test_gate_on_metadata_overrides_candidates` 把「surfaced 且门拒 → 覆盖为拒用」钉为期望语义（注释「预筛后 surfaced，但效用门拒用」）；而真实管道中该组合**只发生于 bypass**（正常路径门拒条目在 trim 前已移除、不可能 surfaced）——该冻结语义与管道事实矛盾，需一并修正。
- **修复建议（集成时由 Leader 落）**：接线处 bypass 作废门载荷——`raw_gate = None if isinstance(raw_gate, dict) and raw_gate.get("bypassed") else raw_gate`；新增 bypass 回执测试（surfaced 保持 selected、回执照常产生）；修正 `test_gate_on_metadata_overrides_candidates` 的场景注释/断言为「非 bypass 门拒（gate 移除后未 surfaced 的条目按 decisions 归因）」语义或直接模拟真实次序（门拒条目不在 surfaced 集）。

### 非阻塞观察（O，不要求处置，供后续卡/运维参考）

- **O1** `apply_utility_gate_metadata` 按 `ref.rsplit("/",1)[-1]` 尾段匹配 item_id——跨 kind 尾段碰撞（episodic uuid 撞 pref_key）理论上会覆盖错候选；当前 I02 门只裁 episodic、pref_key 命名域分离，实际风险低。
- **O2** `record_receipt` 在 build 中途 `db.commit()`——与同类 `mark_items_consumed` 的既有中途提交先例一致，未改变事务风险面；登记知悉。
- **O3** deleted preference → `unknown`（episodic → `deleted`），unresolved 细分粒度按 kind 不对称（均 unresolved，验收不受影响）。
- **O4** 读面 API 在 receipt 解析成功但行有 violations（旧生产者缺 candidates）时不回带 `violations` 字段——轻微可观测性缺口。
- **O5** `memory_epoch` 独立列对 null 存 0（合同 null 语义由 `input_versions` JSONB 保真）；合法 epoch ≥1，0 作「未读」哨兵无歧义。
- **O6** 幂等为预查+插入（非原子）；并发同 id 竞态由唯一约束+接线 except 兜底降级；无并发注入测试、无 DB 挂注入测试。
- **O7** 开关 settings-only（复用 `normalize_mode`，未注册 KillSwitchBinding/Redis 运维切换面）——live 推广时补。

## 结论

- 契约冻结、全集归因、fail-closed 语义、来源双门、两条红线、迁移单头全部核实通过；测试真实可失败且数量声明与亲跑一致；零 HEAVY、零模型调用属实（manifest model_budget）。
- **PASS_WITH_CHALLENGES**：C1 为合并交互缺陷，不阻塞本卡按「独立审查 + 当前集成 SHA 可失败测试」模型销账进入集成，但 **C1 修复必须作为集成必落动作随合并落地**（建议由 Leader 在合并 commit 或紧随 fix commit 落，含 bypass 回执回归测试）。
- 本 receipt 锚定 `a9a59a9e`；集成复验时以合并后 SHA 复跑靶 6 清单 + I02 测试族。

— wtI06R1，2026-09-28
