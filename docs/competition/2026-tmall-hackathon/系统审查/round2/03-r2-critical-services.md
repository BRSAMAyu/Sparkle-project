# 全系统审查·第二轮（R2） · 03 引擎关键服务与贝叶斯证据融合

- 复审员：3 号（Apex，切片：引擎·关键服务与贝叶斯证据融合）
- 基线：main@ca86bda8（冻结工作树 wt3，只读审查；除本报告外未改代码）
- 输入：R1 报告 [03-engine-critical-services.md](../round1/03-engine-critical-services.md)、修复波 commit `f813c3f0`（注：独立 `03-fixes.md` 未入库，修复清单从 commit message + diff 重建）、F3 移交的签名错位专项
- 环境事件：会话中途本机磁盘 100% 满 → Docker Desktop 无法启动 → **PG 与容器 Redis 宕机**。Redis 已用本机 redis-server 8.4.1（同密码、禁持久化）恢复并完成 C2-Redis/C3 实测；**真 PG 腿（C2-P1/P3）环境阻断**，脚本已备好（见 §4.3）。

---

## 1. 修复验证结论（R1 14 项）

修复波 commit `f813c3f0`（"F3"）。逐项核对代码 + 运行测试：

| ID | 落地核对 | 结论 |
|---|---|---|
| E1 属性转发 | `llm_security_wrapper.py:85-96` 新增 `__getattr__`：dunder 拒绝、经 `__dict__` 取 inner、逐次 `getattr`。dispatcher:519/520 的 `chat_model`/`reason_model` 实测可达（demo 模式下返回 `mimo-v2-flash`） | **已修（仅属性面）**——但 `chat()` 调用仍 100% 断裂，见 §2（专项）。`run():63` 的 `_cache_key` 仍在 try 之外（E1 次级加固未做，因属性可解析暂不触发） |
| E2 temperature | `llm_service.py` chat:526/reason:800 默认 `temperature=None`；`_call_with_selection` 两处改为 caller 值优先（`temperature if temperature is not None else selection.config.temperature`） | **已修**，语义正确（None=未指定） |
| E3 fallback 次序 | `fallback.py:279-296` tier_order 补齐 12 档成本降序；未知 tier 显式落 FREE_FAST；另见 §4.2 真 Redis 实测 | **已修** |
| B1 计费时区 | `billing_worker.py:_to_stmt_data` `fromtimestamp(ts, tz=UTC).replace(tzinfo=None)`，与 `_utcnow()` 对齐 | **已修** |
| B2 崩溃恢复 | `_recover_failed_batch`：attempts 计数、退避、`lpush` 逆序回队、超限/回队失败转死信，方法自身绝不抛；`start()`/finally 两处 flush 失败均走恢复路径 | **已修**（残留：Redis 与 DB 同时故障时记录丢失——日志留痕，属可接受边界） |
| Q1 固定窗口 | `rate_limit.lua`：`if ttl > 0 and redis.call("ttl", key) < 0 then expire`（仅首写设 TTL）；`rate_limit_refund.lua`：`SET key val KEEPTTL` + 缺 TTL 补设 | **已修 + 真 Redis 7.4/8.4 实测**（§4.2：TTL 不再滑动、refund 钳制生效） |
| S1 缓存隔离 | `semantic_cache_service.py:202` `if payload.get("user_id") != user_id: continue` 严格同用户 | **已修** |
| A1 会话复活 | `touch_session`/`touch_from_payload` 与 `upsert_session` 拆分：touch 只更新 last_active/元数据/jti，不复位 revoked、不删 Redis 撤销标记；`deps.py:63,115` 已改用 touch | **已修** |
| M1 降级队列 | `memory_inferred_write_lane.py:84` `deque(maxlen=DEGRADED_QUEUE_MAXLEN)` + 丢件计数与日志 | **已修**（有界化；仍无消费者，产品语义待定） |
| M2 拒绝分级 | STRONG/WEAK 双短语表 + 目标改取最近固化条目（时间邻近约束） | **已修** |
| M3 向量降级契约 | `memory_service.py:790` `except (SQLAlchemyError, RuntimeError)` | **已修** |
| P1' 静默时段 | `push_delivery_service.py:223-227` 非跨午夜窗口用 `start <= current < end`；畸形 HH:MM 返回 False；`user_push_opt_in_service.py` `_QUIET_HOURS_PATTERN` 入库校验 | **已修** |
| P2' recall 绕过 | `push_scheduler.py:220-222` recall 发送前复用 `_check_frequency_cap` + `_check_schedule_and_quiet_hours` | **已修** |
| P3' 偏好贯通 | `push_service.py:382-404` `_send_push` 前置 `_aurora_push_opt_in_enabled`（UserPushOptIn 总开关） | **已修** |

**测试**：修复波 10 个新测试文件全绿（34 passed，0 failed）+ 基线失败的 `test_llm_dispatcher_quota.py` 3 passed。逐文件记录见 §5。

### E1 修法安全性复查（`__getattr__` 转发）

- **正向**：dunder 前缀拒绝（防 `__deepcopy__`/pickle 协议误转发）；`self.__dict__.get("llm_service")` 规避初始化前自递归；转发只发生在包装器未定义属性的分支。
- **风险 1（已现实化，非假设）**：转发使 `chat_json`/`reason`/`reason_json`/`continue_with_tool_results`/`chat_stream_with_tools`/`generate_push_content` 等内部服务方法对 wrapper 调用方**直接可用**——这些调用**绕过包装器的输入过滤/配额/输出校验三层**。全仓约 20 个调用点实际走的就是这条旁路（§2 Group B）。安全层目前只覆盖 4 个自定义方法，而这 4 个方法的签名又与全仓约定错位导致无人真正走到——**净效果：wrapper 名义上是安全边界，实际上当前生产流量 100% 走无安全包装的旁路**。
- **风险 2（低）**：inner 的 `provider`/`providers`（含 api_key 的 SecureLLMClient 句柄）等私有属性可经转发触达；无远程暴露面（进程内单例），但若未来 wrapper 被传给不可信插件层则成泄漏面。
- **建议**：转发改为**允许清单**（chat_model/reason_model/default_model/agent_role/model_key/get_current_selection/is_thinking_mode 等只读路由元数据），其余显式 AttributeError。成本极低，且与 §2 统一修复同步落地。

---

## 2. ★专项：`LLMSecurityWrapper.chat` 签名系统性错位（R2 修复波头号输入）

### 2.1 事实链（全部实证，非推断）

1. `llm_service.py:1528` 导出的模块级单例 `llm_service` 是 `LLMSecurityWrapper`，其 `chat` 签名为 **`chat(user_id, messages, model=None, temperature=0.7, **kwargs)`**（user_id 第一位，必填）。
2. 全仓唯一 messages-first 约定的真实现是裸 `LLMService.chat(messages, model, temperature, *, task_type, **kwargs)`（`get_llm_service*` 族返回裸服务）。
3. **全仓生产代码 0 个调用点使用 user_id-first 约定**（仅 wrapper 自身 docstring/demo 用）。
4. 真实单例运行时实证（python3.11，真模块导入，参数绑定期失败、无网络副作用）：

```
singleton type: LLMSecurityWrapper
chat sig      : (user_id: 'str', messages: 'list[dict[str,str]]', model=None, temperature=0.7, **kwargs)
positional chat(messages)   -> TypeError: missing 1 required positional argument: 'messages'
keyword chat(messages=..)   -> TypeError: missing 1 required positional argument: 'user_id'
chat(prompt=..)             -> TypeError: missing 2 required positional arguments: 'user_id' and 'messages'
chat_with_tools(kw)         -> TypeError: missing 1 required positional argument: 'user_id'
safe_llm_call 实跑两轮重试后返回 fallback，日志原文：
  [LLMFallback] Call failed (attempt 1/2): LLMSecurityWrapper.chat() missing 1 required positional argument: 'messages'
```

5. **为什么 R1 修复波 31 测试全绿却没发现**：`test_llm_dispatcher_quota.py:52,74` 用 `monkeypatch.setattr("...llm_service.chat", _chat)` 把 wrapper.chat 整个换成 `(*args, **kwargs)` mock——mock 不做参数绑定，签名错位在测试里结构性不可见（mock-oracle）。E1 的 `__getattr__` 修复让 `chat_model` 可达、测试由红转绿，但紧接着的 `chat()` 调用换了种死法：从 AttributeError 变为每次必 TypeError → dispatcher 的 `except Exception` 兜底 → 返回 `PROVIDER_UNAVAILABLE "chat() missing 1 required positional argument: 'messages'"` 并给熔断器记失败。

### 2.2 全量调用点清单（生产 `app/`，静态 AST 扫描 + 逐点人工溯源）

**Group A — 真坏：wrapper 单例直呼 chat 族，运行时 TypeError（12 个直接点）**

| # | 调用点 | 调用形态 | 运行时实际行为（判定依据） | 影响面 |
|---|---|---|---|---|
| A1 | `services/llm_fallback_utils.py:88`（`safe_llm_call`） | `chat(messages, **kwargs)` 位置传参 | TypeError → except 吞掉 → 重试一次 → **静默返回 fallback 值**（实证日志见上） | **最大枢纽**。经 14 个 `LLMFallbackWrapper` 实例（vocabulary/stt/omnibar/summarization/preferences/agent/cognitive/sufficiency/router/focus/search/plan/hyde/analysis）波及 **23 个消费模块**：意图路由 LLM 层恒返回默认 `{"type":"chat"}`、充分性检查恒 `{"specific":True}`、专家智能体/报告/模拟/剧场/词典/STT/HyDE/证据抽取（`evidence/conversational_extractor`）等全部退化为静态默认值，无任何用户可见错误 |
| A2 | `services/llm_dispatcher.py:98` | `chat(messages, model=model_id)` | TypeError → except Exception → 退配额 + **熔断记失败** + 返回 `PROVIDER_UNAVAILABLE`（错误文本即 TypeError 原文） | gRPC `InferenceService.RunInference` 同步推理契约面 100% 不可用（非 PREDICT_NEXT_ACTIONS 全部）；`task_service.py:1343` 走 PREDICT_NEXT_ACTIONS 子路径不受影响；gateway 侧当前无内部调用方（仅生成桩），故属"契约面死亡"而非线上事故 |
| A3 | `orchestration/graph_rag.py:745` | `chat(messages, temperature=0.0)` | TypeError → warning → 退 `extract_entities` → 又触发 A4 → 最终 regex 启发式切分 | 多跳检索概念抽取降级为正则 |
| A4 | `orchestration/graph_rag.py:1665` | `chat(messages)` | TypeError → 退 `_simple_extract` → **返回 []** | GraphRAG 实体抽取（LLM 路）恒空，图检索召回质量受损 |
| A5 | `services/cognitive_service.py:271` | `chat(messages, temperature=0.7)`（未 await，靠 isawaitable 兜） | TypeError ∈ RECOVERABLE_LLM_ERRORS → 退 `cognitive_llm.call` → **A1 枢纽又死** → 返回 None | 认知 HyDE 双重降级，静默 |
| A6 | `services/cognitive_service.py:516` | 同上 | 仅 mock 检测分支可达（`__class__.__module__.startswith("unittest.mock")`），显式捕 TypeError | 非生产路径；讽刺点：作者已为 mock 场景写了同款 TypeError 防护，生产 wrapper 场景（:271）却没防 |
| A7 | `services/document_service.py:96` | `chat([...], temperature=0.2)` | TypeError → warning → return None | 文档上下文摘要富化恒缺失 |
| A8 | `services/translation_service.py:364` | `chat(messages=..., model=...)` 关键字 | TypeError（缺 user_id）→ 传播至分段级 except → 该分段翻译失败 | 专业供应商全败后的最终兜底死；主路径（SecureLLMClient）健康 |
| A9 | `agents/enhanced_orchestrator.py:433` | `chat(messages=..., model="qwen-plus")` | TypeError → except → format_response(error) | 无专家匹配时的兜底回复恒为错误文案 |
| A10 | `agents/orchestrator_agent.py:158` | `chat(prompt=..., model=...)` | TypeError（prompt 不是任何签名的参数，缺 2 参）→ except → "抱歉，我暂时无法回答这个问题。" | 同上（legacy agent 链） |
| A11 | `api/v1/chat.py:253` | `chat_with_tools(system_prompt=..., user_message=..., tools=..., conversation_history=...)` | TypeError（缺 user_id）→ 无局部 try → 端点 500 | v1 task-chat HTTP API 的 LLM 步骤死亡 |
| A12 | `api/v1/chat.py:466` | 同 A11 | 同上 | 同上（第二个 v1 端点） |

**Group A' — 真坏：wrapper 经参数传递后的 chat_with_tools（1 点 4 个上游）**

| # | 调用点 | 链路 | 行为 |
|---|---|---|---|
| A13 | `orchestration/error_handler.py:61` | `api/v1/chat.py:516,662,774,805` 把 wrapper 单例作 `llm_service=` 传入 → `chat_with_tools(system_prompt=..., user_message=..., tools=...)` | TypeError → except → 工具自我修正恒失败，返回原始错误结果。v1 工具调用错误恢复能力死亡 |

**Group B — 假坏（经 `__getattr__` 转发按裸服务签名工作，功能正常但绕过安全层）**

`reason`(enhanced_agents ×2)、`chat_json`(standard_workflow:2968 / plan_review:1115 / llm_extractor:88 / skill_extract:101 / skill_share:252)、`reason_json`(plan_review:1031 / planning_workflow:2830 / task_guide_enricher:278)、`continue_with_tool_results` + `chat_stream_with_tools`(api/v1/chat ×5、execution_engine:1379)、`chat_model/reason_model`(dispatcher:519,520、translation ×4)、`generate_push_content`(push_service:373)、`__class__`(cognitive mock 检测)。**主聊天脊柱（ChatOrchestrator → standard_workflow）经 `get_configured_llm_service*`（裸服务）+ 转发流式 API，功能完好**——这解释了为何 demo 不易暴露。

**Group C — 不受影响（从一开始就是裸服务/独立 client）**

`get_llm_service*` 全族调用方（standard_workflow 各 runtime/rescue_llm、workflow_experience、context_pruner、validation_engine、goal_quality_evaluator、predictive_service、planning_benchmark、feedback_driven_generation、profile_transparency）、`SecureLLMClient`（translation 主路、ocr）、`get_llm_service_for_task`（reflection generator——但见 N2，另有独立签名 bug）。

**统计**：真坏直接点 12 + 参数传递点 1（4 上游）= **13 处真坏**；F3 报告点名的 dispatcher/graph_rag/cognitive **三处全部属实、零假坏**；但 F3 **漏报了最大枢纽 A1（llm_fallback_utils）及 api/v1/chat、error_handler、translation、两个 agent 兜底、document_service** —— 实际影响面显著大于 F3 描述。

### 2.3 统一修复方案（R2 修复波头号输入）

**单一修复点：把 wrapper 的 4 个安全方法签名与裸服务对齐（messages-first，user_id 降为可选 kwarg）**：

```python
# backend/app/core/llm_security_wrapper.py
async def chat(self, messages, model=None, temperature=None, *, user_id=None, **kwargs): ...
async def stream_chat(self, messages, model=None, temperature=None, *, user_id=None, **kwargs): ...
async def chat_with_tools(self, system_prompt, user_message, tools,
                          conversation_history=None, model=None, *, user_id=None): ...
async def generate_embeddings(self, texts, model=None, *, user_id=None): ...
```

- 依据：①全仓 0 个 user_id-first 生产调用点，改签名零破坏（wrapper docstring/demo 同步改）；②裸 `LLMService.chat` 本就接受 `user_id` kwarg（`_resolve_user_id`）并自带 `secure_messages` 输入净化，wrapper 侧 user_id=None 时跳过配额检查（改记 debug 日志与 metric）即可，内部/批量调用无用户上下文不应被配额门挡死；③`temperature` 默认必须改 **None**（非 0.7），否则 wrapper 路由的调用会以显式 0.7 击穿 E2 的 selection 配置优先级——这是修签名时最容易引入的回归点。
- 一并落地：`__getattr__` 转发改允许清单（§1 E1 复查建议），防止未来新属性静默绕过安全层。
- 修完后必须补**契约测试**（防 mock-oracle 复发）：`inspect.signature(llm_service.chat)` 首参为 `messages`；用 demo-mode/伪 inner 服务走真绑定调用 `llm_service.chat([...])` 全链不 TypeError；`test_llm_dispatcher_quota.py` 的 chat mock 改为"仅替换 provider 层"而非整个 chat。
- 次级独立修复（同族但不同根因）：`agents/reflection_agent.py:566,706` 以 `chat(system_prompt=..., user_message=...)` 调**裸服务**（此签名在全仓任何实现上都不存在）→ TypeError；:706 在 try 内被吞（修正恒失败），:566 无局部防护需确认上游。修法：构造 messages 列表调用。

**影响面排序（修复后收益）**：A1 枢纽（23 模块恢复真实 LLM 能力）> A11/A12/A13（v1 API 与工具自愈恢复）> A2（推理契约面复活 + 停止毒化熔断）> A3/A4（GraphRAG 质量）> A5/A7/A8/A9/A10。

---

## 3. 复审新发现表

| ID | 严重度 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| N1 (R2) | **P1** | `services/quota.py:10-11` + 全部以 `backend/` 为 CWD 的运行模式 | `RATE_LIMIT_LUA_PATH = "backend/app/services/lua/rate_limit.lua"` 为 **CWD 相对路径**。`make grpc-server` 的 `run_grpc_with_env.sh:13` 会 `cd backend/`；容器 WORKDIR=/app + `COPY . .`（backend 为 context）同样拼出不存在路径。**实测**（CWD=backend/，真 Redis）：`Rate limiter script load failed: [Errno 2] No such file...` → `check_and_decr(999999, limit=10)` 返回 `QuotaResult(allowed=True, current=0)` —— **配额在这些运行模式下被静默 fail-open 关闭**，仅一条 warning。R1 记录的"Redis 故障 fail-open 是取舍"之外，这是**确定性触发**的关闭 | pathlib 锚定模块位置：`Path(__file__).resolve().parents[1] / "lua" / "rate_limit.lua"`（refund 同理）。同时建议 load 失败改为启动期 fail-fast 或至少 ERROR 级 + metric |
| N2 (R2) | P2 | `agents/reflection_agent.py:566,706` | `generator.chat(system_prompt=..., user_message=...)` 对裸 LLMService 是不存在的签名（messages 缺失必 TypeError）；:706 被吞（修正恒失败返回原文+失败说明），:566 无局部 try | 构造 messages 调用；补一条真绑定测试 |
| N3 (R2) | P2 | `services/llm_dispatcher.py:63` | `_cache_key`（内含 `_select_model` → wrapper 属性访问）仍在 try 块外；属性转发当前可用，但任何缓存键构造异常将绕过统一错误映射直达 gRPC 层 INTERNAL（R1 已建议，未随 E1 落地） | 移入 try 或单独 try 映射为 SCHEMA_VIOLATION |
| N4 (R2) | P2 | 测试基建（跨切片） | **mock-oracle 类缺陷**：`llm_service.chat` 被 `(*args, **kwargs)` mock 替换后，签名契约在测试中结构性不可见——本次 P0 级错位正是靠它 hiding（§2.1.5） | 契约测试 + 修 mock 粒度（mock provider 层而非 service 方法）；可作为 R2 全切片通用守则 |
| N5 (R2) | P3 | `core/llm_security_wrapper.py` | 修签名前 wrapper 的安全三件套（输入过滤/配额/输出校验）实际覆盖率为零（4 方法无人能成功调用，其余流量走转发旁路）；修签名后覆盖面也仅限 chat 族，chat_json/reason 族仍走旁路 | 与 §2.3 允许清单方案合并处理；若安全层要对全流量生效需在裸服务 `secure_messages` 之外明确分层策略 |
| N6 (R2) | P3 | `services/billing_worker.py`（B2 残余） | `_recover_failed_batch` 在 Redis 与 DB 同时故障时记录丢失（仅日志）；`_billing_attempts` 元数据若记录最终经 `_to_stmt_data` 落库会被显式列丢弃（已核对，无泄漏） | 可选：落库前本地 WAL 或文件死信；当前可接受 |
| N7 (R2) | 环境 | 本机 | 磁盘 100% 满（/ 仅余 866Mi）导致 Docker/PG/Redis 宕机、工具链 ENOSPC——已影响本轮真 PG 验证，**会同样打断 R2 修复波的验证环节** | 人工清理磁盘后再开修复波（Human 执行权） |

R1 台账项（L4/L5/L6/M4/M5/N1/U1/U2/F1/F2/W1 等 P3）本轮未重审，状态不变。

---

## 4. 运行时复审记录（C 任务）

### 4.1 C1 quota.lua CWD（= N1）
确认 + 实证（§3 N1）。修法：`Path(__file__).resolve().parents[1] / "lua"` 锚定。

### 4.2 C2 计费账目一致性（真 Redis 完成；真 PG 被环境阻断）
- **配额 Lua（真 Redis，repo-root CWD）**：`check_and_decr 500 → current=500`；再 `200 → 700`；TTL 86400 → 1.2s 后 86399（**固定窗口不滑动，Q1 live 证实**）；`refund 300 → 400`；`refund 99999 → key 删除（钳 0，无负值）`。全对。
- **商城链（sqlite 单测）**：`test_shop_service.py` 4 passed（购买/幂等/余额约束）。
- **真 PG 腿（P1 事务内购买→幂等重放→余额不足拒绝→对账；P3 billing worker 真库 flush + UTC 时间戳 + request_id 唯一）**：脚本已写好（回滚式 + 双重清理，marker 用户），因 PG 宕机未执行。**状态：未验证（环境），不是通过**。恢复后可直接跑（脚本要点已内化到本报告附录 A）。

### 4.3 C3 LLM fallback 链（真 Redis 实测）
STANDARD 起步 `xiaomi_standard_thinking` → 注入 429 → 同档 `deepseek_chat` → 注入 429 → 同档 `dashscope_standard_thinking` → 成功。健康键 `llm:fail:xiaomi_standard_thinking=1` 真实写入；二次运行同档优先、无向上升级。**次序符合 E3 修复语义（同档优先→成本降序），实证通过**。

### 4.4 C4 证据融合回归
6 个测试文件 34 passed（belief fusion/observation/calibration/health/resolve/scoring）。R1 边界审结论维持，修复波无回归。

---

## 5. 测试记录（命令均自 wt3，env：SECRET_KEY/JWT_SECRET/REDIS_URL 按协调方给定）

```bash
# R1 修复波 10 文件（分 3 批，一次一命令）
pytest tests/services/test_semantic_cache_service.py tests/unit/test_auth_session_touch.py tests/unit/test_billing_worker.py -q   # 12 passed
pytest tests/unit/test_llm_explicit_temperature.py tests/unit/test_llm_tier_fallback_order.py tests/unit/test_memory_inferred_write_lane_queue.py -q  # 9 passed
pytest tests/unit/test_push_quiet_hours.py tests/unit/test_push_recall_policy_guards.py tests/unit/test_rate_limit_lua.py tests/unit/test_working_memory_rejection_guard.py -q  # 13 passed
pytest tests/unit/test_llm_dispatcher_quota.py -q      # 3 passed（R1 基线曾 2 失败）
pytest tests/unit/test_shop_service.py -q              # 4 passed
pytest tests/unit/test_belief_fusion_engine.py test_belief_observation_models.py test_evidence_calibration.py test_evidence_health.py test_evidence_resolve.py test_evidence_scoring.py -q  # 34 passed
```

运行时实证脚本（wrapper 签名 / quota fail-open / fallback 链 / Q1 live）以 heredoc 执行，关键输出已摘录进 §2.1、§3 N1、§4.2、§4.3。

---

## 附录 A：C2 真 PG 脚本要点（恢复后可复跑）

单外层事务（`engine.begin()` + `external_transaction_managed=True`）：建 marker User(photon_balance=1000) + ShopItem(300) → `purchase_item` 断言余额 700 与 ShopPurchase before/after → 同 idempotency_key 重放断言无二次扣减 → 余额改 50 断言 ValueError → 对账 `1000 - sum(price_paid) == 700` → 回滚并验证无残留。P3：提交 marker 用户 → `BillingWorker(db_url=真库)._batch=[record]` → `_flush_to_db()` → 断言 TokenUsage 行、`timestamp == fromtimestamp(ts, tz=UTC).naive`（B1）、同 request_id 二次 flush 唯一约束成立 → 清理删除。Redis 侧（已完成部分）见 §4.2。
