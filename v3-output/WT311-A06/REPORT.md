# A-06 · Aurora "Why this?" / Calibration Receipt — Worker 报告（wt311）

**STATUS: READY_FOR_REVIEW**

- 卡片：`v3/07_tasks/cards/A-06.md`（Stream AURORA，Gate V3-4，Risk high，Reviewers 2，locks aurora-receipt，Depends on A-03✓/M-08✓/U-03✓）
- Base SHA：`2896d5fc`（main HEAD，A-03/M-08/U-03 均已合入）
- Final SHA：见 §8（worktree commit）
- 真实 LLM 调用：**0 次**（纯确定性机制；无语义层通道）
- 新词表事件/outbox/registry：**零**

---

## 1. 实际解决的问题

AURORA_V3 §6「Aurora UI receipts」此前只有文档语义与**单动作**残缺实现：

1. **回复引用记忆时没有可纠偏的完整回执**——生产链路（response_builder →
   chat metadata → mobile `AuroraReceiptChip`）只有 `referenced_memories`
   列表 + 一个「不对」按钮（`/memory/correct lower_confidence`）；没有
   rationale summary、没有 knowledge refs、没有 uncertainties。
2. **四动作纠偏缺失**（卡面 Work 2）：not_relevant / wrong / change_scope /
   delete 四路里只有「降置信」一路，其余三路（引用降噪、收窄范围、删除）
   在回执面上断链——用户必须离开对话去记忆管理页操作。
3. **触发无度**（卡面 Work 3）：回执只要「自然引用」就随回复出现，无呈现
   强度分层、无日预算。

## 2. 交付物

| 文件 | 内容 |
|---|---|
| `backend/app/aurora/calibration_receipt.py` | **纯契约模块**（零 IO、确定性、不 raise）：`CALIBRATION_RECEIPT_VERSION=aurora_calibration_receipt.v1`；四动作封闭词表 + 权威委托声明；不确定类型→用户语言标签（import 期断言恰好覆盖 `AURORA_UNCERTAINTY_KINDS`）；`evaluate_receipt_surfacing` 呈现门（hidden/ambient/surfaced 封闭三值 + 日预算）；`build_calibration_receipt` 装配（rationale 组成摘要 + refs + uncertainties + 每引用四动作）；sha256 指纹（测试双钉） |
| `backend/app/services/aurora_receipt_service.py` | 服务层：`respond()` 四动作**全部委托既有权威真源**，零新写路径/零新表/零迁移：not_relevant→`MemoryService.record_memory_reference_outcome(denied)`；wrong→带更正文本走 `MemoryProvenanceService.update_item`（M-01 supersede 法则），不带走 `apply_correction(lower_confidence)`；change_scope→`update_scope(pause)`；delete→`revoke_item`（M-07 撤销链）。审计 reason 统一 `aurora_receipt:<action>` 前缀 |
| `backend/app/api/v1/aurora_receipts.py` | `POST /aurora/receipts/respond`（四动作入口；词表外 422、跨用户/缺失 404 无存在性泄漏、终态冲突 409）+ `GET /aurora/receipts/actions`（词表自描述面）；已登记 `api/v1/router.py` |
| `backend/app/orchestration/response_builder.py` | 生产链路接线：`_build_memory_reference_receipt` 装配委托纯模块（真实引用解析逻辑不变）；新增 `_knowledge_refs_from_context`（GraphRAG 检索的真实 used_names）与 Redis 日计数（`aurora:calibration_receipts:<uid>:<date>`，surfaced 才 INCR，故障 fail-open 到 0——呈现预算是调节器不是守卫，宁可多呈现不静默吞） |
| `mobile/lib/core/services/aurora_receipt_api_service.dart` | 独立 `AuroraReceiptApiService`（**不扩** `MemoryApiService` 接口——其被 11+ 测试 fake 冻结，加方法即全量破坏；回执纠偏是 Aurora 域面，独立成类与后端路由对称） |
| `mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart` | `_MemoryReceiptRow` 单动作「不对」升级为**四动作行**（不相关/不对/别再用它建议/删除；busy/disabled/destructive 语义 + Semantics）；详情 sheet 新增不确定行（`receiptUncertainLine(count)`）与「参考材料」段（knowledge refs）；设计令牌（DS.*）+ `AppFeedback` 诚实反馈，失败绝不本地伪造成功 |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` (+4 个生成文件) | 新键：receiptActionNotRelevant/Wrong/ChangeScope/Delete、receiptCorrectionRecorded/Scope/Deleted、receiptUncertainLine({count})、receiptKnowledgeRefs；`flutter gen-l10n` 重生成 |

## 3. 关键设计决策（语义决策依据）

1. **回执锚在生产链路的「真实引用解析」上，不建第二真源**：哪些记忆真的进了
   回复由既有 `_collect_memory_reference_candidates` + `_memory_was_naturally_
   referenced` 判定（真实 ContextPack/user_context 解析）；本卡只把解析结果
   升级为完整回执——**receipt 与真实 Context 一致**由数据流结构保证（卡面
   验收 GJ08 前半）。respond 动作对 refs 的所有权/隔离/幂等守卫全部继承
   M-08/MemoryService 既有实现（跨用户 id 与缺失 id 同样 404，测试钉死）。
2. **rationale 是组成摘要，不是推理流（产品红线，守界说明见 §4）**。
3. **呈现门只调强度、永不吞纠偏能力**：`hidden`（无真实引用，绝不硬造回执）
   / `ambient`（全部高置信已确认，或 calibration 日预算 `MAX_CALIBRATION_
   SURFACES_PER_DAY=3` 耗尽——回执与四动作**原样保留**，只是不强调呈现）/
   `surfaced`（有不确定引用且预算内）。理由：AURORA_V3 §6 是「可提供」而非
   「每条强制」；而卡面 Forbidden「不得弱化既有纠偏面」排除了「不发回执」
   这种实现——降级到安静呈现既满足 Work 3（避免每条回复强制展示历史）又不
   收窄 GJ08 纠偏入口。呈现预算是 UX 调节器不是安全守卫，故 Redis 故障
   fail-open（多呈现）而非 fail-closed（静默吞）。
4. **不确定判定 = 单一口径**：置信 <0.6 或未被用户确认 → `unverified_
   inference`（用户语言标签）。0.6 与 M-08 `_confidence_tier` likely 带下限
   对齐，不发明第二置信档。knowledge refs（GraphRAG 真实 used_names）是展示
   面（「参考了：OS.pdf」），不挂四动作——文档域纠偏是 GJ10 链路，不在本卡
   重建。
5. **mobile 独立 service 而非扩 `MemoryApiService`**：该接口被 11 个既有
   测试 fake `implements` 冻结（实测 analyze +11 ERROR），加方法即破坏面
   扩散；回执纠偏走独立 `AuroraReceiptApiService` + 独立 provider，零回归。
6. **wrong 的双路语义**：带更正内容 = supersede（M-01 法则：episodic 建
   user_confirmed 替代行 + 旧行 `superseded_by_id`；preference 版本链推进；
   goal 字段白名单），不带 = 降置信 + 审计行。测试分别钉死两种终态。

## 4. CoT 不泄露守界（产品红线，专项说明）

**结构性守界（数据流边界），不是提示词约定：**

1. `build_calibration_receipt` 的输入只有：response_id、已解析记忆条目
   （id/type/content/time_ago/source/confidence/user_confirmed）、材料名、
   日计数。决策环内部对象（`annotations`、`policy_why`、`joint_why`、
   `allocation_why`、A-03 reason 码、摩擦后验）**在类型与调用面上就进不了
   本模块**——调用方（response_builder 装配层）从不持有也不传递它们。
2. `rationale_summary` 由**回执自身组成事实**模板化生成（引用了几条记忆/
   几份材料/几处不确定 + 校准邀请），逐字可审计；`summary`/`decision_reason`
   与之同源同文（移动端既有消费键兼容，三键同值由测试钉死）。
3. 测试红线（`test_a06_calibration_receipt.py`）：对整个回执 JSON 断言不含
   `policy_why/joint_why/S1.sufficient/Q1.insufficient/B1.budget/R0./
   friction_reasons` 等内部 reason 码形态；断言 rationale 只含组成计数事实、
   不含「推理/因此我判断/思考过程」类过程性陈述。
4. uncertainties 只暴露**封闭类型 + 用户语言标签 + 计数**（`unverified_
   inference` 等），不携带任何产生该判断的中间量（摩擦后验、证据分数明细）。

## 5. 四动作链路（Work 2 验收面）

| 动作 | 用户语义 | 委托权威（零新写路径） | 生效面（测试断言） |
|---|---|---|---|
| not_relevant | 这条与本轮无关 | `record_memory_reference_outcome(denied)` | `memory_reference_denied` 审计行 + 置信衰减 + 飞轮负样本 |
| wrong（带文本） | 内容不对，改一下 | `MemoryProvenanceService.update_item` | episodic：新行 supersede + 旧行 `superseded_by_id`；preference：版本链 `replaced_by_id` |
| wrong（无文本） | 内容不对 | `apply_correction(lower_confidence)` | 置信下降 + `correction_count+1` |
| change_scope | 别再用它建议 | `update_scope(pause)` | `archived_at` 暂停召回（可恢复；终态行 409 Conflict） |
| delete | 删除 | `revoke_item` | `revoked_at` + M-07 epoch bump + derived cache DEL + 三面不可见 |

隔离/词表/幂等：跨用户四动作全部 `MemoryProvenanceNotFoundError`（与缺失
不可区分）；动作/kind 词表外 `ValueError`→422；重复 delete 终态幂等且诚实
报告（测试 12 条钉死）。

## 6. 测试证据（命令 + 数字）

Backend（`cd backend`，`DATABASE_URL=sqlite+aiosqlite:///:memory:` 前缀）：

- `pytest tests/unit/test_a06_calibration_receipt.py tests/unit/test_a06_receipt_respond.py` → **38 passed**
- 上述 + `test_calibration_receipt.py`(既有 correction_feedback 回执) +
  `test_memory_provenance_api.py` + `orchestrator/mixins/test_response_builder_mixin.py`
  + `test_a03_friction_diagnosis.py` + `contract/test_aurora_decision_contract.py`
  → **184 passed**（零回归）
- mypy 棘轮（`mypy app` 全量，冷缓存）：**1796 errors = baseline 1796，零推高**
- `bash scripts/run_all_rule_guards.sh` → **exit 0（83 rules passed）**

Mobile：

- `python3 scripts/check_flutter_analyze_gate.py --project-dir mobile
  --budget-file quality/flutter_analyze_allowlist.json` → **PASS（ERROR=37 /
  WARNING=17 / INFO=598，与 main 基线 clone 逐条 diff 零新增；基线对照法 =
  `git clone <worktree> /tmp/wt311-a06-baseline`，未做任何树变更操作）**
- `flutter test`（新增 widget 测试 5 条：四动作渲染/not_relevant 请求语义/
  delete 请求语义/不确定行/参考材料段）→ **DEFERRED（代码照常交付）**：
  收工前实测 `vm.swapusage free=464M < 1.2G` 且 load 12.6，按舰队内存纪律
  跳过执行。缺口移交：Reviewer 在内存窗口 ≥1.2G 时以
  `flutter test test/features/chat/presentation/widgets/aurora_receipt_chip_test.dart
  --concurrency=1` 复跑。

## 7. 风险与未尽事项

1. **simulator/integration 证据缺口（Required evidence 3）**：本 worker 被
   内存纪律锁 LIGHT（HEAVY≤1 不可占用），未能产出真机/模拟器走查录证。
   GJ08 端到端（纠偏 → memory scope → 下会话自适应）的 UI 侧证据待Reviewer
   在 simulator 窗口补齐；后端侧链路已由 sqlite 行级测试覆盖（§5）。
2. 呈现门日预算当前只覆盖 chat 回执链路（surfaced 计数）；status_band/push
   等其他面的回执预算接入留给后续卡（消费同一纯门函数即可，词表已冻结）。
3. knowledge refs 目前取 GraphRAG 检索 `used_names`（真实被引材料名）；文档
   级四动作（文档删除/排除）是 GJ10 域，本卡未挂接（挂了反而是重建权威）。
4. `sync_engine_test.mocks.dart` 等 mockito 产物缺失在本地 analyze 造成的
   存量 ERROR（基线 clone 同样存在）为环境固有（gitignored codegen），与本卡
   无关、未触碰。

## 8. SHA 与产物

- Base：`2896d5fc`（main）
- Final：分支 `wt311-a06-calibration-receipt` 的 HEAD commit（即包含本报告
  的提交；哈希以 `git rev-parse HEAD` 为准，报告中不自录其后哈希）
- Patch：`v3-output/WT311-A06/changes.patch`（`git diff --binary main...HEAD`）
- 变更规模：15 文件，+1896/−64（后端 5 新 + 2 改；mobile 2 新 + 6 改）
