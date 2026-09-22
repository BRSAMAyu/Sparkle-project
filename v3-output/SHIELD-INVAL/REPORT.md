# SHIELD-INVAL · galaxy 图面双层缓存失效收口 — 交付报告

- Worker：SHIELD-INVAL（V3 舰队）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt140`（基线 `37cac6e8`）
- 交付物：本报告 + `changes.patch` + `verify_probe.py`（同目录）；未 commit / 未 push
- 结论：**API 层 shield 失效面已补齐并三层写路径贯通，活栈 CP-00 假 fail 的根因（shield 回 prime 旧快照）已消除，回归零新增失败**

---

## ① 双层失效方案论证（为何不破坏分层）

### 问题定罪（与主会话活栈实证一致）

`GET /galaxy/graph` 读面有两层进程内/Redis 缓存：

| 层 | 位置 | 机制 | 修复前失效面 |
|---|---|---|---|
| 服务层 | `GalaxyService.get_galaxy_graph` `@cached(ttl=600)`（galaxy_service.py:2270） | Redis 视图键 `{APP_NAME}:view:get_galaxy_graph:{user_id}:*` | ✅ 已有（NBP-4：`invalidate_galaxy_graph_view_cache` + `update_node_mastery` 提交后 `delete_pattern`） |
| API 层 | `_galaxy_graph_shield = EndpointShield(name="galaxy_graph", ttl=10.0)`（galaxy.py） | 进程内 dict：single-flight + 10s TTL + 并发钳制 | ❌ **零失效面**——prime 后写路径无论如何失效 Redis，shield 在 10s 内继续回 prime 旧快照 |

诊断评分路径 `exam_sprint_diagnostic_service._write_mastery_value → GalaxyService.update_node_mastery` 只失效了服务层；shield 层无感知 → 主会话活栈实测「grade 后 +0.5s 取图 mastery 全 null」。

### 选型：核心层失效回调注册表（服务层 → core ← API 层，三角依赖）

被否方案：
- **服务层直接 import API 层的 shield**：违反分层（服务层不得反向依赖 API），且 API 模块未加载时（纯服务调用/单测）直接崩。
- **shield TTL 降到 0（只留 single-flight）**：丢掉恢复风暴场景「5-15s 重复拉取直接命中缓存」的防线，风暴语义受损，否。
- **Redis pub/sub 广播失效**：shield 本就是「零外部依赖、Redis 不可用同样生效」的进程内防线，引入跨进程广播属过度设计。活栈实证吸收消费者与 FastAPI 同进程（`app.main` 中 `OutcomeAbsorptionConsumer` 以 asyncio task 运行，main.py:451-459），进程内回调已覆盖真实拓扑。

**采用方案**（`backend/app/core/request_coalescing.py`）：

1. `EndpointShield.invalidate_prefix(key_prefix) -> int`：按 key 前缀清 TTL 结果缓存（键构与 `run()` 同构，`f"{user_id}:"` 即清该 user 全部参数变体）。**只清已完成结果缓存，不动 `_inflight` 与 semaphore**——single-flight 合并与并发钳制语义原样保留（专项单测钉死）。
2. **回填守卫**：`_compute` 记录计算启动时间戳，`_on_compute_done` 对「启动早于最近一次失效」的计算**不落缓存**——否则「失效 → 在飞旧值完成 → 回填缓存」会把失效悄悄撤销。这是失效语义单调性的关键 5 行。
3. 进程内回调注册表 `register_read_view_invalidation_hook(domain, hook)` / `notify_read_view_invalidated(domain, user_id)`：API 层（galaxy.py）模块导入时把 `_invalidate_galaxy_graph_shield` 挂进 core 注册表；服务层写路径只 `notify("galaxy_graph", user_id)`，**不认识任何 API 符号**。回调闭包在调用时解析 galaxy 模块全局，测试 monkeypatch 替换 shield 实例同样生效；回调异常 notify 内部兜底（只记日志），失效是 best-effort 读投影、绝不阻断写路径（与吸收侧「缓存面不可达只降级不回滚」同款纪律）。

### 接线点（全部既有失效位点追加 notify，共 4 处）

| 写路径 | 文件:位置 | 追加 |
|---|---|---|
| outcome 吸收（`lit`/`flagged`） | `outcome_absorption_service.invalidate_galaxy_graph_view_cache`（:625 helper 内） | 删 Redis 键后 `notify` —— 所有调 helper 的位点自动获得 shield 失效 |
| mastery 更新（REST/手动） | `galaxy_service.update_node_mastery`（commit 后 :3427） | `delete_pattern` 后 `notify` |
| 文档挂载 | `galaxy_service._invalidate_document_attachment_cache`（:1331） | 同款 `notify`（与卡面两处之外多出的一致性收口，1 行，见④） |
| 诊断评分直写分支 | `exam_sprint_diagnostic_service._write_mastery_value`（commit 后） | **补齐完整失效**：`invalidate_galaxy_graph_view_cache(user_id)`（helper 内已含 notify）——该分支（PG 上 update_node_mastery 异常兜底 / sqlite 测试方言）修复前**连服务层 Redis 键都不删**，属同根漏洞一并收口；try/except 包裹，失效失败不回滚已提交评分 |

**诊断路径覆盖确认**：PG 生产主分支 `_write_mastery_value → update_node_mastery → (Redis 删除 + notify)` 全覆盖；直写分支如上独立补齐。两条分支现在双层全失效。

注册时序安全性：hook 在 `app.api.v1.galaxy` 导入时注册，`app.main` 启动链（`from app.api.v1.router import api_router`）保证先于任何请求；未导入 API 模块的纯服务层调用方 notify 为 no-op（返回 0），无导入顺序脆弱性。

## ② 红线面（回归验证）

### 新增测试（红→绿实证）

- `backend/tests/core/test_request_coalescing.py` +4：
  - `test_invalidate_prefix_clears_only_matching_user`：前缀失效只清目标 user 全部变体、不误伤他 user；返回清除计数；
  - `test_invalidation_during_inflight_not_backfilled`：**在飞计算窗口内失效**，旧值交给等待者（single-flight 不破坏）但不得回填缓存，下一请求重算新值；
  - `test_single_flight_and_clamp_survive_invalidation`：失效后 20 并发仍合并为 1 次 loader、零 shed（风暴防护语义红线）；
  - `test_read_view_invalidation_registry`：注册表幂等注册、notify 分发、回调异常吞掉且不影响其他回调、未注册域 no-op。
- `backend/tests/api/test_galaxy_graph_shield_invalidation.py` ×3（httpx ASGI + sqlite，每测注入全新 shield 实例隔离进程全局与事件循环绑定）：
  1. **红线复现**：prime 两层（断言 shield `cache_entries==1` + 服务层本地缓存键存在）→ REST mastery 更新 → **零 sleep** 再取图 → mastery 可见（修复前中 shield 旧快照吞掉）；
  2. 服务层失效 helper 直证同时清 shield 层（`cache_entries: 1 → 0`）；
  3. 诊断评分路径（`_write_mastery_value` 直写分支）→ 立即取图可见 55.0。

**红证**：基线干净 clone（`git clone` 至 /tmp，仅放入新测试文件）跑新 API 测试 → **3 failed**；应用 `changes.patch` 后 → **3 passed**（连同 core 11 个 = 14 passed）。测试不是「修完才写绿」的摆设。

### 回归矩阵（对比法，全部零新增失败）

| 套件 | 基线（37cac6e8） | 修后 | 判定 |
|---|---|---|---|
| `tests/api -k galaxy` | 5 passed | **8 passed**（+3 新） | ✅ |
| `tests/core/test_request_coalescing.py` + `tests/services/galaxy/test_outcome_read_model_visibility.py` | 12 passed | **16 passed**（+4 新） | ✅ |
| `tests/unit -k galaxy` | 4F / 32P / 1S / 3E | **完全相同**（同名单：`test_galaxy_concurrency.py` 3F+3E、theater 1F，均为本机缺 PG 凭据的 asyncpg InvalidPasswordError，环境性既有） | ✅ 零新增 |
| `tests/api/test_exam_sprint_api.py` | 7 passed | 7 passed | ✅ |
| `tests/services/galaxy`（整目录） | — | **93 passed** | ✅ |
| `tests -k diagnostic`（诊断域全域） | 21P+4S（新测试红） | **22P+4S** | ✅ red→green |

**shield 风暴防护红线**：`test_single_flight_merges_concurrent_calls` / `test_concurrency_clamp_limits_parallel_loaders` / `test_shed_when_saturated_beyond_wait_timeout` 等既有 7 个语义测试全数通过，且新增失效后合并/钳制专项。

## ③ 冲突面

- **本卡触碰文件**：`app/core/request_coalescing.py`、`app/api/v1/galaxy.py`、`app/services/galaxy_service.py`、`app/services/galaxy/outcome_absorption_service.py`、`app/services/exam_sprint_diagnostic_service.py`、`tests/core/test_request_coalescing.py`、新增 `tests/api/test_galaxy_graph_shield_invalidation.py`。
- **wt138（迁移错题域）**：无文件交集；其错题域失效链若未来走 `invalidate_galaxy_graph_view_cache` helper 将自动获得 shield 失效，无需改动。
- **wt139（mobile）**：零交集（其消费的是 graph API 响应，行为面对本卡透明）。
- **wt141（冷启动调查，只读）**：零代码交集；本卡在 `exam_sprint_diagnostic_service` 的改动位于写后失效面，不碰冷启动/生成路径。
- **主会话**：`v3-output/SHIELD-INVAL/` 为本卡专属目录，无共享文件。

## ④ 诚实申报

1. **卡面范围外的一致性收口 1 处**：`_invalidate_document_attachment_cache`（文档挂载失效面）也追加了 notify——它删的是同一张 Redis 视图键，不补 shield 失效则属同类缺陷；1 行，已单列说明。
2. **诊断直写分支的服务层漏洞一并修复（超出「确认 shield 也被覆盖」的字面范围）**：实证时发现 sqlite/兜底分支修复前连服务层 `@cached` 视图键都不删（TestClient 复现：prime 后 `_write_mastery_value` 全链无 Redis 失效）；PG 生产仅在 update_node_mastery 抛异常时走到该分支，但一旦走到即 10 分钟级陈旧。已用 helper 补齐并在报告中声明。
3. **`invalidate_prefix` 的回填守卫是 shield 级全局时间戳**（非按 key 粒度）：失效后，任何「启动早于失效时刻」的在飞计算即使属于其他 user 也不落缓存，代价是极低频写路径上的偶发一次重算（miss），正确性优先，语义已注释。
4. **本进程内失效不跨进程**：若未来吸收消费者迁去独立 Celery worker，`notify` 将只清 worker 自己进程的 shield（API 进程收不到）——届时才需要跨进程通道。当前拓扑（同进程 asyncio consumer，main.py 实证）无此问题；已在报告留痕。
5. **shield 有 10s TTL 的天然兜底**：即使失效面意外失灵，最坏陈旧窗口从「必然 10s」退化为「偶发 10s」，且双层失效测试会在此红。
6. **测试环境差异**：`tests/unit -k galaxy` 的 4F/3E 为本机无 PG 凭据的既有环境性失败（基线同一名单），与本卡改动无关；若验收机有可用 PG，该名单应全绿。

## ⑤ 收工核查

- [x] 未 commit / 未 push（`git status`：6 modified + 2 untracked，均为交付物）
- [x] 交付物齐：`REPORT.md` / `changes.patch`（8 文件 765 行，干净基线 clone `git apply --check` 通过 + 应用后 14 passed 实证）/ `verify_probe.py`（语法自检 + `--help` 实证）
- [x] 零凭据（探针自注册一次性账号，密码随机不入输出；测试用 `SECRET_KEY=test`）
- [x] 主仓只读（仅从主仓拷贝 `app/gen/` 至本 worktree 供 import，gitignored 不入库）
- [x] `/tmp` 自清：`/tmp/shield-inval-baseline`、`/tmp/shield-patch-check` 两个基线 clone 已删除
- [x] 无遗留进程（本轮纯 pytest/静态工作，无模拟器/浏览器/长驻服务）
- [x] 磁盘巡检：13Gi 可用（>6G 阈值）；worktree 无 build 产物（pytest 缓存用 `-p no:cacheprovider` 规避）

## 附：verify_probe.py（活栈，留主会话执行）

```bash
python3 v3-output/SHIELD-INVAL/verify_probe.py --base-url http://127.0.0.1:8000
```

流程：注册一次性用户 → 取图 prime（记录 payload 指纹）→ `diagnose/generate`（exam_prep_14d 静态包零 LLM）→ `diagnose/grade`（全答 A、`update_galaxy=true`）→ **零 sleep** 再取图。判定：复读 payload 与 prime 指纹一致 = shield 回旧快照 FAIL；出现带 user_status 的节点且指纹变化 = PASS。退出码 0/1/2（PASS/FAIL/环境错误）。
