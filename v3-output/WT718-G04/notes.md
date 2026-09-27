# WT718 · G-04 Galaxy 对 Correction/Delete/Version 的一致性 — notes

- **Stream / Gate / Locks**: GALAXY / V3-3 / galaxy-model + privacy-delete（风险 high，需 2 reviewer）
- **分支**: `agent/node-b/wt718/g04`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt718-g04`）
- **base SHA**: `a3764761`（main HEAD，worktree 创建时）
- **worker SHA**: `e824a39f`（fix(galaxy): wt718 G-04 验收补强——跨用户隔离收口 V3-FIX-431）
- **状态**: READY_FOR_REVIEW（卡面 reviewers_required=2，收账/DONE 确认由主会话集成时处理）

---

## 0. 现状双证对照（避免重复实现）

- `git log --all --grep=G-04`：**wt314 已实现本卡主链并落 main** —— `05155fff`（2026-09-24，merge-base 实证为 main 祖先），产出 `backend/app/services/galaxy/consistency_service.py`（provenance 剪除 + 弱点重算 + canonical 失效）与回归测试 `backend/tests/services/galaxy/test_delete_correction_consistency.py`（9 测）。
- `v3-output/WT346-POOL-AUDIT/REPORT.md` 判定表：`G-04 | DONE | 合并 05155fff (wt314) + git×1 + v3-output/WT314-G04`（双证：git + 产出目录）。
- `v3/07_tasks/tasks.json` G-04 status 仍为 TODO —— 与卡池审计结论「tasks.json status 107 张全 TODO 不可信」一致，本卡按双证以「已实现→验收补强」执行，**不重做主链**。

## 1. 跨层变更三段（影响面 / 依赖 / 回退）

**影响面**：后端单模块 `backend/app/services/galaxy/consistency_service.py`（仅 `recompute_weak_signals` 的证据查询 WHERE 与 docstring）；测试单文件 `backend/tests/services/galaxy/test_delete_correction_consistency.py`（+3 测）。零 schema/零迁移/零 proto/零网关/零 mobile 改动；gen 三目录按先例 cp -RL 仅本地存在，未入库。

**依赖**：上游 = wt314 主链（consistency_service + delete_error/event_consumer 接线）与 70eb9b68 NBP-4 失效面；判据真源 = `ErrorRecord.is_deleted` 存活面（与读面 `_get_recent_error_counts_by_node` 同源）；消费面 = `schemas/galaxy.py:548` WEAK 推导（`recent_error_count>0 or signal:weak_at∈keywords or study_count&&mastery<35`，keywords 为全局 `KnowledgeNode` 属性、`recent_error_count` 为 14 天窗 per-user）。

**回退**：单 commit revert `e824a39f` 即回 wt314 行为（字段/接口/签名零变化，`recompute_weak_signals(user_id, node_ids)` 公共签名保持）；无数据迁移、无缓存键变更、无协议变更，回退无残留。

## 2. 本卡补强的缺口（V3-FIX-431）

**缺口**：`signal:weak_at` 挂在**全局** `KnowledgeNode.keywords`（全员共读，WEAK 推导三析取之一），wt314 版 `recompute_weak_signals` 却只按**删除者单用户**的存活错题面裁决摘除。双用户 A/B 同挂存活错题于节点 N 时，A 删掉自己最后一条错题 → 全局标记被摘（实测 `weak_tags_cleared=1`），而 B 的存活证据仍在；当 B 的错题在 `recent_error_count` 的 14 天窗外时，该全局标记是 B 的 WEAK 唯一依据 —— **A 的删除改变 B 的派生学习状态**，违反卡面验收 1「删除后相关 edge/node state 正确；不跨用户泄露」。模块 docstring 自称权威判据=存活面，实际按 user 切片读 —— 全局标记×单用户判据错配。

**修法**：证据查询去掉 `user_id` 过滤，改按节点全量存活错题面裁决（`select(ErrorRecord.linked_knowledge_node_ids).where(is_deleted=false)`，Python 侧按 node_ids 交集，与原实现同款解析）。方向保守：标记存活期只会变长（WEAK 宁多示不误摘）。**溯源剪除/缓存失效保持 user 定界不动**（`UserNodeStatus.user_id==user_id`、`view:get_galaxy_graph:{user}:*`），数据面隔离原样；`handle_error_deleted`/`handle_reference_deleted` 公共签名不变。已知取舍：全量存活面查询一次/每次错题删除（无 user 过滤），量级=错题表存活行数，与读面每次渲染即跑的 per-user 查询同数量级，可接受； wt314 报告风险#2 的「按 user 存活面执行」表述自此修正为「按节点全量存活面执行」。

## 3. 红先行实录

新增 3 测（追加于卡面既有回归文件，验收证据同址）：

| 测试 | 修前 | 修后 |
|---|---|---|
| `test_error_delete_keeps_weak_tag_while_another_user_still_has_live_error` | **RED**（`signal:weak_at` 被摘，日志 `weak_tags_cleared: 1` 实证） | GREEN |
| `test_error_delete_prune_is_user_scoped_other_users_provenance_intact` | GREEN（契约锁，base 即绿，如实标注） | GREEN |
| `test_error_delete_isolated_read_model_other_user_view_unchanged` | GREEN（契约锁，base 即绿，如实标注） | GREEN |

契约锁证明的隔离面：A 的删除只剪 A 的 `UserNodeStatus` 溯源行（B 的原样保留）；A 的视图缓存键失效不清 B 的键；B 读面 `recent_error_count` 零变化。

## 4. 卡验收口径逐条达成

1. **删除后相关 edge/node state 正确；不跨用户泄露**
   - edge/node state 正确：wt314 主链（溯源剪除按 reference 定界、弱点重算、canonical 缓存失效、草稿节点即删即消失、任务硬删失效）+ 本卡跨用户补强（全局弱标记证据判据=全量存活面）。
   - 不跨用户泄露：溯源剪除 `user_id` 定界（契约锁 #1）、读面缓存失效 per-user（契约锁 #2）、弱点标记摘除需全量存活面为空（红测 #1）。
2. **有回归测试与事件重放**
   - 回归：`tests/services/galaxy/test_delete_correction_consistency.py` 12 测（wt314 9 + wt718 3）。
   - 事件重放：吸收重放幂等（`test_provenance_prune_cannot_resurrect_absorbed_light`：剪溯源后重放仍 `duplicate`、不二次点亮——幂等门在 append-only audit 行）+ 清理重放安全（`test_consistency_cleanup_is_replay_safe`：重放零剪除零写放大）+ GHOST-OUTCOME 基线（`test_outcome_absorption.py`，galaxy 套件内全绿）。
   - Correction/Version 面（wt314 已核验，本卡未动）：correction 走 ERR-IDEM 内容指纹幂等、update_error 不可改关联节点；version 复活被 audit 硬门阻断（红测 #4 直证）。

## 5. 门禁数字

```
SECRET_KEY=… DATABASE_URL=sqlite+aiosqlite:///:memory: pytest tests/services/galaxy/test_delete_correction_consistency.py -q
  → 修前 11 passed 1 failed（红）／修后 12 passed
pytest tests/services/galaxy/ -q → 164 passed
pytest tests/unit/test_errorbook_review_500_fix.py tests/unit/test_evidence_resolve.py
  tests/unit/test_task_service.py tests/unit/test_error_mastery_idempotency.py
  tests/integration/test_error_link_mastery_e2e.py -q → 36 passed
pytest tests/unit/test_mirofish_wiring_finish.py tests/services/test_galaxy_learning_graph_operational.py
  tests/unit/test_k6_silent_exception_fix.py tests/unit/test_event_bus_reliability.py
  tests/unit/test_error_book_mastery_sync_service.py -q → 79 passed
mypy app --ignore-missing-imports：修前 147 = 修后 147（stash 对照，错误集 diff 全等，零新增；
  棘轮文件 quality/mypy_baseline.txt=380 为 CI linux 权威口径，本机 macOS 代际差既有）
ruff check 触达 2 文件 → All checks passed
black --check --line-length 120：新增行零 flag（文件仅存 2 hunk 均 wt314 既有版本漂移，
  按 wt382 判例不做全文件重排零无关噪声）
ledger verify：300 行 V3-FIX，裸管分布 {8: 300}，verify 通过零 FAIL
```

网关/mobile：本卡零改动，未跑（无受影响面）。

## 6. 台账与卡状态

- 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 新增 **V3-FIX-431**（P2，FIXED@e824a39f，集成收账时按「集成即纠指针」新规补集成 SHA 双注）。
- `v3/07_tasks/tasks.json` G-04 `status: TODO → done`（JSON 解析验证通过；fleet state 未动，由主会话集成时处理）。
- 稳定性红线遵守：未碰 golden 基线 PNG、未动 `.env`、未动 `v3/.sparkle_v3_fleet_state.json`、未改认证/隔离守卫、未删断言；gen 三目录未入库。
