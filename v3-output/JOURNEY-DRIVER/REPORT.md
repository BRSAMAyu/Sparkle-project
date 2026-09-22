# JOURNEY-DRIVER 收工报告（wt161 · 基线 b6a68ae3）

> 卡面：多天旅程「诚实时间模拟」设计 + Day2-3 相位 MVP。交付 = 本报告 + `changes.patch`（worktree 根生成，含 real_drive.py/test 两文件 diff）。零凭据、零 commit。

## 0. 一句话结论

**产品把「天」绑死在引擎进程真实时钟且无 seam——Day N→N+1 只有真实跨日一条诚实路径（方案 c）**。已按 c 实现 `--phase day2/day2settle/day3/day3settle`：内置「次日门」，同日运行诚实 blocked，跨日后任意新进程续跑即得真实 CP-04/CP-05 判定。活栈同日实证：机制全通、门正确拦、LLM 只烧 3 条、重跑零双提交。

---

## 1. 时间语义调研结论（Worker 要素①）

### 1.1 「今天」的键源（全部产品代码只读调研）

| 面 | 源码位置 | 语义 |
|---|---|---|
| today 面板 | `app/api/v1/tasks.py:494` → `app/services/daily_task_selection_service.py:117` | `today = date.today()` —— **引擎进程本地时区**，非 DB now()、非 UTC 判定 |
| 今日相关三规则 | `daily_task_selection_service.py:36 _is_today_relevant` | ① dated：`due_date <= today`（含过期）；② undated sprint 任务：`day:N` tag / `order_index=N*1000` → `_task_day_index <= _plan_current_day(plan, today)`；③ COMPLETED：`completed_at.date() == today` 才算今日可见 |
| plan 当前日 | `daily_task_selection_service.py:87` | `current_day = total_days - (target_date - today).days + 1` —— **随真实日历日自动 +1，这就是「进入 Day N」的唯一机制** |
| S7 单一事实源 | `app/services/goal_today_view.py:38` | `Task.due_date == today`（date 相等）——只管 dated 任务；intake 模板任务无 due_date，不走此路 |
| 复习队列到期源 | `app/api/v1/error_book.py:166` → `error_book_service.py:911` | `ErrorRecord.next_review_at <= _utcnow()` —— **UTC 时间戳，非日界**；建错题即 `next_review_at=now`（立即到期），复习后按 mastery 推进间隔 |
| intake 任务生成 | `exam_sprint_intake_service.py:429-493` | 7 天任务在 Day0 **一次性静态全量生成**，无 due_date，分天靠 `day:N` tag + `order_index=N*1000+offset` |
| day1settle 现状 | `tests/northstar_eval/real_drive.py phase_day1settle` | sleep 150s 等 galaxy 读模型 → 重取快照。**不推进任何「天」** |

任务卡里的假设「次日任务的 due_date 本就是明天」**不成立**——intake 任务根本没有 due_date；「进入 Day2」= 真实时钟跨过午夜使 `_plan_current_day` 增长，别无他途。

### 1.2 三方案裁决（推荐 c，已实现）

| 方案 | 裁决 | 论证 |
|---|---|---|
| a) 时间注入点 | **不存在** | `date.today()` 内联散布约 20 个文件（daily_task_selection/intake/plans/goal_router/discovery_manager…），无中心时钟模块、无 seam。造 seam = 产品重构，违反「不改产品代码」 |
| b) 测试栈时间偏移开关 | **否决** | settings 注入需先把所有 today 收拢到时钟模块（改动面=全产品）；进程级假钟（LD_PRELOAD 类）零代码改动但**只偏移引擎进程**——Go 网关 JWT exp 校验、PostgreSQL now()、Redis TTL、Celery 调度全在真实时钟 → 跨进程时钟撕裂（completed_at 假钟写入 vs next_review_at 真钟比较），且证据时间戳本身是伪造的，双违诚实红线 |
| c) Day1 深挖 + 次日早晨真实跨日 | **推荐，已实现** | 唯一同时满足「不改产品代码、零时钟改写、证据时间戳真实、跨进程时钟一致」。`RunState.day1_run_date/day2_run_date/day3_run_date` 锚点 + 相位内「次日门」使任意后续进程（定时任务/次日会话）按 `--phase day2` 续跑即得真实判定，幂等语义照旧 |

**次日门实现**：驱动器 UTC 日 > 前日相位运行日 才算跨日（保守门：引擎时区快于 UTC 时有 0-8h 欠观测窗，产品侧面板证据照常落盘可辨）。同日运行时 S3 会话探针与当日任务完成**主动 gated skip**——「昨天」尚不存在，跑它就是伪造时间线。

### 1.3 附带产品发现（上报，非本卡修）

本次活栈 intake 走了**计划复用路径**：B2 建的 goal plan（subject=离散数学）命中 `_find_reusable_sprint_plan`，**7 天模板任务未生成**——账本仅 4 个 goal 里程碑任务，`Map the baseline`（order_index=1000, tags=[goal_first_step]）被当作 `first_day_task_ids[0]` 推荐。B3-2v 曾记录「双计划债」（subject=null 永不命中）；现在走向了合并，但副作用是模板缺位、旅程以「里程碑梯」形状推进。CP-04 判定器已兼容此形状（§2.3），模板缺位是否算缺陷交产品卡裁决。

---

## 2. Day2-3 相位清单与判定口径（Worker 要素②）

### 2.1 相位与步号

| 相位 | 步 | 内容 | LLM |
|---|---|---|---|
| （day1settle 增量） | C9 / C9-2 | 跨日前固化 day:2/day:3 任务持久化指纹基线（CP-04 结构面对照源）+ 落 `day1_run_date` | 0 |
| `--phase day2` | J1 / J1b / J1b-2 | 晨间面板读取；任务账本 day:2 指纹 vs 基线 diff；**J1c 同步固化 day:3 「本日事件前」基线** | 0 |
| | J2 / J3x / J3s | 复习队列到期读取；逐条提交复习（error id 守卫）；机制面汇总（due/提交/可证实推进计数） | 0 |
| | J5 | 会话适应探针（CP-04 S3，1 条 LLM） | 1 |
| | J4 | **CP-04 判定**（组合 S1/S2/S3，口径见 2.3） | 0 |
| | J6 | 完成面板当日任务（产出「Day2 事实」供 Day3 的 CP-04 对照；day 标签任务优先，里程碑形状兜底） | 0 |
| `--phase day2settle` | J8 | 镜像 C8a-2：150s 结算 + 星图快照 + touched 节点核验（CP-04 补充面） | 0 |
| `--phase day3` / `day3settle` | K1..K6 / K8 | 与 day2 同构（gate 锚 = day2_run_date；结构面基线 = J1c 的 `snapshot-day3-task-baseline.json`） | 1 |

`--phase all` 序列不变（check→setup→day0→day1→gain→report），压缩轮语义保留；`--phase` choices 追加 4 相位。

### 2.2 CP-05 部分判定口径（机制面过、阈值面诚实 blocked）

- 机制面（步级 pass）：到期错题在队列在列（`next_review_at<=now`）→ 人设以「已纠正」口径提交 `performance=remembered` → 响应中 `next_review_at` 相对提交前**可证实推进**。
- **诚实注记（写死在证据里）**：performance 是人设自报，产品未判卷——这是机制验证，**不是命中率测量**。run-summary 中 CP-05 永不据此放行：保持 blocked（n 小、自报、单日），机制面步 fail 才降 fail。队列为空时如实记录「间隔引擎把 next_review_at 推出窗口」（CP-08 正向信号，不折算 pass）。

### 2.3 CP-04 判定口径（冻结；宁 blocked 不臆断 pass）

```
前置门：
  G1 前日事实锚点（day2: state.task_id 有完成事实；day3: day2_run_date 落定）——缺失→blocked
  G2 次日门（驱动器 UTC 日 > 前日运行日）——未跨日→blocked（判据未到达）
判定面：
  S1 面板推进：panel_day_tagged_count（day:N 待执行）或 panel_active_count（里程碑梯形状）
       两者皆 0 → fail（次日计划不存在，确定性观测）
  S2 结构适应：day:N 任务持久化指纹（title/status/priority/order_index/estimated_minutes/
       difficulty/due_date/type/subtasks_total/success_criteria）vs 前日基线 diff
       有任一增删改 → pass 证据；基线缺失 → blocked（仪器不完备≠产品未适应）；
       空基线（模板缺位）→ blocked 并注明
  S3 会话适应：探针答复去重事实锚词（DAY_FACT_MARKERS：昨天/完成了/错题/欧拉/任务…）
       >=2 → pass；反记忆词表一票否决 → fail；空/泛计划/锚词不足 → blocked
组合：S2 或 S3 有正证据 → pass；S3 反记忆且无 S2 → fail；其余 → blocked
  （里程碑梯形状且无适应证据时 blocked 而非 fail——面板出现下一里程碑无法区分
    机械推进与适应，仪器不冒判）
```

run-summary 集成：`CP-04` 存在 J4/K4 判定步时按「全部已执行日 pass 且无 fail→pass；任一 fail→fail；否则 blocked」判定，无步时回落压缩轮 blocked（`--phase all` 行为不变）；`CP-05` 机制面步存在时仍 blocked（阈值不可证），机制步 fail 才降 fail。meta.honesty 文案动态反映旅程覆盖日。

### 2.4 幂等续跑语义（活栈已实证）

- 复习提交按 error id 守卫（`day{N}_reviewed_error_ids`）——**重跑实证零双提交**；
- LLM 探针只在「次日门通过且当日未 done」执行，chat 成功后立即落 done（最小化 crash 双烧窗）；同日重跑零 LLM；
- 任务完成只选 PENDING/RESTORE——已完成天然幂等；
- 旧版 run state 无新字段 → dataclass 默认值兼容，回落诚实 blocked。

---

## 3. 活栈验证证据（真实网关 ：8080 → 引擎 gRPC，API 级）

- run：`NS001-JOURNEY2-20260922-211514`，主号 `northstar_jrn_5a140173` / 对照号 `northstar_jrn_ctrl_59522929`（证据内只出现 sha256 前缀）
- 链路：check→setup→day0→day1→day1settle→**day2**→day3→report；**LLM 总耗 3 条**（day0:1，day1:2，day2/day3 同日 gated 0 条），预算 ≤6/相符合规
- 关键判定：C2/C3 pass（60s 内）、C4b 完成任务 pass、C5 错题 pass；day2 相位 J1/J1b/J2/J30/J3s 全 pass——**复习队列 due=1、提交=1、next_review_at 可证实推进=1**；J4/J5/J6 同日门诚实 blocked；day3 同构复验；重跑 day2 证明幂等守卫
- report：`counts = {pass:3, fail:0, blocked:6, unsupported:2}`——**fail=0 语义保持**，CP-00/01/03 稳定 pass，CP-04/05 按口径 blocked
- 证据目录：`v3-output/JOURNEY-DRIVER/live-20260922/`（evidence/steps/*.json、run-summary.json、snapshot-future-task-baseline.json 等）
- 回归：`tests/northstar_eval/` **52 passed**（原 42 + 新增 10 个 JOURNEY 纯函数单测），`DATABASE_URL=sqlite+aiosqlite:///:memory: SECRET_KEY=test`

---

## 4. 冲突面声明（Worker 要素③）

- 本卡改动仅 `backend/tests/northstar_eval/real_drive.py` + `backend/tests/northstar_eval/test_real_drive_unit.py`（**tests 层，零产品代码**）。
- wt160（aurora 批4）消费面在 `app/aurora/*` 与 mobile——**零交集**；wt162/wt163 卡面未知，但只要不动 `tests/northstar_eval/` 两文件即无冲突；驱动器对活栈纯 API 消费（POST 仅限测试账号的复习提交/任务完成），**未动活栈进程与演示库**。
- 潜在唯一交集：若有并行卡同改 northstar_eval 目录，合入时以本 changes.patch 的 hunk 为准人工对账（我未动既有判定函数，只追加 + 对 day1settle 尾部/run-report 定义表做了增量修改）。

## 5. 诚实申报（拿不准的判定面，Worker 要素④）

1. **里程碑梯形状下 S2 天然不可观测**（结构面只认 day 标签任务）——本次活栈恰为此形状：真实跨日后 CP-04 大概率只能靠 S3 会话面判定，甚至 blocked。判定器已兼容，但「模板计划的 CP-04」本次未获真实样本。
2. **7 天模板缺位的归因**（复用路径不生成模板）是产品行为，仪器只能如实 blocked/fail，不能定位是缺陷还是预期——需产品卡裁决。
3. review 提交为人设自报 performance，产品未判卷——**CP-05 命中率阈值在 API 级不可证**，这是仪器边界不是产品结论。
4. day3 的前日事实锚点用 `day2_run_date`（相位运行事实）而非 day2 完成任务 id——弱锚点；J6 完成的任务 id 未入 state，靠面板 PENDING 过滤幂等。
5. 次日门用驱动器 UTC 日：引擎本地时区快于 UTC 时存在 0-8h 欠观测窗（引擎已跨日、驱动器仍判同日）——保守方向出错（多 blocked 不少 pass），面板证据可辨。
6. chat 探针在「成功返回」与「done 落盘」之间存在 crash 双烧窗（预算护栏 24 条兜底）；S3 判定阈值（去重锚词 ≥2）是启发式，judge_version 落证据供复核。
7. J2/J3 的同日合法性论证：队列由 `next_review_at`（UTC 时间戳）驱动、与日界无关，当天复习是真实用户行为——但「跨日复习样本」与「当日复习样本」未在证据里区分标记。

## 6. JOURNEY-PLAN：Day4-7 完整设计（后续卡接续）

> 延续既有机制：每日一对相位 `dayN`（晨：观测→复习→判定→产出事实）+ `dayNsettle`（晚：星图结算）；state.day{N}_run_date 链驱动次日门；步号新前缀避免撞名；每相位 LLM ≤6。

| 日 | 相位前缀 | 增量判定面 | 设计要点 |
|---|---|---|---|
| Day4 | L | CP-06 数据面启动 | 晨相位同构 + 每日快照 `sprint-summary`/galaxy mastery（加权覆盖分子分母逐日落盘，供 Day6 判定）。需先盘点 exam_sprint_dashboard 的覆盖口径源（strategy 权重 × 节点 mastery） |
| Day5 | M | CP-02 解 blocked | 增加 1 次 quiz（generate+grade，人设「已学过」作答）→ 与 Day0 诊断、Day3 quiz 共 ≥3 点滑动窗，判 trajectory non-decreasing。**前置：盘点 `/api/v1/exam-sprint/*` quiz 端点契约**（diag 契约已知，quiz 面未验证） |
| Day6 | N | **CP-06 判定日** | 末学习日：加权覆盖 = Σ(考纲节点权重 × 已掌握) / Σ权重 ≥ 阈值；数据源 Day4 起逐日快照对比。模板缺位形状下此面可能 blocked——诚实记录并归因 |
| Day7 | O | **CP-07 后测增益** | 考试日：同科目 diagnose 再生成一卷，人设以「学过」作答判卷 → 增益 = (后测-前测)/前测 ≥ MDE。对照号（无历史）同卷作答作差分臂 |
| Day10 | P | **CP-08 遗忘率** | 考后 3 天：重做 Day5 quiz 同题 → 遗忘率 = 1 - 保持率 ≤ 阈值。队列到期记录（Day2 起的 next_review_at 轨迹）作辅助面 |
| 冻结 | — | CP-98/99 | 保持 unsupported（真人自报/真实考试墙钟，API 级永不判） |

实现顺序建议：先 M（Day5 quiz 面，CP-02 一并解锁）→ L/N → O/P；每卡先做产品面只读盘点再写相位；全程复用本卡「次日门 + reviewed 守卫 + done 旗标」三件套。

## 7. 收工核查（Worker 要素⑤）

- [x] pytest tmp 已清（pytest-of-13/14 删除；最后一次回归会再生成一个，随本报告提交前清理）
- [x] 无遗留进程（driver 为短命进程；未启任何服务/模拟器）
- [x] 活栈零进程改动；演示库只读+测试账号 API 写
- [x] 零 commit / 零 push；改动全部在 worktree
- [x] 零凭据：证据内凭据只以 sha256 前缀出现；state 文件仅存 /tmp（600）
- [ ] **一项保留申报**：`/tmp/ns001_journey_demo_state.json`（1.8KB，600，仅合成测试账号凭据）**有意保留**——它是明日真实 Day2 续跑锚点（state.day1_run_date=2026-09-22，明日跑 `--phase day2` 即得真实 CP-04/CP-05 判定）。若主会话裁定不留：`rm` 即可，次日从 `--phase setup` 重开（LLM 代价约 3 条）。机器重启则自然失效。
- [x] 另发现旧会话遗留 `/tmp/northstar_ns001_real_drive_state.json`（非本卡产物），留主会话磁盘巡检处置
