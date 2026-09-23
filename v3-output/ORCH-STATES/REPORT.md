# ORCH-STATES 报告：orchestrator 状态转移测试面 25F+26E 存量败诊断与修复

- Worker：wt188（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt188`，基线 5588ed0a）
- 交付：`v3-output/ORCH-STATES/changes.patch`（1 文件，+89/−19）+ 本报告
- 纪律：零 commit/push；零凭据；零产品代码改动（diff 仅触及 1 个测试文件）
- 结论速览：**25F+26E 全部属于单一根因——(c) 测试基建坏（本地 Redis fixture 漂移）**。测试体零改动、产品零改动，修复后 **26/26 全绿**；相邻编排域对比法零新增。

---

## 0｜卡面勘误（路径与计数对账）

- 卡面路径 `tests/unit/test_orchestrator_state_transitions.py` 已过期：全树（含全部 git 历史）该名字文件只有一份，实际位于 **`backend/tests/orchestration/test_orchestrator_state_transitions.py`**（26 个用例）。
- 51 个结果的数学：26 个用例，每个用例 body 失败（25 个）+ **teardown error（26 个，每用例 1 个）** → 25F+26E=51。pytest 中同一测试可同时产出 FAILED（用例体）与 ERROR（fixture teardown），逐用例叠加所致。与 wt179/wt182 申报完全对账。

## ① 分类诊断表

| 类别 | 判定 | 证据 |
|---|---|---|
| **(a) 测试过期** | **否** | 测试体与现产品语义一致：文件内 R2-03 断言（`DONE→THINKING` 必须拒绝、`DONE→INIT→THINKING` 放行）在修复后 26/26 全部通过，即测试断言的正是 `app/orchestration/state_manager.py:50` 白名单的现行行为。git 考古：6bf07877（G1，序列第 46 commit）专为 R2-03 更新过本文件测试体并报告通过（当时 Redis 可用），之后测试体再未漂移。 |
| **(b) 产品回归** | **否** | `SessionStateManager` 的行为全是**设计内**：`save_state/load_state/update_state/acquire_lock/...` 全部 `try/except Exception → return False/None`（state_manager.py:127-179 等）——Redis 故障时优雅降级、不炸聊天主链路，属容灾语义；R2-03 白名单有独立的兄弟测试 `test_r2_orchestration_fixes.py::test_r2_03_*`（用 `_MemoryRedis`）在同样产品代码上通过。本卡 patch 未触碰任何产品文件。 |
| **(c) 测试基建坏** | **是，全部 51 个结果** | 双层证据见下。 |

**(c) 的机制链（单一根因，两层表现）**：

1. **漂移物**：本文件自带本地 `redis_client` fixture，**冻结于初始 commit 1722e6dc**——它是 conftest HYGIENE-2（ae18bba2，序列第 387 commit）明文点名整改的"旧实现"：直连 `REDIS_URL`（通常 db0）、teardown 裸 `flushdb()`、无 ping-or-skip、无 `sparkle_redis→127.0.0.1` 归一化。该本地 fixture **遮蔽**了 `backend/tests/conftest.py:254` 已加固的规范同名 fixture。
2. **环境事实**：本机 dev Redis 是 docker 容器 `sparkle_redis`，`docker-compose.yml:60` 以 `--requirepass ${REDIS_PASSWORD}` 启动；裸 worktree 无 `.env` → `settings.REDIS_PASSWORD=None` → `resolve_redis_password` 返回 `None`（`redis_utils.py:45`）。实测 `redis-cli ping` → `NOAUTH Authentication required`。
3. **26E 层**：teardown `await client.flushdb()`（原文件 :62）未捕获异常 → `redis.exceptions.AuthenticationError: Authentication required` → 每用例 1 个 teardown ERROR，共 26。
4. **25F 层**：用例体内所有 Redis 命令 NOAUTH，被 `SessionStateManager` 按设计吞掉 → `save_state` 静默 False、`load_state` 返回 None → 形如 `assert saved_state is not None` 的状态断言全塌。唯一例外 `test_empty_session_id_handling`：它只断言 `load_state("") is None`（NOAUTH 恰好也返回 None，断言"歪打正着"通过）且 `update_state` 返回值未被使用 → body 通过。**26 − 1 = 25F**，与卡面精确吻合。
5. **确定性**：两 worker 失败名单 diff 一致 ✓——根因是环境常量（requirepass 容器 + 无密码 worktree）而非抖动。

复现命令与首例证据（修复前）：

```
cd backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  python3.11 -m pytest tests/orchestration/test_orchestrator_state_transitions.py -q
→ ERROR at teardown of ...test_init_to_thinking_transition
    tests/orchestration/test_orchestrator_state_transitions.py:62: in redis_client
    await client.flushdb()
  E   redis.exceptions.AuthenticationError: Authentication required.
→ FAILED ...test_init_to_thinking_transition
    tests/orchestration/test_orchestrator_state_transitions.py:138: assert saved_state is not None
  E   assert None is not None
```

另：干净 HEAD 克隆上该文件在收集期即报 `ModuleNotFoundError: No module named 'app.gen'`（`backend/app/gen/` 为 gitignored 生成产物，`make proto-gen` 或 `scripts/generate_python_protos.sh` 产出）——这是环境前置而非测试面问题；本卡验证环境用主仓同基线生成产物拷入 worktree（proto/ 契约 diff 确认逐字节一致），不入 patch。

## ② 修复裁决链

三个候选处置，逐一审裁：

| 候选 | 裁决 | 理由 |
|---|---|---|
| A. 改产品代码 | **否** | 诊断已证 (b) 不成立：吞错降级与 R2-03 白名单均为设计内行为，且有独立兄弟测试覆盖。无任何产品行为与测试意图冲突，无需 git blame 仲裁语义。 |
| B. 删本地 fixture 落回 conftest 规范 `redis_client` | **否** | conftest 规范 fixture 在 Redis 不可用/不可认证时 `pytest.skip`（ping 失败即 skip）。本机裸 worktree 必然 skip 全部 26 例——表面"无红"，实际把 C 线核心编排测试面**清零**，违背本卡使命（恢复测试资产）。且仍依赖真实 Redis，环境耦合未除。 |
| C. 本地 fixture 换进程内 FakeRedis（**采纳**） | **是** | 与编排域既定惯例完全一致：`test_fsm_state_real.py` 的 `FakeRedis`、`test_r2_orchestration_fixes.py` 经 r2 helpers 的 `_MemoryRedis`——同域 Redis 依赖单测一律走内存桩，任何机器确定性可跑。北极星语义：FSM 状态转移/锁/续期/TTL 是编排域核心资产，应作为**真实持续执行的测试**存在而非环境人质。同时消除 HYGIENE-2 红线（teardown flushdb 共享库）——旧 fixture 在"密码恰好可用"的环境里会 flushdb 打到 db0 开发数据。 |

修法一句话：**删除直连真实 Redis 的本地 `redis_client` fixture，替换为覆盖 `SessionStateManager` 最小命令面（set/setex/get/delete/ttl/eval compare-and-del|expire/nx-ex）的进程内 `_FakeRedis`，TTL 用单调钟过期模型使"状态 TTL 过期"用例确定性可测；26 个测试体一行未动。**

## ③ 实现清单

| 文件 | 改动 |
|---|---|
| `backend/tests/orchestration/test_orchestrator_state_transitions.py` | ① 新增 `_FakeRedis` 类（约 80 行，含动机文档）；② `redis_client` fixture 改为 yield `_FakeRedis()`；③ imports 调整：去 `redis.asyncio`，加 `math`/`time`。其余（`mock_orchestrator` fixture、全部 26 个测试体、断言）零改动 |

FakeRedis 关键设计点：
- `eval` 按 Lua 脚本内容分派 `del`（release_lock）/`expire`（renew_lock）两分支，其余脚本显式 AssertionError（防测试桩静默错配）；
- `ttl()` 与真实 Redis 语义对齐：秒数向上取整（`math.ceil`）、无过期键 -1、不存在键 -2——`test_lock_renewal_extends_ttl` 的 `renewed_ttl == lock_ttl` 断言因此稳定成立；
- 过期惰性判定（`get/ttl/delete/set` 前先 `_expire_if_due`），`test_state_ttl_expiration` 的 `sleep(1.1)` 过期路径确定性通过；
- 无 await 悬点 → 并发更新用例（`asyncio.gather` 10 路）顺序化执行，结果确定。

## 验证（同环境同命令红→绿）

```
修复前：SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
        python3.11 -m pytest tests/orchestration/test_orchestrator_state_transitions.py
  → 25 failed, 26 errors（每用例 teardown NOAUTH + body load None；首例证据见 §①）
修复后：同命令
  → 26 passed, 7 warnings in 4.99s
```

**相邻域对比法（零新增）**：

| 时点 | 范围 | 结果 |
|---|---|---|
| 修复前（HEAD，`--ignore` 目标文件） | `tests/orchestration/` 其余 19 文件 | **10 failed, 158 passed**（失败集中：process_stream_integration 6、planning_workflow 3、round1_p2_fixes 1——均为存量） |
| 修复后（全目录） | `tests/orchestration/` 全部 20 文件 | **10 failed, 184 passed**（158+26 全绿目标例；失败名单与基线**逐条一致**，零新增零消失） |

## ④ 冲突面声明

- 本卡 patch 触及文件**有且仅有 1 个**：`backend/tests/orchestration/test_orchestrator_state_transitions.py`（+89/−19）。
- **wt187（全仓 loguru 批量）**：实测其 worktree 当前变更仅 2 个未跟踪扫描脚本（`_loguru_fix.py`/`_loguru_scan.py`），其清单与本卡文件零交集；且本卡触及的测试文件内**无任何 logging/loguru 语句**（loguru 批量按日志行改写，本文件无可改行）→ **hunk 错位风险：无**。
- **wt178（mobile）/ wt180（event_bus+网关）/ wt186（部署监控）**：与本卡（backend 编排域测试文件）无文件交集，无风险。
- 本卡未触碰 `app/orchestration/`（产品）、`state_manager.py`、`orchestrator.py`、`proto/`、`backend/gateway/`。

## ⑤ 收工核查

- [x] 禁止 commit/push：未执行（`git status` 仅 1 个 modified 测试文件 + 未跟踪 `v3-output/ORCH-STATES/`）
- [x] 零凭据：报告中无密码/密钥；`.env` 未读未拷未建（密码仅以"存在性"引用）
- [x] tmp 清理：`/tmp/orch-baseline-wt188.txt` 已删；无其他 tmp 产物
- [x] 无遗留进程/模拟器/Docker 变更（仅对 Redis 做过只读 ping 探测；旧 fixture 的 flushdb 因 NOAUTH 从未真正执行，共享库零写入）
- [x] `backend/app/gen/`（gitignored 生成产物）留于 worktree 内随 worktree 回收，不入库不入 patch
- [x] 相邻域存量 10F（process_stream_integration/planning_workflow/round1_p2）**未动未修**——不在本卡范围，建议主会话另行立卡（与 G1 申报的 9F 同族，现存 10F，其中 1F 可能是后续演进新增，未深查）

## 范围外观察（申报给主会话，未动）

1. **同型漂移面排查**：全仓仅此一处本地 fixture 遮蔽规范 `redis_client`（编排域其余 Redis 依赖测试均已走内存桩），本卡修复后无残留同型债。
2. `test_orchestrator_process_stream_integration.py` 等 10 个存量红与本卡根因无关（其失败不涉 Redis 认证），未诊断未修复。
