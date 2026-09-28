# V4-D03 · limitations

1. **生产触发方未接线（本卡最大边界）**：`RetractionRecomputeService` 是登记/栅栏重算/读门的唯一 IO 入口，但**谁调用它**（结果撤回的 UI/FSM 入口、重算 job 的调度/重试队列）本卡未接——仓库当前不存在"用户撤回一个 outcome"的用户入口（outcome ledger 是查询时派生读模型，账本无表）。Rule BJ/AT 按守卫自身机制豁免收口（`# rule-bj: exempt` + `docs/aurora/rule_at_exceptions.md` 登记），消费卡接线时移除。契约面与执行面已可独立审查，接线不改变语义。

2. **三分类只接线了结果撤回**：`material_deleted` 的记忆域撤回已是 M-07 权威管线（本卡零改动、不重做）；`inference_retracted` 与 insight/strategy 面的**具体重算执行体**归消费卡——契约词表（`RetractionKind`/`DerivedFace`/`CANDIDATE_FACES_BY_KIND`/`plan_recompute`）已统一冻结，执行体接入时只有实现面工作。当前 `register_retraction` 对非 result 组合构造期显式拒绝（不静默落错依赖边）。

3. **并发双登记的有界竞态**：登记幂等靠 retraction_id 的 outbox LIKE 扫描 + 墓碑条件更新；顺序重放完全幂等（测试钉死）。但两个**并发**同 target 登记在无锁目标行场景（如该 outcome 从未被星图吸收、无墓碑行可锁）最坏 = 冗余 epoch bump + 冗余事件行——世代计数器语义下无数据损坏、无复活，但违反 M-07"每有效变更恰一次 bump"的严格口径。记忆域入口无此竞态（有记忆行可 FOR UPDATE）。若消费卡需要强口径，需在登记入口引入可锁目标或唯一约束（涉及迁移，归契约 owner）。

4. **墓碑 = effect_kind 原位改写**：append-only 账本上 `evidence→retracted` 只改效果参与标记，审计列（old/new/reason/request_id/created_at）全部保留（audit-without-exposure 不破坏）。"append-only"的字面性在此处有意让位于撤回语义（锁面 evidence-retraction 归本卡）；若审查裁决账本不可原位改写，替代方案是新表/新列（需迁移单头），撤回排除面逻辑不变。

5. **撤回最早证据行的锚语义**：被撤回行的 `old_mastery`（写行时诚实前置值）仍冻结重放锚——这保证撤回最早证据回落其前置基线而非把撤回效果烘焙进锚点；代价是撤回行参与锚选择（尽管其观测永不融合）。`saw_retracted and frozen_anchor is None` 的退化形态（撤回行 old_mastery 为 NULL）现无任何写路径可产生（两处 evidence 写点 old_mastery 均非空），防御分支保留 legacy 回落并已注释。

6. **星图以外的派生面靠 epoch 门间接保护**：I01 resume view（freshness 钉 memory_epoch）、context 快照（C-07 读侧门）、profile context 在登记 bump epoch 后自动判 stale 重算——机制成立但本卡未逐一端到端断言（各自的 epoch 门测试是既有权威测试，本卡 288 回归批覆盖其面）；星图能力节点是唯一做了"登记→栅栏重算→读门"全链测试的面。

7. **capability_node_read_state 的时间比对粒度**：pending 判定 = 最近 `retraction.registered` 时间 > 最近 `retraction_recompute` trace 行时间（同用户聚合级，非按 outcome 细分）——登记任何撤回都会让该用户全部已重算节点进 pending，直到各自被重算或被读方接受"重算先行于撤回"的保守口径。outcome 级细分需要 per-node 撤回关联查询（可从事件 payload 关联，消费卡按需接）。

8. **worktree 环境差异（非代码）**：Rule BG 在 bare worktree FAIL（Go/Dart proto 生成物缺席），主检出同 guard PASS 逐同验证；主检出全量守卫自身有 base 既有失败（BA-ROUTES，main 前进后引入，与本卡零交集）。本卡新增守卫回归 = 0。

9. **验收③的"UI"无截图**：本卡无 UI 交付面——"UI 标过期"落在类型化读门出口（`ui_marker=stale_recomputing`）与既有 epoch 门（context/I01），呈现层冻结文案表归 V4-F03（B05 §3 同款分工）；工具面同理（`suggestions_allowed=False` 是判定面，具体建议生产者的消费归其卡）。
