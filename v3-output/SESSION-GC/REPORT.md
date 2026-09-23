# SESSION-GC — user_sessions 过期清理 Celery 任务 · 交付报告

> 卡面：auth 域会话表行只增不减（AUTH-DEEP REPORT A-2 表末行：live 探针 500 行、12 行 revoked，P2 卫生）。
> worktree：wt232（分支 wt232-session-gc，基线 507070a3）。零 commit 零 push。

## 1. 落地内容

### 1.1 清理任务 `tasks.cleanup_expired_user_sessions`

新文件 `backend/app/tasks/user_session_cleanup.py`，结构完全沿用 `login_attempt_cleanup` 仓库先例（`@shared_task` + `get_db_context` + `asyncio.run` 驱动协程；`max_retries=3, autoretry_for=(Exception,), retry_backoff, acks_late`）。

**删留判据（两侧都过保活期才删）**：

```sql
coalesce(revoked_at, last_active_at) < :cutoff
AND last_active_at < :cutoff        -- cutoff = now - SESSION_TTL_SECONDS
```

- revoked 行：`revoked_at` 与 `last_active_at` 都过 TTL 才删——**刚 revoke 但 TTL 内的行保留**（Redis `session_revoked:{sid}` 标记 TTL 与 SESSION_TTL_SECONDS 同源，TTL 内仍可审计查询）；
- 未 revoke 行：coalesce 自然回退到 `last_active_at`，即停用超 TTL 的死行也回收（refresh token 寿命 = `settings.REFRESH_TOKEN_EXPIRE_DAYS`，与 SESSION_TTL_SECONDS 同一配置源，token 过期且任何真实使用都会经 touch 刷新 `last_active_at`，删除不扩大风险面）。

**TTL 单一事实源**：`SESSION_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400`，与 `app/api/v1/auth.py:78` 同式同源（不从 API 模块反向 import，避免任务层依赖路由层）。

**分批删除**：每批 `select id ... limit 500` → 按主键 `delete ... in` → `commit`（批内短事务、批间释放锁，避免长事务锁表），循环删净为止；`BATCH_SIZE=500`。

**可观测**：清理行数 loguru 日志 + Prometheus 计数器 `sparkle_user_sessions_cleanup_deleted_total`（复用 `app/core/metrics.get_or_create_metric` 全局 metrics 面，记录失败仅告警不阻塞清理）。

### 1.2 调度与路由（双处显式 queue，低_priority 车道）

`backend/app/core/celery_app.py` 三处接线（+12 行）：

| 接线点 | 内容 |
|---|---|
| `conf.include` | 追加 `"app.tasks.user_session_cleanup"`（beat 静态条目引用其任务名，模块必须随 worker 加载，EI-02 守卫语义） |
| `conf.task_routes` | `"tasks.cleanup_expired_user_sessions": {"queue": "low_priority"}`（键=真实任务名，EI-07 语义） |
| `conf.beat_schedule` | `cleanup-expired-user-sessions-daily`：`crontab(hour=4, minute=45)` 日级 + `options.queue=low_priority`（与 04:00/04:30 邻居任务错峰；车道对齐 `cleanup_old_data`/`cleanup_stale_simulation_sessions` 的 maintenance→low 先例） |

### 1.3 迁移评估：不加索引、零迁移（够用不违纪）

- 批量 SELECT 的可 sargable 驱动条件是 `last_active_at < cutoff`，**既有 `ix_user_sessions_last_active_at` 单列索引直接命中**（迁移 `a2d4e6f8b1c3` 已建）；
- `revoked_at` 一侧被 coalesce 包裹（有意为之：从未 revoke 的行也要按停用期回收），任何 `(revoked_at, last_active_at)` 复合索引都无法被该谓词前导使用——加了也是死索引，反而在每次 revoke 时增加写放大；
- 日清循环使过期尾部持续收敛，索引 range scan + LIMIT 500 恒定小代价；live 规模 500 行更无压力。
- **结论：现有索引够用，零 Alembic 迁移，schema 无变更**（DB schema 唯一入口纪律下最小扰动）。

### 1.4 测试（9 条，全绿）

`tests/unit/test_user_session_cleanup_task.py`（5 条）：

1. `test_three_card_classes_delete_keep_boundary` — 卡面三类行：过期 revoked 删 / 活跃留 / 刚 revoke 留；
2. `test_stale_never_revoked_and_ttl_boundary` — 附加类（从未 revoke 停用超 TTL → 删）+ 严格小于边界钉（界内 2s 留 / 界外 1s 删，含 revoked_at 一侧）；
3. `test_batched_deletion_loops_multiple_batches` — `BATCH_SIZE` monkeypatch 为 10，25 行过期经多批删净、3 行在用保留（验证循环多批与终止）；
4. `test_task_wrapper_reports_success_and_increments_counter` — 任务壳 success dict + 计数器增量；
5. `test_task_wrapper_reports_error_on_failure` — 核心抛错返回 error dict（celery autoretry 接管语义不变）。

`tests/core/test_user_session_cleanup_beat.py`（4 条）：include 成员、任务名可注册、beat 单条日级条目显式 queue、task_routes 显式 queue。

**回归（对比法）**：改动面 + 基线 `/tmp` 克隆（HEAD=507070a3）各跑同一切片
（aurora_core_session_entry / auth_refresh_rotation / auth_session_touch / guest_access_ttl_refresh / cache_security_prefix_failclosed / security×2 / auth_login_empty_credentials / release_approvals_authz / celery 双守卫）：

| 面 | 通过 | 失败 |
|---|---|---|
| 基线 HEAD | 102 | 3（celery 守卫 ×3，`ModuleNotFoundError: app.gen`——worktree 未跑 `make proto-gen` 的环境性固有败） |
| 本卡改动后 | 111（+9 新测） | **同一组 3**，零新增失败 |

## 2. Worker 五要素

**① 现状审计**：auth 域此前唯一 retention 任务是 `login_attempt_cleanup`（login_attempts 90 天 GDPR 清理，celery_schedule 注册）；user_sessions 无任何清理路径；`guest_cleanup.py` 两任务无 beat/无路由（既存死挂，未动）。本卡补齐 user_sessions 生命周期管理，判据/TTL/批次按卡面，TTL 锚定 `REFRESH_TOKEN_EXPIRE_DAYS` 单一事实源。

**② 红线面**：分层无触碰（纯 backend tasks 层，无鉴权/AI 逻辑）；**零 proto、零 DB schema 变更**（索引评估结论为不加，见 §1.3）；网关零触碰；beat/路由遵守 EI-02/EI-07/EI-08 三守卫语义（守卫全局断言在本环境因缺 `app.gen` 不可运行，已用等效本地断言钉住本任务接线，合入环境守卫可跑即自动覆盖）；磁盘纪律：唯一临时产物 `/tmp/session-gc-baseline` 克隆（对比法基线），收工已删。

**③ 冲突面**：diff 仅 4 文件——`backend/app/core/celery_app.py`（+12 行：include/routes/beat 各一处）+ 3 个新文件（任务模块 + 2 测试）。`celery_app.py` 是高竞争文件（beat_schedule/task_routes 字典），若在途卡也在该文件加条目，合入时仅可能在相邻行产生 trivial 冲突；与 AUTH-DEEP 后续卡（refresh 503 分级等）无文件交集。

**④ 诚实申报**：(a) 判据用 `coalesce(revoked_at, last_active_at)` 而非字面 `revoked_at < cutoff AND ...`——字面读法下 `revoked_at IS NULL` 的行永不满足第一翼，「行只增不减」只修一半（live 500 行中 488 行是非 revoked）；coalesce 让未 revoke 死行也按停用期回收，安全性论证见 §1.1，**请 Leader 认可此解释，不接受则去掉 coalesce 一行即可收敛为字面语义**；(b) celery 全局守卫三测在基线即败（缺 `app.gen`，非本卡引入，卡面已知固有败清单未列但同性质——worktree 未生成 proto 产物）；(c) 未起 Redis/worker/beat 实进程验证（LIGHT 卡，注册正确性由导入级断言+守卫语义覆盖）；(d) `deleted_at` 软删位与判据正交，过保行无论软删与否一律物理回收（保留期语义）。

**⑤ 收工核查**：零 commit 零 push（`git status` = 1 modified + 3 untracked，均为交付物）；交付物 = 本报告 + `changes.patch`；`/tmp/session-gc-baseline` 已删；无 build/.dart_tool/模拟器/浏览器/常驻进程；主仓与其它 worktree 全程只读未触碰；未动 stash/reset/clean/分支。

## 附：改动文件清单

| 文件 | 变更 |
|---|---|
| `backend/app/tasks/user_session_cleanup.py` | 新增：清理任务（判据/分批/TTL 源/metrics） |
| `backend/app/core/celery_app.py` | +12：include、task_routes、beat_schedule 各一条（双处显式 low_priority） |
| `backend/tests/unit/test_user_session_cleanup_task.py` | 新增：删留边界 5 测 |
| `backend/tests/core/test_user_session_cleanup_beat.py` | 新增：接线 4 测 |
| `v3-output/SESSION-GC/REPORT.md` | 本报告 |
