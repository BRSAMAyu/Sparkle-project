# WT333-MYPY-BURN4 — mypy 烧减批 4（union-attr 余量）报告

- **base SHA**: `24f2a245`（main @ 开工时）
- **final SHA**: 分支 `wt333-mypy-burn4` 最新 commit
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt333-mypy-burn4`
- **家族选择与理由**: 继续 **union-attr 余量**（base 171 条）。理由：wt331 已建立完整修法先例（局部绑定收窄 / None 短路 / 防御分支），同族延续风险最低、可机械核验；arg-type(370)/assignment(244) 体量更大但更分散且 wt325 刚做过 arg-type，同文件二烧易生语义冲突。实测本批把 union-attr 171→105，其余 -8 条来自同文件邻近家族（为修复正确类型而连带消除）。
- **战区回避声明**: 未触碰 wt326 战区（growth_dashboard_service.py、chat_mode 枚举一线、user_settings_service.py / api/v1/users.py / api/v1/user_settings.py / api/v1/goals.py 目标创建激活链）；未触碰 wt330 刚合入的 galaxy 文件（api/v1/galaxy.py、schemas/galaxy.py、galaxy/title_sanitizer.py、galaxy_grpc_service.py、galaxy_service.py），且进一步整个 `app/services/galaxy/` 目录零触碰；未触碰 mobile/gateway 任何文件；未改 `quality/mypy_baseline.txt`（保持 1449，Forbidden 条款）。开工时核对 wt330/wt331/wt332 三个已合 commit 的 diff 文件清单后确定的回避集合。

## 消减数（冷缓存复验，ratchet 同口径 `mypy app --ignore-missing-imports --no-error-summary`）

| 口径 | base | final | Δ |
|---|---|---|---|
| 总错误 | 1449 | **1375** | **−74** |
| union-attr 族 | 171 | **105** | **−66** |

- 环境：worktree 无自有 venv，复用主仓 `backend/.venv` 的 python 以 `-m mypy` 运行（cwd=worktree/backend，.mypy_cache 落在本 worktree，主仓零写入）。base 与 final 均为冷缓存双跑验证。
- **零新增证明（方法）**：对 base SHA 冷缓存全量清单（/tmp/wt333/base_errors.txt）与本批 final 冷缓存清单（/tmp/wt333/final_errors.txt）做「去行号归一化 + multiset 差集」：`file::msg[code]` Counter 对比，**新增实例 = 0，消除实例 = 74**。中途曾出现 7 条新增（worker 6 条 [operator] + telemetry 1 条 [assignment]）——均为「Optional 联合变正确类型后暴露的下游既有隐患」，见「修法类别 7」，已当场修正归零后重跑冷缓存确认。

## 逐模块烧减表（union-attr，冷缓存口径）

| 模块 | base | 烧减 | 修法 |
|---|---|---|---|
| services/community_signal_collector.py | 6 | 6 | 3 个私有方法 redis None 短路（局部绑定，返回值与原异常路径一致：None/0/[]，wt331 chat_signal_collector 同款） |
| workers/signals_learning_worker.py | 5 | 5 | 3 个私有方法 session 局部绑定 + None 显式 RuntimeError（调用方 run_daily_analysis 既有宽 except 兜底语义不变） |
| orchestration/context_builder.py | 6 | 6 | `last_correction_effect` 双调用表达式局部绑定；`_persist_user_message` 形参注解 `AsyncSession \| None`→`AsyncSession`（唯一调用方已有 `if active_db` 守卫，原 `| None` 系注解谎言） |
| services/graph_reasoning_service.py | 5 | 5 | `generate_learning_path` 顶部 graph 局部绑定 + None 防御分支（返回既有 graph_error 契约）；`_build_path_node_payload`/`_build_related_nodes` 增加 `graph: nx.DiGraph` 参数化传图（消除方法间 self.G 不可跨方法收窄） |
| services/experience_phase_evaluator.py | 5 | 5 | `decision_context`×2、`grounding_runtime` 双调用表达式局部绑定（显式 `dict[str, Any]` 注解） |
| services/expansion_service.py | 4 | 4 | `db.get()` 返回 None 显式 ValueError（触发节点不存在原为 AttributeError，同类外抛） |
| services/evidence/reward_model.py | 4 | 4 | `metadata`/`source_metadata` 双调用表达式局部绑定 |
| orchestration/soul_compiler.py | 4 | 4 | `user_preferences`、`visible_update_context` 双调用表达式局部绑定 |
| orchestration/session_state_mixin.py | 4 | 4 | `metadata` 双调用表达式局部绑定 |
| aurora/runtime_v1/telemetry.py | 4 | 4 | `build_summary` db None 显式 RuntimeError（API 唯一调用方恒有 db；构造 db=None 实例只用于 redis 侧，不受影响）；`_cleanup_expired`/`_backfill_previous_outcome` db None 早退（与 record_turn 既有 None 短路语义一致） |
| aurora/runtime_v1/planning.py | 4 | 4 | `note_detour` 的 `_top_open_tension(state)` 双调用→单次绑定；`_recompute` 的 `select_next_tension(state)` 双调用→单次绑定；`_state_from_snapshot` current_intent/activity_profile 双 getattr→局部绑定 + hasattr 收窄（显式 `Any` 注解，原推断本含 Any，非新增消音） |
| services/visual_element_service.py | 3 | 3 | `default_elements.get(TYPE).id` 双调用×3 → 局部绑定 |
| services/task_completion_evidence.py | 3 | 3 | `pause_state` 双调用表达式局部绑定 |
| core/run_steps.py | 3 | 3 | `awaiting` 双调用表达式局部绑定 |
| core/event_bus.py | 3 | 3 | `start_consuming` connect 后 redis 局部绑定 + None 显式 RuntimeError（原 AttributeError 同类外抛）；`_process_stream_message` 顶部 redis 局部绑定 + 防御早退（消费循环只在 redis 就绪后启动，分支实际不可达；两处 xack 改走局部） |
| services/evidence/outcome_evidence_adapter.py | 3 | 3 | `metadata` 双调用表达式局部绑定 |
| **合计** | **66** | **66** | 16 文件；总族差 −74 中其余 −8 为修正确类型时连带消除的邻近家族错误（见修法类别 7） |

## 修法类别（类型学正确，零 ignore、零新增消音 Any）

1. **双调用表达式局部绑定**（wt325 #2 / wt331 #1 的延续）：`x = obj.get(k) if isinstance(obj.get(k), dict) else {}` 全部改为先绑局部再 isinstance；mypy 无法跨两次调用收窄是本族最大成因。
2. **参数注解谎言修正**：`_persist_user_message(active_db: AsyncSession | None)` 唯一调用方已守卫非空、函数体无条件解引用——去掉 `| None`。
3. **Optional 属性方法级短路**：redis/session/db 局部绑定 + None 早退，返回值与原「AttributeError 被宽 except 吞」路径的回退值一致。
4. **不可达分支显式失败**：event_bus `start_consuming`（connect 吞异常置 None 后继续会裸 AttributeError）与 telemetry `build_summary`（API 唯一调用方恒传 db）改显式 RuntimeError，失败类别与传播路径不变、信息可行动。
5. **参数化传图**：graph_reasoning 两个私有 helper 以 `graph: nx.DiGraph` 形参接收已收窄图对象，替代跨方法读 `self.G`（mypy 无法跨方法边跟踪属性状态）。
6. **hasattr 收窄配套单次 getattr**：planning `_state_from_snapshot` 的 `getattr(snapshot, k, None)` 双调用改局部绑定；局部显式 `Any` 注解系把原表达式本就含有的 Any 显式化（wt331 先例口径），hasattr 运行时守卫保留。
7. **中途 7 条新增的处置**：worker 的 `self.session.execute` 从 union-attr 变正确类型后，`row.count`（SQLAlchemy Row 属性歧义，stub 解析为 `list.count`→`Callable[[Any], int]`）暴露 6 条 [operator]——改 `for feedback_type, count in result` 元组解包 + str/int 显式化（运行时同值）；telemetry 同理暴露 `previous.request_id = previous.request_id or None` 的 1 条 [assignment]——改为「缺失且回退非空才赋值」，真实数据下逐字等价（request_id 落库路径恒为非空串或 None，唯一分歧是存量值恰为空串时不再被改写为 None，无可观察差异）。

## 真缺陷 / 类型谎言雷达

1. **planning.py 两处双调用判定不一致风险**（`note_detour`:473、`_recompute_tensions`:894）：原代码 `X if f(state) else None` 形态对 `_top_open_tension(state)` / `select_next_tension(state)` 各调用两次——条件用第一次的结果、取值用第二次的结果。两函数当前为纯读选择器（实verified：list 过滤 + max），故未构成现行 bug，但这是「条件判 A 调用、值取 B 调用」的脆弱模式，任何一方未来引入副作用/时变性即出错。已坍缩为单次调用绑定（预防性修复，未配独立红测：修复对象是模式而非现行故障，记台账）。
2. **event_bus `start_consuming` 吞错后裸奔**：`connect()` 失败时吞异常置 `self.redis = None`，原代码随即在 `xgroup_create` 上 AttributeError——外抛类别未变（仍向上抛），但报错点与真实原因（Redis 连不上）错位。现改为显式 RuntimeError 指明 stream/group，属可诊断性修复。
3. **expansion_service 触发节点已删时的 AttributeError**：`db.get()` None 未检，原在 json 构建深处炸 AttributeError；现于入口显式 ValueError。两调用方（queue_expansion / preview_expansion_candidates）均无捕获，外抛类别等价，信息可行动。
4. 其余烧减点均为类型收窄失败而非运行时缺陷；所有 None 短路分支与既有回退语义逐一对齐（见逐模块表注）。

## 测试证据（DATABASE_URL=sqlite+aiosqlite 内存库 + 占位 SECRET_KEY，路径均经 find/grep 实证）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | test_expansion_service / test_routing_reward_model / test_soul_compiler / test_graph_reasoning / test_visual_element_service / test_outcome_evidence_adapter | **26 passed** |
| 2 | test_aurora_runtime_telemetry / test_aurora_runtime_planning / test_hybrid_run_steps / test_event_bus_lag_monitor / test_eventbus_subscribe_raise / test_community_signal_kill_switch / test_workflow_experience_phase62 | **49 passed** |
| 3 | test_x04_action_flow（含 task_completion_evidence） / test_context_cache_versioning / test_context_sources（ContextBuilder） / test_event_bus_reliability / test_event_ack2_reliability | **95 passed** |

合计 **170 passed，0 failed**——零失败故无需基线克隆对照（无存量失败需归因）。覆盖 16 个被碰文件中 14 个的直接/间接测试面（signals_learning_worker 无直接单测，静态守卫 test_workers_package_location 涉及其存在性，已在守卫 83 条中通过）。

## 守卫与 ruff

- `bash scripts/run_all_rule_guards.sh` → **EXIT 0**（83 条全过；gen 三件套已按协议以 `cp -RL` 从主仓复制 backend/app/gen、gateway/gen、mobile/lib/gen，gitignored 不入库）。
- 16 个被碰文件 `ruff check --fix` → **All checks passed**（exit 0，零自动改动）。
- `git diff` 中 `type: ignore` 出现次数：**0**。

## 其它

- `/tmp` 探针（/tmp/wt333/）收工自清；本卡未建基线克隆（零失败无需对照）。
- worktree 内 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 为 gitignored 生成物副本。
