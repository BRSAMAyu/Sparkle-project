# TOUR · 北极星全旅程——6 新面功能成体检验（一条 API 级用户旅程）

- Worker：TOUR ｜ worktree：`wt162` ｜ 基线：`b6a68ae3` ｜ 未 commit
- 交付物：本文 + `changes.patch`（5 文件，已验在 HEAD 干净导出上 `git apply --check` 通过）+ `backend/tests/northstar_eval/feature_tour.py`
- 证据：`v3-output/TOUR/evidence/steps/S0..S9_*.json`（逐步请求/响应/verdict）+ `evidence/run_summary.json`（**9 pass / 0 fail**）

## 0. 结论（一句话）

6 个新面（计划确认/冲刺小队/自习室/小队榜/自我锚/光子兑换）作为一条真实学生旅程**全链协同可用**：
确认→出任务→小队完成度→榜序→自我锚→攒光子→兑 Pro 全部贯通，且每步的跨面一致性断言
（含与 `sprint_task_ledger` 单一事实源的对账）全绿；旅程中发现并**修复了 2 个接缝缺陷**
（其一为活栈实证的「成就光子整批蒸发」级缺陷），登记 2 项基建/产品问题。

## 一、旅程证据链（每步断言结果，run 2 全绿；配方确定性可重复）

| 步 | 面 | 关键断言（跨面一致性，不只是 200） | verdict |
|---|---|---|---|
| S0 | 栈 | 网关路由探针（假 token 打关键路由：401=已注册/404=缺失）；6 面路由零缺失 | pass |
| S2 | CP-01 计划确认 | `confirmed_at` 落库；重复确认 `already_confirmed=true`；**他人确认 404**（防枚举）；跨面：确认后 `GET /plans/{id}/today` 出任务 | pass |
| S3 | D-COMM-3 小队 | 3 人成队；`sprint-progress` 直读账本，3 成员 `task_total/completed/has_ledger_data` 形状完整 | pass |
| S4 | D-COMM-4 自习室 | enter→heartbeat→presence(in_room)→**真实完成 Day1 任务**→exit→presence(离场)；退出后 heartbeat 诚实 `in_room=false`；`today_minutes=0`（瞬时会话不造时长） | pass |
| S5 | D-COMM-4 小队榜 | 队友 A/B 各走真实任务完成 API；榜条目 (completed,total) 与 sprint-progress 同源对账相等；榜序 **[1,1,3]**（并列名次）+ 完成率非增；`board_valid=true` | pass |
| S6 | D-COMM-1 自我锚 | 7 日窗口（UTC 日界）序列含**今日**；今日 `tasks_completed≥1` 与 S4 真实完成对齐；`has_any_data=true` | pass |
| S7 | 成就/首胜攒光子 | 10 个 sprint×7 任务全走真实 API（actual_minutes 缺省，服务端按真实起止推算——X-04）；**归档 10/10 全 200**；余额 20→5050（确定性可重复） | pass |
| S8 | D-COMM-2 兑换 | 审计流水**重放基数=5050**（四收入+首胜/combo，transfer_in 排除）≥ 兑换价 3000；兑换成功 `entitlement=pro` 到期 **+7 天**；余额精确扣 3000；`redeem_pro` 流水恰 1 条；**二次兑换 409 monthly_cap_reached**（月顶幂等）；DB 直读（psql 只读）：`users.entitlement='pro'`、`entitlement_expires_at=2026-09-29` | pass |
| S9 | 全程一致性 | S7 之后主号账本暴涨至 73 任务，**零缓存失效调用**下小队榜直读 73/71 与翻页重放账本一致（新鲜度即证不走 galaxy 缓存）；`my_rank=1`；确认过的 intake 计划 today 面板照常出任务；队友视角同榜 | pass |

## 二、发现的接缝缺陷清单

### 已修（红绿流程 + 定向回归）

1. **P1 · combo 加成去重键超列宽 → 成就光子整批蒸发**（`app/services/achievement_engine.py`）
   - 症状（活栈实证）：任务完成后成就解锁日志连篇（`Granted 30 photons ... old=20 new=50` 出现 **18 次**），但余额/流水**纹丝不动**——每次发放都在随后的事务回滚中蒸发；连击加成 100% 失败。
   - 根因（双缺陷叠加）：
     ① PHOTON-STREAM 给 combo 写的 `related_item_id=f"achievement_combo:{uuid4()}"` 长 **53 字符**，超出 `photon_transaction_history.related_item_id` **VARCHAR(50)**——PG 上每次发放必炸 `StringDataRightTruncation`；**SQLite 单测不 enforce 列宽所以 6 用例全绿**（假绿）。
     ② 该异常被 `except` 吞掉后仅经 loguru 打 `R2-01 ... %s ...`——**loguru 不认 %s 占位**，异常原文整个丢失（"photon loss must be visible" 的 R2-01 可观测性自身不可见）。截断的 INSERT 毒化 asyncpg 事务 → 同批全部光子发放回滚 → 事件重试 → 无限循环。
   - 修法：键截短为 `achievement_combo:{uuid4().hex[:16]}`（34 字符，保留文档化前缀与「每事件唯一」语义，零迁移）；同文件 9 处 loguru %s 调用改 `{}` 插值（可观测性修复）。
   - 回归：新增 `test_combo_related_item_key_fits_varchar50`（钉 ≤50 长度真相+键唯一语义）；`test_photon_stream_audit_ledger.py` 7 绿、`test_plan_confirm_api.py` 6 绿、`test_plans_api.py` 4 绿（共 17 passed）；修复后活栈复跑：combo 发放入账、归档内联成就入账。
   - 波及修复：归档端点 500（MissingGreenlet）——根因即本缺陷：combo 失败毒化事务回滚 → `current_user` 被过期 → `current_user.id` 在 async 上下文触发惰性加载崩溃。修复后 10/10 归档 200，无需单独改归档代码。

2. **P2 · 直创计划重复 sprint goal 裸 500**（`app/api/v1/plans.py`）
   - 症状：`POST /plans` 撞 `uq_plans_user_sprint_goal_active`（同 user+subject+target_date 的 active sprint）时裸 500 IntegrityError；intake 路径已在 INTAKE-IDX 收敛，直创 handler 漏了同款关闸。
   - 修法：handler 捕 `IntegrityError` → 409 `SPRINT_GOAL_DUPLICATE`（不泄露约束细节）。回归：`test_duplicate_active_sprint_goal_direct_create_returns_409`。

### 登记回执（主会话立卡，本卡不修）

3. **基建 · 活栈 :8080 网关与 :8000/:50051 引擎落后基线一个合并**：进程 03:00 启动（内存代码为合并前版本），`/api/v1/community/squads/{id}/study-room/*` 与小队榜经 :8080 全部 404（证据：`feature_tour --check` 对 :8080 跑出缺失 1 条；study-room 404）。**需主会话重启活栈**；本旅程以 worktree 同基线网关 :8090 + 引擎 :8010（共享演示 DB/Redis）完成全链验证。
4. **产品 · 兑换价校准**：`PHOTON_REDEEM_PRO_COST=3000` 对真实学生意味着：首胜 30/天 → **约 100 天**的诚实积累才能兑一次 Pro 7 天（本次旅程靠成就引擎的冲刺批量成就才在会话内凑足）。设计卡标注【待产品校准】——建议立卡评估（如 800-1200 或首月梯度），否则「学出会员」对免费学生实际不可达。
5. **债务备忘**（顺带发现，不立卡）：`experiments.py` 等 3 处 loguru %s 遮蔽同族问题残留；共享 Redis 双引擎并存时事件消费存在竞争（陈旧引擎消费到的成就事件因缺陷①回滚，重试后落到修复版引擎才入账）——重启活栈后自然消除。

## 三、口径与红线自查

- 小队完成度全程唯一读 `sprint_task_ledger`（BP-4）：S5/S9 两次「榜值==账本重放」对账相等；XP/光子/时长未入榜。
- 光子只经成就/首胜/连击真实路径获取；「可兑换基数」按口径词典独立重放并与服务端行为对账；免费闭环行为零变化。
- 诚实性：瞬时会话 `today_minutes=0` 如实落证据；空数据/失败一律 fail/blocked 不折算（run 1 的 S8/S9 因**脚本断言bug**（月顶常量串、tasks 分页参数）误报 fail，产品行为两次均正确——已修脚本后 run 2 全绿，过程存档 `/tmp/tour_probe/voyage_run.log`）。
- LLM 零消费：intake 走 `exam_prep_14d@v1.0` 静态包确定性路径；全程未触碰 /ws/chat。

## 四、Worker 五要素

1. **旅程证据链**：见 §一（9 pass / 0 fail，证据 JSON 在 `evidence/steps/`）。
2. **缺陷清单**：见 §二（修 2：combo 键截断+loguru 遮蔽、直创 409；登记 2：活栈陈旧、兑换价校准）。
3. **冲突面**：触碰 `achievement_engine.py`（combo 发放点 ~30 行，热点文件——与任何成就域并行卡需 diff 交叉核对）、`plans.py`（+1 import、create handler +12 行，与 CP01-MOBILE/mobile 接线卡无交集）、2 个测试文件纯追加、`feature_tour.py` 全新。**不动 real_drive.py**（独立文件）。与 wt160（aurora）/wt163（声明）按文件面评估无交集；`router.py`/`proxy_routes.go`/迁移零触碰。
4. **诚实申报**：①「完成 Day1 任务」以 API 瞬时完成驱动（未等待真实学习时长，actual_minutes 缺省由服务端按真实起止推算≈0——未伪造观测）；② 攒光子阶段 10×7 任务是成就引擎的真实批量响应，属「冲刺周狂刷」剧情，非典型学生单日行为（这正是缺陷 4 的证据）；③ 双引擎并存期事件消费有竞争，余额轨迹仍确定性可重复（两轮 run 逐冲刺余额完全一致）；④ 证据/补丁零凭据（token 仅 sha256 前缀落盘）。
5. **收工核查**：见 §五。

## 五、收工清理清单

- [x] 进程：本卡自起的 worktree 网关(:8090)/引擎(:8010)已停（收工执行 `kill` + 验证端口释放）
- [x] `/tmp`：`tour_gw/`（含 gateway 二进制/env）、`tour_probe/` 探针脚本与两轮 state 已清；pytest-of tmp 已清
- [x] worktree：无 build/.dart_tool 产物；`backend/gateway/gen`、`backend/app/gen` 为 gitignored 编译所需生成码（随 worktree 回收，不入库不入 patch）
- [x] 探针账号数据留栈（演示 DB 只读约定内：tour_voyage_*/tour_probe_* 两轮账号+小队+兑换记录，供主会话复验）
- [x] 交付物三件齐：`feature_tour.py`（可重复冒烟，以后每轮唤醒可跑）、`REPORT.md`、`changes.patch`（HEAD 干净导出 apply --check 通过）

## 六、给主会话的三句话

1. 合入 patch 后请**重启活栈**（:8080 网关 + :8000/:50051 引擎均落后一个合并），重启后 `TOUR_GATEWAY_URL=http://localhost:8080 python3 -m tests.northstar_eval.feature_tour` 应可直跑全绿（现在需 :8090/:8010 替代）。
2. combo 光子蒸发缺陷在合并前影响所有成就型用户（活栈两轮实证余额卡 1500/2330/2560 台阶），属经济黑洞级，建议优先合入。
3. 兑换价 3000 的可达性校准请立卡（数据：诚实日均收入 ~30-80 光子）。
