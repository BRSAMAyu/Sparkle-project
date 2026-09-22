# D-COMM-3 · 冲刺小队 MVP（社群×exam_sprint 首联动）

- Worker：D-COMM-3 ｜ worktree：`wt157` ｜ 基线：`52fe93a7`（收工时工作树仅含本卡改动，未 commit）
- 设计依据：`v3-output/D-COMMUNITY/DESIGN.md` §3.3 + D-COMM-3 卡（P1）；裁决 MVP 范围=**冲刺完成度单口径**（sprint_task_ledger），XP/光子禁入。

## 一、交付物清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/schemas/community_squad.py` | 新增 | 小队 schemas（SquadCreate 3-8 人收敛、SquadMemberSprintProgress 含空数据诚实标记 `has_ledger_data`） |
| `backend/app/services/community_squad_service.py` | 新增 | SquadService：小队门面 + 成员冲刺完成度跨用户只读聚合 |
| `backend/app/api/v1/community_squad.py` | 新增 | 7 端点，独立路由文件（community.py 5111 行结构债，新端点不增重存量） |
| `backend/app/api/v1/router.py` | 修改（+3 行） | 注册 `community_squad.router` 至 `/community` 前缀 |
| `backend/gateway/internal/handler/proxy_routes.go` | 修改（+10 行） | 网关代理 `/community/squads/**` 7 条路由（proxyWithHeaders，auth 中间件继承） |
| `backend/gateway/internal/handler/proxy_routes_dcomm3_test.go` | 新增 | 网关路由钉住测试（防 404 回归） |
| `backend/tests/unit/test_community_squad_mvp.py` | 新增 | 12 用例：CRUD/聚合口径/非成员 403/空数据诚实/XP-photon 禁入双断言 |

端点面（引擎 REST，网关一一对应代理）：
`POST/GET /community/squads`、`GET /community/squads/{group_id}`、`POST .../join`、`POST .../leave`、`GET .../members`、`GET .../sprint-progress`。

## 二、Worker 五要素

### ① 复用 vs 新表裁决论证 —— **复用 Group(type=SPRINT)，零迁移**

- 模型层早已具备：`app/models/community.py::GroupType.SPRINT`（"冲刺群（短期）"）+ `Group.deadline`/`sprint_goal` 字段 + `GroupMember` 角色/软删；
- 迁移层早已具备：PG 基线 `alembic/versions/cc9383c4c29f_full_baseline_schema.py` 的 `groups.type` 即 `Enum('SQUAD','SPRINT','OFFICIAL', name='grouptype')` —— sprint 值**已在生产枚举内**，无需 ALTER；
- schema 层早已具备：`schemas/community.py::GroupTypeEnum.SPRINT`、`GroupCreate` 支持 sprint 专用字段校验；
- 因此新表（squad/squad_member）是第二套群组语义，徒增迁移与对账成本。裁决：**小队=既有 Group 的一类 type**，本卡服务层只做场景约束（3-8 人、deadline 必填、仅冲刺周期可见/可加入），通用群组行为（软删、成员上限 `with_for_update` 锁、群主先转让、`joined_at` 排序）一律委托既有 `GroupService`，不复制第二套逻辑。
- `alembic heads` 收工验证：唯一 head `erridemconc_20260922`，本卡零迁移，无需 sqlite 重放。

### ② 完成度口径证据（不读 XP/photon）

- **口径来源唯一**：`SquadService.get_squad_sprint_progress` 对每在册成员调用 `sprint_task_ledger.fetch_sprint_ledger_tasks` + `build_ledger_task_stats`（BP-4 单一事实源：账本全集=该成员全部未删除任务，completed=status==COMPLETED，跨 plan/无 plan 全可见）。这是 P1-4 卡裁决的「sprint-completion 唯一定义点」，本卡是它的第一个跨用户消费面。
- **结构断言**：`test_squad_modules_import_scan_no_xp_photon_leaderboard` 用 AST 解析两个新模块的全部 import，断言零 `photon/experience/leaderboard/xp` 域导入；`test_squad_service_must_consume_ledger_ssot` 钉死服务层必须显式 import `sprint_task_ledger`。
- **行为断言**：`test_progress_indifferent_to_photon_and_flame_mutations` 把成员 `photon_balance` 拉到 999999、`flame_level` 改到 99/42，聚合逐字段（total/completed/rate/has_ledger_data）不变——若聚合读了行为量，此处必漂移。
- **空数据诚实语义**：无任务成员返回 `task_total=0, completion_rate=0.0, has_ledger_data=False`——明确表达「账本还没有数据」，不把 0 伪装成「0% 完成率」。

### ③ 冲突面声明

- **本卡触碰面**：`app/api/v1/router.py`（注册行）、`app/api/v1/community_squad.py`（新）、`app/schemas/community_squad.py`（新）、`app/services/community_squad_service.py`（新）、`backend/gateway/internal/handler/proxy_routes.go`（community 段 +7 条路由）、两个新测试文件。**未触碰** leaderboard 数据源、photon/entitlement、events、accountability、群消息/打卡路径。
- **wt155（排行榜）**：无交集。设计卡 3.2「小队榜」属 D-COMM-4（P2，依赖本卡），本卡只提供 sprint-progress 聚合端点，未动 `leaderboard_service` 与 `MyRankResponse`。若 wt155 也在改 leaderboard 的榜型枚举，与本品无文件冲突。
- **wt156（光子）/wt144（events）**：无文件交集；本卡红线恰是**不读**光子与 XP，双方领域隔离。若其测试断言全仓 import 图，注意本卡新增了三个不 import 行为量域的模块（已在 AST 断言中自证）。
- **网关 proxy_routes.go**：wt 系列若有人并行增删 community 段路由（如 R2-08 后续），合并时以行段为准，本卡改动全部带 `// Sprint Squads (D-COMM-3 ...)` 注释锚点。

### ④ 诚实申报

1. **「仅冲刺周期可见」的落地口径**：deadline 已过 → 小队从「我的小队」列表消失、join 被拒（400）；但详情/成员/完成度对**在册成员**仍可读（`sprint_active: false` 诚实上报）——冲刺结束仍允许队友回看最终完成度，是 MVP 的有意取舍；非成员全程不可见。若产品要求到期即全隐，是服务层一行过滤的后续改动。
2. **重加入缺口（既有债务，本卡未修）**：社群既有软删惯例（`deleted_at` 置位）+ `group_members(group_id,user_id)` 唯一键 → 退出后重加入会撞唯一键被当作「已是成员」。此缺口在既有 `/community/groups` join/leave 同样存在，属社群域既有债务，本卡照惯例继承未扩大；建议单开债务卡（迁移动唯一键或软删时改写键）。
3. **审批入队未做**：`join_requires_approval` 小队固定 False（MVP 直接加入），schema 字段保留给后续卡。
4. **聚合取数为逐成员 N 次查询**（N≤8，小队上限内）：MVP 可接受；成员扩容或高频轮询时应改单查询聚合（ledger 条件可 OR 拼接），已留待后续。
5. **worktree 环境处置**：worktree 缺 gitignored 的 gen 产物（`backend/app/gen`、`backend/gateway/gen`），自主仓**只读拷贝**进 worktree 以跑通全量路由导入与 go test；属 gitignored 构建产物，不入 patch、不入库。macOS 无 `timeout` 命令，用 pytest-timeout（`--timeout=90`）+ Bash 工具 timeout 兜底。
6. **网关全量 `go test ./...` 中的 `internal/config` 失败为环境缺省**（JWT_SECRET/RS256 PEM 未设），在基线克隆同样复现，非本卡引入；补 `JWT_SECRET`+`GO_ENV=development` 后网关全量通过。

### ⑤ 收工核查

- [x] 未 `git commit`/`git push`；主仓全程只读（gen 产物为读取拷贝，零写主仓）
- [x] 改动全部在 wt157；`git status` 仅本卡 2 改 + 5 新（见 patch）
- [x] 新测试 12/12 绿；社群域+ledger 域定向回归 99 passed/2 skipped，与基线克隆（52fe93a7 纯 HEAD）对比**零新增失败**
- [x] 网关：新增 7 路由钉住测试过；`CGO_ENABLED=0` 全量绿（补 env 后）；`go vet` 干净
- [x] 既有社群 111 条路由零删改（路由计数器验证：111 既有 + 7 新增）
- [x] 无凭据/无 .env/无生产配置入 patch；测试用 `DATABASE_URL=sqlite+aiosqlite:///:memory: SECRET_KEY=test`
- [x] /tmp 清理：`/tmp/wt157-baseline-dcomm3` 已删；无模拟器/无长驻进程/无 HEAVY 任务

## 三、回归证据（定向对比法）

| 批次 | 选择器 | 本卡改动后 | 基线（52fe93a7） |
|---|---|---|---|
| 新测试 | `tests/unit/test_community_squad_mvp.py` | 12 passed | （不存在，TDD 新增） |
| 社群单测族 | template_injection / privacy_fv05 / service_group_tasks / signal_kill_switch / privacy_production / context_manager_community | 37 passed | 同绿（并入下方合计） |
| ledger 域 | test_sprint_task_ledger + exam_sprint_dashboard_service + exam_sprint_review_service | 5+2+15 passed | 同绿 |
| 社群安全/API 面 | test_community_security + test_exam_sprint_api | 12+7 passed | 同绿 |
| 社群 E2E/integration | test_community_e2e + test_community_integration | 14 passed/2 skipped | 同绿 |
| **定向合计对比** | 12 文件选择器（新测试除外） | **99 passed / 2 skipped** | **99 passed / 2 skipped**（零差异） |
| 网关 | `go test ./internal/handler/ -run TestProxyRoutes`（CGO_ENABLED=0） | ok（含新钉住测试） | ok |
| 路由健全性 | api_router 全量导入 + 路由计数 | 111 既有社群路由不变 + 7 新增，无碰撞 | 111 |

风格：ruff（I001/C408 修复后 All checks passed）+ black --line-length 120 全过。
