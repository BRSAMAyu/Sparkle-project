# wt299-p1-pair 回执报告（C 线·wt294 交接 P1 双修）

> 2026-09-24 ｜ 工作树 wt299-p1-pair ｜ 交付 = 本 REPORT + changes.patch + 分支本地 commit（未 push）
> 两件均为 **实锤并已修复**（非证伪）；先写复现测试跑出红基线，再修，回归全绿。

## ① 各自诊断结论

### P1-1 LLMService 单例切换状态 → 实锤（且比 wt294 报告的更严重）

- 状态面确认：`app/services/llm_service.py` 单例/按角色缓存实例持有可变路由状态 `_current_selection/_provider/chat_model/reason_model/_extra_body`；`switch_model_for_task/switch_to_specific_model` 原地改写。`_state_lock` 只串行化单次变更，防不住「切换后→下次切换前」的跨请求串读：消费点在 `chat()` L691 `model = model or self.chat_model` 与 L780 `active_selection = cascade_selection or self._current_selection`。
- **wt294「生产无单例调用方（multi_intent_service 自建实例）」的结论已过时**。本卡全量核对调用面，两个工厂 helper 正在**按角色缓存共享实例**上做原地 switch，且都在请求主链上：
  - `get_configured_llm_service(role, task_type)`（带 task_type 时 `switch_model_for_task`）→ standard_workflow 主聊天路径 L368/383/1591/1597、aurora decision_loop L1802、aurora chat_adapter L844、graph_rag L768/1416/1692、bottleneck_analyzer L105、multi_agent_adapter L412，共 10+ 调用点；
  - `get_llm_service_for_specific_model(model_key, role)`（`switch_to_specific_model`）→ standard_workflow 自定义专家 L357、predictive L880/1282、capsule_generation L549、node_sector L633、cognitive L310、planning_benchmark L358，共 7 调用点。
- 两种触发形态：**并发串读**（A 的 batch 切换落窗内 B 的 chat 读到 A 的模型）与**粘滞泄漏**（共享实例被切后无 switch-back，其后所有 `get_llm_service(role)` 调用方永久继承错误模型，直至下一个人切换）。
- 复现（修前实测红）：并发两路 `get_llm_service_for_specific_model("model_a"/"model_b")` → 两请求 chat 实际都用 model_b；顺序形态下普通请求静默继承 batch 模型。9 项断言 4 红（LLM）+5 红（SSE）。

### P1-2 SSE seq 毫秒非单调 → 实锤

- `app/core/sse.py` `send_to_user` 以 `int(time.time()*1000)` 生成 seq；同毫秒多条事件 seq 相同。重放契约 `connect()` `if seq > last_seq_int` 为**严格大于**过滤：客户端断线前最后收到 seq=T，同毫秒后续事件重放时全被判「已收到」而静默丢失。
- 高发面：galaxy_event_bridge（一轮连发多条星图事件）、plan_review_service L2436-2475、expansion_worker、knowledge_service。全链消费方为 mobile `enhanced_galaxy_repository` 的 `Last-Event-ID` 断线续传。
- 复现（修前实测红）：冻结时钟连发 3 事件 → `seqs=[1790000000000×3]`；以首条 seq 重连重放 **0 条**（应 2 条）。

## ② 修法

### P1-1（`app/services/llm_service.py`，语义增量集中在两个工厂）

- `get_llm_service_for_specific_model`：改为 `llm_router.select_specific_model` → 返回 **per-request 独立 LLMService 实例**（与已安全的 `get_llm_service_for_task`/`get_configured_llm_service_for_tier` 同型）。保持 `async def` 与返回类型不变，全部调用方零改动。
- `get_configured_llm_service`：task_type 为空维持原语义（返回按角色缓存共享实例，兼容面有测试钉住）；非空时改为选型后返回独立实例，**角色缓存从此不被任何工厂变更**。
- 无 key/demo 语义等价性：独立实例 `__init__` 按 selection 的 api_key 现估 demo_mode，覆盖原 `switch_to_specific_model` 的 wt9 修复场景（keyless 模型 → demo=True；keyed 模型 → 不粘 demo）。
- `switch_model_for_task/switch_to_specific_model` 方法**保留**（multi_intent_service 等自建实例用法合法，对外 API 兼容），仅补「严禁用于按角色共享实例」调用约束 docstring。
- 已知代价：per-request 实例 = 每请求新建 AsyncOpenAI client（连接池随 GC 回收）。这与代码库既有主导模式一致（standard_workflow 每轮生成已经由 `get_configured_llm_service_for_tier` 走 per-request 实例；fallback 路径 L848 本就即席建 provider），非新增量级。
- 边界：多进程部署下 seq/锁类问题不在本卡范围；本修为进程内语义修复，与部署拓扑无关，无新增分布性假设。

### P1-2（`app/core/sse.py`，+14 行）

- `SSEManager` 增加 `_last_seq: dict[str, int]` 与 `_next_seq(user_key)`：`seq = max(now_ms, last+1)`——毫秒时间戳为主体、同毫秒自增、时钟回拨不回退。`send_to_user` 按用户取号；`broadcast` 用 `"__broadcast__"` 键同款处理。
- 原子性：`_next_seq` 纯同步且在协程首个 await 之前完成，事件循环内天然原子，无需加锁。
- 内存：每用户一个 int 条目，量级可忽略（与 `connections` 同阶）；未做容量上限，如未来需可挂 LRU。
- 兼容性：seq 仍为 int、仍随真实时间前进（`id:` 行格式不变），mobile/gateway 消费方零改动。

## ③ 测试

- 新增回归（复现先红→修后绿，变异闭环以「未修代码即变异体」形式完成）：
  - `backend/tests/services/test_llm_factory_isolation.py`（7 用例）：隔离性（specific/configured 工厂不改写共享缓存）、并发形态（两并发 specific-model 请求 chat 级各用各的模型）、混合流量压力、无 task_type 兼容语义。FakeRouter+StubProvider 全注入，零网络。修前 4 红 → 修后全绿。
  - `backend/tests/core/test_sse_seq_monotonic.py`（6 用例）：同毫秒严格递增、时钟回拨、真实前进语义保持、per-user 隔离、**重放不丢同毫秒事件**（核心消费方契约）、event_generator `id:` 行严格递增。FakeRedis 替身离线。修前 5 红 → 修后全绿。
- 消费方定向回归（改动域 + SSE 消费方 + wt294 修复域）：**231 passed, 0 failed**（12s），覆盖 standard_workflow 路由、same-tier fallback、prediction routing、planning_benchmark、multi_agent_adapter、capability_lane、bottleneck_analyzer、generation_reasoning_progress、c03_spine、ttft_cfg、validation_engine、predictive_degrade、cognitive、node_sector、capsule、belief_fusion_engine（wt294 域无回归）、SSE heartbeat、evidence_pack_sse、minimax/batch 路由。
- 唯一未纳入：`tests/integration/test_capsule_ai_personalization.py`（`no such table: users`）——**基线克隆同红**，存量环境限制（内存 sqlite 无迁移表），与本卡无关。
- ruff：两改动文件 + 两新测试文件 **0 问题**（修掉自产 1 处 F401 后）。
- 守卫：`run_all_rule_guards.sh` exit=1，失败项仅 **Rule BG**（proto 生成物缺失/过期，worktree 无 `make proto-gen` 产物）——**基线克隆同 exit=1 同失败项**，环境红非本卡引入；其余 90 项规则全绿（worktree 补 `app/gen` symlink 后较 wt294 基线还消了 AQ 红）。

## ④ 资源峰值

LIGHT 卡全程：无模拟器/Gradle/浏览器/全库测试；pytest 定向串行单批（最大单批 231 用例 / 12s）；基线克隆与守卫日志入 /tmp（收工已清）；磁盘净增 <10MB（patch+报告+测试），swap 零压力，未触发 HEAVY 门。

## ⑤ 交接（含 FF 收敛批执行建议）

1. **合入**：`git apply --3way v3-output/wt299-p1-pair/changes.patch`（或直接合分支 commit）→ 定向对比法跑 `tests/services/test_llm_factory_isolation.py tests/core/test_sse_seq_monotonic.py` + 上面消费方清单。
2. **P1-3（FF 收敛批，~10 处仍挂账）执行建议**——wt294 报告第三节第 3 条清单不变，机械批量卡一次清完：
   - **模式**：统一收敛到 `task_feedback_service.spawn_followup_task` P1-C 形态——模块级 `_tasks: set[asyncio.Task]` 持强引用 + `task.add_done_callback(_tasks.discard)`；若要顺带补异常可见性，callback 里先 `task.exception()` 取出再 discard（防 "Task exception was never retrieved"）。
   - **建议抽公共 helper**（放 `app/core/background_tasks.py` 或就近 utils），签名 `spawn_tracked(coro, *, name, on_error=log)`，10 处全部替换调用，避免 10 份复制粘贴；`orchestrator._track_task` 亦可迁到同一 helper。
   - **逐站点注意项**：`aurora/privacy.py:119`（隐私刷新丢失）与 `core/auth_audit_service.py:62`（审计写丢失）优先级最高——丢失后果不可见；`core/llm_monitoring.py:185` 的 ACTIVE_TASKS gauge 漂移需在 done-callback 里同步 decrement；`achievement_engine.py:84` 已有回调只缺强引用，最简。每站点配「FF 泄漏可见性」断言测试（注入 done-callback 计数或 `asyncio.all_tasks()` 快照），批量卡一次绿。
   - **验证**：定向跑各站点单测 + `python -W error::RuntimeWarning` 式 异常可见性探针；不碰推理链路，LIGHT 卡可完成。
3. **另开卡（存量）**：`test_capsule_ai_personalization` 内存 sqlite 缺表（基线红）；`error_book_mastery_sync_service` 装配缺失（wt294 已报）。
4. **wt294 P1-4/5/6**（graph_sync_worker 优雅关停、job_service reaper 确认、predictive DEBUG 锁释放）仍未动，维持 wt294 原建议。
5. 本卡环境提示：worktree 需 `ln -s <主仓>/backend/app/gen backend/app/gen` 才能跑带 proto 的测试/守卫（本卡验证期临时挂载，已随收工移除；主仓合入后无此问题）。
