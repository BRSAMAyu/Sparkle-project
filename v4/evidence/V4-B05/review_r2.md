# V4-B05 独立审查 receipt（二审 · wtB05R2）

- 审查对象：修订版 `v4/evidence/V4-B05/contract_receipt_min.md` @ commit `627205f1`（branch `agent/v4/b05fix`；修订基线 = 一审对象 `1c1ad4e5` + 一审 receipt `83b3633e`）
- 审查人：wtB05R2（未参与 B05 实现与一审；只读审查 + 本 receipt）
- 方法：对修订 diff（`git diff 1c1ad4e5..627205f1`，仅 contract_receipt_min.md + run_manifest.json，40+/11-）逐 hunk 核验；一审 C1–C5 逐条对照落稿情况；对修订处引用的代码锚**抽验 12 处**（行号级 sed/grep 打开真实文件）；反例对齐计数用脚本对 `examples/counterexamples.json` 独立重算；5 个示例 JSON 独立复跑 `python3 -m json.tool` 全部通过。

---

## 1. 五项修订落地核验（对照一审 C1–C5）— 全部落地

### C1 版本集合门机制节（§4.1 新增）— ✅ 落地，逻辑自洽、锚真实
- 锚核验：写侧 `backend/app/core/action_plan.py:259` 确为 `if self.schema_version != ACTION_PLAN_SCHEMA_VERSION`（严格相等，violation）；读侧 `:340` 确为 `!=` 即 `_degrade` + 整块 `return None`；docstring 原句「版本 bump 未迁移存量行时该 WARN 会随读放大（已知代价…）」逐字在场（:327 附近）。§4.1 对现状的描述与代码完全相符。
- 机制消险论证成立：读门改 `∈ {action_plan.v1, action_plan.v1.1}` + 按版本分派（v1 行原样输出、why_now 补位二选一由实现卡钉死并以测试冻结；集合外/脏值维持整块 None+WARN fail-closed）→ 存量 v1 行不再因 bump 整块降级，一审指认的破坏路径被真实关闭；写侧双版本共存窗口 + 新写落 v1.1 + 回归断言（bump 后 v1 行投影逐字节等价、WARN 不放大）构成可失败的验收项。「对 v1 行零影响」改为以 §4.1 落地为前提的如实表述；字段级降级明示为相对 X-01 整块降级的**有意新 delta**（原稿「与 X-01 相同」作废）。与现行读门 legacy 行（空 schema_version 静默 None）不冲突。

### C2 幻引替换 — ✅ 落地，新权威全部真实
- `AURORA_SEMANTIC_POLICY`/`semantic_policy` 在 backend/proto/mobile 全仓 grep **零命中**（复核属实）；`v4/03_intelligence/AURORA_SEMANTIC_POLICY.md` 存在，「受限输出」段含原句「confidence_band是审慎标签，不向用户显示虚构精度百分比」——「语义词源 lineage 参考、不作合同权威」的降级处理与事实相符。
- 新锚逐一定位：`backend/app/core/aurora_decision.py:108` `AURORA_UNCERTAINTY_KINDS`、`:191` `class DecisionUncertainty` 精确；`backend/app/aurora/calibration_receipt.py:109` 注释「0.6 与 M-08 ``_confidence_tier`` 的 likely 带下限对齐（同一口径，不另造档）」逐字在场——合同「同一口径不另造档」措辞即源自该注释，引用忠实。

### C3 六值投影 + INVALID_COMMAND 排除论证 — ✅ 落地，论证与代码行为相符
- `action_command.py:164` `ACTION_ERROR_CODES` 实为 **6 值** dict，含 `"INVALID_COMMAND": "ACTION_INVALID_COMMAND"`（修订计数正确）。
- 排除论证逐点与代码相符：`ActionCommandError` 基类（:177）默认 `error_code = ACTION_ERROR_CODES["INVALID_COMMAND"]`；`CommandValidationError`（:231）同码且 `http_status = 422`，docstring「payload/命令前置校验失败（确定性预筛，非 LLM）」；raise 点在授权入口即拒（`action_permission_service.py:85/:115`，"授权入口即拒"）、先于 proposal 生命周期落账，**无 proposal 身份可投影**——论证成立；`to_payload`（:187）经 `_to_http_error`（`api/v1/action_proposals.py:114`）同步返回请求方，422 表述属实。投影器 fail-loud 断言登记覆盖残余情形。
- `run_manifest.json` 以追加 `r1_erratum` 字段更正而非回改原 evidence——不篡改既有证据、更正透明，方法可接受；erratum 称「原 grep -A 8 实际输出即含 6 值」经复算正确（:164 起match+8 行覆盖全部 6 个条目）。

### C4 四终态全函数投影 + demo 透传 — ✅ 落地，完备自洽
- `TerminalReason`（`action_command.py:117`）确为 **4 终态** committed/user_cancelled/user_rejected/expired，docstring（expired 懒转+sweep 持久化、committed receipt 权威）与修订表述相符。
- 全函数表每值恰一结局：代码事实核对成立——receipt **仅 committed 落账**（`get_receipt` :541-549 非 COMMITTED 即抛），expired 经懒转+sweep 显式持久化（ProposalExpiredError docstring 同款），user_cancelled/user_rejected 为用户在确认卡上的**同步** API 动作（cancel/reject 直接返回结果），「补发事件属噪音、结果已即时可知」的跳过论证与代码行为相符；「覆盖完备」失实表述已改为仅主张互斥（卡验收 3 保留）。
- `TruthClass`（`outcome_ledger.py:104`）确为 **5 值**含 `demo`；修订对 demo 的三重标注「demo/seed cohort、消费方标注、确定性分级不产此值」与 `:110` 注释及文件头 :9-11 逐字相符；「resume 聚合器遇 demo 行透传不排除 + 呈现端显式演示/种子标注、永不进成功/精通面」与账本侧「demo 为合法消费方标注行、确定性分级不产此值」语义一致，既不对合法账本数据 fail-closed，也不破坏 D-02 分级纪律。

### C5 双集对齐声明 + owner 指定 — ✅ 落地，计数精确
- §9 对齐声明计数经脚本独立重算**全对**：`counterexamples.json` 12 条；与 §9 表重叠恰 7 条；表独有恰 `tracking_events`/`harness_mock` 2 条；JSON 独有恰为声明所列 5 条（`error_state_mixed_with_committed`/`cross_object_subject`/`empty_candidates_rendered_as_has_evidence`/`fabricated_ref_scheme`/`why_now_without_basis`）。补入责任（contract-owner、实现卡开工前）与「此后以 JSON 为唯一权威冻结集」明确。
- copy_key 冻结文案表 owner 指定 V4-F03 实现卡（contract-owner）：F03 卡存在（experience-presenter 锁、依赖 V4-B05），归属自洽；本合同只冻结键位与纪律的边界清晰。

## 2. 新引入问题扫描 — 未见阻塞项

- 修订处代码锚抽验 **12 处全部命中**（action_plan.py:259/:340/docstring、aurora_decision.py:108/:191、calibration_receipt.py:109、action_command.py:117/:164/:177/:187/:231、permission_service raise 点、outcome_ledger.py:104-110），无新幻引。
- 越权复核：修订 commit `627205f1` 相对一审 `83b3633e` 仅改 contract + run_manifest 两个 evidence 文件，`git diff -- backend mobile proto gateway` 为空；修订内容全部为文档级机制/表述修订，未引入实现声明或第二权威。
- 逻辑自洽性：§4.1 读侧三 分派（v1 原样/v1.1 追加解码/集合外 fail-closed）与 §8 双读断言、§6 全函数表、§5 demo 透传相互一致；§1 表、§3 字段表、§6 修订相互引用无矛盾。

### 残留（均非阻塞，不 gating）
1. **新引入笔误**：合同头部修订记录引一审 receipt SHA 作 `83b363e`——该缩写不可解析（`git rev-parse` 失败），实际为 `83b3633e`（短 SHA 应为 `83b3633` 或全串）。建议实现卡顺手更正，不影响销账。
2. 既有（一审已接受、未变）：§1 表引 `action_command.py:288`，`CommandEffects` 实际类行在 `:287`，差一行。
3. `AURORA_SEMANTIC_POLICY.md` 的「（v0.1 提案）」版本标签在文档本体无版本标记可验（文档存在性与「受限输出」段已验证）；纯描述性、非权威引用，无碍。
4. §9 注称本表为「叙述面冻结子集声明」，当前实为 7/9 子集（2 条表独有）——注内已如实展开并责令补齐，措辞瑕疵、无失实。

## 3. 总裁决：**APPROVE（可销账）**

一审 4 项必须条件（C1–C4）+ 1 项建议条件（C5）全部以文档级修订落回合同，修订处引用的权威/代码锚抽验 12/12 命中，无新幻引、无新失实、零产品码 diff。残留 4 项均为笔误/措辞级，不构成阻塞；残留 1（SHA 笔误）建议随实现卡顺手更正。按一审约定「修复后由独立会话对修订 diff 做点验即可」，本 receipt 即该点验。

— wtB05R2，2026-09-28，审查基线 `627205f1`（branch `agent/v4/b05fix`）
