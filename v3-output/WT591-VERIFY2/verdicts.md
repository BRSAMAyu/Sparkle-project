# WT591-VERIFY2 · 诚实性轴第一轮发现（wt587）独立复核裁决

- 工位：wt591（第二轮独立复核）｜ 对象：`v3-output/WT587-HONESTY/findings.md` 六条
- 基线：`agent/node-b/wt591/verify2` @ c34d1c88（main 头）｜ 日期：2026-09-27
- 方法：只读对码 + 真实代码路径可运行实验（未改任何产品/测试文件；实验代码为临时 scratch，跑完即删不入库）
- 环境：backend venv，`DATABASE_URL=sqlite+aiosqlite:///:memory:`

## 裁决总表

| 编号（wt587 建议） | 一句话 | 裁决 | 严重度 | 严重度调整 |
|---|---|---|---|---|
| V3-FIX-301（已被占用，需重编） | 降级计划伪造 APPROVED 审查 | **存活** | P2 | 维持 |
| V3-FIX-302→重编 | token/成本记账用原选模型 | **存活** | P2 | 维持 |
| V3-FIX-303 | requires_hitl 确定性闸门主链路被丢弃 | **存活**（含一处重要精化） | P2 | 维持 |
| V3-FIX-304 | 恒真断言掩盖 JSON 形态密码漏检 | **存活**（范围扩大：生产 sanitizer 同漏） | P3 | 维持 |
| V3-FIX-305 | gRPC invalid-user 测试永真 | **存活** | P3 | 维持 |
| V3-FIX-306 | execution_trust 空契约/未知 criteria 缺省通过 | **存活** | P3 | 维持 |

六条全部存活，无误报，无降级。行号经对码全部核实（个别 ±3 行漂移见各节）。

> 编号注：台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 已占至 V3-FIX-300，且 **V3-FIX-301 已被占用**（wt585 InterventionLevel KNOWN_DRIFT 配套项，因撞号顺延入账）。本工位只复核不编号——下文沿用 wt587 建议号 302-306，301 撞号由集成侧重排。台账 grep 证实：六条主题（synthesized fallback 伪审查 / final_model_key / requires_hitl / assert True / contains_sensitive_data / ExecutionTrustEngine）均无既有条目，全部为新发现。

---

## 301（wt587 建议号，编号已被 wt585 项占用）｜降级计划伪造 APPROVED 审查｜存活 P2

**核实路径（全部对码确认）**
- `backend/app/orchestration/execution_engine.py:2499-2512`：rationale 含 `"synthesized fallback"` → 跳过 `plan_review_service.review_plan`，硬编码写入 `decision=APPROVED, confidence/alignment_score=executable_plan.confidence, reasoning_source="rule_skip_synthesized_fallback"`。
- 同文件 `:2690-2718`：审查否决（REQUIRES_CONFIRMATION/NEEDS_MODIFICATION/REJECTED）的复杂计划被降级为兜底后同样伪造 APPROVED（`reasoning_source="review_degraded_to_synthesized_fallback"`），原始否决只留在 `original_review_decision`。
- `backend/app/orchestration/lang_graph_planner.py:605-606`：`build_fallback_plan` 把 `source` 改写为 `"langgraph"`、`confidence` 抬到 `max(confidence, 0.35)`。
- 用户面：`backend/app/orchestration/ux_envelope.py:1569-1570`（highlights「已记录本轮计划审查状态」）、`:1804-1810`（下轮「上轮已经生成了计划审查结果」）、`_confidence_band`（:966 起）对伪造置信 0.35 落默认分支返回 `"medium"`。

**可证伪复现（3 实验全绿 = 现状即如此）**
1. 熔断 OPEN 强制降级链跑真实 `_plan_and_validate`（其余依赖 mock、审查调用计数）：`review_plan` **零调用**；`state.context_data["plan_review"]["decision"]=="approved"`、`alignment_score==plan.confidence(0.35)`、`reasoning_source=="rule_skip_synthesized_fallback"`、无 `action_id`。
2. 真实 `build_fallback_plan`（monkeypatch `_convert_to_plan` 给低置信底料）：输出 `source=="langgraph"`、`confidence==0.35`（原始 0.05 被抬升）。
3. 伪造记录喂 `UXEnvelopeBuilder._memory_updates`：highlights 含「已记录本轮计划审查状态」；`_confidence_band` 返回 `"medium"`。

**对 wt587 的修正/精化**
- 「落库」表述需收窄：伪造记录**不写 plan_review 表**（不走 `store_review_result`，无 action_id），失真面是 `context_data` → 响应信封 highlights/下轮文案/置信带。账本失真程度略低于原报告语气，用户可见失真（P2 依据）成立。
- rationale 子串契约复核：全部 7 个 fallback 产出点均含 "synthesized fallback"（execution_engine:2249/2301/2702、multi_agent_adapter:117、lang_graph_planner:213/244、plan_review_service:2392），当前无漏网；字符串匹配契约脆弱性属实（改词/i18n 即失灵）。

**修法一句话**：兜底计划引入诚实元数据（如 `source="fallback"` 或 `degraded=true`），`alignment_score` 只允许来自真实审查产物，降级场景如实标 `review_skipped` 且不进「已记录本轮计划审查状态」highlights。

---

## 302（token/成本记账）｜fallback 后仍记原选模型｜存活 P2

**核实路径**
- `backend/app/services/llm_service.py`：三条链路记账全部用调用前 `selection = self._current_selection` 的 `selection.model_key`——`chat_with_tools` :1449→:1466-1473（token+cost+日额度）、`continue_with_tool_results` :1561→:1577-1584、流式 `chat_stream_with_tools` :1676→:1804-1813，且 :1814-1817 O-02 span 把 `selection.model_key` 写进 `"model"` 标签、注释自称 "actual model"。
- `backend/app/services/llm/fallback.py`：成功路径 `:633` 只 `return result`（裸返回）；`:621` 写入的 `session.final_model_key` **全仓仅此一处写、零读点**（grep 证实），无任何外传通道。
- 对照（诚实先例）：`send_chat` 的 `_report_call_outcome`（:782-798）在 `_call_with_selection` 内按当次真实 selection 上报——仅限路由健康统计，usage/成本/trace 未跟上。

**可证伪复现（2 实验全绿）**
1. 真实 `llm_fallback_manager.execute_with_fallback`：首候选抛 `429`、次候选成功——返回值是裸字符串（无 model_key/任何模型元数据），manager 上也无调用方可读的 final 模型残留。
2. 真实 `LLMService.chat_with_tools`（stub provider + 真实 fallback 管理器，首候选 429→次候选 `model-b` 实际服务，call_fn 内断言实际服务方）：`_record_token_usage` 与 `record_llm_cost` 均以 `("wt591-model-a", "chat_with_tools")` 记账——**服务在 model-b、账记在 model-a**。

**修法一句话**：`execute_with_fallback`/`execute_stream_with_fallback` 返回 `(result, final_selection)`（或经 contextvar 暴露 `final_model_key`），三处记账与 O-02 span 的 `"model"` 一律取最终实际服务模型。

---

## 303｜requires_hitl 确定性闸门主链路被丢弃｜存活 P2（含关键精化）

**核实路径**
- `backend/app/orchestration/grounding_validator.py`：:153-157 PONR/破坏性工具进 risk_flags；:177-189 `requires_confirmation = len(risk_flags)>0`、`requires_hitl=True`（tool.requires_confirmation 或 PONR）；:191-197 随 ValidationResult 返回。
- `backend/app/orchestration/execution_engine.py:2452`（主链 langgraph/hybrid 必经）调用后，`grep -n 'validation_result\.' execution_engine.py` 全部 6 处命中仅 `is_valid`/`failure_reason`/`warnings` 三类——`requires_hitl`/`requires_confirmation` 在该文件**零消费**（全文件唯一 `requires_hitl` 是 :2430 版本冲突 resolution，与 validate_plan 无关）。计划随后 `state.context_data["executable_plan"] = executable_plan` 直接进 DAG 自动执行。
- 对照组：`backend/app/agents/standard_workflow.py:2546-2568` 与 `:2731-2753` 对同两字段 queue HITL action + 置 `validation_failed` + `__end__`——同接口 enforcing 语义在侧链存在，engine 路径为漏接。
- 纯 log 分支：`grounding_validator.py:412-419`「# 4. PONR 操作需要额外确认」下只有 `logger.warning` + `return {"is_valid": True}`。
- DoD 原文在案：`v3/V3_DEFINITION_OF_DONE.md` Gate V3-3「高风险不可逆行为 autonomous execution = 0」。
- 测试面：`grep -rn requires_hitl backend/tests` 仅 version_conflict 侧，无 engine-side enforcing 断言。

**可证伪复现（2 实验全绿）**
1. **真实** `GroundingValidator.validate_plan`（38 工具 allowlist）对含 `batch_create_tasks` 的计划返回 `is_valid=True, requires_hitl=True`、risk_flags 含 `confirm:batch_create_tasks`——确定性闸门确实在亮。
2. 同一计划、同一真实闸门走主链 `_plan_and_validate`（LLM 审查 mock 为 APPROVED）：计划**原样放行**（tool_calls 完整），全程无 HITL 流帧——闸门输出被丢弃。

**对 wt587 的关键精化（影响派发判断）**
- `PONR_TOOLS` 五件套（delete_task/delete_plan/remove_user/clear_all_tasks/reset_progress）**当前均不在动态工具注册表**（实测注册 33-38 工具、PONR 交集为空）——PONR 半边的直达风险是**潜伏**的。
- 但 `requires_confirmation` 级工具 **`batch_create_tasks` 与 `generate_tasks_for_plan` 在册且在 allowlist**——闸门丢弃路径**今天即可达**（实验即用 batch_create_tasks 证实）。
- 与 302 的叠加确认：降级链跳过 LLM 审查后，主链只剩概率闸门也没了；若先修 302（确定性闸门接线），叠加风险即被结构性封住。

**修法一句话**：`_plan_and_validate` 在 validate_plan 后消费 `requires_hitl/requires_confirmation`——任一为真即 queue HITL action（复用 standard_workflow 的 `_queue_hitl_action` 模式）并 return，不进自动执行。

---

## 304｜恒真断言 + JSON 形态密码漏检｜存活 P3（范围扩大）

**核实路径**
- `backend/tests/security/test_security.py:529-536`：`test_password_in_response_detected` 把 `security_validator.contains_sensitive_data(response)` 返回值丢弃、以 `assert True` 收尾（:536）——结构上不可能失败。
- 注意：该 fixture（:207）实例化的是**测试文件内自定义** `SecurityValidator`（:24，模式 `password\s*[:=]`），非生产检测器——原报告未区分，不影响结论。
- 生产面：`backend/app/core/llm_safety.py:114` `password\s*[:：]\s*\S{8,}`。

**可证伪复现（正则/真函数实验）**
- 生产 `llm_safety.SENSITIVE_PATTERNS`：`'{"username": "user", "password": "secret123"}'` → **零命中**；`password: secret123` → 命中 `password\s*[:：]\s*\S{8,}`。
- 测试内自定义 validator 对同一 JSON 形态 → False（若把恒真断言改成真断言，测试当场红——证实其一直在掩盖漏检）。
- **范围扩大**：生产输出消毒器 `backend/app/core/llm_secure_io.py:25` `_ASSIGNMENT_SECRET_RE`（`sanitize_llm_output`，主聊天出口在用）同样漏检 JSON 形态——实测 JSON 形态 False、plain 形态 True。即 LLM 输出以 `"password": "..."` 形态泄露时，主出口消毒器静默放行。

**修法一句话**：三处模式（llm_safety:114、llm_secure_io:25、测试内副本）统一加引号容忍（如 `["']?password["']?\s*[:：]\s*["']?\S{8,}`），测试改真断言。

---

## 305｜gRPC invalid-user 测试永真｜存活 P3

**核实路径**
- `backend/tests/integration/test_grpc_streaming_integration.py:436-470`：`except Exception: assert True`（:465-467）；唯一收尾断言被注释（:469-470，wt587 标 :466-467 系微小漂移）。函数任何路径（异常/正常流/错误 metadata/空流）都通过——对被测命题零约束力。
- 补充事实：模块级 `pytestmark = skipif(FULL_STACK_TESTS != 1)`——默认 CI 直接 skip；永真危害在全栈模式计入通过数时显形。

**可证伪复现**
用桩 grpc_stub 直接驱动**真实测试函数体**：服务端抛 gRPC 异常 → 通过；服务端把 invalid user 当正常请求服务（无错误 metadata、正常 done）→ 也通过。两种相反行为下同绿，永真属性坐实。

**修法一句话**：恢复收尾断言 `assert error_received or len(responses) == 0`，except 分支改 `pytest.fail(f"unexpected exception: {e}")`。

---

## 306｜execution_trust 空契约/未知 criteria 双缺省通过｜存活 P3

**核实路径**
- `backend/app/core/execution_trust.py`：`_validate_schema` :155-158（无 `required_fields` → (0,0) 零校验）；`_check_success_criteria` :168-169（type 缺失 → True）与 :184（**未知 type → True**，含拼写错误，零告警）；`evaluate` :86-97 空跑时 `validation_total>0` 分支跳过、criteria 缺省 True、richness 5 键拿满 0.3 + criteria 0.3 ≥ 0.3 门槛 → `VALIDATED` 且 reasons 自称 `"schema_and_criteria_passed"`。
- 下游通道：`backend/app/services/execution_service.py` :3041（record.trust_level 落库）、:3073（intent.trust_level）、:2493-2506（trust_bucket success_rate/current_trust 决定 approval_policy 放宽到 `deny` 或收紧 `require_for_side_effects`）——空契约执行器的「已验证」标签可进信任通道影响审批策略。

**可证伪复现（2 实验全绿）**
1. `evaluate(raw_result={"output":{5键}}, success_criteria={}, result_contract={})` → `VALIDATED` + reasons 含 `"schema_and_criteria_passed"`、`validation_total==0`。
2. `success_criteria={"type":"structured_ouput", "required_fields":["missing_field"]}`（拼错 type）→ 同样 `VALIDATED`，零告警，required_fields 根本没被检查。

**修法一句话**：至少其一如实入 reasons（`schema_not_evaluated` / `criteria_unknown_type`），未知 criteria_type 返回 False 并告警。

---

## 存活项建议派发顺序

1. **303**（P2，安全闸门）：confirm 级工具今天即可达 + DoD Gate V3-3 直接线；修好它同时封掉与 301 的叠加风险（降级链 PONR 全无门）。
2. **301（伪造审查）**（P2，用户可见失真）：依赖与 303 相同的诚实元数据契约（degraded 标记），宜同一或相邻卡片交付。
3. **302（记账口径）**（P2，成本/健康度报表失真）：改动面收敛在 fallback 返回契约 + 三处记账点。
4. **304**（P3 但含生产出口检测缺口）：三处正则一起修，工时极小。
5. **306**（P3）：reasons 如实标注，工时极小。
6. **305**（P3，纯测试债，trivial）：可随手捎带。

## 复核过程备注

- 本工位实验代码存放 `backend/tests/scratch_wt591/`（F-301×3、F-302×2、F-303×2、F-305×1、F-306×2 共 10 断言组），全部在当前代码下绿（即证实各条现状属实），复核完成后已删除，不入库。
- 台账（`v3/06_agent_fleet/DYNAMIC_ISSUES.md`）查重：六条主题均无既有条目；编号 302-306 空闲、301 已被 wt585 项占用，集成侧重排。
- 本 worktree 在复核期间出现第三方未提交改动（community/inventory/routes 等 10 文件，疑似并行会话）；本提交仅含本文件，未触碰这些改动。
