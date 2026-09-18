# R2 修复波·Wave1 · G3 修复记录（03 引擎关键服务切片）

- 修复员：G3
- 基线：main@ca86bda8（冻结工作树 wt3）
- 输入：[03-r2-critical-services.md](03-r2-critical-services.md)（§2.3 专项 + §3 新发现表）
- patch：[03-r2-fixes.patch](03-r2-fixes.patch)
- 测试环境：`cd backend && SECRET_KEY=… JWT_SECRET=… REDIS_URL=redis://:…@localhost:6379/1 pytest <目标> -q`（真 Redis 8.4.1 本机实例；PG 未涉及本波修复）

---

## 1. 修复清单（ID → 修复 → 测试 → 证据）

### ★P0：wrapper 签名统一（报告 §2.3）

**修复**：`backend/app/core/llm_security_wrapper.py`

| 项 | 位置 | 内容 |
|---|---|---|
| chat | `:146` | `chat(messages, model=None, temperature=None, *, user_id=None, **kwargs)`——messages-first；temperature 默认 **None**（非 0.7，防击穿 E2 selection 优先级）；user_id 可选 kwarg |
| chat_with_tools | `:250` | `(system_prompt, user_message, tools, conversation_history=None, model=None, *, user_id=None)`——前三参与裸服务及全部生产调用点对齐；内层调用**不再转发 `model=`**（裸服务不接受该 kwarg，原内层调用即便签名修好也必 TypeError） |
| stream_chat | `:370` | `(messages, model=None, temperature=None, *, user_id=None, **kwargs)`；temperature=None 时不向内层注入（内层保留自身默认与 E2 语义） |
| generate_embeddings | `:460` | `(texts, model=None, *, user_id=None)` |
| 配额门 | `:518 _quota_guard` | `user_id=None` = 内部/批量调用：跳过配额检查/用量记录，记 debug 日志（报告 §2.3 ②） |
| 内层调用 | `:196-198` 等 | user_id 经 kwargs 透传裸服务（`_resolve_user_id` 消费） |

**配套**：类 docstring 契约声明（`:42-60`）、`__main__` demo 调用改 messages-first、`_call_llm_with_monitoring` 类型签名放宽。

**契约测试**（防 mock-oracle 复发）：`backend/tests/unit/test_llm_wrapper_signature_contract.py`
- `TestSingletonSignatureContract`（8 条）：真单例 `inspect.signature` 断言首参/参数序/`temperature.default is None`/`user_id` keyword-only，且与裸 `LLMService.chat` 参数面对齐。
- `TestProductionCallSiteShapesBind`（13 条 = 13 真坏点逐一）：以**真实单例绑定方法签名**做 `sig.bind(...)`，形状逐一取自报告 §2.2 Group A/A'（file:line 注明）。
- `TestRealBindingFullChain`（10 条）：bare-signature 内层桩（多余 kwarg 即 TypeError）+ 真 wrapper 代码路径全链调用，断言无 TypeError、temperature=None 原样透传、`chat_with_tools` 内层不收到 `model=`、非空 conversation_history 过滤路径可用。
- `TestGetattrAllowlist`（4 条）：见 E1。

**红证据**（修复前，27 failed / 5 passed）：
```
TypeError: LLMSecurityWrapper.chat() missing 1 required positional argument: 'messages'
TypeError: missing a required argument: 'self'   ← a11/a13 形状对旧签名绑定失败
```
与报告 §2.1.4 运行时实证逐字一致。

**绿证据**：46 passed（契约 34 + quota 1 + reflection 2 + dispatcher 4 + 旧 wrapper 测试 2 + E2 温度 3，单批命令）。

**运行时实证**（真单例、真导入，等价复测报告 §2.1.4）：
```
chat sig       : (messages: 'list[dict[str, str]]', model: 'str | None' = None,
                  temperature: 'float | None' = None, *, user_id: 'str | None' = None, **kwargs)
chat(messages)                     -> RESULT-OK（demo 模式响应全文返回）
chat(messages, temperature=0.0)    -> RESULT-OK
chat(messages=, model=chat_model)  -> RESULT-OK
chat_with_tools(system_prompt=, user_message=, tools=, conversation_history=)
                                   -> 无 TypeError；穿透 wrapper 三层安全后真实发起
                                      provider 调用（本沙箱 401 Invalid API Key，环境性，
                                      绑定与安全链路全通）
chat(prompt=)                      -> 仍 TypeError（该形状无签名可容，调用点已修，见 A10）
```

### 13 真坏调用点恢复验证（A1–A13）

静态核对（逐一 sed/grep 确认调用形状与新签名匹配）+ `TestProductionCallSiteShapesBind` 对真单例签名绑定 + 全链/运行时实证：

| # | 调用点 | 修复方式 | 验证 |
|---|---|---|---|
| A1 | `services/llm_fallback_utils.py:88` | 签名统一（无需改调用点） | 绑定测试 a1 + 全链 chat 透传 **kwargs |
| A2 | `services/llm_dispatcher.py:105` | 同上 | `test_llm_dispatcher_quota.py` 4 passed（spec 化 mock） |
| A3 | `orchestration/graph_rag.py:745` | 同上 | 绑定测试 a3 |
| A4 | `orchestration/graph_rag.py:1665` | 同上 | 绑定测试 a4 |
| A5 | `services/cognitive_service.py:271` | 同上 | 绑定测试 a5 |
| A6 | `services/cognitive_service.py:516` | 同上 | 绑定测试 a6 |
| A7 | `services/document_service.py:96` | 同上 | 绑定测试 a7 |
| A8 | `services/translation_service.py:364` | 同上（`chat_model` 入 allowlist） | 绑定测试 a8 |
| A9 | `agents/enhanced_orchestrator.py:433` | 同上 | 绑定测试 a9 |
| A10 | `agents/orchestrator_agent.py:158` | **调用点修复**：`prompt=` 改构造 messages 列表（该形状任何签名都无法绑定） | 绑定测试 a10 + 文件内 `messages=[...]` 实证 |
| A11 | `api/v1/chat.py:253` | 签名统一 | 绑定测试 a11 + `test_chat_with_tools_sanitizes_conversation_history` |
| A12 | `api/v1/chat.py:466` | 同上 | 同上 |
| A13 | `orchestration/error_handler.py:61`（上游 chat.py:516/662/774/805 传入单例） | 同上 | 绑定测试 a13 + 仅三必参全链用例 |

### E1 补强：`__getattr__` allowlist

**修复**：`llm_security_wrapper.py:101-141`——`_FORWARD_ALLOWLIST` frozenset：
- 只读路由元数据：`chat_model / reason_model / default_model / agent_role / model_key / get_current_selection / is_thinking_mode`（dispatcher:519-520、translation ×4、persistence_layer:40 在用）；
- 经审计的功能透传（报告 Group B 生产在用，含主链 `standard_workflow.py:2968 chat_json`、api/v1/chat 流式工具族、push_service、enhanced_agents reason ×2 等）：`chat_json / reason / reason_json / continue_with_tool_results / chat_stream_with_tools / generate_push_content`。
- 其余属性显式 `AttributeError`（含 `provider`/`providers` 等私有句柄面）；dunder 拒绝保留。
- allowlist 收敛前对全仓做了 AST 扫描 + 参数传递链核查（`self.llm_service.*`、`PlanMatchingService` 等旁支），确认无生产访问面遗漏。

**测试**：`TestGetattrAllowlist` 4 条（allowlist 内转发 ✓ / 功能透传 ✓ / 白名单外 AttributeError ✓ / dunder 拒绝 ✓）。
**红/绿**：红（修复前）`test_non_allowlisted_attributes_blocked` 与 `test_dunder_forwarding_rejected` 失败（全量转发放行 `provider` 等）→ 绿（修复后 34/34）。

### P1：quota.py Lua CWD（N1）

**修复**：`backend/app/services/quota.py:15-17`——`_LUA_DIR = Path(__file__).resolve().parent / "lua"`，两脚本路径常量随之锚定。
注：报告建议 `parents[1]`，实测会指到 `app/lua`（不存在）；quota.py 与 `lua/` 同在 `app/services/` 下，正确锚定是 `parent`。以 chdir 红测试实测为准绳。

**测试**：`backend/tests/unit/test_quota_lua_cwd.py`——chdir `/tmp` 后：`check_and_decr(6)→current=6`、`check_and_decr(5)→allowed=False`（limit=10）、`refund(3)→用量 3`（refund 语义 = 回退后累计用量，与报告 §4.2 实测一致）；真 Redis，键测试后清理。
**红证据**：fail-open 形态 `allowed=True, current=0`（脚本加载失败仅 warning）→ **绿**。
（存量 `test_rate_limit_lua.py` 9 passed 无回归。）

### P1：reflection_agent 真实签名（N2）

**修复**：`backend/app/agents/reflection_agent.py:566-573`（`_reflect_trigger`）、`:710-725`（`_execute_fix`）——构造 `[{role: system}, {role: user}]` messages 列表按裸服务签名调用。

**测试**：`backend/tests/unit/test_reflection_agent_chat_binding.py`——注入 bare-signature 假生成器（`system_prompt=` 落入即 TypeError）真绑定调用两路径，断言 messages 形态与解析结果。
**红证据**：`:566` TypeError `missing ... 'messages'`；`:706` 被吞——日志原文 `[ReflectionAgent] Fix execution failed: BareSignatureGenerator.chat() missing 1 required positional argument: 'messages'`（与报告"修正恒失败"一致）→ **绿** 2 passed。

### P2：dispatcher `_cache_key` 入 try（N3）

**修复**：`backend/app/services/llm_dispatcher.py:62-69`——`_cache_key` 单独 try，异常映射 `SCHEMA_VIOLATION`（报告许可的最小方案，不重排配额/缓存段）。
**测试**：`test_llm_dispatcher_quota.py::test_dispatcher_maps_cache_key_failure_to_schema_violation`。
**红**：异常穿出 `run()`（gRPC 层 INTERNAL）→ **绿**：返回 `ok=False, error_reason=SCHEMA_VIOLATION`。

### mock-oracle 加固（N4，本切片部分）

`test_llm_dispatcher_quota.py` 的 chat mock 由 `(*args, **kwargs)` 裸函数改为 `AsyncMock(spec=llm_service.chat)`（真实绑定方法为 spec，签名不匹配即 TypeError）。两用例在 spec 化后仍绿，证明 dispatcher 调用形状与新签名一致。

---

## 2. 新发现（本波实证，已随手修复 / 记档）

| ID | 严重度 | 位置 | 问题 | 处置 |
|---|---|---|---|---|
| G3-N8 | P1（随 P0 一并修） | `llm_security_wrapper.py:214,336,430,501,626,631` | `TASK_FAILURES`/`LLM_CALLS_TOTAL`/`LLM_LATENCY_SECONDS` 是 llm_monitoring **模块级**指标，wrapper 错用 `self.monitor.X` 访问——monitor 开启（生产单例默认）时任何内层失败的 except 路径自身 AttributeError，**吞掉原始错误**（运行时实证撞出） | 已修：改为模块级导入直用；新增回归测试 `test_monitor_enabled_original_error_propagates` |
| G3-N9 | P1（随 P0 一并修） | `llm_security_wrapper.py:275-294,478-482` | `sanitize_input` 返回 `SafetyCheckResult` 对象，wrapper 的 `chat_with_tools`/`generate_embeddings` 输入过滤路径对其做**元组解包**——必 TypeError（含 conversation_history 过滤循环，A11/A12 必经）。因这俩方法从未能调通而潜伏 | 已修：改用 `.sanitized_text`；全链用例覆盖（含非空 history） |
| G3-N10 | P3（记档不修） | `tests/unit/test_learning_path_task_fallback.py:110` | 基线既有失败（stash 验证 ca86bda8 同样失败）：未传 locale（默认 en）却断言中文标题"补齐前置知识"，实际返回 "Fill prerequisite knowledge: …" | 与本波修复无关，留待 i18n 切片 |
| G3-N11 | P3（记档不修） | `tests/unit/test_stage38_d3_persistence.py` 链路 | 该测试链将 `sys.modules["inference_pb2"]` 换成缺 `QUOTA_EXCEEDED` 的 SimpleNamespace 假桩；与 `test_orchestrator_request_scoping.py`（导入 llm_dispatcher，模块级引用 pb2 枚举）同批收集时污染收集期（stash 验证基线同样复现）。单独/两两组合均绿 | 测试隔离债务，留待测试基建切片 |
| G3-N12 | P3（记档不修） | `services/plan_matching_service.py:290` | `self.llm_service.complete(prompt)`——生产实例化（context_builder.py:1395）不传 llm_service（None 短路不可达），且 `complete` 在裸服务上也不存在 | 死代码路径，留待清理 |

## 3. 回归记录（改动后全绿；一次一命令）

```bash
pytest tests/unit/test_llm_wrapper_signature_contract.py tests/unit/test_quota_lua_cwd.py \
       tests/unit/test_reflection_agent_chat_binding.py tests/unit/test_llm_dispatcher_quota.py \
       tests/unit/test_llm_security_wrapper.py tests/unit/test_llm_explicit_temperature.py -q
# 46 passed
pytest tests/unit/test_rate_limit_lua.py tests/unit/test_llm_cost_monitoring.py（+temperature）  # 14 passed
pytest tests/unit/test_llm_same_tier_fallback.py tests/services/test_cognitive_service_core.py  # 与 learning_path 同批 39 passed（1 失败为基线既有 G3-N10）
pytest tests/services/test_translation_service.py tests/agents/test_enhanced_orchestrator.py    # 29 passed, 3 skipped
pytest tests/unit/test_llm_service_security.py tests/unit/test_llm_extractor_service.py tests/unit/test_skill_extract_service.py -q  # 8 passed
pytest tests/unit/test_standard_workflow_generation_routing.py / test_stage38_d3_persistence.py / test_orchestrator_request_scoping.py  # 28+4+3 passed（三件套同批收集污染为基线既有 G3-N11）
```

## 4. 剩余清单

- N5（报告原列 P3）：安全层覆盖面仍仅 chat 族四方法；`chat_json`/`reason` 族经 allowlist 显式透传仍绕过 wrapper 三层（裸服务自身有 `secure_messages`）。分层策略待产品决策。
- N7（环境）：磁盘/容器健康由 Human 持续保障；本波已在真 Redis 上验证。
- C2 真 PG 腿（报告附录 A 脚本）：环境恢复后可复跑，不在本波范围。
- G3-N10/N11/N12：见上表，记档待后续波次。
