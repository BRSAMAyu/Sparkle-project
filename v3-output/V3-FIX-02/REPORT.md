# V3-FIX-02 REPORT — 拆除 IsPro=FlameLevel>=3 派生，权益改为独立字段

- 任务：V3-FIX-02（P0，D17 冻结决策）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt8` @ `0cbfd777`
- 交付：本报告 + `changes.patch`（`git add -N` 后 `git diff`，已扫描无 .env/密钥/凭据）
- 结论：**READY_FOR_REVIEW**。红→绿完成，迁移已应用共享 dev DB，SQLC 已重生成。

## 1. 变更总览

| 层 | 文件 | 变更 |
|---|---|---|
| 迁移 | `backend/alembic/versions/ent01_20260919_add_user_entitlement.py`（新增） | `users` 加 `entitlement varchar(32) NOT NULL DEFAULT 'free'`，`down_revision=ud01_20260919` |
| 网关 | `backend/gateway/internal/service/user_context.go` | 新增 `EntitlementFree/EntitlementPro` 常量与 `IsProEntitlement()`；`GetChatUserProfileSnapshot` 的 `IsPro: user.FlameLevel >= 3` → `IsPro: IsProEntitlement(user.Entitlement)` |
| 网关 | `backend/gateway/internal/handler/chat_orchestrator_chatflow.go` | fallback 同式 `fallbackUser.FlameLevel >= 3` → `service.IsProEntitlement(fallbackUser.Entitlement)` |
| 网关 | `backend/gateway/internal/db/{schema.sql,models.go,query.sql.go}` | schema.sql 快照重生成 + `sqlc generate`（`db.User.Entitlement string`） |
| 引擎 | `backend/app/models/user.py` | User 模型加 `entitlement = Column(String(32), default="free", nullable=False, server_default="free")` |
| 引擎 | `backend/app/services/user_service.py:208` | `is_pro=user.flame_level >= 3` → `is_pro=(user.entitlement or "free").strip().lower() == "pro"` |
| 引擎 | `backend/app/services/agent_grpc_service.py` | 仅注释：`_resolve_request_user_tier` 文档串中派生链描述改为 `users.entitlement` |
| 测试 | `backend/gateway/internal/handler/chat_orchestrator_helpers_test.go` | 新增 flame=15 红→绿测试；`TestBuildAgentUserProfileFallsBackToResolvedUser` 更新为 entitlement='pro' 语义 |
| 测试 | `backend/tests/unit/test_user_service.py` | 新增 flame=15 与 entitlement='pro' 两条测试 |

proto 不动：`UserProfile.is_pro`（agent_service.proto:140）仍是过界信号，仅取值来源改为 entitlement 字段，符合 D17（不改 proto，消费端零改动）。

## 2. 红绿证据（红测先行）

### RED（改动前，两路均失败）
1. Go（`CGO_ENABLED=0 go test ./internal/handler/ -run TestBuildAgentUserProfile`）：
   ```
   --- FAIL: TestBuildAgentUserProfileFlameFifteenGuestIsNotPro
       chat_orchestrator_helpers_test.go:334: expected is_pro to be false for flame_level=15 user without pro entitlement
   ```
   （构造 `db.User{FlameLevel: 15}` 游客，旧实现 `flame_level>=3` → IsPro=true，断言 false 失败）
2. 引擎（`pytest tests/unit/test_user_service.py -k flame_fifteen`，sqlite 内存基座）：
   ```
   assert context.is_pro is False
   E   AssertionError: assert True is False
   ```

### GREEN（改动后）
1. Go 定向包：`TestBuildAgentUserProfile*` 3/3 PASS；`go build ./...` 通过；
   `CGO_ENABLED=0 go test ./internal/...` → 8 包 ok；`internal/config` 1 例失败为
   **预存环境依赖**（缺 `JWT_SECRET` 环境变量，注入后 ok；本卡未触碰该包，master 同样失败）。
2. 引擎定向文件：`pytest tests/unit/test_user_service.py` → **8 passed**（含 2 条新测试）；
   相邻 `tests/test_user_service_get_by_email.py` 1 passed。

## 3. 迁移内容与执行状态

- 列：`entitlement character varying(32) DEFAULT 'free'::character varying NOT NULL`
- **已执行** `alembic upgrade head`（wt8 worktree，经 wt7 venv→后因 wt7 venv 被清，
  改用本 worktree 内 `.venv`，仅 interpreter 复用，未写主仓/主仓 venv）：
  - 共享 dev DB `sparkle`：`ud01_20260919 → ent01_20260919`，`alembic current = ent01_20260919 (head)`
  - 验证（只读 SELECT）：information_schema 确认列存在；`SELECT entitlement, COUNT(*) FROM users` → **248 行全部 'free'**（guest/seed/email 一视同仁）
- schema.sql 快照按 R2-08-06 规程从一次性 fresh 迁移库 `sparkle_syncdb_fresh` 导出
  （全链 142 迁移从零重放成功），导出后 scratch 库已 DROP。快照 diff 除新列外，
  还补进了链上已有但旧快照缺失的 `understanding_depth_daily` 表（ud01，快照时滞，属管线正常产物）。

## 4. SQLC 状态

**已重生成，无需主会话再跑**：`make sync-db` 管线在本 worktree 等价手测完成
（db-migrate → 等价 db-dump → `sqlc generate`），`db.User.Entitlement string` 已入
`models.go`，`GetUser/GetUserByEmail/CreateUser/UpdateUser...` 全部显式列清单已带
`entitlement`。主会话合入后重跑 `make sync-db` 应为零 diff（幂等）。

**部署告警（重要）**：`GetUser*` 为 `SELECT *` 显式扫描，列数不匹配会在运行期报错。
dev DB 已加列，故**任何由旧 SQLC 产物构建的网关二进制在重编译前对 users 表查询会失败**。
合入本 patch（含重生成产物）并重建网关即恢复；请在合并窗口内尽快重建网关进程。

## 5. 语义变化（明示）

1. **游客从 pro 层降回 free 层**：`guest_seed_service.py:1486` 仍写 flame=15（展示层
   动机不变），但游客 is_pro 不再为 true → `llm_router` 请求级 tier 钳制
   （`agent_grpc_service._resolve_request_user_tier`）将游客钳到 free 模型层。
   这是 D17 目标态：166/166 游客走 pro 层属 bug 行为。**guest_seed_service 本身不需要改**。
2. **存量真实用户全部回到 free 层**：迁移将 248 行（含 email 用户）置 'free'。
   此前 75/75 真实 email 用户被 flame 派生压在 free 层，行为不变；若有本应 pro 的
   付费用户，需后续运营位显式 UPDATE entitlement='pro'（本卡不含此回填，值域已留位）。
3. **flame_level 保留为展示层字段**：`community.py` 徽章阈值（>=5/>=8）、
   `user_service` engagement 分级（>=5/>=3/>=2）等非权益用途全部未动。
4. 判据语义：`'pro'`（大小写/首尾空格容忍）→ pro；其余任何值（含 NULL 防御）→ free，默认安全。

## 6. 验证补充

- 引擎测试基座为 sqlite 内存（`tests/conftest.py`），全程未向 dev DB 写业务数据；
  对 dev DB 仅有一项写操作即 alembic 迁移本身，其余为只读 SELECT/pg_dump。
- 风格：gofmt 0 diff；ruff 对新迁移文件 clean（`tests/unit/test_user_service.py`
  剩余 I001 为预存 import 顺序问题，未触碰）；`user_service.py` 等 3 文件 black
  不达标为 HEAD 预存基线（HEAD 版本同样不达标，且 black hunk 不在本卡改动行）。
- 环境说明：本机无后端 venv（wt7 venv 中途被舰队清理），故在 worktree 内自建
  `.venv`（uv + pypi.org，阿里云镜像 403）；`backend/gateway/gen/`（pb 生成物，
  git 不可见）从 proto/ 完全一致的 wt7 复制以满足编译。这两项均为 worktree 内临时产物。

## 7. 收工清理

- [x] scratch 库 `sparkle_syncdb_fresh` 已 DROP
- [x] 无独立端口进程遗留（未起网关/引擎服务，测试全为进程内）
- [x] `/tmp/v3fix02-*` 临时文件清理（见收工命令）
- [x] worktree 内 `.venv` 删除（磁盘回收 ~1.2G；gen/ 与测试产物随 worktree 生命周期回收）
- [x] 未 commit/push；主仓零写入
