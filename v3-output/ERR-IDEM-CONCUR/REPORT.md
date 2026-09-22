# ERR-IDEM-CONCUR · 错题幂等毫秒窗口收口（audit 唯一索引迁移）— 收工报告

- Worker：V3 舰队 Worker（ERR-IDEM-CONCUR 卡）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt138`（基线 a1572cfa，含 ERR-IDEM a4ed7493）
- 日期：2026-09-23
- 交付物：
  - `backend/alembic/versions/erridemconc_20260922_mastery_audit_idem_unique.py`（新增，迁移）
  - `backend/app/services/galaxy_service.py`（修改，写侧冲突仲裁）
  - `backend/app/services/error_book_mastery_sync_service.py`（修改，duplicate 语义分支）
  - `backend/tests/unit/test_error_mastery_concurrency.py`（新增，并发绿证）
  - `backend/tests/unit/test_galaxy_service_audit_idem_duplicate.py`（新增，写侧契约直测）
  - `backend/tests/unit/test_erridemconc_mastery_audit_idem_unique_migration_sqlite.py`（新增，迁移重放）
  - 本报告 + `changes.patch`
- 未 commit / 未 push（纪律遵守）；**未动活库**（sparkle_db 只读 SELECT，迁移由合入方执行）

---

## ① 红证：毫秒窗口并发双扣（修复前）

**探针**（/tmp，跑在未修复 wt138 代码上，已清理）：ERR-IDEM 同构 harness（sqlite 内存库 + 与 galaxy_service 第 B 步同契约的写入桥）+ `asyncio.Barrier` 把「两个请求都过读侧门、彼此都还没写审计行」的亚毫秒窗口放大成确定性交错点，`asyncio.gather` 两个同键 `apply_error_diagnosis`：

```text
=== ERR-IDEM-CONCUR 红证（修复前） ===
读侧门通过次数        : 2
并发请求1 生效条数     : 1 delta=-8
并发请求2 生效条数     : 1 delta=-8
最终 mastery_score     : 34.0  (初始 50, 单扣应为 42)
审计行数（同键）       : 2
  audit: edi:5c01faf84e364ccc809993ba00048efd:d90c7fa3:2112c07aa0b34fde8a7695c07406c1d9 50->42
  audit: edi:5c01faf84e364ccc809993ba00048efd:d90c7fa3:2112c07aa0b34fde8a7695c07406c1d9 42->34
判定: RED — 毫秒窗口并发双扣复现
```

根因确认：ERR-IDEM 的门是**读侧先查重**（`_sync_already_applied` SELECT），两请求在窗口内都读到「未吸收」→ 双写双扣、同键审计行 ×2。

**灵敏度验证**（防绿证空洞）：把交付测试的写入桥换成真实 `GalaxyService.update_node_mastery`（不 stub 审计行）。临时把写侧修回「普通 INSERT 无冲突处理」（单文件粒度改动、备份还原）→ 交付测试立刻红：

```text
E  sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed:
   mastery_audit_log.user_id, mastery_audit_log.node_id, mastery_audit_log.request_id
```

即：只有索引没有冲突处理时，竞态败者直接 500；测试对两种残缺形态都能抓。

## ② 方案裁决：唯一**部分索引** `(user_id, node_id, request_id) WHERE request_id LIKE 'edi:%' OR 'erv:%'`（否决全列唯一 / 新列）

**request_id 取值域证据（全库代码面 + 演示库只读 SELECT，2026-09-23）：**

| 命名空间 | 写入方 | 演示库实测 |
|---|---|---|
| NULL | Galaxy REST `/sync/mastery`、`/node/{id}/mastery` 等不传 request_id | 45 行 |
| 裸 task_id | `stats_service`（task_complete，`str(task_id)`） | 20 行 |
| `sprint_task_completed:{task}:{node}` | `task_service.py:984` | 有 |
| `obs=..;conf=..;oc=<32hex>[;tk=..]` | `outcome_absorption_service._evidence_request_id`（G-01 证据账本） | 2 行 |
| gRPC 客户端自由串 | `galaxy_grpc_service.py:154,185`（透传 `request.request_id`） | 有 |
| `focus session_id` / aurora `request_id` | focus_service / aurora runtime | 有 |
| 旧格式 `error_diagnosis:{err}:{node}` | ERR-IDEM 前的历史格式 | 演示库中即 3 组重复三元组 |
| `edi:` / `erv:` | ErrorBookMasterySyncService（ERR-IDEM） | 0 行（未部署） |

- **全列唯一否决**：gRPC 客户端自由 request_id 会被去重吞写；演示库**非管辖域已存在 3 组重复 (user,node,request_id) 三元组**（旧格式历史 double-write），全列索引在存量数据上根本建不起来，且会改写 4 个无辜写入方的语义。
- **新列（idempotency_key）否决**：需要动全部写入方 + 读侧门查询 + 新列迁移；部分索引以零列变更达成同等约束，键域与读侧门（`WHERE user_id AND node_id AND request_id`）严格同域。
- **选中**：`CREATE UNIQUE INDEX uq_mastery_audit_log_idem_key ON mastery_audit_log(user_id, node_id, request_id) WHERE request_id LIKE 'edi:%' OR request_id LIKE 'erv:%'`——只约束 ERR-IDEM 幂等键，其余取值域零影响；NULL/域外重复对不归它管（演示库实测域外重复对原样存活，迁移测试锁定该行为）。

## ③ 写入侧改造：冲突即「已吸收」，与读侧门命中同结局

`galaxy_service.update_node_mastery` 第 B 步（唯一真实 edi/erv 审计写入口）：

```sql
INSERT INTO mastery_audit_log (...)
VALUES (...)
ON CONFLICT DO NOTHING
RETURNING id
```

- RETURNING 无行 **且** request_id 带 `edi:`/`erv:` 前缀 → `await self.db.rollback()`（掌握度变体、stats、outbox 全部不落账）→ 返回 `{"success": False, "reason": "duplicate"}`。与上方 revision-conflict 路径同一恢复方向。
- GUID-typed bindparams（`outcome_absorption_service` 同款惯例）：asyncpg 原生绑 UUID、aiosqlite 绑 str，PG 语义不变。
- 其他写入方：非 edi/erv 命名空间不进部分索引谓词 → INSERT 永不冲突 → 行为逐字节不变（gRPC `success=False, reason="duplicate"` 走既有失败分支，形状同 stale_update，无契约破坏）。
- `ErrorBookMasterySyncService._update_node_mastery`：`reason == "duplicate"` 走 info 日志（「lost write-side idempotency race」）→ 返回 None——调用方拿到与读侧门命中完全相同的「本次无变化」，无新增分支语义。
- 读侧门原样保留（快路径：串行重放不触达写侧，交付测试锁定）。

## ④ 迁移细节（合入方执行）

- 文件：`erridemconc_20260922_mastery_audit_idem_unique.py`，`down_revision = "cp01confirm_20260922"`；`alembic heads` 单头 `erridemconc_20260922`（本机已验）。
- **合入方步骤**（活库我只读，未动）：
  1. 合入 patch；
  2. `cd backend && alembic upgrade head`；
  3. 验证：`SELECT indexname FROM pg_indexes WHERE indexname='uq_mastery_audit_log_idem_key';` 应恰一行。
- 迁移内容：先收敛存量（DELETE … NOT IN (SELECT MIN(id) … GROUP BY user_id,node_id,request_id)，保留最早=首个生效证据，删除后来者=并发双写污染；PG/SQLite 双方言可移植写法），再建唯一部分索引（`IF NOT EXISTS`，可重入）。downgrade 仅 DROP INDEX。
- **存量申报（演示库只读实测）**：93 行审计中 edi/erv 行 0、管辖域内重复 0 → 索引当下可无损创建；域外另有 3 组旧格式重复三元组（`error_diagnosis:{err}:{node}` 历史 double-write，对应已在历史上发生的重复扣分）——**不在本索引管辖域**，是否清洗属独立决策（删除审计行不追溯修复已扣的掌握度），合入方裁决，本迁移不碰。
- sqlite 兼容性：部分索引 + LIKE 谓词 + `ON CONFLICT DO NOTHING RETURNING` 均为 PG/SQLite 双支持（本地 sqlite 3.53 验证；`ON CONFLICT DO NOTHING` 无 target 形态可命中部分索引）。

## ⑤ 回归矩阵（全绿）

| 套件 | 结果 |
|---|---|
| **新增** 并发绿证（双 session + Barrier + 真实 GalaxyService 写路径）：同键诊断恰一扣 50→42、同键复盘恰一升 42→46、败者结局==读侧门命中、串行重放读侧快路径 | 4/4 passed |
| **新增** 写侧直测：同键 edi/erv → duplicate、掌握度保持胜者值、审计不重复；跨节点同源键不误伤；裸 task_id/NULL 重复不受影响 | 4/4 passed |
| **新增** 迁移 sqlite 重放（test_cp01 模式）：存量收敛保留最早、域外零影响、索引违约 + ON CONFLICT 契约、round-trip 可重入 | 4/4 passed |
| **ERR-IDEM 8 测试**（无回归红线） | 8/8 passed |
| error/absorption 域定向（对比法）：error_book_mastery_sync_service、error_mastery_loop、sprint_galaxy_mastery、outcome_absorption、outcome_read_model_visibility、mastery_evidence、error_book_galaxy_mastery_sync 集成 | 129/129 passed |
| task_galaxy_coupling + error_link_mastery_e2e + stage35 smoke | 7/7 passed |
| `alembic heads` | 单头 `erridemconc_20260922` ✓ |

**环境性既有失败（与本卡无关，诚实申报）**：`tests/unit/test_galaxy_concurrency.py` 3F+3E，全部为 `asyncpg InvalidPasswordError`（该文件连真实 PG，worktree 无 .env；失败发生在任何业务代码执行之前；本卡 diff 未触碰该文件）。

## ⑥ 冲突面

- **本卡改动面**：`error_book_mastery_sync_service.py`（+17 行语义分支）、`galaxy_service.py` 第 B 步（+44/-4）+ 3 个 import、1 个新迁移、3 个新测试文件。
- **wt137（event 消费面）**：消费 `node_mastery_updated` 事件，不读 `update_node_mastery` 返回值、不写审计行 → 无冲突。
- **wt139（mobile）**：经网关调 `/errors/{id}/analyze` 与 review 端点，响应契约未变（重复分析照样 200、结果为空集语义与 ERR-IDEM 一致）→ 无冲突。
- **wt136（测试域）**：未触碰其改动文件；`test_galaxy_concurrency.py`（真实 PG 依赖）为既有环境失败，非本卡引入。
- ERR-IDEM 已合入（a4ed7493 在基线内），无在途冲突。outcome_absorption/stats_service 的审计写入是独立命名空间，行为不变。

## ⑦ 诚实申报

1. 存量：演示库管辖域内 0 重复（可无损建索引）；域外 3 组旧格式重复对未处置（见 ④，超范围）。
2. 活库未动（只读 SELECT ×4 次取值域取证），迁移留合入方。
3. 并发绿证用 sqlite 文件库双连接建模生产并发：`Barrier` 放大交错窗口为确定性；胜者/败者交错无关断言（谁先落账都恰一扣）。PG 真机语义由同一代码路径覆盖（ON CONFLICT RETURNING 双方言成立），但**真 PG 上的端到端并发演练未做**（活库只读纪律），合入后建议以 staging 压一轮同错误并发 analyze。
4. 灵敏度实验中曾单文件临时改写 galaxy_service（备份→改→还原→diff 核对），最终 diff 只含交付改动。
5. worktree 曾缺 `app/gen/`，已按卡从主仓拷贝（gitignored，不入 patch）。

## ⑧ 收工核查

- [x] 未 commit / 未 push
- [x] 活库与主仓只读（SELECT 取值域 ×4，无任何写）
- [x] /tmp 探针与备份（`/tmp/erridemconc_red/`）已清理
- [x] 交付物零凭据（连接串/密码未出现在本报告与 patch）
- [x] 新文件走 `add -N → diff → git reset -q`（patch 内 `--- /dev/null` 头）
- [x] 内存纪律：无 HEAVY 任务（纯 sqlite 单进程测试，峰值 <1G）
