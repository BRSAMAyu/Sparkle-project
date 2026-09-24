# WT314 · G-04 Galaxy 对 Correction/Delete/Version 的一致性 — REPORT

- **Stream / Gate / Locks**: GALAXY / V3-3 / galaxy-model + privacy-delete
- **base SHA**: `2421a04f`（worktree 创建时 main HEAD）
- **final SHA**: `089dd255`（fix(galaxy): G-04 delete/correction consistency）
- **交付物**: `v3-output/WT314-G04/changes.patch`（与报告一起 commit 进分支 `wt314-g04-galaxy-consistency`）
- **状态**: READY_FOR_REVIEW（LIGHT 任务，全程未触 HEAVY 门）

---

## 1. 缺口清单（修复前，file:line 为 base 2421a04f 上的位置）

重点真源 = galaxy read-model 缓存链（`get_galaxy_graph` @cached(ttl=600) → API 层 shield 10s，键 `{APP}:view:get_galaxy_graph:{user}:*`）与 outcome absorption 链。70eb9b68 修了吸收链的失效缺口；同类缺口清点如下：

### A. 删除路径残影（G-04 卡面核心）

| # | 缺口 | 位置 | 残影形态 |
|---|------|------|----------|
| A1 | `delete_error` 软删后零清理 | `backend/app/services/error_book_service.py:1249-1259` | ① node detail 溯源行（`graph_event_sources.source_type=error_book`）悬空引用已删错题；② `signal:weak_at` 弱点标记不摘除 → 学习状态 WEAK 复活（`schemas/galaxy.py:511` 以该标记判 WEAK）；③ 无读面失效 → `recent_error_count`/review_signal 旧值最长 600s |
| A2 | `delete_draft_node` 删节点后零失效 | `backend/app/services/knowledge_integration_service.py:345-381` | 被删草稿节点在星图读面活到 TTL（600s）——字面意义的残影节点 |
| A3 | `TaskService.delete` 硬删后零失效 | `backend/app/services/task_service.py:1608-1614` | 目标关联（`_get_goal_connected_node_ids` 活查询但外层 @cached 600s）旧值残影 |

### B. 异步事件写路径失效缺口（70eb9b68 同类）

| # | 缺口 | 位置 | 后果 |
|---|------|------|------|
| B1 | `_handle_error_created` 提交后不失效 | `backend/app/services/galaxy_event_consumer.py:103-204` | 新 error-gap 节点/弱点标记/溯源最长 600s 不可见 |
| B2 | `_handle_task_completed` 不失效 | 同文件 :417-424 | 投入分钟/邻居边强/弱点标记最长 600s 不可见 |
| B3 | `_handle_mastery_updated` 不失效 | 同文件 :426-433 | **时序性最差**：它在 `update_node_mastery` 失效**之后**才改边强/标记——若不补失效，读面以旧值回填并存活到 TTL（失效被后写穿越） |

### C. Correction / Version 面清点（结论：既有语义自洽，未动）

- **Correction（错题纠正）**：`update_error` 不可改关联节点（`ErrorRecordUpdate` 无该字段，`schemas/error_book.py:232`）；重分析走 ERR-IDEM 内容指纹幂等键（`error_book_mastery_sync_service.py:99-150`），内容变→新证据生效，分类抖动不绕门。自洽。
- **Version（重放/复活）**：吸收硬门 = append-only `mastery_audit_log` 行（非溯源行、非 snapshot 标记）→ 剪溯源不可能复活点亮（红测 #4 直证）；GHOST-OUTCOME 守卫已阻断已删任务的 outcome 点亮（`test_outcome_absorption.py:426` 基线已有）；极性翻转只写 corrected 溯源、不二次点亮。自洽。
- **memory（episodic）**：galaxy 读面零耦合（galaxy 服务不 import EpisodicMemory，已核）→ 无派生残影面，按卡「按类型处理」记录为 zero-coupling。
- **document**：`document.ontology_created` 溯源以 `(source_type="document", reference_id=file_id)` 落库；文档删除路径尚未落地（SECURITY_PRIVACY 的 tombstone 条目是待建项），通用 handler `handle_reference_deleted` 已预留该面。

## 2. 修法

**新模块 `backend/app/services/galaxy/consistency_service.py`（G-04 一致性面，零新表、零真源重建）**：

- `prune_provenance(user_id, source_type, reference_id, node_ids)` —— 按受影响节点**定界**剪除溯源行（不做全图重建，卡面 work 3）；JSON 拷贝在先、变更落副本（同对象原地变更被 `==` 变更检测吞掉——本 worker 首版就踩了此坑，红测 #1 捕获后修正，`_stamp_absorbed_marker` docstring 警告的同款陷阱）。
- `recompute_weak_signals(user_id, node_ids)` —— 权威判据 = `ErrorRecord.is_deleted` 存活面（与读面 `_get_recent_error_counts_by_node` 同一真源）；无存活错题 → 摘 `signal:weak_at`（走既有 `tag_node_signal`，keywords 集合语义幂等）；判据不可读时保守不摘。
- `handle_error_deleted`（溯源剪除→弱点重算→失效）+ `handle_reference_deleted`（document/translation/outcome_ledger/task_completion 面预留）。
- 失效统一走 NBP-4 canonical `invalidate_galaxy_graph_view_cache`（Redis 视图键 + shield 进程内面）。

**接线（全部 best-effort，删除主流程永不因派生面清理失败）**：A1→`delete_error`（tombstone 前先读关联节点做定界集）；A2→`delete_draft_node`（删前收集全部持状态用户，逐个失效）；A3→`TaskService.delete`；B1-B3→`galaxy_event_consumer` 提交后失效。

**刻意裁决（不回滚已吸收掌握度）**：任务硬删后，真实完成过的学习是已发生事实——mastery/溯源保留；未来点亮由 GHOST-OUTCOME 阻断。审计链（append-only）不剪。

## 3. 测试证据（命令 + 数字）

```
SECRET_KEY=... python -m pytest tests/services/galaxy/test_delete_correction_consistency.py -q
  → 9 passed in 12.67s   （新增：溯源剪除按 reference 定界/不误伤、弱点标记摘除/保留、
    零 sleep 读面新值、剪溯源后重放仍 duplicate（幂等门不在溯源上）、草稿节点即刻消失、
    任务删失效、清理重放安全）
python -m pytest tests/services/galaxy/ tests/unit/test_task_service.py -q → 120 passed
python -m pytest tests/unit/test_errorbook_review_500_fix.py tests/unit/test_evidence_resolve.py
  tests/unit/test_task_service.py tests/unit/test_error_mastery_idempotency.py -q → 34 passed
DATABASE_URL="sqlite+aiosqlite:///:memory:" pytest tests/integration/test_error_link_mastery_e2e.py -q → 2 passed
ruff check <6 改动文件> → All checks passed
mypy app --ignore-missing-imports → 1795 = quality/mypy_baseline.txt（棘轮持平，未推高）
bash scripts/run_all_rule_guards.sh → all rule guards passed (83 rules)，exit 0
```

事件重放验收：吸收重放（duplicate）+ 清理重放（零剪除零写放大）+ GHOST-OUTCOME 基线回归，三类重放均不复活旧状态。

## 4. 兼容性确认

- wt305（焦点随相机、详情减一跳）：纯 mobile 端，本卡零 mobile 改动；后端读面字段（`review_signal`/`user_status`/节点集）语义未变，仅删除/纠正后更快收敛到真值。
- 70eb9b68 吸收失效：未触碰其键面与动作集（lit/flagged）；corrected 保持不失效（溯源-only，读面零变化）。

## 5. 风险

1. `delete_error` 现在多 2 次小事务（溯源剪除 + 弱点标记）——按节点定界，行数 = 错题关联节点数（≤3 关联 + ≤1 gap 节点），量级无虞。
2. 弱点标记挂 `KnowledgeNode.keywords`（全局行、跨用户语义为既有设计）——重算判据按 user 的存活错题面执行，与既有 `tag_node_signal` 写法一致，未改全局语义。
3. B2/B3 的失效在事件消费侧，事件风暴时增加 delete_pattern 流量——与 70eb9b68 已接受的 lit/flagged 失效流量同量级（每事件一次 best-effort 删除）。
4. 文档删除路径落地时须调用 `handle_reference_deleted(source_type="document", reference_id=file_id, node_ids=该文档节点集)`——已预留，防未来再欠账。

## 6. 收工清单

- worktree 内无构建产物/模拟器/独立端口进程；gen 三件套（backend rsync -aL 解引用 + mobile/gen + gateway/gen）仅本地存在（gitignored，不入库）。
- `git status` 干净（除本报告与 patch 已入库）。
