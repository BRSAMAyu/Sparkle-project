# WT325-ARGTYPE — mypy 四期 arg-type 烧减批 报告

- **base SHA**: `1c5f2d8d`（main @ 开工时）
- **final SHA**: 见分支 `wt325-mypy-argtype` 最新 commit
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt325-mypy-argtype`

## 消减数（冷缓存复验，ratchet 同口径 `mypy app --ignore-missing-imports --no-error-summary`）

| 口径 | base | final | Δ |
|---|---|---|---|
| 总错误 | 1795 | **1615** | **−180** |
| arg-type 族 | 526 | **376** | **−150** |

- `quality/mypy_baseline.txt`: 1795 → **1615**（棘轮下压，冷缓存双跑稳定 1615）。
- 回归核查：全量错误集与 base SHA 干净克隆（/tmp 干净基线对照，git clone 天然基线）做归一化 diff（去行号），**新增错误 0 条**。

## 修法类别（全部类型学正确，零 ignore、零 error-消音 Any）

1. **SQLAlchemy 条件列表参数化**：`list[BinaryExpression[bool]]` → `list[ColumnElement[bool]]` 显式注解（seed_library_service，21 条）；`text("FALSE")` → `false()`、`SeedItem.is_active` → `.is_(True)`（类型正确的等价 SQL 语义）。
2. **跨表达式收窄失败修复**：`if payload.get(k) is not None: f(payload.get(k))` 双调用模式 → 局部变量绑定后再窄化（memory_admin kill-switch 端点 16 条等）。
3. **float/int 强制转换边界**：`float(EXPR)` 在 `try/except (TypeError, ValueError)` 中的 None 路径显式化（None → TypeError → except 路径，改写为显式 `is None` 短路，语义逐条等价核对），共 ~30 处（dual_core、reward_model、predictive、adaptive_replanner、aurora runtime 等 16 文件）。
4. **TypedDict 参数化**：`BottleneckAnalysisKwargs`（`analyze(**kwargs)` 精确映射）、galaxy `_GalaxyPathEdge`/`_NodeGraphPayload`、aurora `_ModeCache`、onboarding 响应字段。
5. **Sequence 协变放宽**（只读链路）：handoff_packets（workflow_experience/collaboration_workflows/standard_workflow）、group_ids 链（retrieval_service→group_file_service）。
6. **LangGraph 节点契约**：`GraphExpertSpec.node_handler` → `Callable[[SparkleState, dict | None], Any]`（与 langgraph `_Node` 协议一致）；workflow.py 两处 `add_node` 对联合推断限制做 **有依据 cast**（`StateNode[SparkleState, Any]`，注释说明）。
7. **隐式 Optional 修正**：`build_system_prompt` 等 `dict = None`/`str = None` → `X | None`（prompts.py），连带消掉 standard_workflow 3 条调用侧错误。
8. **直接构造替代 dict 解包**：chat.py 三处 `ChatResponse(**response_data)` 改为显式 kwargs（`dict[str, object]` 中毒推断根因消除）。
9. **孤儿模块回避**：`ope_gatekeeper.py` 修复已回退——该文件是 Rule AT（no-orphan）跟踪的无 runtime importer 孤儿，修改即入守卫范围触发 AT001；按守卫语义不动它（已记录，留给孤儿清理专项）。

## 真 bug / 类型谎言发现（本卡真实价值部分）

1. **`GalaxyStructureService.get_graph_view` 返回注解谎言**：注解 `-> GalaxyGraphResponse`（pydantic 模型），实际 `return nodes_with_status, relations`（tuple）。运行时因真实返回 tuple 而未崩，但任何按注解使用 `.nodes` 的调用方会 AttributeError。已修正注解为 `tuple[Sequence[tuple[KnowledgeNode, UserNodeStatus | None]], Sequence[NodeRelation]]` 并收紧下游两处参数类型。
2. **协作 gather 的 CancelledError 漏网**（collaboration_workflows.py:296）：`asyncio.gather(..., return_exceptions=True)` 后用 `isinstance(result, Exception)` 过滤——`CancelledError` 是 `BaseException` 不是 `Exception`，取消时会漏进 outputs 并在 `result.response_text` 处二次 AttributeError。已改为 `isinstance(result, BaseException)`（类型收窄同时闭合运行时漏洞）。
3. **`reward_model.from_task_outcome` 潜在未捕获 TypeError**：`float(event.get("completion_rate") if completed else 0.0)` 在 completed 且字段缺失时 `float(None)` 裸抛（原代码无 try 包裹）。已改为 None 短路 0.0（防御性收口，属行为改善，已记录）。
4. **`build_system_prompt(user_context, "History injected.")` 幽灵实参**：chat.py 两处传字符串给 `conversation_history: dict` 形参，运行时被 `isinstance(..., dict)` 守卫静默丢弃（纯死实参）。已删；`_format_conversation_history` 的 None/str 防御本就存在，无行为变化。

## 测试证据（pytest 抽测被碰域，DATABASE_URL=sqlite+aiosqlite 内存库 + 占位 SECRET_KEY）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | test_seed_library_service / test_bottleneck_analyzer / test_routing_reward_model / test_workflow_experience_phase62 | **38 passed** |
| 2 | test_seed_library_stage22 / test_langgraph_planner_circuit_breaker / test_langgraph_planner_synthesized_plan / test_adaptive_replanner_cognitive_trigger | **12 passed** |
| 3 | test_dual_core_router / test_memory_admin_api / test_galaxy_service_audit_idem_duplicate / test_a01_aurora_decision_l2_wiring | 40 passed + **4 failed**（见下） |
| 4 | test_privacy_kill_switch_gauge / test_community_privacy_fv05 / test_galaxy_concurrency | **3 failed + 3 errors**（见下） |
| 5 | test_session_feedback_adaptation / test_signal_spine / test_capability_lane / test_review_urgency_service / test_context_builder_mixin | **1042 passed** |
| 6 | test_predictive_service_productization / test_state_aggregator_service / test_community_template_injection / test_aurora_language_principles | **34 passed** |

失败对照：memory_admin（4）、privacy/galaxy_concurrency（3+3）在 **base SHA 干净克隆上逐字复现同失败集**——全部为存量失败，与本批无关。合计 ~1126 passed，0 新增失败。

## 守卫

`bash scripts/run_all_rule_guards.sh` → **EXIT 0**。
- Rule BG（proto 生成物缺失）为 worktree 环境性缺 gen：已从主仓复制 `gateway/gen`、`mobile/lib/gen`（gitignored，不入库）后通过。
- Rule AT：`ope_gatekeeper.py` 修改触发 AT001（无 runtime importer 的孤儿模块），按守卫语义回退该文件修改后通过。

## 其它

- 38 个被碰文件 `ruff check` 全绿；`ruff format` 顺带把被碰文件里 30 个文件的存量格式偏差一并归一（约 ±500 行纯格式 churn，已在本报告声明）。
- worktree 内 `app/gen`、`gateway/gen`、`mobile/lib/gen` 为 gitignored 生成物副本；`/tmp` 探针与基线克隆 `wt325-baseline-check` 收工自清。
