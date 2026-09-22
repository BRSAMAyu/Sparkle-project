# D-COMM-1 · 排行榜 P1 债务 #3 裁决落地（自我视图挂路由 / 全站榜不路由）· 施工报告（wt155）

> 交付物：`v3-output/D-COMM-1/changes.patch`（8 文件：4 改 4 新，+588/−1）+ 本报告。
> 基线：wt155，基于 `7eb3b9c9`（D-COMMUNITY 设计落库提交）。零 commit / 零 push / 零迁移 / 零模拟器 / 零构建产物落仓。
> 卡面：D-COMMUNITY DESIGN §2.2/§3.2 + §5 D-COMM-1 卡；KNOWN_CODE_DEBT_LEDGER P1 #3。
> 范围裁决（主会话批准的任务卡）：**移动端 1,143 行死代码不动**（独立债务），本卡只做后端自我锚视图端点 + 裁决固化；mobile 侧改造留 D-COMM-4。

---

## ① 盘点表（榜型 / 路由 / 服务层现状，只读复核）

| 面 | 现状（改动前） | 证据 |
|---|---|---|
| 引擎榜型 | 9 种榜型枚举就绪（global/friends/group/subject/weekly/streak/group_flame/photon/photon_weekly） | `backend/app/schemas/leaderboard.py` `LeaderboardType` |
| 引擎路由 | 6 端点已注册（列表/summary/my-rank/types/top-three/{type}/refresh-cache），全部鉴权 | `backend/app/api/v1/leaderboards.py`；挂载 `api/v1/router.py:258` |
| 网关路由 | leaderboards 组 wildcard-only 代理（`registerREST(leaderboards, "/*path")` + 组级 authMiddleware；bare path 直代理 + 尾斜杠修剪，gamification-eval P1-2 先例） | `backend/gateway/internal/handler/proxy_routes.go:986-992` |
| 自我 7 日锚视图服务层 | **不存在**（服务/schema/端点零实现）——需按任务卡补最小实现 | grep self-view/anchor 全仓无命中 |
| 数据源既有面 | ①冲刺完成度：`sprint_task_ledger.py`（BP-4 单一事实源，`sprint_ledger_condition` + `Task.completed_at`）；②掌握度增量：`study_records`（galaxy 掌握度事件流，`galaxy/stats_service.py:155` 与 `error_book_mastery_sync_service.py:446` 写入、celery 周任务消费）；③state_aggregator 的 `learning_state` 是 prompt 侧即时快照、无按日历史 → 按日增量读其底层事实面 study_records | `backend/app/services/sprint_task_ledger.py`；`backend/app/models/galaxy.py:289` |
| D17 隐藏守卫 | **不存在**——无任何守卫防全站榜被误挂路由（BA-ROUTES 只管网关↔引擎 parity，BA 只管 chat DTO）；隐藏状态仅靠「碰巧没人挂」 | `scripts/rule_guard_manifest.tsv` 全量核对 |
| 债务台账 P1 #3 | 挂账中：「要么挂路由上线，要么整链删除」待产品决策 | `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md:30` |

## ② 落点清单

| # | 文件 | 动作 | 内容 |
|---|---|---|---|
| 1 | `backend/app/services/leaderboard_self_anchor_service.py` | 新增 | 自我 7 日锚视图服务：固定 7 天 UTC 窗口（含今天）；完成度 = `sprint_ledger_condition` 域内 `status==COMPLETED` 按 `completed_at` 落日（**状态过滤不可省**——abandon 路径也写 completed_at，`task_service.py:1238`；reopen 会清空，`:1439`）；掌握度 = `study_records` 按日 `SUM(mastery_delta)`。零新聚合口径，只读既有面 |
| 2 | `backend/app/schemas/leaderboard.py` | 追加 | `SelfAnchorDayPoint` / `SelfAnchorViewResponse`（`has_any_data` 诚实空态标记）。遵循本仓 `date as date_type` 惯例（pydantic 字段名 `date` 与类型同名陷阱） |
| 3 | `backend/app/api/v1/leaderboards.py` | 追加 | `GET /leaderboards/self-anchor`（鉴权，`# route-tier: authed`，AX 守卫要求） |
| 4 | `backend/gateway/…` | **零改动（有意）** | 实测 gin 1.9.1 在 `/*path` catch-all 同级注册静态路由即 panic（探针：`panic` "conflicts with existing wildcard"，探针文件已删）；wildcard 已覆盖新端点且过组级 authMiddleware——加显式路由行既不可能也无必要 |
| 5 | `scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py` | 新增 | COMM-LB 守卫固化裁决两条不变量：①`mobile/lib/app/routes.dart` 零 `LeaderboardScreen`/leaderboard 引用（全站榜 UI 无入口）；②网关 leaderboards 组保持 wildcard-only（任何显式榜面路由行=把榜 promoted 成产品路由）。escape hatch `rule-comm-lb: ignore <reason>` |
| 6 | `scripts/rule_guard_manifest.tsv` | 追加 1 行 | `COMM-LB` 登记（与既有 76 规则码无冲突） |
| 7 | `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` | 改写 #3 行 | 销账说明：裁决=全站榜保持 D17 隐藏不路由；唯一路由产品面=自我 7 日锚视图；守卫 COMM-LB 固化；移动端死代码仍是独立债务（待 D-COMM-4 处置），本条不再跟踪该决策本身 |
| 8 | `backend/tests/api/test_leaderboard_self_anchor_api.py` | 新增 | 4 测试：401 鉴权 / 诚实空态（全零+`has_any_data=False`）/ 按日分桶正确性（含 ABANDONED、软删、窗口外排除）/ 跨用户隔离 |
| — | `backend/gateway/internal/handler/proxy_routes_leaderboard_self_anchor_test.go` | 新增 | 3 测试：self-anchor 经 wildcard 代理可达（路径原样透传）/ 组级 authMiddleware 拦截未认证 / 既有榜面路径零回归 |

**API 形状**（供 D-COMM-4 消费）：`GET /api/v1/leaderboards/self-anchor` →
`{success, data: {window_start, window_end, series: [{date, tasks_completed, mastery_delta}]×7 旧→新, total_tasks_completed, total_mastery_delta, has_any_data}}`。无查询参数（窗口固定 7 天）；无数据日如实补零，`has_any_data=False` 表示窗口内完全无记录（空态，不是真零曲线）；日界 UTC，本地化属展示层职责。

## ③ 冲突面（在途卡声明）

- **wt144（EVENT-ACK-2）**：改动集中在 `backend/app/aurora/proactive/pipeline.py`、`backend/app/consumers/*`、`backend/app/services/*_event_consumer.py` + `backend/tests/unit/test_event_ack2_reliability.py`——与本卡 8 个落点**零交集**。
- **wt152（galaxy servicer）**：该 worktree **当前不在磁盘上**（`Sparkle-sysrev/` 下仅 wt144/wt155），无法实物核对；本卡未触碰 `backend/app/services/galaxy/*`、任何 gRPC servicer 与 `proto/`——按文件面推断零交集。
- 本卡生成物全部在 wt155 内；主仓只读未动。

## ④ 诚实申报

1. **服务层是新建的，不是"只差路由"**：盘点确认自我 7 日锚视图后端零实现，按任务卡补了最小实现（服务 130 行）。聚合方式 = 两条按日 group（Python 侧分桶，量级=单用户 7 天任务/学习事件，极小），未引入新表、新口径、新聚合作业——「不新造聚合」理解为不造新口径/新事实面，与 sprint_task_ledger、study_records 完全同源。
2. **掌握度增量的局限（如实）**：`study_records.mastery_delta` 是 galaxy 事件流增量，BKT 融合路径（`galaxy/stats_service.py:131-139`）的 mastery_delta 会写入该表吗——**写入点核实过两处**（stats_service:155、error_book_mastery_sync_service:446），但 BKT fuse 分支的 delta 是否总伴随 StudyRecord 落行未逐分支验证；若存在只改 `user_node_status` 不落 StudyRecord 的路径，本视图会**低估**该日增量（不会虚高）。`mastery_audit_log`（raw SQL 表、无 ORM 模型）是另一潜在更全的数据源，留 D-COMM-4 评估。
3. **时区**：按 UTC 落日（与存储一致），中国用户晚间 8 小时偏移意味着「今天」的体感分桶与 UTC 不同——设计上把本地化日界留给展示层（与 exam_sprint dashboard 的 `_days_left` 用 `date.today()`（设备本地）的既有做法不一致，如需统一由消费卡裁决）。
4. **网关零改动的取舍**：任务卡写「网关路由行照 plans confirm 的先例」，但 gin 1.9.1 实测 catch-all 同级静态路由 panic（见②#4），leaderboards 组的既有先例就是 wildcard-only——以可运行性为准，未加行；3 个网关测试把「可达 + 鉴权 + 不回归」钉住，COMM-LB 守卫把「wildcard-only」钉住。
5. **black 全文件重排已回退**：对 `leaderboards.py`/`schemas/leaderboard.py` 跑 black 会重排大量既有代码（该两文件本就不 black-clean），已 `git checkout --` 回退后手工最小补丁，最终 diff 仅 +58/−1 行（4 个改动文件合计）。
6. **接口变更零**：本卡纯增量端点，不改任何既有端点/ schema 字段；9 种榜型枚举、既有 6 端点原样（既有榜面经网关 wildcard 仍可达——那是存量状态，D17 裁决管的是**产品入口**，端点面收缩属后续卡范围，见⑤#4）。
7. **wt152 无法实物核对**（见③），冲突声明基于文件面推断而非实物 diff。

## ⑤ 收工核查（红线逐条）

| 红线 | 结果 |
|---|---|
| 新端点 API 测试（含鉴权/空数据诚实语义） | `tests/api/test_leaderboard_self_anchor_api.py` **4 passed**（401 / 空态全零 / 分桶正确 / 跨用户隔离） |
| 排行榜域既有测试对比法零新增 | 改前基线 **19 passed** → 改后同集 + 新测试 **23 passed**，零回退零跳过 |
| 网关路由测试 CGO_ENABLED=0 | 新增 3 测试 passed；`CGO_ENABLED=0 go test ./...`（JWT_SECRET/SECRET_KEY 前缀）**10 包全 ok** 零失败（本地台账里的 `TestChatOrchestrator_QuotaIntegration` 已不再失败） |
| 治理守卫（设计卡验收） | `bash scripts/run_all_rule_guards.sh` **76 规则全绿**（含新 COMM-LB；BA-ROUTES 963 引擎路由 ↔ 352 网关，+1 端点已计入无漂移） |
| lint/format | ruff + black(120)：4 个我方 Python 文件全绿；Go 侧随 `go test` 编译零告警 |
| 迁移能免则免 | **零迁移**（纯读既有表 tasks/study_records） |
| 纪律 | 零 commit / 零 push / 主仓只读 / 未动活栈 / 零凭据入库（测试用 `sqlite+aiosqlite:///:memory:` + test SECRET/JWT 前缀）/ mobile 死代码未动 |
| 收工清理 | /tmp 探针（dc1-gin-probe、gin_probe_main_test.go、worktree 内临时探针文件、基线克隆 dc1-baseline）已删；为腾盘已删本 worktree 的 gitignored 构建产物 `gateway/gen`+`app/gen`（复验 Go 测试前先 `make proto-gen`）；无独立端口进程、无模拟器（`ps` 核查 0） |

**给主会话的合入提示**：patch 应用后跑三件套即可验收——①`pytest tests/api/test_leaderboard_self_anchor_api.py`（引擎）；②`CGO_ENABLED=0 JWT_SECRET=… go test ./internal/handler/ -run TestLeaderboard`（网关）；③`bash scripts/run_all_rule_guards.sh --rule COMM-LB`（守卫）。**patch 已在干净基线克隆（HEAD=7eb3b9c9）上做过 apply + 三件套实跑验证（引擎 23 绿 / 守卫绿 / 网关 4 绿；克隆侧需先补 gitignored 的 `gen/` 才能编 Go）**。移动端侧 `api_endpoints.dart` 端点常量与 l10n 未动（按 DESIGN §5 D-COMM-1「保留，后端端点不变」），D-COMM-4 接 UI 时直接消费 `/leaderboards/self-anchor`。
