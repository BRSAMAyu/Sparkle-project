# WT331-UNIONATTR — mypy union-attr 家族烧减批 报告

- **base SHA**: `a9a2e993`（main @ 开工时）
- **final SHA**: 分支 `wt331-mypy-unionattr` 最新 commit
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt331-mypy-unionattr`
- **战区回避声明**: 未触碰 wt326 战区（growth dashboard 瓶颈推导 `growth_dashboard_service.py`、chat_mode 枚举 `orchestration/chat_modes.py` 一线、goal 创建/激活链 `user_settings_service.py`/`api/v1/users.py`/`api/v1/user_settings.py` 的 current_goal_id 全家）；未触碰任何 mobile/gateway 文件；未改 `quality/mypy_baseline.txt`。开工时 wt326 分支尚无领先 main 的 commit（worktree 干净），战区以卡面定义为准执行回避。

## 消减数（冷缓存复验，ratchet 同口径 `mypy app --ignore-missing-imports --no-error-summary`）

| 口径 | base | final | Δ |
|---|---|---|---|
| 总错误 | 1615 | **1449** | **−166** |
| union-attr 族 | 327 | **171** | **−156** |

- `quality/mypy_baseline.txt` 保持 1615 未动（按卡面 Forbidden，主会话合并后统一刷基线）。
- **零新增证明（方法）**：对 base SHA 冷缓存全量错误清单（/tmp/wt331/base_errors.txt）与本批 final 冷缓存清单（final_errors.txt）做「去行号归一化 + multiset 差集」：`final − base` 的多重集差 = **0 条**（方法：对每条 `file:line: error: msg [code]` 剥离行号后以 Counter 对比，新增实例数 sum(final−base)=0，删除实例数 sum(base−final)=166）。中途曾出现 6 条新增 `[misc]` await 错误（redis-py 7.x 双模式桩 `Union[Awaitable[X], X]` 所致），已当场修正至 0，见「修法类别 7」。

## 逐模块烧减表（union-attr，冷缓存口径）

| 模块 | base | 烧减 | 修法 |
|---|---|---|---|
| agents/graph/nodes/review_nodes.py | 40 | 40 | reflect() 联合返回值显式 isinstance 收窄（review-mode 契约恒返 ReflectionResult），不可能分支走既有 FAILED 返回 |
| agents/graph/nodes/collaboration.py | 16 | 16 | `with_structured_output` 契约 cast（CollaborationDecision / DelegationPlan，非 include_raw 模式运行时恒返 schema 实例，注释说明） |
| services/task_event_consumer.py | 13 | 13 | `source_metadata` 局部绑定后 isinstance 收窄（3 处双调用模式） |
| services/insight_prediction_service.py | 11 | 11 | `_extract_features` 6 个双调用表达式的局部绑定收窄 |
| services/theater/prediction_theater_service.py | 10 | 10 | `selected_prediction` 局部绑定；`strategy_samples` 值类型改 TypedDict `_StrategySampleBucket`（list/int 混装 dict 消除） |
| services/achievement_engine.py | 10 | 10 | `_append_recent_event` redis None 短路；叙事构建 5 处双调用局部绑定；3 处 `rarity: Any` 显式注解（原 `.get()` 返回 `Any \| None` 上 `.value`） |
| api/v1/translation.py | 9 | 9 | `result.data or {}` 局部绑定，success 分支 9 处 `.get` 改走局部 |
| orchestration/prompts.py | 9 | 9 | persona 两函数 section_weights/identity/nested_context 局部绑定收窄；两处 `payload is not None and hasattr(...)` |
| services/agent_stats_service.py | 8 | 8 | 两处聚合查询 `fetchone()` → `.one()`（无 GROUP BY 恒返一行，类型 Row 非 Optional） |
| tools/task_query_tool.py | 8 | 8 | `knowledge_context` 局部绑定 + isinstance 收窄（details 值类型过宽） |
| aurora/engine.py | 8 | 8 | `_build_stay/transition_decision` 顶部 snapshot None 防御分支（与调用方既有 missing_snapshot fallback 语义一致）+ 局部绑定 |
| services/llm_service.py | 7 | 7 | redis None 短路；`_get_provider_name_from_url` provider 局部绑定；ABC async-gen 契约（见下）消除流式联合；`_direct_stream` provider None 防御分支（入口已 501） |
| services/chat_signal_collector.py | 7 | 7 | 4 个私有方法 redis_client None 短路（返回值与原异常路径一致：None/0/[]） |
| **合计** | **156** | **156** | 14 文件，`services/llm/base.py` 为使能修复（0 直接烧减） |

## 修法类别（类型学正确，零 ignore、零新增消音 Any）

1. **双调用表达式局部绑定**（wt325 先例 #2 的延续应用）：`x.get(k) if isinstance(x.get(k), dict) else {}` 类表达式 mypy 无法收窄，全部改为先绑局部再 isinstance。
2. **联合返回值显式收窄**：review_nodes 对 `ReflectionResult | TriggeredReflectionResult` 用 isinstance 分支，不可能分支落既有失败路径（非 assert、非 cast，控制流可证）。
3. **有据 cast**：仅 collaboration.py 2 处，langchain `with_structured_output(schema)` 的运行时契约（注释写明）。
4. **TypedDict 参数化**：prediction_theater `_StrategySampleBucket`。
5. **Optional 检查语义修正**：achievement `hasattr(cache_service, 'redis')`（恒真，防不住 None）→ `is not None`；agent_stats `fetchone()` → `.one()`。
6. **SQLAlchemy/langchain 契约化**：`.one()` 聚合单行、structured-output cast。
7. **redis-py 双模式桩适配**：首次给 chat_signal_collector 注解 `Redis | None` 后暴露 redis 7.x 桩 `Union[Awaitable[X], X]` 的 6 条新 `[misc]` await 错误——回退该文件注解（原推断本含 Any，非新增消音），仅靠 None 守卫收窄；achievement pipeline 两处 list 操作改用库官方 dual-mode 模式 `inspect.isawaitable`（import inspect）。此为存量家族（base 中 cache.py:139 同类），本批**零新增**。

## 真缺陷 / 类型谎言雷达

1. **`LLMProvider.stream_chat` ABC 声明谎言**（`app/services/llm/base.py`）：抽象方法写作 `async def ... -> AsyncGenerator[str, None]` 且函数体只有 `pass`——即「协程返回生成器」。但唯一实现 `OpenAICompatibleProvider`、安全包装层、以及 `LLMService.stream_chat` 本体全部是 async-generator 函数（体内含 yield），唯一调用面 `async for chunk in current_provider.stream_chat(...)`（llm_service.py:1294）只兼容 async-generator。若有实现者照 ABC 字面（协程式）实现，运行时 `async for` 直接 TypeError: not async iterable。已把抽象体改为含 `yield` 的 async-generator 声明（注释写明契约，yield 永不执行），mypy 联合随之坍缩。属 wt325「注解说谎」同类。
2. **`_append_recent_event` 的 hasattr 假守卫**（achievement_engine.py）：`pipe = cache_service.redis.pipeline() if hasattr(cache_service, 'redis') else None`——`redis` 属性恒存在（模块级单例，类型 `Redis | None`），hasattr 永真，guard 形同虚设；redis 缺席时 `.pipeline()` 在 None 上 AttributeError（仅被外层宽 except 吞掉）。改为显式 `redis_client is not None` 判断，防御真正生效。
3. 其余烧减点均为类型收窄失败而非运行时缺陷；唯一行为级差异是各 None 短路分支从「AttributeError 被宽 except 吞」变为「显式早退/回退」，全部与既有回退语义对齐（见逐模块表注）。

## 测试证据（DATABASE_URL=sqlite+aiosqlite 内存库 + 占位 SECRET_KEY，路径均经 find 实证）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | review/reflection 7 文件 + theater 2 + insight_prediction + chat_signal_collector 2 | **95 passed** + 2 failed |
| 2 | achievement 3 + llm_service 2 + prompts_safe_format + agent_stats | **39 passed** |
| 3 | translation_api + route_history + belief_fusion + reward_model + langgraph 2 + plan_task_tools | **109 passed** + 2 failed |
| 4 | aurora 4（a01_l2_wiring/contract/decision_loop/closed_loop）+ standard_workflow_binding + reflection y_gate/trigger | **153 passed** |

失败对照：4 个失败（test_theater_seed_and_accuracy 的 promote-to-galaxy 2 条、test_translation_api 2 条）在 **base HEAD 干净克隆**（`git clone <worktree> /tmp/wt331-baseline`，按并发安全纪律未用 stash/reset）逐字复现同失败集——全部为存量失败，与本批无关。合计 **396 passed，0 新增失败**。期间一次 "no tests ran" 系本 worker 猜错路径（tests/plan/ 前缀），纠正后重跑，非测试绿口径问题。

## 守卫与 ruff

- `bash scripts/run_all_rule_guards.sh` → **EXIT 0**（83 条；Rule BG 为 worktree 环境性缺 gen，已从主仓以 `cp -RL` 复制 backend/app/gen、gateway/gen、mobile/lib/gen 后通过，gitignored 不入库）。
- 14 个被碰文件 `ruff check --fix` → **All checks passed**（exit 0，且未产生任何自动改动）。

## 其它

- `/tmp` 探针与基线克隆（/tmp/wt331、/tmp/wt331-baseline）收工自清。
- worktree 内 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 为 gitignored 生成物副本。
