# WT341-MEMORYADMIN-RED — memory_admin kill_switch 4 个存量失败：定性+处置 报告

- **base SHA**: `460aa32d`（main，含 wt340 批次；wt340 报告登记的 4 个失败在本批处置）
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt341-memoryadmin-red`
- **触碰面**: 仅 `backend/tests/unit/test_memory_admin_api.py`（+42/−19）。零产品代码改动；galaxy/aurora/goal 链/chat_mode/mobile/gateway 全部未触碰。

## 一、复现（逐字）

`DATABASE_URL="sqlite+aiosqlite:///:memory:"`（backend/.venv python，worktree 无 .env）跑 `tests/unit/test_memory_admin_api.py`：**4 failed, 4 passed**，失败集与 wt340 登记完全一致：

| 测试 | 失败断言 | 实际 vs 期望 |
|---|---|---|
| test_memory_admin_stage18_kill_switches | L215 | `push_delivery_enabled`: `'live' != 'off'` |
| test_memory_admin_stage19_kill_switches | L262 | `consolidation_enabled`: `'live' != 'off'` |
| test_memory_admin_stage21_kill_switches | L309 | `skill_share_enabled`: `'live' != 'off'` |
| test_memory_admin_expanded_aurora_kill_switches | L394 | stage24 `policy_compiler_mode`: `'live' != 'shadow'`（循环内首个非 settings 默认期望即炸） |

四个失败共同日志特征：`kill_switch write_mode called without Redis for NN/xxx; write ignored (mode=...)`（app/core/kill_switch.py:142）。

## 二、定性证据链 → (b) 测试环境错位（装配错误），非产品缺陷

1. **产品写路径是有意的、有文档的设计**：`write_mode` 在 `redis_client is None` 时告警并**忽略写入**（kill_switch.py:141-148），读路径回落 settings 配置（`resolve_settings_mode`）。这与 cache.py AUTH-DEEP A-2 立下的纪律同源：控制面状态绝不允许静默落进程内兜底（多 worker/多实例互不可见、prod fail-open 风险）。Redis 是部署栈一级依赖（make dev-up、CI redis service）。
2. **PUT 响应是诚实的**：端点返回 `get_all()`（当前生效态），flags 反映"写没生效"这一事实，不是返回伪造的提交值。产品语义 = kill switch 是 Redis 内的运行时覆盖，无 Redis 时生效态=settings 态。12+ 个 aurora_stageN 服务共用同一 read_mode/write_mode。
3. **测试自相矛盾（ smoking gun）**：这些测试断言 PUT→GET round-trip 语义（提交值回读），但 stage19/21/expanded **显式把 `cache_service.redis` monkeypatch 成 `None`**，stage18 依赖环境缺省值（同为 None）。`None` 恰好使写入被忽略——断言的翻转从此不可观察，响应 flags 只能回落 settings 默认。
4. **settings 默认全 `"live"`**（settings.py:312-326，含 push_delivery/consolidation/skill_share/stage24），与测试提交的混合值（`False`→期望 `"off"`、stage24 期望 `"shadow"`）必然冲突——精确解释上表 4 个失败点。
5. **同功能服务级测试已给出正确装配先例**：`tests/unit/test_stage18_kill_switch.py:73-85` 的 `_InMemoryKillSwitchRedis`（get/set 内存桩），注释明写 *"None would make flips unobservable"*。本批把同一装配搬到 admin API 测试。
6. **测试进程内 `cache_service.redis` 恒为 None（本地=CI 同态）**：`init_redis()` 只在 app lifespan/celery tasks 调用（app/main.py:212 等），pytest 不起 lifespan；conftest 的 `redis_client` fixture 仅被显式请求才连接且本文件未请求。

## 三、CI 判定：**两个 CI 入口都会红（潜在雷成立，非"sqlite 本地红 CI 绿"）**

| 入口 | 命令 | 判定 | 依据 |
|---|---|---|---|
| ci-pr.yml `python-checks`（PR 触发） | `pytest backend/tests/unit -v --timeout=60 -x -q` | **必红** | 无 redis service、无 REDIS_URL env；全 unit 目录无任何调用方对 cache_service 赋可用 client（两处 init_redis 调用方分别有 `SPARKLE_RUN_REAL_REDIS_TESTS=1` / `E05_LIVE=1` 模块级 skip，且都不在 unit 目录）→ redis=None，与本地复现同失败集；`-x` 使 job 在此中止 |
| ci.yml `backend-test`（push 触发，即交接文档中两次被取消的 Backend Tests） | `pytest backend/tests -v`（redis:alpine service + REDIS_URL env） | **红** | 该 step env 只有 DATABASE_URL/REDIS_URL/TESTING，不设上述两个 skip 钥匙 → init_redis 调用方全 skip；api/integration/services 目录中所有 `cache_service.redis` 赋值均 try/finally 恢复原值（None，逐个核过：test_belief_shadow_real_redis[skip]、test_document_retrieval_isolation[skip]、test_preference_to_plan_e2e[autouse 恢复]、profile_transparency/client_telemetry[finally 恢复]、achievement_reward_observability[finally 恢复]）→ kill_switch 4 测试运行时仍为 None → 同败；该 step 无 -x，4 败全部暴露 |

collection 顺序按目录字母序（api<benchmark<contract<golden<integration<…<services<unit<workflow），先于 unit 的目录无一留下可用 redis client。

## 四、处置（环境错位 → 修测试环境装配，非"为绿而绿"）

- 新增 `_InMemoryKillSwitchRedis` 桩（get/set/delete/incr/expire，内存语义对齐 redis 契约；delete 为 stage28 `reset_bias_streak` 路径所需，incr/expire 为桩完备性），docstring 写明依据并指向服务级先例。
- stage18/19/21：`cache_service.redis` 注入桩（stage18 原先无 patch 靠环境缺省 None，一并显式化）。
- expanded：原对 10 个服务模块逐个 `setattr(None)`（同一单例属性重复赋值本就冗余）→ 改为单次注入桩，注释说明单例共享原理。
- 效果：测试恢复其本意——验证 admin 路由→kill_switch 服务→Redis 落键→回读的完整 round-trip；monkeypatch 逐测自动恢复，无状态泄漏。
- **不修产品的理由**：产品行为正确且有意（见二-1/2）；若把 PUT 改成无 Redis 时报错/本地兜底才是迁就测试改产品，违反定调令。

## 五、结果

- `tests/unit/test_memory_admin_api.py`：**8 passed**（4 个目标测试绿 + 原 4 个存绿不回归）。
- memory/admin 相邻批（memory_api / memory_episodic_governance_api / memory_settings_api / memory_provenance_api / admin_audit）：全绿。
- kill_switch 服务级相邻批（26 文件）：137 passed，**8 failed=存量**（基线克隆 /tmp/wt341-baseline @ 460aa32d 同败集实证，与本批改动无关）：
  - **7 个与本卡同根因**（kill_switch 写入无 Redis 被忽略，同款桩可修）：foresight 4（mode off 写入不生效→attractors/deviations/hints 未按预期清空）、idiographic #1/#3、metacognition #1；
  - **1 个另族**：idiographic #2/#3 伴生 `no such table: idiographic_associations`（app 全局 engine 指向 `:memory:` 每连接空库，与 fixture 引擎不同源——独立环境装配问题）。
  - 均在 aurora 战区文件族，本卡 Forbidden 不越界，**移交主会话派后续卡**（修法可直接复用本报告 §四）。

## 六、收工门

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **EXIT 0**（83 条；gen 三件套已 cp -RL：backend/app/gen、gateway/gen、mobile/lib/gen） |
| 冷 mypy（`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`） | **1278 = 棘轮基线，零漂移** |
| ruff（被碰文件） | **0**（顺带修掉该测试文件 3 处存量 lint：I001×2 + UP017，零语义变化） |
| 定向回归 | 目标文件 8/8 + memory/admin 邻批全绿 |

## 七、/tmp 自产清理

- 删除：/tmp/wt341-baseline（基线克隆）、/tmp/wt341_mypy_cold.txt、/tmp/wt341_guards.log、/tmp/wt341_guards2.log。
