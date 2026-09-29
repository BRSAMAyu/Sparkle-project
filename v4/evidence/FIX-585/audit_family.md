# FIX-585 残留：同族冻结日期时间炸弹审计（六文件判定 + 全仓扩扫）

- 审计人：V4 舰队修复工程师（FIX-585 残留任务）
- 日期：2026-09-29（本轮机器本地日期；工作区 darwin/arm64）
- 主仓：`/Users/brsama/code/GitHub/Sparkle-project`（基线 commit `d1efa9dd`）
- 首例参照：`backend/tests/api/test_stuck_journey_api.py` `_NOW=datetime(2026,9,25)` 冻结 vs `stuck_journey_service.py:275` 服务端真实 `utcnow()` 开 7 天窗 → CI53 绿→CI54 红（Sep 29 10:00 UTC 边界穿越）。修法=测试侧 `_NOW = datetime.utcnow()` 动态化。
- 判定方法：对每处冻结 `datetime(202x,…)` grep 消费链实查（不猜）——「冻结双端」（服务时钟也被注入/参数化 → 安全）vs「真实时钟差值/窗口」（→ 炸弹，爆点=冻结日期+窗口）。

## 一、六文件判定表

结论先行：**六文件 0 枚炸弹**，全部走「冻结双端」或「纯渲染」安全链；无爆点日期；**无需修复**。当前全部绿（`six_files_pytest.log`，18 passed / 2 skipped，EXIT=0）。

| # | 测试文件 | 冻结点 | 消费链实查 | 判定 | 爆点 |
|---|---|---|---|---|---|
| 1 | `backend/tests/test_db_partitioning.py` | `created_at=datetime(2024,2,1)` / `(2025,5,1)`（L87-88, L105-106） | 日期只作为**分区路由键** INSERT 进 `chat_messages`，随后按 id 数 `chat_messages_2024_q1` / `2025_q2` 行数；无任何与真实时钟的差值/窗口。两层守卫：demo 库 import 期整模块跳过；`to_regclass` 查不到分区则 skipTest（分区被维护任务停建时退化为 skip 而非 fail）。sqlite 环境下实测 2 skipped | 安全（非时钟炸弹；分区存在性已守卫） | 无 |
| 2 | `backend/tests/test_context_manager.py` | `start_time/end_time=datetime(2026,4,26,…,tzinfo=UTC)`（L15-16） | 消费面 `ContextOrchestrator._serialize_busy_calendar_events`（context_manager.py:947）为纯序列化：tz 剥离→`strftime("%H:%M")`，仅校验 `end<=start` 跳过；无真实时钟参与。另两用例全 mock 注入 | 安全（纯渲染） | 无 |
| 3 | `backend/tests/unit/test_calibration_receipt.py` | `timestamp=datetime(2026,5,1,12,0,0)`（L32） | `generate_calibration_receipt(..., timestamp=…)`（correction_feedback.py:198-201）：`occurred_at = timestamp or _utcnow()` → 仅写入回执 `"timestamp": occurred_at.isoformat()` 渲染字段；断言不触碰 timestamp；无时钟差值。**重叠纪律已执行**：动手前查 `git -C wtF584 status --short`（干净）+ `git diff main...HEAD` 无 calibration/correction_feedback 改动 → 不属 F584 在航领地，本文件无需修改 | 安全（冻结双端：显式参数注入） | 无 |
| 4 | `backend/tests/unit/test_exam_sprint_days_left_local.py` | `NOW_LATE=dt.datetime(2026,9,25,20,0)`（L27）+ 冻结 `date.today()=2026-09-25` | **本族标准冻结双端**：`_freeze_clocks` 同时 monkeypatch 服务模块级 `utcnow` 与 `date`（exam_sprint_dashboard_service.py L6/L14 确认两属性真实存在，`raising=False` 无哑火风险）；`_days_left`（:382-385）`today or local_date(utcnow(), tz)` 全走冻结钟。target 09-25/09-26 对冻结今日 09-26，确定性恒真 | 安全（冻结双端，本族范式本尊） | 无 |
| 5 | `backend/tests/unit/test_share_card_service.py` | `created_at/updated_at=datetime(2026,3,10,9,0)`、`unlocked_at=datetime(2026,3,10,10,0)`（L27-28/51/90） | share_card_service.py 实查：`unlocked_at` 仅做非空校验（:88）后传入渲染，最终 `unlocked_at.strftime("Unlocked on %Y-%m-%d %H:%M UTC")`（:491）纯格式化；缓存键=`user+achievement+template+privacy_hash`，缓存校验只看 privacy_hash 与文件存在性（:166-176），`generated_at` 仅随结果携带不做新鲜度窗口；`_utcnow()` 只出现在事件 payload timestamp 与渲染时戳。断言不含日期 | 安全（纯渲染 + 秒级 TTL 缓存） | 无 |
| 6 | `backend/tests/unit/test_glm_batch_adaptive.py` | `monkeypatch.setattr(manager, "_now", lambda: datetime(2026,3,19,15/21/22,0))`（L17/29/47） | concurrency.py 实查：`_now()`（:192）为实例时钟；`_is_peak_hour`/`_bucket_for`/`_default_glm_limit`/`_clamp_glm_limit` 全部 `now or self._now()` 走 patch；峰值判定只用 `hour`（默认窗 14–18，settings.py:743-744），冻结 15:00=峰、21/22:00=谷恒成立，**日期（含星期）不参与判定**。`cooldown_until` 用 `time.time()` 真实 epoch 但两侧同源（测试内 `report_rate_limit` 现写现读，断言仅 `>0`）；`get_runtime_limit` 的 peak 分支走 patch 后 `_is_peak_hour()` | 安全（冻结双端：实例时钟全量 patch） | 无 |

取证跑（修前=修后同一命令，因无改动）：

```
DATABASE_URL=sqlite:// SECRET_KEY=x /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest \
  tests/test_db_partitioning.py tests/test_context_manager.py tests/unit/test_calibration_receipt.py \
  tests/unit/test_exam_sprint_days_left_local.py tests/unit/test_share_card_service.py tests/unit/test_glm_batch_adaptive.py -q
→ 18 passed, 2 skipped (test_db_partitioning 两用例 sqlite 下守卫自跳), EXIT=0
日志：v4/evidence/FIX-585/six_files_pytest.log
```

> 「未爆≠安全」的反向校验同样成立：本审计不是以跑绿为判据，而是以消费链实查为判据；跑绿仅证明当前未爆与改动无回归。

## 二、同族边界甄别（为何 0 炸弹可信）

首例炸弹的必要条件是**双钟分叉**：测试冻结一个「当前时刻」当作数据基点，服务端另用真实 `utcnow()` 对同批数据开窗口做差。六文件的冻结日期要么被服务端同源冻结（#4 #6 patch/实例注入），要么只进渲染和路由（#1 #2 #3 #5），不存在第三种「服务真实时钟差值」路径。首例 stuck_journey 恰是唯一漏网组合（数据冻结 + 服务真实窗），已由 e694242d 修掉。

## 三、全仓扩扫登记（只登记不修）

`grep -rn 'datetime(202[0-9]' backend/tests/ --include='*.py'`：**245 文件**命中，规模远超逐文件深审，故用「首例签名」收敛——抓 `NOW* = datetime(202x…)` 冻结当前时刻常量（首例的直接签名），得 **81 文件**；再按消费链安全信号三级分型（脚本判别 + 逐文件抽查校正）：

**A 型（74 文件 = 首过 patch 信号 55 + 二/三道判别补证参数注入 19，安全信号充分，豁免）**：同文件存在时钟 patch（`setattr(…utcnow/_now/date)`、`freeze_time`、`_freeze/_freeze_clocks`、`FrozenDate`）或显式时间参数/工厂注入（`now=NOW`、`now_fn=lambda: NOW`、`now_factory=`、位置参数传 NOW、`staticmethod(lambda: FROZEN_TODAY)` patch 服务 `_today()`）。与 #4 #6 同构，双端同冻。例：`test_calendar_api_local_clock.py`、`test_policy_scheduler*.py`、`test_state_aggregator_*local_clock*.py`（实查 `_build_engagement_state(user.id, NOW)` 位置传参）、`test_predictive_focus_window_local.py`（`_freeze(monkeypatch, NOW_EVENING)`）、`test_working_memory_rejection_guard.py`（`now_fn=lambda: NOW`）、`api/test_exam_sprint_api.py`（patch 服务 `_today`；其 `FROZEN_UTC_NOW` 常量本身无消费点）、`api/test_episode_resume_api.py`（`_NOW` 定义后零消费=死常量，无炸弹面）。

**B 型（7 文件，冻结时间戳以「数据」注入、服务端消费是否真实时钟未证，登记待深审）**——这是扩扫出的真实候选面，建议后续任务逐个走六文件同款消费链实查：
1. `backend/tests/api/test_insights_evidence_cards_api.py`（`occurred_at=_NOW-…` 造数据，:91/:413）
2. `backend/tests/api/test_insights_understanding_dimensions_api.py`（`ran_at=FROZEN_NOW`，:94）
3. `backend/tests/aurora/test_shadow_comparison.py`（`collected_at=_NOW`，:26/:63）
4. `backend/tests/unit/test_card_protocol_phase4.py`（`completed_at=FROZEN_NOW`、`"submitted_at"` ISO 串，:32-33/:186/:201）
5. `backend/tests/aurora/test_proactive_autoexec.py`（grant 时间戳 `_NOW.isoformat()` 写入授权文档；若授权面有「grant 新鲜度」真实时钟窗则是同构炸弹，:56/:203/:228/:255）
6. `backend/tests/unit/test_memory_retrieval_prefilter.py`（`occurred_at/created_at=NOW-1d` 造数据，`now=NOW` 注入信号存在但预过滤阈值消费面未证）
7. `backend/tests/unit/test_memory_utility_gate.py`（同上，`NOW=2026-09-28` 造数据 + `now=NOW` 注入信号，阈值消费面未证）

**C 型（其余 ~164 文件）**：仅含历史日期字面量（fixture 建档日期、契约样本日期），无「冻结当前时刻」签名，不属本族。不逐个登记。

判别口径与已知局限：A/B 分型基于静态信号（同文件 patch/参数注入），未逐个实查服务端；conftest 无共享时钟夹具（已查 tests/conftest.py 等），不存在跨文件隐藏冻结。B 型仅「未证」，非「已爆」——无一起当前红。

## 四、修复记录

**无修复动作**。六文件 0 炸弹 → 无爆点日期可记；台账 FIX-585 行以「同族审计完成：0 炸弹，6/6 豁免（判定表见本文件），扩扫 B 型 7 文件登记待深审」收口。本目录另有 `six_files_pytest.log` 全量取证。
