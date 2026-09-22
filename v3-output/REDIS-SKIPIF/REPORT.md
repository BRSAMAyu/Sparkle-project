# REDIS-SKIPIF 收工报告 — test_redis_fixture_isolation 密码环境条件红收口

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt153`（基线 `6f647323`）
- 交付物：本报告 + `changes.patch`（唯一改动文件 `backend/tests/unit/test_redis_fixture_isolation.py`）
- 日期：2026-09-22

## ① 修法选择论证

**根因**：`TestRedisClientFixtureIsolation::test_fixture_writes_visible_and_scoped` 的 probe
裸连接只从 `connection_pool.connection_kwargs` 挑了 `host`/`port`，再配 `db=TEST_REDIS_DB`
手工重构同步 `Redis(...)`，丢掉了 `password`（及潜在 `username`）。fixture 侧
（`backend/tests/conftest.py:254-273`）经 `resolve_redis_password` 正确带 auth，于是
带密码的 redis（主仓 dev 环境）下 fixture 写入成功、probe 读取 → `AuthenticationError`
——环境条件性假红，与隔离逻辑本身无关。

**选型**：卡片给了两条路——(a) probe 复用 fixture 同款连接参数；(b) 对需认证环境
`pytest.mark.skipif` 跳过。选 **(a)**：真验证优于跳过。skipif 只能把红藏起来，让该用例
在带密码环境失去守卫价值；而 (a) 让 probe 与 fixture 永远共享同一份连接事实，后续
conftest 若新增连接参数（TLS、socket 超时等）也自动跟随，无第二处漂移点。

**改动（最小，+9/-7 行，仅测试文件）**：

```python
probe_kwargs = dict(redis_client.connection_pool.connection_kwargs)
probe_kwargs.setdefault("socket_connect_timeout", 2)
probe = Redis(**probe_kwargs)
```

运行时实证过 `connection_kwargs` 实际内容为 `{db, decode_responses, encoding, host,
password, port}`，全部是 `redis.Redis.__init__` 合法参数；URL 带 username 时 from_url
也会把它放进 kwargs，`Redis(**kwargs)` 同样接受。probe 仍是**独立新连接**（新 socket），
「数据确实落在隔离 DB」的验证语义不变。未改 conftest / app 代码，未用 skipif。

## ② 双环境验证结果

一次性容器（`redis:7-alpine`，用完即停删）：

| 场景 | env | 结果 |
| --- | --- | --- |
| 基线（改动前）·无密码 | `REDIS_URL=redis://127.0.0.1:16379/0` | 7 passed |
| 基线（改动前）·密码 env | `:16380/0` + `REDIS_PASSWORD=testpw` | 1 failed（AuthenticationError，复现卡片所述红），6 passed |
| 基线（改动前）·密码 URL | `redis://:testpw@127.0.0.1:16380/0` | 1 failed（同上），6 passed |
| 修复后 ·无密码 | `:16379/0` | **7 passed** |
| 修复后 ·密码 env | `:16380/0` + `REDIS_PASSWORD=testpw` | **7 passed** |
| 修复后 ·密码 URL | `redis://:testpw@127.0.0.1:16380/0` | **7 passed**（逐用例 -v 确认） |

密码场景双传递方式（env 变量 / URL 内嵌）都覆盖：主仓 dev 两种配置习惯下都绿。
测试密码仅用占位 `testpw`，零真实凭据。

## ③ 冲突面

零交集。改动面 = 单个测试文件 `backend/tests/unit/test_redis_fixture_isolation.py`；
在途卡全在 galaxy/grpc/events 域，不触碰该文件与 `tests/conftest.py`。

## ④ 诚实申报

1. **回归收集错误（基线既有，非本次引入）**：`tests/unit/test_state_manager_real_redis.py`
   收集期 `ModuleNotFoundError: No module named 'app.gen'`——本 worktree 未跑
   `make proto-gen`/`make sync-db`，生成代码缺失所致。已按纪律用
   `git clone <worktree> /tmp/wt153-baseline` 干净基线对照：克隆（不含本次改动）同样
   报错，证明基线既有；且该错误发生在 import 期，与本次 diff（纯测试内逻辑）无因果。
2. **回归族范围**：相邻 redis fixture 消费族取 `tests/unit/test_distributed_lock_real_redis.py`
   + `test_event_bus_real_redis.py` + 目标文件 = 21 passed × 双环境（16379 / 16380+testpw）
   零新增红。更大范围消费族（integration/orchestration 等几十个文件）未全跑——本卡为
   micro 卡且改动不触及 conftest/应用代码，import 期之外的涟漪面为零；如需全量回归
   由主会话决断。
3. pytest 运行环境复用了主仓 venv 解释器（`Sparkle-project/backend/.venv`，只读执行）；
   worktree 无自带 venv。所有运行显式注入 `SECRET_KEY`（一次性随机占位值，未落盘）与
   `REDIS_URL`，避免 settings 默认值指向主仓 dev redis（:6379）——全程未触碰真 dev redis。
4. 未 commit / 未 push，主仓零写入（含零 `.env` 写入）。

## ⑤ 收工核查

- [x] 容器 `wt153-redis-nopw`（:16379）、`wt153-redis-pw`（:16380）已 stop 并随 `--rm` 删除，`docker ps` 确认为空
- [x] `/tmp/wt153-baseline` 基线克隆已删除
- [x] 无其他 /tmp 残留；无构建产物落盘
- [x] worktree 变更仅 `M backend/tests/unit/test_redis_fixture_isolation.py`（git status 确认），交付物在 `v3-output/REDIS-SKIPIF/`
- [x] 主仓只读纪律、内存纪律（LIGHT 任务，无模拟器/Gradle/浏览器）全程遵守
