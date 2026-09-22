# PHASE4-RED 收工报告 — test_phase4_galaxy_services.py 存量红清偿

- Worker: V3 舰队 Worker（micro 卡）
- Worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt127`
- 日期: 2026-09-22
- 结论: **文件全绿（24 passed, 0 warnings），生产代码零 diff，纯测试夹具漂移修复**

---

## ① 基线红证（改前失败清单原文）

```
$ cd backend && SECRET_KEY=test /opt/homebrew/bin/pytest tests/test_phase4_galaxy_services.py -q

_______ TestPhase4Integration.test_event_flow_task_complete_to_websocket _______
tests/test_phase4_galaxy_services.py:457: in test_event_flow_task_complete_to_websocket
    event_listener = TaskEventListener(mock_db, feedback_service, mock_event_bus)
E   TypeError: TaskEventListener.__init__() takes 3 positional arguments but 4 were given
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_event_listener_initialization
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_on_event_task_completed
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_on_event_error_created
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_on_event_task_abandoned
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_on_event_unknown_type
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_stop
ERROR tests/test_phase4_galaxy_services.py::TestTaskEventListener::test_shutdown_closes_event_bus
==================== 1 failed, 16 passed, 7 errors in 0.48s ====================
```

实际基线为 **1 FAILED + 7 ERROR（8 个红）**，任务卡预估的第 2 个 FAILED 即
`TestTaskEventListener::test_on_event_error_created`——它在构造函数修复前根本到不了断言行
（setup 即 ERROR）；构造函数一修，其断言 `mock_feedback_service.collect_implicit_feedback.called`
必然转为 FAILED（注入式 mock 在现契约下永不被调用）。本次连同该断言一起修，合计清偿 **9 处测试结局**。

## ② 契约判定（生产代码为准）

`TaskEventListener.__init__`（`backend/app/services/galaxy/event_listener.py:45`）自 **Initial commit
(1722e6dc) 起就是 2 参**，此后唯一改动 f2ee1d2c 仅是 f-string 去前缀（cosmetic）：

```python
def __init__(self, session_factory: Any, event_bus: EventBus):
```

生产实例化（`app/main.py:438-441`）：

```python
task_event_listener = TaskEventListener(session_factory=AsyncSessionLocal, event_bus=event_bus)
```

- **event_bus 仍走构造函数**，未被误删注入能力；
- **feedback_service 不再（从未）注入**——监听器在事件处理内部按会话自建
  `GalaxyFeedbackService(db)`（event_listener.py:174、221）；
- `GalaxyFeedbackService(db, redis_client=None)` 签名未变，集成测试该行无需改。

**判定：纯测试夹具按想象中的旧契约书写、从未绿过；生产代码无功能缺失，零改动、零恢复。**

## ③ 修复清单（9 处逐项）

改动仅 `backend/tests/test_phase4_galaxy_services.py` 一个文件：

| # | 测试 | 错 | 修 |
|---|------|----|----|
| 1-7 | `TestTaskEventListener` 7 个（initialization / task_completed / error_created / task_abandoned / unknown_type / stop / shutdown_closes_event_bus） | setup 即炸：fixture 传 3 参 `(mock_db, mock_feedback_service, mock_event_bus)`，现契约收 2 参 `(session_factory, event_bus)` | fixture `event_listener` 改为 `TaskEventListener(mock_session_factory, mock_event_bus)`；新增 `mock_session_factory` fixture：`Mock(return_value=mock_db)`，镜像生产 `AsyncSessionLocal`（同步工厂→async-with 会话） |
| 8 | `test_on_event_error_created` | 构造修复后断言失配：`mock_feedback_service` 不再被注入，永不被调用 | 按现契约 patch 监听器模块内的服务边界：`patch("app.services.galaxy.event_listener.GalaxyFeedbackService", return_value=mock_feedback_service)`，原断言语义保留（error_created → 收集负反馈） |
| 9 | `TestPhase4Integration::test_event_flow_task_complete_to_websocket` | 同 TypeError：`TaskEventListener(mock_db, feedback_service, mock_event_bus)` 3 参 | 改为 `TaskEventListener(mock_db, mock_event_bus)`（session_factory + event_bus）；`GalaxyFeedbackService(mock_db, mock_redis)` 行签名未变，保留 |

夹具保真度顺带修正（消 5 个 RuntimeWarning，非红但属 mock 失真）：

- `mock_db.add = Mock()` —— `AsyncSession.add` 本是同步方法；
- `db.execute = AsyncMock(return_value=Mock(scalar_one_or_none=...))` —— `execute` 需 await、Result 方法是同步；
- `db.__aenter__.return_value = db` —— 使 `async with session_factory() as db` 产出配置过的同一 mock，而非匿名子 mock。

## ④ 测试结果

```
$ SECRET_KEY=test /opt/homebrew/bin/pytest tests/test_phase4_galaxy_services.py -q
============================== 24 passed in 2.24s ==============================   （0 warnings）

$ SECRET_KEY=test /opt/homebrew/bin/pytest tests/test_phase4_galaxy_services.py tests/test_event_bus_shutdown.py -q
============================== 25 passed in 2.15s ==============================
```

回归说明（相邻 galaxy/event/task 扫描）：

- `tests/test_f16_galaxy_weak_node_injection.py` 出现 1F+3E —— 已用 HEAD 干净克隆
  （`git clone wt127 /tmp/ph4red-baseline`， sanctioned 方法）复跑，**HEAD 基线同红**；
  根因是本 worktree 未生成 `app.gen`（`make proto-gen` 未跑，gRPC 产物缺失），
  属环境预存问题，与本卡无关，未动。
- `tests/test_plan_task_*_production.py` 同因 `No module named 'app.gen'` collection error，预存，未动。
- 全 `tests/` 目录 `-k` 扫描会触发 202 个无关 collection error（模块级 DB/env 导入），
  按内存纪律不做全库收集，以定向文件扫描为准。

## ⑤ Worker 五要素

1. **基线红证**：见 ①，原文保留（1 FAILED + 7 ERROR；任务卡的"第 2 个 FAILED"实为构造修复后才显形的 `test_on_event_error_created` 断言失配）。
2. **红线面**：只改 `backend/tests/test_phase4_galaxy_services.py`；`git status` 唯一改动即该文件，**生产代码零 diff**。无功能缺失，无恢复性改动需要论证（event_bus 注入能力健在）。
3. **冲突面**：本卡只动 `tests/test_phase4_galaxy_services.py`；已知在途卡均不涉及该文件，无冲突。
4. **诚实申报**：
   - 按当前行为修改的断言：#8（error_created 改为 patch 模块内 `GalaxyFeedbackService`，语义等价：验证事件触发反馈收集）；#9（构造参数对齐现契约）。
   - **功能疑点**：未发现生产回归。但记录两点观察：(a) `test_on_event_task_completed` / `test_on_event_task_abandoned` 本身无副作用断言，监听器内部 try/except 吞掉一切异常，测试只能证明"不炸"，证明不了"更新生效"——历史即如此，未越权加强；(b) `test_event_bus_shutdown.py` 中 `TaskEventListener.stop()` 用 `getattr(event_bus, "close")` 判协程后 `create_task`，属生产现状，未动。
5. **收工核查**：无 commit/push；无新增进程/模拟器/构建产物；`/tmp` 探针克隆已删；`v3-output/PHASE4-RED/` 下仅 REPORT.md + changes.patch；worktree 干净（除本卡两交付物 + 测试文件改动）。
