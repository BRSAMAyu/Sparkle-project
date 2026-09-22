# D-COMM-4 · 共学自习室（在场证明）+ 小队榜

- Worker：D-COMM-4 ｜ worktree：`wt158` ｜ 基线：`7d8a828d`（含 D-COMM-3 冲刺小队）｜ 未 commit
- 设计依据：`v3-output/D-COMMUNITY/DESIGN.md` §3.3（自习室）+ §3.2/§5 D-COMM-4 卡（小队榜）
- 交付物：`REPORT.md`（本文）+ `changes.patch`（新文件 `--- /dev/null` 头，已验在基线克隆可干净 apply）

## 一、交付物清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/models/study_room.py` | 新增 | `StudyRoomSession`（一条记录=一次进出场；部分唯一索引 `uq_study_room_open_session` 双方言等价：`sqlite_where`+`postgresql_where`） |
| `backend/alembic/versions/dc4room_20260922_study_room_sessions.py` | 新增 | 迁移挂唯一 head `erridemconc_20260922`；含 Migration Contract；upgrade/downgrade 双向在 sqlite 隔离验证通过 |
| `backend/app/models/__init__.py` | 修改（+3 行） | 登记 `StudyRoomSession`（import + `__all__`） |
| `backend/app/schemas/community_study_room.py` | 新增 | 进出/心跳/在室视图 schemas（含 `STUDY_ROOM_STALE_MINUTES=15`） |
| `backend/app/services/community_study_room_service.py` | 新增 | `StudyRoomService`：enter（幂等）/exit（幂等诚实）/heartbeat（兜底）/presence（谁在自习+今日累计） |
| `backend/app/schemas/community_squad_board.py` | 新增 | 小队榜 schemas（rank 并列名次、percentile 区间、`board_valid`/`self_view_only`） |
| `backend/app/services/community_squad_board_service.py` | 新增 | `SquadBoardService`：D-COMM-3 聚合面的排序+分页包装（零新口径） |
| `backend/app/api/v1/community_study_room.py` | 新增 | 4 端点，独立路由文件（照 D-COMM-3 先例，不增重 community.py） |
| `backend/app/api/v1/community_squad_board.py` | 新增 | 1 端点（GET leaderboard） |
| `backend/app/api/v1/router.py` | 修改（+5 行） | 注册两个新 router 至 `/community` 前缀 |
| `backend/gateway/internal/handler/proxy_routes.go` | 修改（+11 行） | 网关代理 5 条新路由（proxyWithHeaders，auth 继承，带 D-COMM-4 注释锚点） |
| `backend/gateway/internal/handler/proxy_routes_dcomm4_test.go` | 新增 | 网关 5 路由钉住测试（防 404 回归） |
| `backend/tests/unit/test_community_study_room.py` | 新增 | 13 用例（见 §四） |

端点面（引擎 REST，网关一一对应代理）：
`POST /community/squads/{group_id}/study-room/enter`、`POST .../exit`、`POST .../heartbeat`、
`GET .../study-room/presence`、`GET /community/squads/{group_id}/leaderboard`。

## 二、Worker 五要素

### ① 复用 vs 新表裁决

- **自习室：社群域无可复用的 presence/session 结构，最小新表**。逐项排查：
  `GroupMember.last_active_at`（`models/community.py:275`）是成员级单时间戳，无会话边界、算不出时长；
  `models/focus.py::FocusSession` 是个人番茄钟**结算**记录（写入即要求 end_time/duration_minutes，
  无 group_id，撑不起「谁正在自习」的活体在场面）；`User.status`（UserStatus online/offline/invisible）
  是全局在线状态，非小队作用域；`agent_run.heartbeat_at` 跨域不适用。故按设计卡 §3.3
  「落库最小记录」立 `study_room_sessions`；会话记录不可复用 ⇒ 迁移不可避免，挂唯一 head。
- **成员/小队鉴权：全额复用 D-COMM-3**。`SquadService._get_active_squad`（404 不泄露存在性）+
  `_require_active_member`（非成员 403）；自习室与榜单零自有鉴权逻辑。
- **时区日界：复用督促域口径而非代码**。「今日」按成员本地日界（`push_preference.timezone`，
  缺省回落 `Asia/Shanghai`，naive-UTC 存储）——与 `api/v1/accountability.py::_user_timezone`/
  `_day_range_for_timezone` 同口径；但以纯函数就地实现（`get_user_timezone` 直查 PushPreference），
  理由见 §四-3。
- **小队榜：零新口径、零新表、零迁移**。唯一消费 `SquadService.get_sprint_progress`
  （即 `get_squad_sprint_progress`，其口径唯一来自 `sprint_task_ledger`，BP-4 SSOT），
  本卡只加排序（完成率↓ → 完成数↓ → 有账本优先 → user_id 定序）、并列名次（竞赛排名 1,1,3）、
  percentile 区间、limit/offset 分页（名次全集计算后切片）、<3 人降级标记。

### ② 实现清单（两件的语义要点）

**共学自习室（beacon 式在场，显式进出为主、心跳兜底；无音视频/屏幕共享）**：
- `enter`：记录 entered_at；**幂等**——已有开放会话（含 stale）只刷新心跳并返回 `reentered=true`，
  不建重复记录；`exit`：置 exited_at、结算本次分钟数（防时钟回拨）；**幂等诚实**——无开放会话
  返回 `already_out=true` 不报错不造记录；`heartbeat`：在场刷新 last_heartbeat_at，不在场如实
  上报 `in_room=false`（不自动重开）。
- `presence`：全体在册成员 + `in_room`/`is_stale`（心跳 >15 分钟）/当前会话分钟/今日累计分钟；
  未入场成员如实列 0（设计裁决：不惩罚缺席）；非成员 403。
- 「今日累计」：会话与本地日界窗口的**重叠部分**求和（跨日会话裁剪，昨日不计），地板取整分钟。
- **时长仅展示、不进任何榜分**（防「挂机刷时长」，设计卡 §3.3 风险条；榜模块 AST 断言禁入 study_room）。

**小队榜（冲刺完成度口径）**：
- 排序/并列名次/percentile（完成度严格更低者占比，D21「展示区间而非赤裸名次」）/分页；
- `member_count < 3` ⇒ `board_valid=false` + `self_view_only=true`（设计裁决：榜不成立，客户端切自我锚），
  `my_rank` 仍给出（自我锚位置）；
- 请求者本人名次 `my_rank` 直出；非成员 403、非 SPRINT 404（映射全照 D-COMM-3）。

### ③ 冲突面声明

- **本卡触碰面**：`app/api/v1/router.py`（+1 import、+1 注册 import、+3 注册行）、
  `app/models/__init__.py`（import + `__all__` 各一处）、`gateway proxy_routes.go`（squads 段后 +11 行，
  全部带 `D-COMM-4` 注释锚点）+ 上表新增文件。**未触碰** community.py、community_squad_service.py、
  sprint_task_ledger、exam_sprint、accountability、leaderboard_service、photon/entitlement、events。
- **wt144（events）**：无文件交集。本卡新迁移挂 `erridemconc_20260922` head——若 wt144 也新增迁移，
  合并时 `down_revision` 可能同父形成分支，需主会话按 `alembic heads` 裁决串接。
- **wt159 / wt160**：按 fleet 状态推测为并行卡；潜在共同触碰面仅三处小修改点：
  ①`router.py` 注册区（本卡 +5 行，全部紧跟 D-COMM-3 锚点注释）；②`models/__init__.py`
  按字母序的两个插入点；③`proxy_routes.go` squads 段尾部（本卡 5 条路由带注释锚点，
  合并以行段为准）。服务/schema/api 主体均为全新文件，无交集风险。
- **迁移头**：收工时 `alembic heads` 唯一 head = `dc4room_20260922`（本卡），父 `erridemconc_20260922`。

### ④ 诚实申报

1. **stale 会话不强制结算**：崩溃后未显式退出的开放会话，其时长**继续如实累计**（仅标 `is_stale`
   提示客户端）。这是「离开不惩罚 + 如实记录」裁决的直接推论；副作用是失联客户端的时长会虚增，
   直到该成员重新 enter（幂等）或 exit。若产品要「stale 自动封顶」，是服务层一处小改，未擅自加。
2. **「今日」时区口径的边界**：以 `push_preference.timezone` 为准（缺省 Asia/Shanghai）——该偏好
   语义是「推送时区」，与「学习日界时区」混用是督促域既有惯例，本卡照惯例继承未扩大。
3. **未 import accountability 的日界函数而是就地实现同口径纯函数**：`accountability.py` 是 API 层
   模块（service→api 反向分层），且其传递 import 图含 `leaderboard_service`——恰是本卡 AST 钉死的
   禁入域，不把它拉进自习室/榜的 import 闭包。代价是 ~15 行口径镜像（已注明出处），
   若两口径将来分叉，应以 accountability 为准回改。
4. **小队榜未实现「非冲刺周期无榜入口」的硬关闭**：deadline 已过 → `sprint_active=false` 如实上报、
   榜仍可读（与 D-COMM-3「结束后允许队友回看最终完成度」取舍一致）；入口隐藏是客户端职责。
   若要求后端硬关闭，是 service 一行拦截的后续改动。
5. **percentile 定义是本卡自定**：`round(100 × 完成度严格更低人数 / 总人数)`（并列口径=排序前两键）。
   未复用全局榜 `MyRankResponse.percentile`（设计卡虽提及，但本卡裁决不复用全局榜任何路径——
   D17 全站榜下沉，小队榜零耦合）。
6. **worktree 环境处置**：wt158 缺 gitignored gen 产物（`backend/app/gen`、`backend/gateway/gen`），
   自主仓**只读拷贝**进 worktree 以跑通全路由导入与 go test（D-COMM-3 同款处置；不入 patch、不入库）。
   全仓 `alembic upgrade` 在 sqlite 不可重放（早期迁移含 PG `CREATE EXTENSION vector`），
   故本卡迁移用「stamp 父修订 → upgrade head → downgrade -1」隔离验证，表结构/部分索引/回滚均实证。
7. **测试环境**：`DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=test`；macOS 无 `timeout`，
   用 pytest-timeout（`--timeout=120/150`）+ Bash 工具超时兜底；swap 紧张（<1G）全程 LIGHT 定向子集，
   未跑全量测试、未跑全量 `go test ./...`（只跑 `-run TestProxyRoutesHandler` + `go vet`）。

### ⑤ 收工核查

- [x] 未 `git commit`/`git push`；主仓全程只读（gen 产物为只读拷贝，零写主仓；收工前复核主仓 `git status` 与本卡开工前一致——其已有改动属其他会话）
- [x] 改动全部在 wt158；`git status` 仅本卡 3 改 + 10 新（见 patch），gen 产物 gitignored 确认（`git check-ignore` 双证）
- [x] 新测试 13/13 绿；定向对比法：12 文件选择器（社群族 + D-COMM-3 + ledger/exam_sprint + security + e2e/integration）
      本卡改动后 **124 passed / 2 skipped**（含新 13）vs 基线克隆（7d8a828d 纯 HEAD）**111 passed / 2 skipped**——**零新增失败、skip 数一致**
- [x] patch 可复现性：`changes.patch` 在基线克隆 `git apply` 干净，apply 后新测试 + D-COMM-3 测试 25/25 绿
- [x] 网关：新增 5 路由钉住测试过；`TestProxyRoutesHandler` 全族 7 个测试绿（CGO_ENABLED=0 + JWT_SECRET env）；
      `go vet ./internal/handler/` 干净
- [x] 路由健全性：api_router 全量导入，squad 面 12 条 = D-COMM-3 的 7 + 本卡 5，无碰撞；community 面总数 123 = 111 既有 + 7（D-COMM-3）+ 5（本卡）
- [x] 迁移：`alembic heads` 唯一 head；sqlite 隔离 upgrade/downgrade 往返通过（含部分唯一索引 WHERE 谓词实证）
- [x] Lint：ruff 全绿（新文件；router.py 的 I001 为基线既有，未动）；black --line-length 120 全过
- [x] 无凭据/无 .env/无生产配置入 patch；零音视频、零 WebSocket、零 Redis 依赖（纯 DB 在场记录）
- [x] /tmp 清理：`/tmp/wt158-baseline-dcomm4`、`/tmp/wt158-changes-raw.patch`、`/tmp/wt158-router-head.py`、
      `/tmp/wt158-dcomm4-migcheck.db` 已删；`/private/var/folders/*/T/pytest-of-*` 已清；无模拟器/无长驻进程/无 HEAVY 任务

## 三、回归证据（定向对比法）

| 批次 | 选择器 | wt158（本卡改动后） | 基线克隆（7d8a828d） |
|---|---|---|---|
| 新测试 | `tests/unit/test_community_study_room.py` | **13 passed** | （不存在，TDD 新增） |
| 小队+社群族 | squad_mvp / template_injection / privacy_fv05 / service_group_tasks / signal_kill_switch / privacy_production / context_manager_community | 45 passed（去重新测试后同基线） | 45 passed |
| ledger+冲刺域 | test_sprint_task_ledger + exam_sprint_dashboard_service + exam_sprint_review_service | 同绿（并入下行合计） | 同绿 |
| 安全/API/E2E | test_community_security + api/test_exam_sprint_api + test_community_e2e + integration/test_community_integration | 66 passed / 2 skipped | 66 passed / 2 skipped |
| **定向合计** | 12 选择器（新测试除外） | **111 passed / 2 skipped** | **111 passed / 2 skipped（零差异）** |
| patch 复现 | 基线克隆 apply patch → 新测试 + squad_mvp | — | **25 passed** |
| 网关 | `go test ./internal/handler/ -run TestProxyRoutesHandler`（CGO_ENABLED=0） | ok（含新钉住测试，全族 7 绿） | ok |
| 静态检查 | ruff + black(120) + go vet | 全绿（豁免：router.py 基线既有 I001） | — |

新测试覆盖面（13 用例）：进出回路与时长结算（90 分钟回拨实证）、重复进入幂等（唯一开放会话）、
重复退出诚实上报（already_out）、本地日界窗口与跨日裁剪（Asia/Shanghai 冻结时钟：60+330 精确断言）、
在室视图（在室/离席/从未入场三分 + 非成员不出现在视图）、stale 心跳标记与心跳兜底、
榜排序正确性（1.0 / 0.667 / 0.0 有账本 / 空账本四档定序）、并列名次（竞赛排名 1,1,3）、
percentile 区间、分页切片（名次全集计算）、<3 人降级与恢复、非成员 403（服务层 5 入口 + API 层）、
非 SPRINT 404（不泄露存在性）、XP-photon 双钉（AST 导入扫描 ×4 模块 + 光子/火苗扰动行为断言 +
榜必须消费 D-COMM-3 SSOT 的结构断言 + 榜模块禁入 study_room 断言）。
