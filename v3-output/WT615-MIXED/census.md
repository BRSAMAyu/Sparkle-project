# WT615-MIXED · task.created_at 混型悬案裁决（wt602 遗留 · V3-FIX-314 附带）

- 工位：wt615（worktree `wt615-mixed`，分支 `agent/node-b/wt615/mixed`，基线 = main 头 `e4f64801`）
- 日期：2026-09-25（取证当日 live 库已滚动至 2026-09-27）
- 悬案：模型缺省 `_utcnow`（UTC），但 wt602 裁决表记载「JOURNEY 生产库实证 task.created_at=22:37 与 day0 会话同钟 = **上海墙上钟**」——两者矛盾，必有某条写路径传了客户端/agent 时间。
- 方法：全仓写点普查（只读）+ live PG 只读剖面（`postgres@127.0.0.1:5432/sparkle`，服务器 TZ=`Etc/UTC`）+ JOURNEY 现场证据交叉锚定。**未改任何产品代码。**

---

## 0. 一句话裁决

**tasks.created_at = naive-UTC，100% 单钟，混型比例 0/3087（0%）；不存在传客户端/agent 时间的写路径。** wt602/wt582 的「同钟 = 上海墙上钟」是**对错了钟名的同钟**：与 22:37 同钟的那个「day0 会话钟」本身是 **UTC**（JOURNEY 驱动器 `run_id=NS001-JOURNEY2-20260922-211514` 由 `datetime.now(UTC)` 打戳，与 DB 行 21:15:14.29 精确同秒）——真实跑批发生在上海墙上 **09-23 05:15–06:37（凌晨自动化夜跑，AGENTS.md 夜间执行）**，而非 22:37 的晚间。「22:37 看起来像晚上」是钟名误贴的唯一来源。**下游 :69 的 `created==today` 判定（V3-FIX-221 `_as_local_date` UTC 读法）在 UTC 存储下是正确的，task 侧零修。**

**连带发现（交主会话，不在本卡擅动）**：同一「同钟=上海墙上钟」误读也是 **V3-FIX-314（wt610，commit 125db915）把 `_plan_current_day` 改成 plan.created_at 按墙钟直取 `.date()`** 的前提；本卡同一条锚链证明 plan.created_at 同样是 UTC（计划行 7917e864 created=21:15:30.064186 == 驱动器 run-summary `started_at` 与 UTC 打戳的 run_id）。该读法对 UTC 16:00–24:00 创建的计划（live 库 128/975 = **13.1%**，含 JOURNEY 计划本身）会把创建日本地日读成前一日 → total_days +1 → current_day +1 → 明日 day:N 任务提前泄入今日面。

---

## 1. 写点普查（Task 创建全量，13 处）

ORM 基线：`backend/app/models/base.py:153` `created_at = mapped_column(DateTime, default=_utcnow)`；`core/time_utils.py:26` `utcnow() = datetime.now(UTC).replace(tzinfo=None)`（真 UTC naive，与宿主机时区无关）。

| # | 写点 | 显式传 created_at？ | 钟 |
|---|------|--------------------|----|
| 1 | `app/services/task_service.py:178`（`TaskService.create` ← POST /api/v1/tasks，**生产主路径**，含 JOURNEY 驱动器 `create_sprint_plan_with_tasks`） | 否 → ORM 默认 | UTC |
| 2 | `app/services/execution_service.py:2105`（隐藏聊天控制任务） | 否 → 默认 | UTC |
| 3 | `app/orchestration/adaptive_replanner.py:1021`（检查点补强） | 否 → 默认 | UTC |
| 4 | `app/services/task_feedback_service.py:555`（知识缺口补强） | 否 → 默认 | UTC |
| 5 | `app/services/community_service.py:2435`（群任务认领个人卡） | 否 → 默认 | UTC |
| 6 | `app/services/plan_adjustment_applier.py:362`（前置复习插卡） | 否 → 默认 | UTC |
| 7 | `app/services/guest_seed_service.py:420`（`_ensure_task`）与 `:2099`（访客批量） | 否 → 默认 | UTC |
| 8 | `scripts/seed_demo_user.py:356` | 否 → 默认 | UTC |
| 9 | `scripts/seed_demo_user_enhanced.py:438` | **是**，但 `now = datetime.utcnow()`（:1002）派生 | UTC |
| 10 | `scripts/seed_phase2_demo_data.py:620,633,646` | 否 → 默认 | UTC |
| 11 | `scripts/verify_data_integrity_full.py:142` | 否 → 默认 | UTC |
| 12 | `scripts/celery_acceptance.py:221` | 否 → 默认（completed_at 显式 UTC） | UTC |
| 13 | **`gateway/internal/service/task_command.go:114`**：`INSERT INTO tasks (... created_at, updated_at) VALUES (..., NOW(), NOW())` | **是，`NOW()`** | **服务器本地墙钟**（TIMESTAMP WITHOUT TIME ZONE 吸收 NOW() 的会话时区渲染）——**潜在隐患，非现实写手**：(a) 全网关无生产调用方（仅 `cmd/server/setup.go:214` DI 装配 + 单测），唯一 handler 调用是 `ConfirmGeneratedTasks`（UPDATE 面）；(b) live 服务器 TZ=`Etc/UTC`，NOW()=UTC。**若未来该路径接活且生产库 TZ=Asia/Shanghai，它将变成唯一的真墙钟写手**，建议届时改 `(now() AT TIME ZONE 'utc')`。 |

排雷记录：
- `backend/app/schemas/task.py:209` `TaskCreate` **无 created_at 字段** → 客户端无法注入任务创建时间。
- mobile `lib/core/services/demo_data_service.dart` 用设备本地钟 `DateTime.now()` 拼 `created_at`，但仅 demo 模式下 `api_interceptor` 本地拦截消费，**不入服务端库**。
- workers/celery/consumers、alembic 迁移：无 tasks INSERT（迁移仅 sqlite 测试夹具）。
- SQL 无 `bulk_create`/`insert(Task)`；`session_state_mixin.py:860`（RoutingDecisionLog）、`planning_workflow.py:310`（Redis 内 PlanningSession）、`aurora/runtime_v1/service.py:3071/3117`（内存 Tension/Thread）均非 tasks 表。

---

## 2. live PG 只读剖面（sparkle@127.0.0.1:5432，3087 行）

### 2.1 created_at 小时直方图（存储值原样分桶）

```
utc_hour  0:132  1:117  2:74   3:18  4:95  5:12  6:22  7:0  8:0  9:0
         10:18  11:100 12:76 13:65 14:1015 15:293 16:161 17:198 18:116
         19:76  20:141 21:176 22:124 23:58
updated_at 直方图形状与 created_at 统计上同构（14:1017, 15:291, ...，同谷 7–9）。
```

行为学解读：若按 UTC 读，UTC14 = 上海 22:00–22:59 **晚间活跃峰**（且 1015 行横跨 09-18→09-25 多天访客播种，min=09-18 14:03、max=09-25 14:58——连续多日都在「上海晚上十点档」跑 eval，完全合理）；若按墙上钟读，7–9 点（清晨）全空、14 点单点 33% 爆仓反而不自然。

### 2.2 created_at vs updated_at（同表 UTC 基准）差值分布

- `updated_at - created_at`：**3062/3087 落在 [0s, 83min]**（插入即更新的事务/短窗），长尾至 147 天（正常生命周期）；
- **`updated_at < created_at` 的行数 = 0**；
- `updated_at < created_at - 7h` = 0，`> created_at + 7h` = 17（真实晚更新，非 +8h 簇）。

→ **不存在 ±8h 混钟签名**。若 created 为墙钟而 updated 为 UTC（或反之），必现 ≈∓8h 的负差值簇——一条都没有。plans 表同测：`updated_at < created_at` = 0/975。**tasks.created_at 与 tasks.updated_at 同钟。**

### 2.3 wt602 悬案现场还原（northstar JOURNEY 用户 `northstar_jrn_5a140173`）

该用户 11 张任务：day0 四张 created=**2026-09-22 21:15:30.095–224**，Day1–Day7 七张 created=**2026-09-22 22:37:20.909–21.027**（驱动器在 day0 收尾一次性预建 7 天台账——这就是 wt602 看到的「task.created_at=22:37」）。

锚定链（每一环都是独立可复现证据）：

| 环 | 证据 | 值 | 钟 |
|----|------|----|----|
| ① 驱动器自戳 run_id | `real_drive.py:983` `f"NS001-{LOOP_TAG}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"` → 现场证据 `v3-output/JOURNEY-DRIVER/live-20260922/evidence/run-summary.json` `"run_id": "NS001-JOURNEY2-20260922-211514"` | 21:15:14 | **UTC（代码即 utcnow）** |
| ② 驱动器汇总钟 | 同文件 `"meta.generated_at": "2026-09-22T21:26:36.569014+00:00"`（`utcnow_iso()` 带 +00:00 后缀） | 21:26:36 | **UTC 显式** |
| ③ users 行 | DB `northstar_jrn_5a140173.created_at = 2026-09-22 21:15:14.293885` | **与 ① 同秒** | 同 ① |
| ④ plans 行 | DB `7917e864… created = 2026-09-22 21:15:30.064186` == run-summary `sprint_summary.started_at` | 21:15:30 | 同 ① |
| ⑤ tasks day0 批 | DB `21:15:30.095–224`（7 行 created_at 与证据 JSON 内 7×`"2026-09-22T21:15:30.095897"` 等逐一吻合） | 21:15:30 | 同 ① |
| ⑥ Day1–7 预建批 | DB `22:37:20–21` | 22:37 | 同 ①（同一次运行 82 分钟后的 UTC 墙钟 = 上海 09-23 06:37） |
| ⑦ 多日节奏 | Day1–6 completed_at = 09-23 06:09 / 09-24 00:02 / 09-25 00:00 / 09-26 00:18 / **09-27 00:26（= 今日上海 08:26 晨）** UTC | 每日一跑 | 上海 08:00–14:00 学习时段，唯 UTC 读法成立 |

①→⑤ 五环把「存储钟 = 驱动器钟 = UTC」钉死；⑥ 就是悬案里那个「22:37」——它是**UTC 22:37 = 上海凌晨 06:37**，与「day0 会话」同钟属实，但钟名是 UTC。

---

## 3. 裁决

1. **主导约定：UTC（naive），占比 100%（3087/3087）**。全部 13 处写点或走 `_utcnow` 默认、或显式 UTC 派生；唯一的墙钟写法（gateway `NOW()`）零调用方且当前服务器 TZ=UTC。**混型比例 0%。**
2. wt602「必有某条写路径传了客户端/agent 时间」的前提不成立——矛盾出在**读证侧把 UTC 锚（run_id/驱动器日志）误认成上海墙上钟**，写侧从头到尾只有 UTC 一只钟。
3. **:69 `created == today`（`_as_local_date` 按 tz 换算，V3-FIX-221）在 UTC 存储下正确，task 侧无需修。**
4. 连带 overturn（证据充分但越卡，交主会话）：V3-FIX-314 对 `plan.created_at` 的「本地墙上钟」认定与 314 同源的 wt582「mobile/服务写入无时区后缀本地 ISO」在 plans 表上未能复现（`schemas/plan.py` PlanCreate 无 created_at；`plan_service.py:108`、guest_seed、tour/API 全部不传）。JOURNEY 计划 7917e864 自身就是 UTC 锚（④）。**wt610 依 314 落的 `_plan_current_day` 墙钟直取 `.date()` 读法（`daily_task_selection_service.py:108–133`）建议复审**——该文件正是 wt610 刚修过的同一 fence，本卡不越权回改，避免跨 fence 同文件冲突。

---

## 4. 影响面量化（live 3087 tasks / 975 plans）

| 判定点 | 读法 | 误差 |
|--------|------|------|
| `daily_task_selection_service.py:69` `created == today`（undated open task 的「创建日」锚） | 现行 `_as_local_date`（UTC→用户本地日） | **0 错**（与存储约定一致） |
| 同上，若按「墙钟直取 `.date()`」改写 | 错读 | 存储值落在 UTC 16:00–24:00（=上海 00:00–08:59 夜/晨创建，多为夜间自动化）的 **470/3087 = 15.2%** 会被记到前一日：创建当日 `created != today` → 当日消失、次日照 今天 |
| `_plan_current_day`（:108–133，314 改为墙钟直取） | 现行（314 后） | UTC 16:00–24:00 创建的计划 **128/975 = 13.1%**（含 JOURNEY 7917e864, 21:15 UTC）创建日本地日读成前一日 → total_days +1 → current_day +1 → **明日 day:N 提前入今日面**；其余 86.9% 恰好重合无误 |
| 同上，若回退 `_as_local_date`（221 读法） | 与存储约定一致 | **0 错**（314 注释里「created 21:15 被推成次日 → total_days 少一天」的「病征」实为正确行为，day6 `/tasks/today=[]` 的真因需另行排查，如 day:N tag/门条件本身） |

---

## 5. 修法决定

- **task 侧：零修**（读面已按主导约定 UTC，写面全 UTC）。卡内「≤3 文件小修」条件对 task 悬案本身无可修对象。
- **plan 侧（314 回退，1 文件）**：证据充分但与 wt610 新落 fix（125db915，同文件 `daily_task_selection_service.py`）直接冲突，属跨 fence 翻案 → **只交裁决材料，由主会话调度 wt610/wt602 后续**（含 day6 `[]` 病征的重新归因）。
- **登记项（防御性，非本卡执行）**：① gateway `task_command.go:114` 若接活须改 `(now() AT TIME ZONE 'utc')`，且部署侧锁定 DB TZ=Etc/UTC；② `guest_seed_service.py` 内 `date.today()`（:2006/:2042/:2098 due/target_date）与 UTC 派生 created_at 同函数混钟（wt604 已列，本卡复核仍在）。

## 6. 证据附录

- 悬案行：`SELECT … FROM tasks t JOIN users u … WHERE u.username='northstar_jrn_5a140173'` → 11 行，Day1–7 created 2026-09-22 22:37:20.909–21.027。
- 差值签名：`SELECT count(*) FILTER (WHERE updated_at < created_at) FROM tasks` → 0；`width_bucket(epoch(updated_at-created_at),-40000,40000,16)` → 3062 行落 [0,5000s) 桶。
- 直方图/批量日/22:37 定位/锚定链 SQL：见 §2 各段（全部只读）。
- 代码锚：`real_drive.py:983,101-102`（run_id/utcnow_iso=UTC）；`run-summary.json`（run_id、generated_at+00:00、started_at）；`feature_tour.py:75-76`（同一 UTC 约定）。
- 环境注：取证期间从主仓 compose 项目拉起了既有数据卷 `sparkle-cosmos_sparkle_postgres_data` 的 sparkle_db（只读查询），未写入任何业务行。
