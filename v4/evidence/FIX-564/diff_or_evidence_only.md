# FIX-564 · 撤源失效 sweep 纳 candidate + 人工入口真撤回验证门（diff 与证据面）

I05R2 R2-D1 产品缺陷闭环（P2）。缺陷：`invalidate_on_source_withdrawal` sweep
候选集仅 active/evidenced——candidate 态引用已撤源的 patch 不进 sweep，之后
`admit_evidence` 照常爬档可 active（off/live 双档亲证）；live 收益门只拦无收益
不感知撤回；人工入口（撤回报告入口）不验证源真已撤回。

## 修法选型（台账二选一）

**选 sweep 纳 candidate（选项一），弃 admit 前查撤回台账（选项二）。**

1. **台账在 A-05 可消费的持久面不存在**。D03 `retraction.registered` 事件载荷
   携带 `(retraction_id, kind, target_type=result, target_id=outcome marker)`；
   M-07 `memory.invalidated` 携带 memory 表 UUID——两者都不携带
   `memory://experience/expmem_*` / `decision://aurora_*` 引用身份。按 ref 身份
   查台账需新建映射存储 = 第二套身份系统（P2 资源姿态禁止）。
2. **admit 前查真源已结构性存在**。`_verify_evidence` 在 admit 时逐条对真源
   重解析（M-06 投影 / D-05 未删 outcome 行）——真删的源 admit 走 G1
   fail-closed（I05R2 已亲证的缓解面）。台账查询对唯一危险形态「报告但源未
   真撤」零保护。
3. **A 是权威收口点**。sweep 是「该源已撤」这一事实在 A-05 的唯一确立点；在
   此对全部非终态一次性 enforce「引用已撤源的 patch 必 revoked」，admit/confirm
   各自无需感知撤回（revoked 终态 + T6 封闭 + 内容寻址防复活：同内容重提议
   返回 revoked 行；异内容重提议真删后死于 G1）。
4. **两修互补闭环**（见下「补门」）。

## 补门：人工入口真撤回验证门

`invalidate_on_source_withdrawal` 新增 `_source_withdrawal_visible`（fresh 读，
缓存旁路）：

- memory 引用：fresh 投影中记录**消失**，或记录仍在但**已无 outcome 方向证据**
  （outcome 墓碑口径——结果撤回后经验骨架可存续而证据面已撤）；
- decision 引用：该 decision 无未删 `outcome_observed` 行（与 admit 解析谓词
  同款——证据面不再解析 = 已撤可见）；
- 不可验证的报告 → ValueError 拒绝、零 revoke。

### 入口信任契约（显式声明）

本入口是撤回的**报告面**（通知性记账，不删真源数据）——FIX-564 后只受理
**真源证据面可见**的撤回。事件接线卡（未来）必须在撤回于其所属域落定（删除/
墓碑已提交）后投递本入口。**inference 域撤回（源证据合法存续）不可经本入口
受理**：inference 消费卡应走自己的失效路径，或在证据面落定后经
`result_retracted`/`material_deleted` 报告。

## 闭环矩阵

| 场景 | 修前（main d84cf6cc） | 修后 |
|---|---|---|
| 源真撤 + 已报告 + candidate 存在 | sweep 豁免 candidate → admit 爬档 active（off 亲证 repeated→active；live 正收益放行；live 无收益 evidenced→confirm active） | sweep revoke candidate（终态）→ admit/confirm 全 T6 |
| 源真撤 + 未报告 + candidate 存在 | admit 可 active | admit G1（证据不解析——I05 既有证据门，非本卡新增） |
| 源未撤 + 虚假报告 | sweep revoke 真实证据的 active/evidenced patch（**误伤**） | 入口 ValueError 拒绝、零 revoke（补门独立价值） |

## 审计面增注

返回审计新增 `affected_states` 键（patch_id → 撤收前状态，如
`{"polpatch_…": "candidate"}`），其余键与形状不变；
`schema_version` 保持 `experience_strategy.v4.i05.v1`（ additive-only）。
`kind` 字段从调用方原样改为 `RetractionKind` 规范化值（词表校验前置，IO 前
fail-loud）。

## 变更文件

- `backend/app/services/policy_patch_service.py`：
  - `invalidate_on_source_withdrawal`：kind 词表校验前置；验证门；候选集
    `["candidate", "evidenced", "active"]`；审计 `affected_states`；docstring
    记录选型理由与入口契约；
  - 新增 `_source_withdrawal_visible`；
  - 模块头 I05 撤回条目同步更新。
- `backend/tests/services/test_experience_strategy_service.py`：
  - `TestSourceWithdrawalInvalidation`：4 测 setup 增真撤回步骤（软删 D-05 行，
    M-07 删除链口径，test_experience_memory_projector 先例同款）——**断言零
    改动**（原 setup 报告未撤源，新入口契约下属不可验证报告）；
  - 新增 `TestWithdrawalSweepCandidateClosure`（5 测，见 test_results.json）；
  - 新增 `_withdraw_experience_source` helper；模块 docstring 登记 FIX-564。

## 不变量（零削弱核对）

- I05 契约 73 新测：56 unit（零文件改动）+ 17 service（断言零改动）全部原样
  通过；影子红线突变面（shadow 逐字节恒等）不在本卡触面；
- D03 strategy 面（core `strategy_withdrawal_plan` / `plan_recompute`）零改动，
  全 kind 词表支持不回退（`core/retraction_recompute.py`、
  `core/experience_strategy.py` 未触）；
- off/live 双档行为语义测试保持：`TestLiveBenefitGate` 5 测原样通过（收益门、
  有界窗语义未触）。
