# EVENTBUS-HANG — 2 例无限挂起测试修复（wt180 登记项）

- **Worktree**: wt192（基线 de9fcd42，含 wt180 组隔离幂等键）
- **日期**: 2026-09-23
- **对象**: `backend/tests/unit/test_eventbus_subscribe_raise.py`（3 测试中 2 条无限挂起）
- **裁决**: **测试侧修**（产品无死锁面，零产品代码改动）
- **结果**: 本文件 3/3 全绿（0.05s，无 deselect）；event_bus 域对比法零新增

---

## ① 挂起机制诊断（谁等谁、为何永不醒）

### 复现（带 `--timeout=20 --timeout-method=thread` 保护，线程法超时自动转储全栈）

```
test_non_busygroup_responseerror_raises      PASSED（ subscribe 在建任务前就 raise，无消费任务产生）
test_busygroup_proceeds_to_consume_loop      HANG ← 20s 超时，栈转储如下
test_consumer_pattern_receives_exception     HANG（同构；wt180 基线克隆上实测，本次超时杀进程未跑到）
```

### 挂起点的栈证据（pytest-timeout thread 法转储，`/tmp` 取证后已清理）

```
asyncio/runners.py:118  run()  → self._loop.run_until_complete(task)     ← asyncio.run 尚未走到关停段
asyncio/base_events.py:608  run_forever → self._run_once()
asyncio/base_events.py:1936 _run_once → handle._run()
app/core/event_bus.py:1314  _consume_loop → await self._claim_stale_messages(...)
app/core/event_bus.py:1211  _claim_stale_messages → if next_id:
unittest/mock.py:1123/1162  MagicMock.__call__ / _increment_mock_call
```

### 机制（四步链）

1. **谁等谁**：`asyncio.run(_run())` 的 `run_until_complete` 在等事件循环空闲以执行排在后面的 loop-stop 回调；而事件循环线程被 `_consume_loop` 任务的**首个 `Task._step` 永久占用**——栈显示仍卡在第一轮 `while self._running:` 迭代里（`runners.py:118` 未返回 = `asyncio.run` 连 `finally` 关停段都没进入）。
2. **为何永不醒（根因）**：`bus.redis = mock.AsyncMock()` 下，`_consume_loop` 里每个 `await`（`xautoclaim`/`xreadgroup`）都是**不让出事件循环的同步完成协程**（AsyncMock 的 `_execute_mock_call` 内部无挂起点）；`xreadgroup` 返回 truthy mock 但默认迭代为空 → `while self._running:` **热自旋**（`_running` 被 subscribe 置 True 后测试侧再无人置 False）。
3. **为何取消也救不了**：任务取消必须在 `Task._step` 返回后才能投递（`coro.throw` 发生在下一次 step）；step 永不返回 → 取消永远无法送达 → `asyncio.run` 无限等。此前 wt180 观察到的"进程级挂起、超时难回收"与此吻合（signal 法把异常抛进被独占的线程也依赖字节码间隙，行为不稳）。
4. **纠正 wt180 的旧诊断**：wt180 判为「F3 重启回调在关停期无限重生任务」。栈证据显示 **F3 回调从未执行过一次**——`_restart_consume_loop` 只在任务**完成且带异常**时经 done-callback 触发；这里任务连第一步都没走完，`_on_done` 根本没机会跑（日志恰一条 "Starting consumer loop"，无任何 "died with ... restarting"）。真相是热自旋独占线程，不是重启风暴。

### 产品侧有无真死锁面？——无（证据）

- 生产路径 `xreadgroup(block=2000)` / `xautoclaim` 是真 Redis I/O，**每轮迭代真实挂起让出**，不可能独占循环线程；热自旋是 AsyncMock 特有的形态。
- F3 重启回调自带 `self._running` 门（EI-04：`begin_shutdown()` 先置 False），且只在任务「非取消异常退出」时触发；`_consume_loop` 整个循环体包在 `try/except Exception` 内，生产中几乎不可能带异常退出 → 该回调实际接近死代码、无风暴面。
- 真实关停形制有既有测试覆盖且全绿：`tests/core/test_event_bus_lifespan_shutdown.py`、`tests/test_event_bus_shutdown.py`（本卡域回归通过）。

## ② 修法裁决：测试侧

**依据**：产品无死锁面（上节）；坏的是测试形制——测试用 `subscribe()` 起了 `_consume_loop` 后台任务，却**从未执行任何真实调用方都必须走的关停路径**（`app/main.py` lifespan：`begin_shutdown()` @561 → `await event_bus.close()` @787），把孤儿任务直接丢给 `asyncio.run` 拆循环。修复 = 对齐真实用法：断言后在 `asyncio.run` 退出前 `await bus.close()` 排空消费任务。**未用 sleep、未用 deselect、未动产品代码。**

## ③ 实现清单

仅 1 个文件：`backend/tests/unit/test_eventbus_subscribe_raise.py`（+53/−32）

1. 模块 docstring 增补 EVENTBUS-HANG 生命周期注记（为何必须 drain、机制一句话）。
2. `test_busygroup_proceeds_to_consume_loop`：`_run()` 主体包 `try/finally`，`finally: await bus.close()`——断言失败也不留自旋任务（`close()` 置 `_running=False`、cancel+排空 `_consumer_tasks`、关 mock redis）。
3. `test_consumer_pattern_receives_exception`：重试 while 循环同构包 `try/finally` + `await bus.close()`。
4. `test_non_busygroup_responseerror_raises` 不动（subscribe 在建任务前即 raise，本就不挂）。

排空时序安全性：`_run()` 从 subscribe 返回到 `close()` 之间无挂起点，`close()` 的 `_running=False` + `task.cancel()` 均为同步语句，先于任何让出 → 消费任务在首个 step 前即被标记取消，首个 step 直接 `coro.throw(CancelledError)` 终止；done-callback 里 `.exception()` 对取消任务抛 CancelledError 被吞（exc=None）且 `_running` 已 False → F3 不复活。测试内不新增任何 sleep/等待。

## ④ 冲突面声明

- **本卡触碰**：`backend/tests/unit/test_eventbus_subscribe_raise.py`（仅此一文件，`git status` 干净佐证；`app/gen/` 为 `make proto-gen` 产物，根 .gitignore:242 已忽略，不入 patch）。
- **wt187（loguru 批量）**：无交叠——本 patch 零产品文件、零日志语句（该测试文件本就不 import loguru）；wt187 改 `app/` 日志调用面，与测试文件不相交。当前舰队存活的兄弟 worktree（wt178/wt193/wt194）均不持本文件。
- **wt178（mobile）/wt189（评测资产）/wt190（tests/orchestration）/wt191（study room）**：文件面零交叠。
- **与 wt180 组隔离幂等键（基线已含）共存**：本卡未触碰 `_process_stream_message`/幂等键逻辑；`test_event_bus_group_scoped_idempotency.py` 域回归 5 passed 不变。

## ⑤ 收工核查

- [x] 目标文件 3/3 全绿，无 deselect（`--timeout=60`，0.05s；连跑 3 次稳定）
- [x] 对比法零新增：域 12 文件，基线 `49 passed, 18 skipped, 2 deselected` → 修复后 `51 passed, 18 skipped, 0 deselected`；**逐文件计数 diff = 空**，唯一增量恰为原先 deselect 的 2 条转 pass；skip 全同（活 Redis 6+3 / e2e 9，纪律不动活栈）
- [x] 定向守卫 `scripts/guards/check_rule_az_eventbus_reliability.py` → `[Rule AZ] PASS`
- [x] 无 commit / 无 push；交付 = 本 REPORT + changes.patch（109 行，单文件）
- [x] 收工清理：`/tmp/eventbus-hang-{repro,baseline,postfix}.log` 已删；无独立端口进程（pytest 全前台短命）；无模拟器/浏览器实例
- [x] 环境注记：worktree 内执行过 `make proto-gen`（收集期缺 `app.gen`，生成产物 gitignore，不入库）

## 附：验证命令（口径）

```bash
cd backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  python -m pytest tests/unit/test_eventbus_subscribe_raise.py -q --timeout=60
# 3 passed in 0.05s（修复前：1 passed + 2 无限挂起，20s thread 法栈转储取证）
```
