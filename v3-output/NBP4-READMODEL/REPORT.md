# NBP-4 · 任务完成 → 星图读模型可见延迟消除 — 收工报告

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt132`（分支 `wt132-v3`，基线 `b7956f1c`）
- 交付物：`REPORT.md`（本文）、`changes.patch`、`verify_probe.py`、代码改动 2 文件、新测试 1 文件
- 红线声明：**零迁移**（`alembic heads` 单头 `cp01confirm_20260922` 未动）；**零凭据**；未 commit/push；主仓与演示 DB 只读

---

## ① 延迟归因链（配置值/行号证据）

任务卡给出的 `task_complete_galaxy_outbox` 表名在代码库**不存在**（全库 grep 零命中）。真实链路与逐段计时归因如下：

```
任务完成（TaskService.complete / execution_service / execution_ingestor）
  → capture_task_outcome → event_bus_reliable.publish("outcome.recorded")
     app/services/outcome_capture_service.py:192  —— 直连 Redis XADD，无缓冲、无 outbox 周期，≈0ms
  → OutcomeAbsorptionConsumer（app/main.py:451 启动）
     app/core/event_bus.py:1316-1321  xreadgroup block=2000 —— 消费延迟 ≤2s
  → GalaxyOutcomeAbsorber._absorb_positive（Kalman 融合 → UserNodeStatus + mastery_audit_log）
     app/services/galaxy/outcome_absorption_service.py:186-241 —— DB 写，秒级
  → ★ 星图读 API（分钟级延迟病灶在这里）
     GET /galaxy/graph（网关）→ GetGraph(galaxy_handler.go:531)
       → gRPC GetUserGalaxy（galaxy_grpc_service.py:290）/ REST 回源 app/api/v1/galaxy.py:206
       → GalaxyService.get_galaxy_graph —— @cached(ttl=600)
         app/services/galaxy_service.py:2268-2271 ★★ 读面视图缓存 10 分钟 TTL ★★
```

**根因（单点）**：`get_galaxy_graph` 挂 `@cached(ttl=600, ...)` 视图缓存（键面 `{APP_NAME}:view:get_galaxy_graph:{user_id}:*`，实测 APP_NAME=`Sparkle`）。任务完成的吸收链把掌握度写进 DB 后，**从不失效这个缓存** → 读面最长陈旧 600s，即 LOOP3 实测的「分钟级才可见」。

**旁证（为什么偏偏是 outcome 链慢）**：掌握度的其他写路径全部有提交后失效——
- `GalaxyService.update_mastery`：galaxy_service.py:3424 `delete_pattern(...get_galaxy_graph...)`（提交后）；
- `GalaxyStatsService.spark_node`：stats_service.py:264-265（"9. Invalidate Cache"，覆盖 task.completed legacy spark 与网关手动点亮）；
- **唯独 G-02 outcome 吸收路径（新链）没有**——与实测「吸收可达（40→30→34 链路活栈证明）、但读面分钟级不见」完全吻合。

**排除项（都有证据）**：
- outbox 派发周期：Go 网关 CQRS outbox 轮询 `PollInterval: 100ms`（internal/cqrs/outbox/publisher.go:50），非瓶颈；
- 消费循环：`block=2000`（2s），非分钟级；
- 网关二层缓存：`invalidateGalaxyGraphCache`（galaxy_handler.go:365）删除的 `galaxy:graph:<uid>` 键全库**无写入点**（死代码），网关 GetGraph 每次回源 Python；
- REST 路由 `EndpointShield`（app/api/v1/galaxy.py:66）进程内 ttl=10s 风暴保护：gRPC 主读路径（网关默认分支）不经过它；10s 亚分钟、保设计不动，如实申报为残余窗口。

**次生病灶（一并修）**：`CacheService.delete_pattern`（app/core/cache.py:169）在无 Redis 兜底模式（本地 `_local_cache`）下是 **no-op**——`@cached` 写进本地缓存的键删不掉。这意味着在 Redis 不可达/测试环境下，连 `update_mastery`/`spark_node` 的既有失效也形同虚设。

## ② 修复裁决（最小侵入，NBP-6「写后即时投影/缓存失效」形态）

不引入即时派发、不改扫描周期（发布是直连 XADD，本就没有周期可缩）；不缩短 ttl=600（会伤全图读缓存命中率）。选择**写后失效**，共 2 个生产文件：

1. **`backend/app/services/galaxy/outcome_absorption_service.py`**
   - `absorb_outcome` 提交后（`await self.db.commit()` 之后）：`result.action ∈ {"lit","flagged"}` 时调用新 helper `invalidate_galaxy_graph_view_cache(user_id)`，删除 `{APP_NAME}:view:get_galaxy_graph:{user_id}:*`。与 `update_mastery` 提交后失效**同款同键**；best-effort try/except，缓存面故障只降级告警、不回滚吸收真源。
   - `duplicate/recorded_only/corrected/no_target` 读面零变化 → 不产生失效流量（重放幂等零开销）。
   - 负载影响：每次可见吸收 1 次 Redis SCAN（按 user 前缀，键数=读参数组合数，个位数）+ DEL，**default/glm_batch 队列零参与**，无回积面。
2. **`backend/app/core/cache.py`**
   - `delete_pattern` 兜底模式剔除 `_local_cache` 匹配键（fnmatch），返回删除计数；Redis 模式语义不变。修掉「失效面在兜底模式下整体失灵」的回归坑，惠及既有全部失效调用方。

**否决项**：`spark_node`/`update_mastery` 无需改动（它们已有失效）；不在 API 层动 EndpointShield（风暴保护，10s 残余窗口如实申报）；不动 wt129 的幂等键面。

## ③ 测试矩阵（对比法，同命令同过滤）

命令：`cd backend && SECRET_KEY=test /opt/homebrew/bin/pytest tests -q -k "galaxy or absorption or outcome or outbox" --ignore=tests/northstar_eval`

| 轮次 | 结果 | 失败集 |
|---|---|---|
| 基线（b7956f1c，跑了 2 次互相印证） | 7 failed, 520 passed, 4 skipped, 3 errors | 见下 |
| 修复后 | 7 failed, **525** passed, 4 skipped, 3 errors | **与基线完全同集** |

基线=修复后失败集（全部**存量失败**，与本卡无关，逐一核对失败原因未受修复影响）：
- `tests/unit/test_galaxy_concurrency.py` 3 项（FAILED+ERROR，revision 相关，sqlite 方言存量问题）
- `tests/integration/test_north_star_journey.py::test_task_completion_updates_galaxy_mastery`（sprint mastery 面断言 0.25，其内 `event_bus_reliable.publish` 被 mock，吸收链不参与，存量失败）
- `tests/unit/test_intervention_outcome_tracker.py`、`tests/unit/test_outcome_promotion_governor.py`、`tests/unit/test_theater_seed_and_accuracy.py`（存量）

新增测试（`backend/tests/services/galaxy/test_outcome_read_model_visibility.py`，5/5 绿，全部零 sleep）：
1. `test_absorbed_outcome_visible_on_galaxy_graph_immediately` —— 预热图缓存 → 吸收 → **立即**重读，掌握度=融合后 30.0；
2. `test_read_model_cache_really_invalidated_between_reads` —— 直证缓存键被失效（键面观察）+ 读面换新值；
3. `test_invalidation_fires_on_visible_actions_only` —— lit 失效 1 次、duplicate 重放 0 次（精确性）；
4. `test_negative_flag_invalidates_read_face` —— flagged（弱点标记入图）触发失效；
5. `test_delete_pattern_evicts_local_cache_fallback` —— 兜底模式失效语义回归坑直证。

**红绿对照（诚实性证据）**：把 2 个生产文件临时还原为基线版，独立红测复现病灶——DB 日志显示吸收成功（`mastery 0.0 → 30.0`），但立即重读星图 `user_status=None`（命中 ttl=600 旧缓存）→ 测试红；恢复修复版 → 同流程 19/19 绿（新 5 + 既有 absorption 14）。

## ④ verify_probe.py 用法（活栈验证留主会话）

`v3-output/NBP4-READMODEL/verify_probe.py`（API 级、零凭据、零 DB 直连，面向运行中的 Python 引擎 :8000）：

```bash
python3 v3-output/NBP4-READMODEL/verify_probe.py --base-url http://127.0.0.1:8000
# 可选：--timeout 120 --poll-interval 0.2 --threshold 60
```

流程：注册一次性用户 → GET /galaxy/graph 预热 → 建任务 → start→complete → 自完成时刻 0.2s 轮询星图读面直到任务星 mastery>0。输出延迟与判定：`PASS < 60s`（分钟级消除），首拍 <1s 额外标注「亚秒级」（NBP-6 同款爽点）。退出码 0/1/2。注意经网关验证时走 `:8080` 同路径亦可（GetGraph 会回源 Python 同一读面）。

## ⑤ 冲突面（重点：与 wt129 absorption 幂等的文件交集声明）

- **`backend/app/services/galaxy/outcome_absorption_service.py` 与 wt129 同文件**。wt129 动**幂等键（读侧去重）**：预期 hunk 落在 `_already_absorbed`（≈L364-398）、`_request_id_segments`/`_evidence_request_id`/`_outcome_hex`（≈L488-514）。
- 本卡在该文件只动 3 处，**全部与上述 hunk 不相交**（追加式为主）：
  1. 模块 docstring 末行「零 Redis 依赖」后追加 NBP-4 注记（≈L43-46）；
  2. `absorb_outcome` 尾部 `await self.db.commit()` 与 `return result` 之间插入失效块（≈L166-174）；
  3. 文件尾部新增 `_READ_MODEL_VISIBLE_ACTIONS` + `invalidate_galaxy_graph_view_cache` + `__all__` 追加（≈L592-616 起）。
  → 3way 合并预期零冲突；若 wt129 改动波及 `absorb_outcome` 主体，冲突面唯一候选即第 2 处 hunk。
- 其余改动文件（`app/core/cache.py`、新测试文件、v3-output）与 wt129 无交集。

## ⑥ 诚实申报

1. **残余 10s 窗口**：REST 直连路径的 `EndpointShield`（进程内 ttl=10s，galaxy.py:66）与本次失效不同步——完成后的前 10s 内该入口可能仍吐旧图。gRPC 主路径（网关默认分支）无此层。10s 亚分钟、属风暴保护设计，未动；若主会话要求极致，可在 absorb 后调 `shield._cache.clear()`（需反向 import api 层，裁决留给主会话）。
2. **失败语义**：失效失败（Redis 抖动）时最坏退回 TTL 自然过期（≤600s）——best-effort 是与 `update_mastery` 同款的既有权衡，未引入新的强依赖。
3. **基线跑批口径**：10955 deselected 的定向集里 7 失败/3 错误均为存量（两次基线互证 + 逐项失败原因比对），非本卡引入；`test_task_completion_updates_galaxy_mastery` 存量失败与 absorber 无关（事件发布被 mock），已在上文说明。
4. `app/gen/` 从主仓拷贝入 worktree（gitignored，未入 git）；`/tmp` 探针与基线日志收工自清。
5. 活栈未验证（按卡留主会话，探针已交付）；Go 网关测试未跑（网关零改动，`git diff` 可证）。

## ⑦ 收工核查

- [x] worktree 内改动仅 2 生产文件 + 1 新测试 + v3-output 3 件（`git status` 干净可查）
- [x] 无 commit/push；index 已还原（`add -N → diff → reset -q` 流程生成 changes.patch）
- [x] 零迁移（alembic 单头 `cp01confirm_20260922`）；零凭据入交付物
- [x] 无遗留进程（本卡未起任何服务/模拟器）；`/tmp/nbp4_*` 已清理
- [x] 内存纪律：全程 LIGHT（pytest 单进程定向跑批，无模拟器/构建）
