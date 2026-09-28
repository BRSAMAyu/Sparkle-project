# V4-D03 · 独立审查 receipt（一审 R1）

- **审查者**：wtD03R1（独立会话，未参与 D03 实现）
- **审查对象**：`agent/v4/d03` @ `a24e368a`（自 main@`150bc205` 开出；base 干净性已核：`git merge-base`=150bc205）
- **审查方式**：只读实现 + 独立复跑 + 独立反例探针 + 突变亲做（M1/M3）+ 逐块 diff 审计；零修改实现面（突变注入均 sha256 字节级还原）
- **总裁决**：**APPROVE（一审通过，待第二审）**。预登记挑战点 ①-⑥ 全部独立下判，无阻断挑战（CHALLENGED=∅）；4 条非阻断观察（C-1~C-4）移交消费卡/后续，不构成本卡回退理由。

---

## 1. 语义主链核验（逐步读实现）

主链五环全部核实为**真实委托**，无复制、无第二权威：

| 环节 | 实现位置 | 委托核验 |
|---|---|---|
| 撤回登记（rtr_ 幂等） | `retraction_recompute_service.register_retraction` | id=`derive_retraction_id`（纯 stdlib sha256，不含时间；探针 I1-I5 确认重放恒同/维度敏感）；幂等检出=compact-payload LIKE needle，重放 `duplicate=True` 零副作用（`test_register_retraction_replay_is_idempotent`：不双 bump、event_count==1） |
| 持久墓碑 | `_tombstone_evidence_rows` → `effect_kind='retracted'` | 条件 UPDATE 只改 effect_kind（审计列全保留）；G-01 重放 skip 集含 RETRACTED（`mastery_evidence.recompute_evidence_state` diff 亲读确认）；`test_replay_after_tombstone_excludes_retracted_evidence` 证明**完全不知晓撤回的直呼 G-01 重放也拿不回效果**——「账本本身=第二道防御」为**结构保证**成立（不依赖任何调用方自觉） |
| 同事务 epoch bump | `_bump_memory_epoch_in_txn`（M-01） | **import 复用**（service L86-90），亲读该函数：单条 `UPDATE..RETURNING`、flush 不 commit、加入调用方事务——register 内墓碑 UPDATE + bump + outbox INSERT 后**恰一次** `db.commit()`（L203），同事务成立；无第二计数器（全仓 epoch 权威仍唯一） |
| 栅栏下 G-01 前向回放 | `recompute_capability_nodes` → `GalaxyStatsService._load_prior_belief` → `recompute_evidence_state` | 生产读路径重放（含锚逻辑），非复制品；`test_recompute_equals_authoritative_replay_of_valid_events` 以权威回放值**精确相等**钉死，且显式断 ≠55（没撤回态）、≠40（减法态）；契约模块无任何接收"分数增量"做减法的函数位——**逆推减分结构上不可能**成立 |
| 读门 | `capability_node_read_state` → `evaluate_read_gate` | pending 无条件 stale+禁建议；`test_discarded_gate_keeps_pending_stale_state` 确认栅栏丢弃不静默恢复新鲜 |

**import 复用清单核实**：G-01=`MasteryEffectKind`/`recompute_evidence_state`（core import）；G-02=`_evidence_request_id` 往返测试钉死（`test_outcome_marker_roundtrip_with_g02_encoder` 与编码器互逆）；M-01/M-07=`_bump_memory_epoch_in_txn`/`_next_sequence`/`MemoryInvalidationPipeline.invalidate_derived_caches`；mastery 事件面=`GalaxyService._write_mastery_outbox_event`；事件元数据=`build_event_metadata`。core 契约内自带的 oc= 解析/构造是薄适配（core→services 反向 import 会造成分层倒置，选择合理），一致性由往返测试守卫。

## 2. 预登记挑战点逐一独立下判

### ① 锚语义：撤回最早证据行取 old_mastery 冻结锚 —— **接受（三选一判对）**

- **回落存储值 = 复活**：存储值仍含撤回效果，直接违反验收①，被正确排除；
- **回落外部"基线"**：V3-FIX-292 纪律下账本本身就是基线权威，外造基线=第二权威，且不反映该用户真实前置态；
- **old_mastery 冻结锚**：被撤回行的 old_mastery 是写行时落账的诚实前置事实，与 FIX-292「锚=首效果行前置值、从账本冻结」完全同构；撤回只退出**融合**，不涂改**历史事实**。

独立探针（非实现测试）亲跑：B1 最早行撤回后重放 == 同锚下仅有效行回放（<1e-12 精确相等）；C1 后位墓碑不驱逐前位锚（`frozen_anchor is None` 守卫）；A1 全撤回落 20 而非 90。**测试在库性**：契约层 `test_retract_all_events_falls_back_to_baseline_not_stored_value` + 服务层 `test_replay_after_tombstone_excludes_retracted_evidence`（42.0→20.0 非 42）双层在库。退化形态（撤回行 old_mastery=NULL）：生产迁移 `old_mastery INTEGER NOT NULL`（c8e4f2a3b1d5 亲读）+ 两处 evidence 写点非空 + 墓碑只转化既有 evidence 行 ⇒ 不可达，防御分支如实登记 limitation #5。**与 FIX-292 相容性论证成立**。

### ② 栅栏 fail-closed —— **接受（无静默通过路径）**

独立探针 10 项亲跑（F1-F10，非复制实现测试）：三栅栏各一反例（base 11 vs current 14 / 排除缺 m2 / 目标已删）全 discard；`None/None`、`None/9`、`4/None` 三种不可证组合全 discard；不等/负值/exact-string 排除均正确。「放行需要两侧世代可证相等」是唯一安全口径，接受。**任何静默通过路径**：域内无——唯一的"通过"要求调用方谎报 `retracted_ids=[]`，但服务层重放结构性跳过**全部** retracted 行（超集排除）+ epoch 栅栏兜底，双保险封死。域外注记：`int()` 截断使 7.5 vs 7 判等（F6）——两侧 epoch 均出自 INTEGER 列，域外输入，一句话注记不构成缺口。

### ③ 墓碑原位改写 vs append-only —— **接受（取舍如实登记）**

亲读 UPDATE 语句：`SET effect_kind = :retracted` 单列，old/new/reason/request_id/created_at/revision 全保留（audit-without-exposure 不破坏）；`test_register_retraction_tombstones_derived_rows` 断言行本体保留。先例核查：全仓此前**无任何运行时 UPDATE mastery_audit_log**（本卡是首例），但 wt598 已确立 effect_kind=服务端写侧定性字段（含迁移期 backfill UPDATE）——该字段的"分类可由服务端改写"语义先于本卡存在，墓碑是其自然延伸而非对账本事实列的涂改。备选（新表/新列）需迁移单头，limitation #4 如实登记并给出服从条款。排除面必须持久（重启/重放后仍生效），原位改写是无迁移约束下的最小实现。**登记如实，接受**。

### ④ 读门同门两出口 —— **接受绑死（分裂态正是要禁的口子）**

`evaluate_read_gate` 不存在 `stale=True ∧ suggestions_allowed=True` 输出（探针 R1-R6 全穷举）；pending 无条件双出、世代落后同出、新鲜才双开。卡面验收③原文是「UI 与工具**均**标过期，不继续旧建议」——绑死正是验收语义；字段仍分立（stale / suggestions_allowed / ui_marker），未来若真出现"UI 过期但建议可续"的产品需求，是消费面的策略决定，不须改门。**当前判定"绑死更安全"成立**。

### ⑤ 幂等 LIKE 扫描 + 并发竞态 —— **接受（有界竞态登记准确）**

顺序重放幂等由测试钉死（duplicate / 不双 bump / event_count==1）。并发同 target 双登记最坏=冗余 epoch bump + 冗余事件行：世代语义下多余 bump 只会让读者**更** stale（单调方向，安全侧），无损坏无复活——limitation #3 描述精确，强口径需求（可锁目标/唯一约束）正确指向迁移单头。LIKE needle 与 compact 序列化形状耦合（`separators=(",",":")`）较脆：序列化格式变更会静默破坏去重——非阻断，移交消费卡时一并处理（见 C-4 建议）。

### ⑥ BJ/AT 豁免 —— **接受（豁免依据成立、消费卡归属清晰）**

独立核实：全仓 `RetractionRecomputeService` 零生产消费者（仅 event_registry 的 producer 路径串与测试）；outcome ledger 确为查询时派生读模型、无"用户撤回 outcome"入口；本卡 diff 零触碰 mobile/gateway/api/proto。守卫亲跑：`[Rule BJ] PASS`、`[Rule AT] PASS`（2026-09-28，worktree）。台账 P3 #14 + `rule_at_exceptions.md` 双登记在库，消费卡归属（结果撤回 UI/FSM 入口 + 重算 job 调度 + insight/strategy 执行体）三处文字一致（limitation #1 / ledger #14 / tasks.json implementation_note）。**待接线状态可接受**。

## 3. 突变复现（亲做）

| 突变 | 注入 | 结果 | 还原 |
|---|---|---|---|
| M1 栅栏旁路 | `evaluate_publish_gate` epoch 判定改 `if False and (...)` | **4 failed**（claim 3 条 + 我全量跑多杀 1 条 `test_discarded_gate_keeps_pending_stale_state`，≥ 登记） | `git checkout` + sha256 `618dc015…ea9e` **字节级恒等**（与注入前快照及 run_manifest 记录前缀 618dc015 一致） |
| M3 读门旁路 | pending 分支改 `if False and status_value == ...` | **3 failed**（与 claim 完全一致） | 同上，sha256 恒等；`git status` 干净 |

（M2 按抽做指令未亲做；其判据"权威回放精确相等"已由 `test_recompute_equals_authoritative_replay_of_valid_events` 的 ≠55/≠40 双反断言独立复核为不可跳过。）

## 4. 复跑（独立执行，同环境 SECRET_KEY=ci-test-key DATABASE_URL=sqlite://）

| 批次 | 我的复跑 | manifest 登记 | 判定 |
|---|---|---|---|
| 34 新测（core 23 + services 11） | **34 passed** (5.15s) | 34 passed | ✅ 一致 |
| 受影响批 288 + 事件批 67（合并跑） | **355 passed** (79.5s) | 288+67 | ✅ 一致 |
| tests/services 全量 | **1047 passed, 10 skipped** (456s) | 同 | ✅ 逐数一致 |
| mypy 棘轮 | **55**（主检出同命令 55/55；retraction 新文件 0 error 行） | 55 / baseline 77 | ✅ 零新增 |
| ruff + black（4 新文件） | All checks passed / 4 files unchanged | 同 | ✅ |
| Rule BJ / Rule AT | PASS / PASS | PASS | ✅ |

既有失败处置核验：bert 36 errors、BG worktree、BA-ROUTES 均为 base 既有/环境差异，与本卡零文件交集（diff 面亲核）。

## 5. 既有权威面最小改动逐块审计

- `mastery_evidence.py` **+15/−2**：`RETRACTED` 枚举成员 + skip 集 `!= PROJECTION` 改 `not in skip_kinds`（语义等价扩集）+ 文档注释。**融合数学零改动**（Kalman/decay/排序逐行未触）。
- `stats_service.py` **+20/−0**：RETRACTED 分支（不融合、不进 presence、old_mastery 冻结锚）+ 全撤回回落分支（`saw_retracted and frozen_anchor is not None` → 回落锚而非存储值）。既有分支逐行未触；FIX-292/299 锚纪律保持。
- `event_registry.py` **+15**：单一 `RegisteredEvent("retraction.registered")`，producer/status 正确。见 W-2 用词注记。
- `tasks.json`：状态翻转 + implementation_note；`KNOWN_CODE_DEBT_LEDGER` #14、`rule_at_exceptions` +2：纯登记。
- 零迁移、零 proto、零生成物手改、`git status` 干净（审查终态）。

## 6. 非阻断观察（移交消费卡/后续，不构成本卡回退）

- **C-1（中低）**：`recompute_capability_nodes` 的 `current_epoch` 在重算开始读**一次**（L255），栅栏逐节点用它判，**提交前不重读**。交错窗口（重算回放 SELECT 之后、commit 之前另一撤回 commit）可把含被撤回效果的值写进 `user_node_status`，直至下次重算——账本自身干净、墓碑使该值不可经重放复活、读门按时间戳大概率转 pending，但严格口径下与契约 docstring「发布时点 current_epoch」有差。**消费卡（重算 job 调度）应在 commit 前重读 epoch 或对 epoch 行加锁**；生产触发方未接线前无运行时暴露。
- **C-2（低）**：服务路径 `excluded_ids === retracted_ids`（同一名单传两参），排除完备栅栏在服务层由构造满足（DISCARD_MISSING_EXCLUSION 不可达）；其安全语义由「重放跳过全部 retracted 行（超集）」承载，栅栏本体在契约层测试到位。属接线形态注记，非缺陷。
- **C-3（低）**：`capability_node_read_state` 用墙钟比较（MAX(created_at)）且向 `evaluate_read_gate` 传 `computed_epoch=None/current_epoch=None`——契约层的 epoch 分支在服务层未启用；sqlite `CURRENT_TIMESTAMP` 秒粒度（Postgres 微秒）同秒撤回可漏 pending。建议消费卡把重算钉的 epoch 落进 trace 行（request_id 空位可用），读门切 epoch 比较。
- **C-4（低）**：重算后 `galaxy.mastery.updated` outbox 事件复用 GalaxyService 写面在 sqlite 恒失败（UUID 裸绑定）被 try/except 吞为 warning——该分支**零有效测试覆盖**（Postgres 应原生绑定，生产预期可用）。消费卡补 PG 形状断言或对写面直测；顺带处理 ⑤ 所述 needle 与序列化形状的耦合。

**用词勘误（W，不影响数字）**：
- **W-1**：run_manifest「增量 29 = 本卡 11 + F02 等已并卡测试」——F02 本体在 main 上晚于本卡 base（150bc205 之后），不在本分支；增量实际来自 D02 审查基线（1018）与本卡 base 之间已并卡测试。1047/10 的**数字本身**经我独立复跑逐数一致，仅归因短语不精确。
- **W-2**：event_registry 注册注释 "Emitted once per effective non-memory retraction (result/material/inference)"——当前服务构造期只放行 result（material/inference 显式拒绝）。注释描述契约终态而非当前接线，建议后续顺手指正。

## 7. 集成 SHA 复验提示

main 已前进至 `71553984`（F02 销账）。与 本卡 diff 面（`git diff --name-only 150bc205..main`）唯一交集 = `v4/04_tasks/tasks.json` 状态行，代码零交集——合并冲突风险仅 tasks.json 琐碎级。集成复验按流程由合并方执行。

---

**裁决汇总**：APPROVE（一审）。预登记 ①②③④⑤⑥ = 接受×6；CHALLENGED = ∅（无阻断）；非阻断 C-1~C-4 + W-1/W-2 随 receipt 移交。第 34/1047/355/55 等所有数字为本审查者独立复跑所得，非转录。
