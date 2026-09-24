# WT338-GOALTODAY-RED REPORT

- 日期：2026-09-25
- 基线：main = 450437c0（与卡面一致）
- 分支：wt338-goal-today-red（worktree Sparkle-sysrev/wt338-goal-today-red）
- 结论：**READY_FOR_REVIEW**。判定为 (b) 测试侧时间炸弹，产品查询无缺陷；仅改 1 个测试文件（+29/−4），红测语义完整保留并经变异实验验证仍然有效。

## 一、复现

`DATABASE_URL="sqlite+aiosqlite:///:memory:"` 下 `tests/unit/test_goal_today_view.py`：13 过 1 败，失败即卡面指名的 `test_surface_queries_both_filter_by_ssot_condition`：

```
assert due_values == {TODAY}
E   assert {datetime.date(2026, 9, 24)} == {datetime.date(2026, 9, 22)}
```

被捕获的两消费面查询里 `due_date` 参数是 **运行期 UTC 今日（2026-09-24）**，而测试模块常量 `TODAY = dt.date(2026, 9, 22)`（第 29 行）。失败值随日历走，不随代码走。

## 二、诊断证据链（判定：b 测试缺陷，非产品缺陷）

1. **产品侧行为符合设计**。两消费面全部委托 SSOT 取数入口：
   - `app/api/v1/experience/goal_router.py::_todays_next_task` → `fetch_todays_next_task(..., today=datetime.now(UTC).date())`；
   - `app/api/v1/experience_readouts.py::_next_task` → `fetch_todays_next_task(..., today=_utcnow().date())`；
   - `app/services/goal_today_view.py::fetch_todays_next_task` 用唯一出口 `todays_task_condition(today)` 组查询。
2. **探针实测**（同测试手法捕获 statement 编译参数）：两面查询都携带 `due_date == 运行期今日`、状态集恰好等于 `TODAY_ACTIVE_STATUSES`、含 `deleted_at IS NULL`。SSOT 过滤**存在且正确**——失败断言后的两条断言（状态集/软删）均成立，唯一不成立的是日期常量比对。
3. **时间炸弹溯源**：测试与实现同 commit 落地——24c827fd（2026-09-22 20:02 +0800，B1-A）。当时 UTC 日期即 2026-09-22，与硬编码常量恰好相等，故落地当日绿；**2026-09-23 00:00 UTC（北京时间 09-23 08:00）起恒红**。测试对时钟零控制（无 monkeypatch/freezegun），把运行期参数与裸常量比。该文件此后仅被 wt292 类型化批碰过（67a7c109，改类型不改行为）——与 wt313 today_day/degraded、wt335 F-7 无关，不是合法演进而测试没跟上，而是**出生即带炸弹**。
4. 排除 (a)：不存在过滤条件失效/漂移——若真失效，第 1 节失败值应表现为参数缺失或状态集错位，实测都不是。

## 三、修复（测试侧，保留红测语义）

`backend/tests/unit/test_goal_today_view.py` 单文件改动：

- `monkeypatch.setattr(goal_router, "datetime", _FrozenDatetime)`：`_FrozenDatetime` 是真实 `datetime` 子类，`now()` 固定返回 `2026-09-22 12:00 UTC`（与模块常量 TODAY 同日），`.date()` 语义不变；
- `monkeypatch.setattr(experience_readouts, "_utcnow", lambda: fixed_now.replace(tzinfo=None))`：与生产 `_utcnow` 返回 naive UTC 的形状一致；
- 三条断言原样保留：`due_values == {TODAY}`、`_status_params == set(TODAY_ACTIVE_STATUSES)`、`"deleted_at" in str(compiled)`，两面循环不变。**没有放宽任何期望值**。

**变异验证（证明不是为绿而绿）**：

| 变异 | 结果 |
|---|---|
| 从 `todays_task_condition` 删掉 today 过滤 | 测试 FAIL（due 参数集为空）✓ 拦截 |
| 删掉状态集过滤 | 测试 FAIL（状态集不匹配）✓ 拦截 |
| 对照（未变异） | PASS ✓ |

即：若未来任一消费面真的丢失 SSOT 过滤，本测试照样红。

## 四、回归面

- 本文件全量：**14/14 绿**。
- 消费面相邻批（62 绿）：test_goal_detail_route_shadowing、test_experience_readouts_criterion_label、test_goal_backfill_boundary、test_goal_quality_evaluator、tests/api/test_current_goal_id_goal_space、tests/api/test_no_unregistered_routers、test_sprint_task_ledger。
- goal/plan service 批（46 绿）：test_goal_strategy_services、test_plan_state_service、test_plan_review_service、test_task_default_plan_link。

## 五、收工门

- ruff：touched 文件 All checks passed（另抽验 goal_router/experience_readouts/goal_today_view 三个相邻 app 文件，均净）。
- 冷缓存 mypy（`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'`）：**1375**，≤ 卡面 ceiling 1375（纯测试改动，`mypy app` 不计测试，数值与基线一致）。
- 守卫：`bash scripts/run_all_rule_guards.sh` **exit 0，83 条全过**。
- 环境（不入库）：worktree 按协议补拷 gitignored gen 三件套（backend/app/gen、backend/gateway/gen、mobile/lib/gen，均 `cp -RL` 自主仓）后 BG/AQ 守卫恢复；测试环境 SECRET_KEY 以 env 内联提供（worktree 无 .env 属正常）。

## 六、边界声明

- 零产品代码改动；未碰 galaxy/chat_mode/current_goal_id 链；未碰 mobile 代码（仅 gitignored gen 拷贝）；未改认证/授权；无 /tmp 遗留（guards 日志收尾清理）。
