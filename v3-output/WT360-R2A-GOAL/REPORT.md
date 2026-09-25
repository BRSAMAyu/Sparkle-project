# WT360-R2A-GOAL — 卡 R2-A：task_event_consumer Goal 进度口径修复（H1 blocker + H2 同文件并卡）

- **worker**: wt360 ｜ **日期**: 2026-09-25 ｜ **分支**: `wt360-r2a-goal`（基于 main@557cf78c）
- **卡面权威**: `v3-output/WT355-HUNT-R2/REPORT.md` 「卡 R2-A」节（wt348 猎缺 + wt355 双轮复核确认）
- **模式**: LIGHT（sqlite 内存库定向 pytest + 守卫 + 冷 mypy；未连 PG/Redis；未跑 flutter/模拟器/浏览器）
- **改动文件**: 仅 `backend/app/services/task_event_consumer.py`（+23/−7）+ 新增红测 `backend/tests/unit/test_wt360_goal_progress_consumer_fix.py`

---

## 一、改动清单（对照卡面 ①②③）

| # | 卡面要求 | 落点（修后行号） | 实现 |
|---|---|---|---|
| ① | `:262`/`:323` 小写串 → 枚举成员 | 两处 count 查询 | `Task.status == "completed"` → `Task.status == TaskStatus.COMPLETED`（与 `plan_service.py` / `plan_progress_service.py:295` 同口径；import 处补 `TaskStatus`） |
| ② | 两处 count 补软删过滤 | 分子分母共 4 条 count（两 handler 各 total+completed） | 均补 `Task.deleted_at.is_(None)`（软删任务不进分母也不进分子，与 `goal_today_view.py:38-44` SSOT 同） |
| ③ | Goal 查找 `:250`/`:311` 改 `.limit(1)+scalars().first()` | 两处 Goal 查找 | `scalar_one_or_none()` → `.limit(1)` + `result.scalars().first()`（顺带消 H5 MultipleResultsFound 面，未加 DB 索引） |

**Forbidden 全守**：未改 `models/task.py` 枚举；未改 `schema.sql`；未动事件契约字段（`:788` 附近 `"completed": completed` 是 Spine outcome payload 契约键，非查询口径，保留）；未碰 `goal_router` falsy-or 显示层（R2-D 范围）。

## 二、红测与验证证据

### 新增红测 `tests/unit/test_wt360_goal_progress_consumer_fix.py`（4 用例）

与 wt348/wt355 两份取证探针（查询形状复演）不同，本红测直接驱动真实 handler
（`_handle_task_completed` / `_handle_task_abandoned`）在 sqlite 内存库写库，锁产品行为本身。
协作者（BehaviorSignalCollector/Metacognition/CommunityBridge/AutoFragment/AdaptiveReplanner/Spine/
RouteHistory/Belief shadow）全部 no-op 隔离，只保留 Goal.progress 块的真实 DB 行为。

| 用例 | 断言 | 修前 | 修后 |
|---|---|---|---|
| task.completed 事件写库（卡面种子：1 COMPLETED+1 PENDING+1 软删 COMPLETED） | goal.progress == 0.5 | **FAIL**（写 0.0） | PASS |
| task.abandoned 事件写库（同种子） | goal.progress == 0.5 | **FAIL** | PASS |
| 同 plan 挂两个 Goal 时写入不被吞 | 至少一个 Goal 写中 0.5 | **FAIL**（实测日志 `Failed to update goal progress: Multiple rows were found when one or none was required`——H5 面的直接实证） | PASS |
| 口径对照（小写串形状保留为回归证明） | 旧形状 (0,3)→0.0；修复口径 (1,2)→0.5 | PASS（形状文档，与产品代码无关） | PASS |

**修前红验证方法**：单文件粒度变异——修后文件备份至 /tmp → `git checkout -- <consumer>` → 跑红测（3 failed 1 passed，且捕获到 H5 的 MultipleResultsFound warning 实证）→ 从 /tmp 还原修后文件。符合并发验收工作树安全纪律（未用 stash）。

### 定向回归

- 修复文件 + 两份探针 + 消费者相关面（`test_consumer_exception_propagation` / `test_event_idempotency_isolation` / `test_c03_adaptive_replanner_wiring` / `test_c01_outcome_tracker_wiring` / `test_spine_event_bridge` / `test_event_ack2_reliability`）：**49 passed**。
- `pytest tests/unit -q` 全目录跑批（sqlite 内存口径）：实测见本报告「五、收工记录」。

## 三、PG 语义注记（发布说明人肉验证项）

本机红线禁止连 PG，以下为语义推证链（承接 wt355 报告 H1 节三段链：schema 快照 `tasks.status` 为原生枚举 `taskstatus` 全大写标签 + SQLAlchemy 2.0.48 对未知小写串 bind 透传实测 + PG 枚举输入解析语义）：

- **修前**：生产 PG 上 `WHERE status = 'completed'` 抛 `22P02 invalid input value for enum taskstatus`，被两 handler 内层 `except Exception` 吞成 warning → 写入不发生，Goal.progress 冻结于列默认 0.0。
- **修后预期**：枚举成员 bind 到 `'COMPLETED'` 标签，查询合法执行；生产日志**不应再出现** `Failed to update goal progress: ... invalid input value for enum taskstatus`（含 `... on abandon` 变体）。
- **人肉验证项（进发布说明）**：上线后检索生产日志确认上述 warning 消失；并抽一个活跃 plan 的 Goal.progress 值随 task.completed 事件递增。

## 四、收工门数值

| 门 | 要求 | 实测 |
|---|---|---|
| 守卫 | 84 条 exit 0 | all rule guards passed (84 rules)，exit 0 |
| 冷 mypy | ≤1278（不得推高） | 1278（=基线） |
| 定向 pytest | 相关面无回归 | 消费者相关面 49 passed；新红测 4/4；全量 tests/unit 失败集与 pristine main 逐 ID 一致（见「五」） |

（各门实测的完整记录见文末「五、收工记录」。）

## 五、收工记录（实测回填）

- 守卫：`bash scripts/run_all_rule_guards.sh` → **all rule guards passed (84 rules)**，exit 0。
- 冷 mypy：`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'` → **1278**（= 基线 1278，未推高）。
- ruff：被碰两文件 `ruff check --fix` → 1 处 I001 修复后 **0 error**。
- 全量 `pytest tests/unit -q`（sqlite 内存，deselect 1 个已知日期敏感既有失败）：**8709 passed（含本卡新红测 4 用例）/ 65 failed / 6 errors / 42 skipped**。
- **全量失败集非因果验证（双跑对照）**：23 个失败文件在**还原本卡改动后的 pristine consumer** 上重跑 → 失败集与全量套件**逐 ID 一致**（65F+6E=71，仅两行日志格式噪声：RuntimeWarning 黏行 + 随机 UUID 参数值）→ **全部失败为 main 既有，与本卡零因果**。失败族：srl_phase_tracker(17)/orchestrator_real_engine(11)/spine(16)/openclaw(10)/theater(2)/其它(15)，无一引用 goal-progress 块；另有 1 个 deselect 的 user_insight calendar 日期敏感既有失败（还原改动后单测复现同败）。
- 修前红验证：单文件粒度变异（备份 → `git checkout --` → 跑红测 3F1P，捕获 `Failed to update goal progress: Multiple rows were found when one or none was required` 实证 H5 → 从备份还原），未用 stash，符合并发验收工作树安全纪律。
- 提交：路径限定 commit（consumer + 红测 + 本交付物目录）。

## 六、诚实边界

- 未连 PG/Redis（红线）：PG 22P02 症状的消除为语义推证，非实测；已列入第三节人肉验证项。
- 存量 Goal.progress 重算（当前全库恒 0.0）按卡面要求**另立卡**，本卡不做一次性重算；修后首个事件只自愈当前 plan。
- 同 plan 多 Goal 时 limit(1) 选中哪个 Goal 无确定序（现行 1:1 不可达，防御深度性质）；若未来放开多 Goal 挂同一 plan，应加 DB 部分唯一索引或显式排序，本卡不越权处理。
- `test_lowercase_literal_versus_fixed_caliber_on_card_seed` 是口径对照文档用例，修前修后均绿（它锁的是形状语义不是产品代码）；行为级锁定由前三个 handler 用例承担。
