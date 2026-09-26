# WT587 诚实性轴猎缺 · 第一轮发现

- 工位：wt587 ｜ 轴：诚实性/未兑现承诺（声称 X 实际做 Y）
- 基线：main 头 `c4ad754d`（分支 `agent/node-b/wt587/honesty`）
- 日期：2026-09-25 ｜ 方法：只读对码 + 正则/调用图核验 + 可运行证伪实验
- 已避开在案编号：256–300 全占（含 286 GUEST_SEED_TOTAL、287 demo 面误标、292–300 wt573/wt576/wt582 数据正确性轴）。本文发现建议编号自 **V3-FIX-301** 起，撞号由集成侧重排。
- 严重度口径：P1 冒充模型结果 / P2 用户可见或账本失真 / P3 文档债·测试债。

---

## V3-FIX-301（建议）｜P2｜域1 降级路径：合成兜底计划自动获得伪造「计划审查 APPROVED」记录，且对齐度分数是拿计划自身置信度冒充的

**声称 vs 实际**
- 声称：计划在执行前经 plan review（LLM 审查对齐度/风险），审查结论写入 `plan_review` 并向用户呈现（ux_envelope：`已记录本轮计划审查状态`）。
- 实际：凡是「synthesized fallback」计划（planner 超时/熔断 OPEN/审查降级三路），LLM 审查被整段跳过，直接写入一条 `decision=APPROVED` 的伪审查记录；`alignment_score` 与 `confidence` 都取自 `executable_plan.confidence`——而该置信度在 `build_fallback_plan` 里刚被人为抬到 `max(confidence, 0.35)`。即：对齐度字段里的数字不是任何对齐评估的产物，是兜底模板自己声称的置信度。

**证据链**
1. `backend/app/orchestration/lang_graph_planner.py:565-609`：`build_fallback_plan` 把 `fallback_plan.source` 置为 `"langgraph"`（`orchestration/schemas.py:139` 的 `Literal["langgraph","fast_path","shadow"]` 无 fallback 值——降级计划在元数据层与真实 LLM 计划不可区分），并把 `confidence` 抬到 ≥0.35（:606）。rationale 文本是唯一诚实标记。
2. `backend/app/orchestration/execution_engine.py:2499-2514`（`_plan_and_validate`，经 `orchestrator.py:3714` 接入主聊天链）：`synthesized_fallback = "synthesized fallback" in rationale` → 跳过 `plan_review_service.review_plan`，硬编码 `{"decision": APPROVED, "confidence": executable_plan.confidence, "alignment_score": executable_plan.confidence, "reasoning_source": "rule_skip_synthesized_fallback"}`。
3. 同文件 :2696-2717：审查 REQUIRES_CONFIRMATION/NEEDS_MODIFICATION 的复杂计划被「降级」为兜底计划后，同样伪造 APPROVED 记录（`reasoning_source: "review_degraded_to_synthesized_fallback"`），原始否决结论只留在 `original_review_decision` 字段。
4. 用户可见面：`backend/app/orchestration/ux_envelope.py:1569-1570` 只要 `plan_review` 存在就向 highlights 追加 **「已记录本轮计划审查状态」**（经 `build()` :365→:394 进响应信封）；:1804-1810 下一轮还会说 **「上轮已经生成了计划审查结果」**。伪造记录的诚实文本 `alignment_summary`（"Fallback plan auto-approved…"）不在任何用户可见字段（用户面只消费 `reasoning_summary`，伪造记录没有该键）。
5. 同信封 `_confidence_band`（ux_envelope.py:~975-990）无任何置信信号时默认返回 `"medium"`——兜底计划（伪造置信 0.35）在 UI 置信带层同样呈现为 medium，三态（真实/降级/未知）在响应字段层完全不可区分。

**可证伪验证草图**
单测：构造 planner 抛异常 → `build_fallback_plan` → 走 `_plan_and_validate` 的 review 分支 → 断言 `context_data["plan_review"]["decision"] == "approved"` 且 `alignment_score == plan.confidence`，同时 `plan_review_service.review_plan` 零调用（mock 计数）。再断言信封 highlights 含「已记录本轮计划审查状态」。当前代码下应全绿；若修复（如引入 `source="fallback"`/`degraded=true` 字段并不再伪造 alignment_score）则对应断言翻红。

---

## V3-FIX-302（建议）｜P2｜域2 指标口径：token/成本/trace 账本把降级后实际服务的模型记成「原选模型」，O-02 span 字面自称 actual model

**声称 vs 实际**
- 声称：`chat_with_tools`/`continue_with_tool_results`/`chat_stream_with_tools` 三条链路的成本账本按真实消费模型记账；O-02 trace spine 的 llm_call span 注释明言记录 "actual model/token/cost/latency"（`llm_service.py:1814`）。
- 实际：三处都用 `execute_with_fallback`/`execute_stream_with_fallback` 执行（内部可切换到 fallback 模型），但 usage/成本记账一律用**调用前的** `selection.model_key`。fallback manager 的 `session.final_model_key`（`backend/app/services/llm/fallback.py:621`）是私有状态，`execute_with_fallback` 返回裸 result（:633），真实服务模型信息从未传回调用方。不同模型单价不同 → 模型级成本指标、`llm.usage.*` span、"actual model" trace 全部可归因到错误模型；按模型聚合的健康度/成功率报表分母同样被污染。

**证据链**
1. `backend/app/services/llm_service.py:1451-1455` + `:1466-1468`：`_create_raw_completion_with_fallback(selection, …)` 后 `_record_token_usage(selection.model_key, …)`（source="chat_with_tools"）。
2. `:1560-1561` + `:1577-1582`：同模式（source="tool_results"）。
3. `:1676` + `:1360` + `:1804-1813`：流式链 `selection = self._current_selection` 之后经 `execute_stream_with_fallback` 执行，`model_name = selection.model_key`，并写入 O-02 span `"model": str(model_name)`——注释自称 "actual model"。
4. `backend/app/services/llm/fallback.py:611-633`：成功路径只 `return result`；`:620-621` 记录的 `final_model_key` 无任何外传通道。
5. 对照（非问题面）：非流式 `send_chat` 的 `_report_call_outcome`（:782-798）按真实 selection 逐次上报——说明引擎内已有正确口径先例，三处账本未跟上。

**可证伪验证草图**
单测：`execute_with_fallback` 注入首候选抛 429、次候选成功；捕获 `_record_token_usage`/`record_llm_cost`/span 参数。当前实现下断言「记账 model == 次候选」失败（实际记的是首候选）→ 证明口径失真。修复后（fallback 返回 final selection 或 usage 记账取 final_model_key）同断言转绿。

---

## V3-FIX-303（建议）｜P2｜域3 文档-实现缺口：DoD Gate V3-3「高风险不可逆行为 autonomous execution = 0」——PONR 确定性闸门在主聊天链路被计算后整段丢弃，只靠 LLM 审查兜底

**声称 vs 实际**
- 声称：`v3/V3_DEFINITION_OF_DONE.md:25`「高风险不可逆行为 autonomous execution = 0」；`v3/MASTER_DESIGN.md:15`「工具执行受权限/幂等/预算/回执控制」、:63「UI 的『成功』必须由真实 receipt 驱动」（本条对前两处对码）。
- 实际：`grounding_validator.validate_plan` 会为 `point_of_no_return` 工具与破坏性工具算出 `requires_hitl`/`requires_confirmation`（确定性闸门），但主链路唯一生产调用点把这两个字段**读了 `is_valid`/`failure_reason`/`warnings` 之后其余全部丢弃**——PONR 计划照样进入自动执行。同一接口在 `standard_workflow` 侧有完整 enforcing 实现（queue HITL action），两套并行实现语义相反。业务规则校验里的 PONR 分支更是纯 log。

**证据链**
1. `backend/app/orchestration/grounding_validator.py:153-158`：`if tool_call.point_of_no_return: risk_flags.append(f"irreversible:…")`；`:185-190`：`if tool_call.point_of_no_return: requires_hitl = True`；`:186-193`：`requires_confirmation = len(risk_flags) > 0`。
2. `backend/app/orchestration/execution_engine.py:2452`（`_plan_and_validate`，主链 langgraph/hybrid 必经）：`validate_plan` 全仓唯一生产调用点之一；:2458-2482 只消费 `is_valid`/`failure_reason`/`warnings`——`grep "validation_result\." execution_engine.py` 全部命中仅此三类，`requires_hitl`/`requires_confirmation` 零消费。随后计划直接进入 DAG 自动执行。
3. 对照组（同接口有接线）：`backend/app/agents/standard_workflow.py:2546-2567` 与 `:2731-2753`（`tool_execution_node`）对同两个字段 queue HITL action 并终止流程——证明字段本意是 enforcing，engine 路径是漏接而非有意设计。
4. 纯 log 分支：`grounding_validator.py:412-419`「# 4. PONR 操作需要额外确认」注释下的实现只是 `logger.warning(...)` 后 `return {"is_valid": True}`——注释声称要确认，代码只记日志。
5. 现存兜底只剩概率闸门：PONR 工具的 risk_flags 会进 LLM plan review 提示词（`plan_review_service.py:1291`），reviewer 可返回 REQUIRES_CONFIRMATION 且该路径被 enforcing（engine :2660-2680）——即「不可逆动作 0 自主执行」实际寄望于 LLM 审查每次都注意到 risk_flags；而按 V3-FIX-301，一旦计划降级为 synthesized fallback，这最后一道概率闸门也被跳过（叠加效应：降级链上的 PONR 工具完全无门）。
6. 测试面佐证：`grep -rn "requires_hitl" backend/tests` 无任何 execution_engine 侧 enforcing 断言（仅 standard_workflow/version_conflict 侧有）。

**可证伪验证草图**
单测：构造含 `point_of_no_return=True` 工具（如 `delete_plan`，见 `lang_graph_planner.py:43` PONR_TOOLS）的 ExecutablePlan，mock plan review 返回 APPROVED，跑 `_plan_and_validate` 后断言执行器收到的 tool_calls 为空/有 HITL action。当前代码下该断言失败（tool_calls 原样下达）；对照跑 `standard_workflow.tool_execution_node` 同输入则通过——两条链路行为差即证。

---

## V3-FIX-304（建议）｜P3｜域4 测试空转：安全测试对「JSON 形态密码必须被检出」恒真断言，掩盖了检测模式对该形态确实漏检（已实证）

**声称 vs 实际**
- 声称：`backend/tests/security/test_security.py:529-536` `test_password_in_response_detected`——测试名与 docstring 称「Test that password in response is detected」。
- 实际：被测调用 `security_validator.contains_sensitive_data('{"username": "user", "password": "secret123"}')` 的返回值**被丢弃**，函数以 `assert True` 结束（注释自认「JSON format with : might not match … This is acceptable」）。该测试不可能失败，永远绿。
- 掩盖的真实缺口（本工位已证伪实验）：`llm_safety.py:114` 模式 `password\s*[:：]\s*\S{8,}` 对 JSON 键形态 `"password": "secret123"` **不匹配**（key 与冒号间有引号，`\s*` 吃不掉 `"`）。`python3 -c` 实测：plain 形态 `password: secret123` → True；JSON 形态 → **False**。即 LLM 输出/错误信息里以 JSON 泄露密码时该检测器静默放行，而测试绿着。

**可证伪验证草图**
把该测试改为 `assert security_validator.contains_sensitive_data(response) is True` → 当场红（已用独立正则实验复现 miss）。修法二选一：模式补 `"?password"?\s*[:：]\s*"?\S{8,}`，或测试改 `xfail(strict=True)` 如实登记缺口。

---

## V3-FIX-305（建议）｜P3｜域4 测试空转：gRPC StreamChat 无效用户测试为永真测试（异常路径 assert True、唯一有效断言被注释）

**声称 vs 实际**
- 声称：`backend/tests/integration/test_grpc_streaming_integration.py:436-467` `test_stream_chat_with_invalid_user_id`（"Test StreamChat with invalid user ID"，正常计入通过数）。
- 实际：`try` 内收集错误标志后，唯一收尾断言 `# assert error_received or len(responses) == 0` 被注释（:466-467）；`except Exception` 分支是裸 `assert True`（:465-467）。任何一种行为（错误 metadata、正常完成、异常、空流）都通过——对「无效用户被拒绝」这一被测命题零约束力。

**可证伪验证草图**
在函数体尾部加 `assert False`（或恢复被注释断言）并跑该测试：当前实现下若服务端对 invalid user 正常回错误 metadata，恢复断言即红/绿立辨；若测试继续绿，直接证明其永真属性。修法：恢复收尾断言并对 `except` 分支 `pytest.fail("unexpected exception: …")`。

---

## V3-FIX-306（建议）｜P3｜域2 指标口径：execution_trust 空契约/未知标准类型双双「缺省通过」，但结论仍自称 schema_and_criteria_passed

**声称 vs 实际**
- 声称：`backend/app/core/execution_trust.py:97` 给出 `trust_level=VALIDATED` + `reasons=["schema_and_criteria_passed"]`——语义是「schema 校验与成功标准均已通过」。
- 实际：`_validate_schema`（:155-158）契约无 `required_fields` 时返回 `(0,0)`——0 项校验；`_check_success_criteria`（:166-169、:184）`criteria_type` 缺失或**未知值**（含拼写错误）一律 `return True`。两者皆空跑时结果照样可能 VALIDATED（richness 分 5 个键即拿满 0.3 + criteria 缺省 0.3 ≥ 0.3 门槛），而 reason 字符串仍写 "schema_and_criteria_passed"。下游 `execution_service.py:2497-2504` 以 `success_rate`/信任桶决定放宽或收紧——空契约执行器的结果可凭「已验证」的假标签进入信任通道。
- 未知 criteria_type 静默通过是其中较硬的一半：拼写错误的校验标准与没有标准不可区分，且无任何告警。

**可证伪验证草图**
单测：`evaluate(raw_result={"output": {"a":1,"b":2,"c":3,"d":4,"e":5}}, success_criteria={}, result_contract={})` → 断言当前返回 `VALIDATED` + `"schema_and_criteria_passed"`（现状绿即证「两跳空跑仍发已验证标签」）；再传 `success_criteria={"type":"structured_ouput"}`（拼错）→ 现状同样 VALIDATED 零告警。修法：两者至少其一在 reasons 里如实标 `schema_not_evaluated`/`criteria_unknown_type`，或对未知 type 返回 False+warning。

---

## 扫过无发现 / 未深入的域（如实记录）

- **demo/stub/真实三态在消息落库层**：`persistence_layer.py:93-102` 经 V3-FIX-287 修复后单点保证 demo_mode ⇒ origin=DEMO；本工位复核其注释与实现一致，未发现同类「真实产出被标 DEMO / DEMO 产出无标」残留。
- **LLM 主聊天非流式链（send_chat）**：预算耗尽 429、无 provider 501、熔断 503、全候选不健康 typed error（V3-FIX-78）均为诚实失败路径，未发现把 fallback 文本当真实结果无标返回的面；`_check_demo_match` 拦截在 span 里带 `llm.demo_mode=true`。
- **限流/预算**：`is_llm_within_budget` 耗尽路径 fail-fast 为 429 用户可见文案，无静默降级。
- **runtime probe（Gate V3-0「能力由 runtime probe 得到」）**：仅定位到 `stt_service`/`llm_router` 局部探测痕迹，未完成全量对码——**未验证，不算发现也不算清白**，留第二轮。
- **可恢复 Run（Gate V3-6）**：`backend/app/checkpoint/`（LangGraph Redis checkpointer）与 run 状态机存在，engine :1933 有 `resume_policy="interrupted_only"` 恢复入口；未做端到端恢复演练对码，第二轮可接。
- **tool call 幂等键（Gate V3-6）**：幂等存储存在（`core/idempotency.py`）但接线点是**请求级**（session_id+request_id，`session_state_mixin.py:895`）与 plan_review action 级；未发现 per-tool-call 幂等键。倾向算 DoD 缺口，但执行面工具注册表尚未穷尽扫描，本轮不下结论。

## 复核提示（给第二轮）

1. F-301 最硬的攻击面是「rationale 含 'synthesized fallback' 才触发伪审查」——已核对全部 4 个 `build_fallback_plan` 调用点的 rationale 均含该子串（lang_graph_planner :213/:244、execution_engine :2249/:2301、plan_review_service :2392），无漏网路径；但该字符串匹配契约本身脆弱（i18n/改词即失灵），复核可顺手确认。
2. F-302 注意区分：`_report_call_outcome`（路由健康统计）按真实 selection 上报是**对的**；失真只在 usage/成本/trace 三处记账。
3. F-303 若复核认为「LLM plan review 兜底已满足 DoD」，请回答：为什么 standard_workflow 同接口走了确定性 enforcing 而主链路不走？两套行为差本身即缺口。
