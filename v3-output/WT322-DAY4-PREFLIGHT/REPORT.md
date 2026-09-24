# WT322 · JOURNEY day4 API 级预检报告

> 卡面：NS001-JOURNEY2 day4（2026-09-25 08:00 CST 自动跑）前的只读预检｜工号 wt322｜2026-09-24 21:2x CST 实测
> 结论先行：**GO —— day4 可跑**。当前栈全链路 7/7 绿；今晚合入（wt313/wt317/wt318/wt309/wt315/community 等，已全部落 main）经静态核对不触碰旅程调用面；两个「条件爆炸点」均需人为 env 翻转才会触发，见 §风险。

## 0. 环境事实（影响判读）

| 件 | 状态 |
|---|---|
| gateway :8080 | 进程 `/tmp/sparkle_gateway`（built 09-23 12:55，**pre-wt317/318/313**），cwd=主仓 backend/gateway |
| engine :8000 | uvicorn `app.main:app`，**09-21 20:39 启动、无 --reload（内存代码冻结）**，cwd=主仓 backend |
| main 分支 | 预检期间 72cfdb47 → 61e78483 → 8e563e8d（合入正在进行）；wt313（today_day/degraded/replan/health）、wt317（RS256）、wt318（WS_TICKET_REQUIRED）、wt309/wt315（mobile）、wt314 已在 main |
| 旅程调用面 | 从 /tmp/ns001_journey_out/evidence/steps/（day1-3 29 步）逐条还原：`GET /tasks/today`、`GET /tasks?limit=100`、`GET /errors/today-review`、`GET /galaxy/graph`、`POST /tasks/{id}/start|complete`、`POST /errors/{id}/review`、`WS /ws/chat`（chat probe）+ login |
| 只读纪律 | 全部预检调用为 GET + login；**未触碰任何任务/错题/聊天进度数据**。副作用记录：main 账号成功 login ×2（取 token 用），可能刷新登录时间戳，属卡面允许副作用 |

## 1. 逐项结果

### a. main 账号登录 —— 🟢 GREEN
```
POST /api/v1/auth/login  {"username":"northstar_jrn_5a140173","password":"***"}
→ 200；user.id = 01ad2e3e-19ad-4a82-8ddd-3b3f98356af3（与状态文件一致）
响应键：access_token / refresh_token / token / token_type / user —— 与 day1-3 使用的形状相同
签发 token：HS256（运行栈为 wt317 前网关，符合预期）
```
账号未锁定、密码有效、响应 schema 未变 → day4 起跑第一步不会死。

### b. plan 详情（wt313 后 payload + 链完整性）—— 🟢 GREEN（运行栈）+ 🟢 静态核对合入后
```
GET /api/v1/plans/7917e864-59eb-4a3f-b33a-11e6e4b00385 (Bearer) → 200
```
- 链完整：plan.user_id=main 账号；tasks[0..10].plan_id 全部指向本 plan；target_date=2026-09-29；progress 4/11。
- `today_day`/`degraded`：**运行栈（pre-wt313）暂无此二字段**（预期内）；day_highlights 仍呈旧「恒 Day 1」行为（`{"day":1,"recommendation":"今天先做好这 1 件事…"}`）——正是 wt313 修的缺陷。
- 静态核对合入后（worktree=main 内容）：`_build_day_highlights` 改为日期感知，09-25 会派生 today_day=4（created 09-22、target 09-29、initial 7 → 7−4+1），三态=「today」；**纯增量字段**（`PlanDayHighlights` 加 `today_day: int|None`、`degraded: bool`），老消费者不炸；旅程 driver 判定读的是 `/tasks?limit=100` 账本（J4/K4 criteria=S1 panel advancement/S2 structural diff），不消费 highlights → 无影响。

### c. day4 依赖的任务态/推荐接口 —— 🟢 GREEN
```
GET /api/v1/tasks/today → 200，返回 1 项：day:3 任务（今日已完成，符合「COMPLETED 且 completed_at=今天」规则）
GET /api/v1/tasks?limit=100 → 200，11 项：
  day:1/2/3 COMPLETED；day:4 = 62759f16-7456-457a-9b45-3631fda1d6bc「Day 4 · 检索攻克 - 树与生成树 等3个点」PENDING ✓
GET /api/v1/errors/today-review → 200，{items:[],total:"0",page:1,page_size:20,has_next:false}（形状与 day2/3 证据一致；空队列 day2 已有处理先例 J2）
GET /api/v1/galaxy/graph → 200，nodes=314
```
**09-25 08:00 /tasks/today 会 surfaced day4 任务的推导核验**：`DailyTaskSelectionService._plan_current_day` = (target−created).days − days_left + 1 = 7−4+1 = **4**；day:4 PENDING 且 4≤4 → today-relevant。旁证：09-24 实测返回 day:3（当日 current_day=3），公式与运行行为一致。

### d. health 含 days_since_last_activity 无 KeyError —— 🟢（运行栈=字段缺席但零错误；合入后=已修，生产行为已验证）
- 运行栈：`GET /plans/{id}` 的 `health_metrics` 无 `days_since_last_activity` 字段（pre-wt313），payload 正常渲染、health_status=healthy、requires_adjustment=false、reasons=[] —— 无任何 500/KeyError。
- 合入后行为（wt313 `_compute_days_since_last_activity`）：用生产数据按同公式实算——DB 只读查询 `plans.updated_at=2026-09-24 00:02:01`、`max(completed tasks.updated_at)=2026-09-24 00:02:01` → 09-25 当天 days=**1** < `INACTIVITY_STALE_DAYS=3` → 不加 inactivity reason，health 保持 healthy。**且注意**：若 day4 顺延 ≥2 天（09-27 起），health 转 warning + requires_adjustment=true——旅程 driver 不读该字段，不构成阻断。

### e. 旅程脚本 vs 当前 API 形状 —— 🟢 GREEN（静态核对）
NS001 真驱脚本不在仓库内（day1-3 为 ad-hoc 驱动；仓库内 `scripts/journey_smoke`、`scripts/devtools/journey_harness` 为 GUI 旅程 GJ01 等，与本旅程无关）。故以证据步还原调用面逐条对 merged main 核对：

| 旅程调用 | merged main 引擎路由 | gateway 代理 | 判定 |
|---|---|---|---|
| POST /api/v1/auth/login | auth.py:437（UserLogin：username/email/password） | setup.go:908 public | 🟢 形状未变 |
| GET /api/v1/tasks/today | tasks.py:495 | proxy | 🟢 wt313 未触碰 |
| GET /api/v1/tasks | tasks.py | proxy | 🟢 |
| POST /tasks/{id}/start · /complete | tasks.py:1116 / 1278 | proxy | 🟢（day4 driver 自身写操作，预检未执行） |
| GET /errors/today-review | error_book.py:166 | proxy | 🟢 |
| POST /errors/{id}/review | error_book.py:300 | proxy | 🟢（同上未执行） |
| GET /galaxy/graph | galaxy handler | 显式注册 | 🟢 wt314 改一致性清理，读形状未变 |
| WS /ws/chat（chat probe） | WsAuthMiddleware | setup.go:516 | 🟢 见 §风险 R1 |

## 2. 今晚合入对调用面的影响矩阵（静态核对结论）

| 变更 | 对 day4 的影响 |
|---|---|
| wt313 plans（today_day/degraded/replan/health days_since_last_activity） | 纯增量/修复；/tasks/today 语义未动（wt313 报告 §5.1 明确 /today 维持 max_task_day 截断）；driver 不消费 highlights/health → 无影响 |
| wt317 RS256 JWT | dev 默认仍 HS256 签发（config.go:769-774，无 JWT_ALGORITHM 时 IsDevelopment→HS256）；校验侧 kid 路由 + `JWT_HS256_FALLBACK` 默认 true；引擎侧 `_jwt_verify_keys` 自 09-15 初始提交即 RS256-first/HS256-fallback → 双向兼容 |
| wt318 WS_TICKET_REQUIRED | **默认 false**（config.go:641）；false 时 Authorization header / ?token= / ?ticket= 三通道全保留 → driver 的 chat probe 连接方式（day1-3 已在 09-23 网关上成功）不受影响 |
| wt309/wt315 mobile WS ticket/三屏 | 旅程为 API 级，不经 mobile → 无影响 |
| community 重构 / wt314 galaxy 一致性 / wt319 编排路由 | 旅程不触 community；galaxy 读形状未变；wt319 只改编排内部路由（chat 质量面，非接口面）→ 无影响 |

## 3. 风险清单（按 08:00 引爆概率排序）

- **R1（条件引爆 · 需人为翻转才会发生）WS_TICKET_REQUIRED 若今晚被翻成 true**：WsAuthMiddleware 在 true 时跳过 Bearer/?token= 两条 JWT 通道、只收 ?ticket=。旅程 driver 的 /ws/chat 认证方式无证据留存（day1-3 只记录 `ws:/ws/chat`），若它走的是 JWT 通道（极可能，driver 无 ticket 客户端代码痕迹），chat probe（J5/K5 类步骤）会 401 `ws_ticket_required`。**最小修复**：保持默认 false 不动（wt318 本身就是默认 OFF 观察期）；若已翻转，回 false 或给 driver 补 ticket 获取步骤（GET ticket 端点→?ticket= 连接）。
- **R2（条件引爆 · 需人为改 env）网关翻 prod+RS256 而引擎无 JWT_PUBLIC_KEY**：新网关会签 RS256 token，引擎 `_jwt_verify_keys` 只剩 HS256 → 引擎对一切代理请求 401，day4 第一个 GET 即死。**最小修复**：不要动 JWT env；两边同时配对齐 key（gateway JWT_PRIVATE_KEY/JWT_PUBLIC_KEY + backend JWT_PUBLIC_KEY + ALGORITHM=RS256）或都不配。另注意：无 key 时 prod 模式网关启动即 Fatal——是显性失败不是静默错，08:00 前重启失败会立刻看见。
- **R3（流程性，最可能实际发生）08:00 前栈重启与合入窗口交错**：现网关二进制 09-23 版、引擎进程 09-21 版。若重启只做一半（新网关+旧引擎或反之），存在理论错位面；按 §2 核对，main 单一代（两端都重启到 main）是自洽的：HS256 继续签发、引擎 RS256/HS256 双验、路由全在。**最小修复**：重启时两端一起重启到同一 main commit；重启后跑一次 `curl /healthz` + login 探针（本报告 §1a/1c 命令原样可复用）。
- **R4（低）gateway 二进制住在 /tmp**（/tmp/sparkle_gateway）：重启机器即失；需从 merged main 重新 build。属主会话常识即可。
- **R5（低）/tmp 状态文件脆弱**：/tmp/northstar_ns001_real_drive_state.json 权限 600、单副本；备份在 Sparkle-sysrev/.journey_ns001_state_backup.json（已核对内容同源）。若 day4 driver 只读 /tmp 路径，/tmp 清理任务（舰队磁盘纪律）可能误删。**建议**：主会话今晚确认该文件在 disk-guard 清单豁免内。
- **R6（信息）进度噪音**：本次预检 2 次 login 可能刷新账号登录时间戳（卡面允许副作用）；未做任何任务/错题/聊天写操作，day4 起点（day:1-3 COMPLETED、day:4 PENDING、review 队列空）未被移动。

## 4. 收工核查

- [x] 全部调用 GET/login 只读；day4 起点 untouched（账本快照见 §1c）
- [x] 主仓只读；改动全部在 worktree wt322-day4-preflight（本报告 + changes.patch）
- [x] 无模拟器/Gradle/flutter/浏览器；LIGHT 纪律遵守
- [x] /tmp 探针清理：wt322_token.txt / wt322_login_result.txt / wt322_today.json 已删
- [x] rule guards exit 0（见提交记录）
