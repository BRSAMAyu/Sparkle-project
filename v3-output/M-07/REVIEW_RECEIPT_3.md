# M-07 R2 Delta 复核回执（返修复验）

- 审查人：R2（DeepAudit，持探针 #1/#2 与变异手法的第一手记录）
- 时间：2026-09-19（返修后）；基点 wt8 @ 10fde918，返修 patch 9 文件 1689+/127-，md5 `721b0e7308ed683ae9c5fde15f6f1041`（已核对一致）
- **总 Verdict：ACCEPT**

## 1. 逐项复验结果

### C1（R2-P1，supersede 链后删链头 live 键不摘除）— **PASS**

- 源码：`_remove_live_preference_key_in_txn` 链头查询补 `MemoryPreference.replaced_by_id.is_(None)`（memory_service.py，带契约对齐注释）。语义与 `derive_status` 的 SUPERSEDED 判定一致；active 链头 = replaced_by NULL 且未撤未删，删除真链头时无其他候选 → 摘键，删除历史版本时真链头在场 → 保键，方向安全。
- **R2 探针 #1 原样重跑：PASS**（set 0.6 → 0.8 → 删 v2 → live `explicit["depth_preference"]` 消失）。
- 采纳的回归 `test_preference_delete_after_supersede_chain_removes_live_key` 构造与探针等价（含 head.version==2 前置）。

### C2-1（R2-P2-4，epoch 门测试未钉住）— **PASS**

- 加固后的 `test_profile_context_cache_rejected_after_epoch_bump` 采纳探针 #2 构造：monkeypatch `PreferenceService.get_preference_version` 返回 7 与构建 fake version 一致（测试 :576），唯一拒绝因素只剩 epoch。
- **变异 M1 重跑（删 `and context.memory_epoch == current_epoch` 行）：FAILED（击杀）**——原交付此变异下 17/17 仍绿，返修后真钉住。
- 顺带核实 R1 C3-①：`assert await fake_redis.get(...)`（:595）已 await，恒真断言已修。

### C2-2（R2-P2-3，bulk 无行锁无复查）— **PASS（并发论证评估见 §2）**

- 源码：`revoke_inferred_memories` select 补 `.with_for_update()` + 锁内逐行 `derive_status(...) == active` 复查过滤（memory_service.py）；全终态时零副作用返回 0。
- 新测试 `test_bulk_revoke_locked_recheck_skips_terminal_rows`：superseded 行（superseded_by_id 置位、revoked_at NULL，能穿 SQL 预过滤）不被撤销/不计数/不进 memory_ids，恰一次 bump 一条事件——构造真实（终态行只能靠复查识别）。
- **变异重跑（删复查过滤）：FAILED（击杀）**。

### C2-3（R2-P2-1，DEL 在 commit 之前）— **PASS**

- 管线：`apply_in_txn` 在 `commit=False` 时只经纯函数 `derived_cache_keys`（staticmethod，字符串格式化，零 IO）**计算**键不 DEL（pipeline:178,187-190）；`commit=True`（WM）内部 commit 后 DEL，顺序正确（:179-181）。docstring 已如实更正。
- **5 个服务层调用点逐一读核**：memory_service.py:210（supersede）、:1177（retract）、:1253（bulk）、:1334（correction-reject）、:1447（revoke_episodic）——每处都是 `await self.db.commit()` **之后**才 `invalidate_derived_caches`。「提交后 DEL」表述与实现一致。
- 既有 DEL 行为测试保持绿（DEL 后置无回归）。

### C2-4（R2-P2-2，写时钉 epoch 的 ABA 窗）— **PASS**

- 源码：`get_profile_context` 把 `memory_epoch = await self._get_memory_epoch(user_id)` 前置到 prefs/knowledge/cognitive/error/compile 全部内容装配之前（profile_context_service.py:171），单次读取、两处复用（ProfileContext 构造 :180 与 `_write_inline_snapshot_cache(memory_epoch=...)` :210）；写时二次读取仅作直调回退。
- 方向论证成立：epoch 先读 → 装配期间删除 commit → 快照携带旧 epoch → 读侧门以 current（已 bump）拒绝 → fail-closed（多一次重编译，无复活）。「旧内容+新 epoch」过门路径消除。
- ABA 测试真实性核实：`_racing_epoch`（首读=1，此后=2）模拟构建期删除 commit；断言三重钉住——恰一次读取（`epoch_reads["count"] == 1`）、两处载荷均携带 1、`get_inline_snapshot` 返回 None（门拒）。**变异重跑（快照写回退为写时读取 memory_epoch=None）：FAILED（击杀）**，且会先撞 count 断言再撞门断言，双保险。

### P3 项 — **PASS（处置合理）**

- P3-6：两条 episodic 衰减路径（`apply_episodic_decay_policies` :67、`_apply_episodic_decay` :382）均补 `superseded_by_id.is_(None)`，核实。
- P3-7（lower_confidence 不走管线）/P3-8（epoch=0 极窄互配）：登记为语义边界不修——评估同意（分数微调非删除、无复活通道；fail-closed 方向正确）。
- REPORT §0 表述与返修后实现一致性核实（原对 bulk 失实的「四入口统一 FOR UPDATE+复查」在返修后成立，§9.3 如实说明更正过程）。

### 词汇表 / 回归 / patch 完整性 — **PASS**

- 词表 34 名，独立重算 sha256 = `c2815560…70fd9c` 不变。
- 管线套件 **20/20**（wt8/backend/.venv 复跑）；回归 spot（write_guard/epistemic/conflict_resolver/working_memory_rejection）**25 passed** 与自报一致。
- `changes.patch` 在 10fde918 基线导出树上 apply 后与 wt8 工作树 **9 文件 byte-identical**——patch 即树，无隐性漂移。

## 2. C2-2 并发论证的独立评估（回答「接受代码层论证还是要 CHANGES」）

**判断：接受代码层论证，不构成 CHANGES 理由。** 依据：

1. PG READ COMMITTED 下 `SELECT ... FOR UPDATE` 对已锁行阻塞、先到事务提交后按 EvalPlanQual 语义对**最新已提交行版本**重估 WHERE 谓词——先到批次置 `revoked_at` 后，后到批次的 `revoked_at IS NULL` 谓词直接剔除该行，行不进结果集。
2. 能穿过 SQL 谓词的终态行（如 superseded_by_id 置位但 revoked_at NULL）由锁内 `derive_status` 复查排除——复查在锁持有后执行，读到的是重估后的行状态，与谓词重估同一版本链。
3. 不相交行集的两个并发批次（同用户不同记忆）各产生一次 bump+事件——这是**两个有效变更各自的恰一次**，符合「每个有效变更恰一次」契约，不是双发。
4. 残留理论缺口仅「本事务 SELECT 已扫过后并发 INSERT 的新行不被本批覆盖」——新行本就不属任何一批的撤销范围，无不变量破坏。

真双连接 PG 实测受 dev DB 只读纪律限制（R1/R2/返修三方一致），sqlite 测试钉住的是与方言无关的复查语义。建议合入后择机补一个两连接 PG 集成测试（观察项，非阻断）。

## 3. 变异重跑表（R2 原始手法，cp /tmp 备份法）

| # | 变异 | 钉住测试 | 结果 | 还原 |
|---|---|---|---|---|
| MU-1 | 删 C1 过滤行 `replaced_by_id.is_(None)` | test_preference_delete_after_supersede_chain_removes_live_key | **击杀（RED）** | byte-identical |
| MU-2 | 删 M1 门条件行 `and context.memory_epoch == current_epoch` | test_profile_context_cache_rejected_after_epoch_bump | **击杀（RED）** | byte-identical |
| MU-3 | 删 C2-2 锁内复查过滤 | test_bulk_revoke_locked_recheck_skips_terminal_rows | **击杀（RED）** | byte-identical |
| MU-4 | 快照 epoch 回退写时二次读取（memory_epoch=None） | test_inline_snapshot_pins_epoch_read_before_content_assembly | **击杀（RED）** | byte-identical |

还原后 20/20 复绿；两源文件与备份 diff 为空。

## 4. 探针双验

| 探针 | 场景 | 结果 |
|---|---|---|
| r2_probe1 | supersede 链（0.6→0.8）删链头 → live 键必须消失 | **PASS**（返修前 RED） |
| r2_probe2 | preference_version 匹配、仅 epoch 失配 → 必须拒绝 | **PASS** |

探针临时副本已从 tests/unit 移除（证据版仍在 v3-output/M-07/）。

## 5. 合入预演

- 主仓 HEAD `ee885386`（B-03 合入；stat 核实只动 mobile/scripts/v3-output/.gitignore，backend 零重叠）。
- `git apply --3way --check changes.patch` 于 ee885386 导出树：**exit 0**，7 文件全部 cleanly（2 个 3way 回退后自动解析）+ 2 新增平凡落地。
- REVIEW_RECEIPT_2 §3 的合入 checklist（M-03 接线 `memory_epoch_version_string`、context_manager fail-open、F4/F5）仍归 Leader/M-03R2，不随本卡。

## 6. 残留（如实，均不阻断）

1. ltm_e2e 未复跑（PG 认证环境性，R1/R2 双路已核基线预存）。
2. 真双连接 PG 并发未实测（§2 论证接受；建议合入后补集成测试）。
3. dev Redis ~4 个 `aurora:self_model:{uuid}` 残留键（90d TTL，Leader 择机）。
4. P3-7/P3-8 语义边界登记（处置同意）。

## 7. 结论

R2 全部发现（P1 + P2×4 + P3×4）逐项闭环且以 R2 原始探针与变异手法独立复证：4/4 击杀、2/2 探针过、5 调用点时序读核、patch-树一致、词表哈希不变、主仓 ee885386 合入预演干净。返修自报与实测**零偏差**。

**ACCEPT。**

— R2 深层验收员（delta 复核），2026-09-19
