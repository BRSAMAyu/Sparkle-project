# WT297-MYPY3-BURN — D 线 mypy 三期烧减报告

- 卡号：wt297-mypy3-burn ｜ worktree：`Sparkle-sysrev/wt297-mypy3-burn`（分支同名，本地 commit `164856e5`，未 push）
- 日期：2026-09-24 ｜ mypy 1.20.2 + CPython 3.11（复用主仓 `backend/.venv`，只读使用）
- 上游依据：wt295 报告 §四（2251 诚实锚点 + 三期弹药清单）、wt292 报告 §二.3/§六（mixin 打法、家族修法）

## 一、烧减数字（回执①）

| 口径 | 前 | 后 | 烧减 |
|---|---|---|---|
| **backend/ 目录口径**（卡口径：`cd backend && rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary`，**冷缓存铁律**） | **2251** | **1803** | **-448（-19.9%）** |
| quality/mypy_baseline.txt | 2251 | **1803** | 已刷新 |
| root 口径（CI ratchet 备用，`mypy backend/app`） | 2242（wt295 存证） | **1797** | 一致收敛 |

**目标 ≤1900 达成（1803 < 1900）**。1803 为 4 连测逐位一致锚点：冷×3 + 热×1，全程 `INTERNAL ERROR = 0`（wt295 根治 context_builder 崩溃后口径稳定，本轮零漂移）。

### 家族 × 修法 × 计数表

| 家族（文件） | 前 | 后 | 烧减 | 修法 |
|---|---|---|---|---|
| A1 execution_engine.py mixin 声明债 | 91 | **0** | -91 | 见 §二.1 |
| B1 community.py object 多态 + 跨枚举 | 104 | **0** | -104 | 见 §二.2 |
| C1 token_tracker.py redis 桩 await 联合 | 31 | **0** | -31 | 精确码豁免 ×31（§二.3） |
| C2 routing_engine.py mixin 声明 + 流分析 | 33 | **0** | -33 | 见 §二.4 |
| C3 context_pack/ranker RankedItem 非泛型 | 52 | **0** | -52 | `RankedItem(Generic[T])`（§二.5） |
| C4 graph_monitor.py 健康负载推断 + redis 桩 | 53 | **9** | -44 | dict[str, Any] 注解 + 精确豁免；**残余 7 条为真实功能缺失**（§三） |
| C5 memory_service.py AsyncSession 双契约 | 87 | **0** | -87 | 类级声明 + 1 处精确豁免（§二.6） |
| C6 collaboration_service 等连带 | 2 | 0 | -2 | comment 隐式 Optional 化；Sequence→list 物化 |

## 二、家族修法（回执②）

### 1) execution_engine.py（91→0）
- **mixin 成员声明（形制照 wt292 四 mixin 打法，属性升级为精确类型）**：`ExecutionEngineMixin` 类体补 12 属性 + 15 方法声明。属性给精确类型（`ToolExecutor`/`LangGraphPlanner`/`CircuitBreaker`/`ObservabilityLogger` 等，全部经 `if TYPE_CHECKING:` 导入——零运行时依赖、零循环导入风险）；跨 mixin 私有方法按 wt292 形制 `Callable[..., Any]`。类体纯注解不创建类属性，运行时零变化。
- **连带收益**：`lang_graph_planner` 从 Any 变精确类型后，20 条 union-attr 浮现为 `ExecutablePlan | None` 精确形态，以规划三出口（synthesized/成功/超时兜底）均产出计划或上抛的**真不变式 assert** 一次收口。
- **真类型修复**：openclaw 短路流裸 `object()` 哨兵 → `_ChatControlSentinel` 唯一类 + `isinstance` 判定（is 判定对非单例不窄化，行为等价）；`arguments` 显式 `dict[str, Any]`（executor 契约）；`execute_multi_agent_workflow(orchestrator=cast("ChatOrchestrator", self))`（mixin 仅被 ChatOrchestrator 组合，cast 为真类型非谎言，TYPE_CHECKING 导入避循环）；`user_context_payload` None 防护（原 AttributeError 会整轮规划退直连）；plan 反馈写入前 `active_db is not None` 防护（服务签名 db: AsyncSession）；局部名 `summary` 双语义复用拆分。
- **safe_error_messages.py**：`build_safe_chat_error` 返回注解 `int` → `agent_service_pb2.ErrorCode`（9 条返回路径全为枚举成员验证，int 子类型收窄，调用方 error_code 类型检查通过，运行时零变化）。

### 2) community.py（104→0）
- **object 多态（55 条 attr-defined）**：`_build_share_meta`/`_build_share_brief` 的 `resource: object` 按 `SharedResourceType` 枚举派发后属性访问——8 分支 × 2 函数 16 处局部别名改 `cast("Plan"/"Task"/.../ "CognitiveFragment", resource)`（派发契约与 `_get_share_resource` 返回一一对应，精确 cast 非谎言）。
- **跨枚举（17 处 arg-type）**：模型 StrEnum ↔ schema StrEnum 同值跨名（MessageType/GroupRole/UserStatus/ReportReason/ReportStatus/ModerationAction/OfflineMessageStatus/GroupFileTrustLevel），**7 对枚举值集逐对运行时验证**（子集关系全绿）后，payload 构建点 17 处点侧 cast（wt292 同款）。
- **真缺陷修复（4 处，全部为运行时必炸的潜伏 ImportError）**：
  1. `GroupMembership`（2 端点）：模型实名 `GroupMember`——资源推荐/质量排序端点每次调用必 ImportError 500，已改名（字段 group_id/user_id/deleted_at 验证存在）；
  2. `COMMUNITY_RESOURCE_MISLEADING_FLAGS_TOTAL`：计数器从未定义，flag-misleading 端点必 500——按调用契约（labels resource_id）在 app/core/metrics.py 以 `get_or_create_metric` 惯用形补齐；
  3. `CommunityMessageReport`（admin 举报端点）：模型实名 `MessageReport`，且原 payload 访问的 `r.group_id`/`r.message_id` 亦非真实列（实为 `group_message_id`/`private_message_id`）——按实际列修复，该端点从未成功响应过（无存量消费契约可破坏）；
  4. **广播消息 500**：模型侧 `MessageType.BROADCAST` 为真实落库值（community_advanced_service 写入 GroupMessage），schema 侧 `MessageTypeEnum` 缺失该成员——实测含广播消息的消息列表 ValidationError 500（pydantic 4 错误探针复现）。补 `BROADCAST = "broadcast"` 成员。
- **诚实 Optional 化（3 个 schema 字段）**：`GroupTaskInfo.creator`/`SharedResourceInfo.sharer`/`MessageReportInfo.reporter`——构建端对已删除/缺失用户合法产出 `None`（原路径 ValidationError 500），`UserBrief` → `UserBrief | None`。
- **Optional 防护**：update_status 的 `db.get` 结果 404 防护；adopt 流程导入产物 Plan/Task 404 防护（原 AttributeError）；`favorite` 双语义复用拆分；`message_info`/`msg_info` 显式联合注解；adopt-plan 分支 `original` 与 task 分支同名复用致 mypy 误绑 Task 类型——改名 `original_plan`。
- **collaboration_service**：`comment: str = None` 隐式 Optional → `str | None = None`（调用方 schema 即 Optional、DB 列可空）。

### 3) token_tracker.py（31→0，纯桩缺陷）
31 处 `await self.redis.<cmd>` 全部报 `Awaitable[int] | int` 联合——redis-py 桩 `ResponseT` 含同步 int 分支（同步桩残留），asyncio 客户端运行时恒 awaitable。属**类型库缺陷**，按卡规「stub 缺失精确码 ignore 注明原因」：31 行统一 `# type: ignore[misc]  # redis-py 桩 ResponseT=Awaitable|int 联合（同步桩残留）；asyncio 客户端运行时恒 awaitable`。零裸豁免。

### 4) routing_engine.py（33→0）
- `RoutingEngineMixin` 类体声明（同 §二.1 形制）：redis: Any + 3 精确类型 + 2 Callable 方法。
- `awareness` 三分支字面量 join 成 str → 显式 `Literal["weak", "moderate", "strong"]`（2 处）。
- `debug`/`scores` 重复 `.get`+isinstance 三元（mypy 无法窄化第二次调用）→ 绑定一次再判（运行时等价且少一次 get）。
- `json.loads` 返回 Any 流入 `str | None` → `isinstance` 窄化后返回（诚实 Optional）。
- belief_state `BeliefState | dict | None` 增加 isinstance dict 早退（原路径靠 except 兜底，行为等价）。
- `from_mode: str` 跨分支声明；`optional_signals` 第二处注解去除（no-redef）；`detail: dict[str, Any]` 注解。

### 5) context_pack.py（52→0，单点根治）
`app/core/context_ranker.py` 的 `RankedItem` 类体已用 `TypeVar T` 却**未继承 `Generic[T]`**——16 条 `RankedItem[X]` 非法下标 + 31 条 `entry.item` 成员访问（T? → object）全部同源。补 `Generic[T]` 一处修复两族 47 条（运行时零变化），余 5 条：tiktoken 可选依赖回退精确豁免、3 处 dict.get None 键显式化（语义等价）、ttl_map `dict[Literal, int]`→`Mapping[str, int]` 键不变性 cast（键实为 str 字面量成员，cast 为真）。

### 6) memory_service.py（87→0，双契约声明）
`MemoryService.__init__(db: AsyncSession | None)` 但类内 66 处触库访问（execute/commit/add/refresh/rollback/flush）要求非空——运行时探针证实存在 `MemoryService(None, redis)` 的合法调用（aurora correction_feedback，仅走不触库方法）。**双契约诚实表达**：类体 `db: AsyncSession` 声明使用侧契约，构造点 divergence 单点精确豁免注明缘由。余 4 条：降级占位 `apply_decision_to_record = None` 精确豁免（verdict 恒 ignore 必先 return，永不被调用）；`_build_episodic_memory_record` evidence_snapshot 参数按真实契约放宽（build_snapshot 产物即 list[dict]，JSONB 列 Mapped[Any]，消费端 1482/1625 已显式 `{"history": snapshot}` 包裹 list）；`ensure_naive_utc` 非空输入 cast。

### 7) graph_monitor.py（53→9）
两处健康负载 dict 字面量（str/dict/list 异构值）→ `dict[str, Any]` 注解（-33）；redis 桩 llen/xlen/xadd 精确豁免 ×4（同 §二.3 缘由，xadd 为 dict 值联合不变性）；`graph_rag_search` 签名 `user_id: uuid.UUID` → `uuid.UUID | None = None`（监控端点以 None 做无主测试查询，调用契约即 Optional）。**残余 9 条见 §三。**

## 三、诚实残余（9 条，未烧）

graph_monitor.py 剩 9 条中 **7 条**为：`GraphKnowledgeService.check_graph_connection / check_vector_connection / get_graph_statistics / get_detailed_statistics` —— **全库检索证实这 4 个方法从未存在过**。两个图健康端点的核心探测每次调用必然 AttributeError（被 except 吞掉后报 degraded/error），即**该监控面从未真正工作过**。属功能缺失而非类型债：正确修法是实现 AGE/pgvector 连通性探针（功能工作，超出本卡类型烧减范畴），**拒绝用 ignore 掩盖真实缺陷**。余 2 条为同一服务类上 import 回退的连带（随上述方法一并实现时自然消除）。建议四期单卡「graph-monitor 探针实现 + 类型收口」。

## 四、验证（回执③）

| 项 | 结果 |
|---|---|
| 终态官方口径 | `rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary` = **1803**，冷×3 + 热×1 逐位一致，`INTERNAL ERROR = 0` |
| 定向 pytest | **7 批 316 passed / 0 failed**：①execution_engine/多代理/planner 超时/熔断(15) ②orchestrator FSM/状态迁移/planning/tool 净化/init(68) ③community API×7(20) ④share/community 安全/资源质量(22+36=58) ⑤context_pack/排名/memory 服务/门控/cache 版本/双核 kill switch(45) ⑥observability/context manager/心跳/profile/insights(27) ⑦memory 治理/preference/working memory(18)。sqlite + 测试 SECRET_KEY，零真实库接触 |
| import 烟雾 | `import app.main` + `app.models` + `app.api.v1.community` + `execution_engine` + `routing_engine` + `memory_service` + `context_pack` OK |
| ruff（CI 同口径 `ruff check backend/app`） | **All checks passed!**（过程 14 处 I001 导入排序已 --fix，修后 mypy 计数不动、烟雾 OK） |
| 守卫 `run_all_rule_guards.sh`（exit-checked） | **K 0 / Z 0**；**AQ PASS**；**BG FAIL = 存量**——已在 HEAD 纯净克隆（`git clone` 至 /tmp，零改动基线）复现同等失败（克隆上更连 AQ 一起挂，系克隆缺 gitignored app/gen 的环境性问题，非代码回归） |
| mypy 棘轮 | quality/mypy_baseline.txt = 1803；backend 口径 1803 ≤ 1803、root 口径 1797 ≤ 1803，双通过 |

## 五、资源与守卫峰值（回执④）

- 无 HEAVY（无模拟器/Gradle/浏览器/全量测试）；mypy 冷跑串行 4 次，pytest 7 批串行
- 磁盘：开工 7.9G free（>6G 红线）；swap 空闲 1.2G 达标，全程无熔断
- app/gen（gitignored）自主仓只读复制并**符号链接实体化**（复用 wt292/295 教训，本轮 K/Z 守卫零崩溃）
- 临时区：/tmp/wt297-*（基线/中间/终态 mypy 输出 ×6、守卫日志 ×2、HEAD 基线克隆、probe 脚本 ×2）+ backend/.mypy_cache + .pytest_cache——收工全部清除（见 §七）

## 六、四期建议（回执⑤）

1. **graph-monitor 探针实现卡**：实现 `GraphKnowledgeService` 的 4 个缺失探针方法（AGE `cypher SELECT 1` 式连通检查 + pgvector `SELECT 1` + 统计聚合），一并收口残余 7 条 attr-defined——监控面从「从未工作」到可用，价值/类型双收。
2. **arg-type 556 + union-attr 412 大盘**：本轮后 arg-type 仍居首（community 消化前为 588）。union-attr 新大户为 review_nodes.py(40)、galaxy_service(15)、collaboration(16)——多为 `db.get` 产物与 Optional 参数，沿本轮「404 防护/点侧 cast/诚实 Optional 化」三件套分 2-3 卡可消化。
3. **assignment 258 残盘**：非 SQLCore 的首赋值窄推断模式（本轮 `arguments`/`from_mode`/`detail` 三处手法已验证），可半脚本化。
4. **redis-py ResponseT 桩债（横向）**：token_tracker/graph_monitor 已用精确豁免 35 处；建议四期评估**全库统一 await 边界 helper**（`inspect.isawaitable` 单点）或 mypy 插件，一次性消除 ~百处量级的同类豁免；更长期是钉版 redis-py 并向上游/类型 stub 提 issue。
5. **给 Leader 的口径建议（沿一/二期再提）**：CI ratchet 改 `cd backend && mypy app` 两口径合一（本轮 root 1797 vs backend 1803，差 6 条 warn_return_any 配置差）；mypy 钉版 1.20.2。

## 七、收工清理（已执行）

`backend/.mypy_cache`、`.pytest_cache`、/tmp 下 wt297 前缀全部产物（mypy 输出 6 份、守卫日志 2 份、probe 脚本 2 份、HEAD 基线克隆）已删；无残留进程、无模拟器。正式产物仅：worktree 13 文件改动 + quality/mypy_baseline.txt + 本报告 + changes.patch。

## 交付物清单

- worktree 改动：13 个 Python 文件（+316/-143）+ `quality/mypy_baseline.txt`（2251→1803）
- `v3-output/WT297-MYPY3/REPORT.md`（本文件）+ `v3-output/WT297-MYPY3/changes.patch`（全量 diff）
- 本地 commit `164856e5`（未 push，未动 main，未 stash/reset/clean）
