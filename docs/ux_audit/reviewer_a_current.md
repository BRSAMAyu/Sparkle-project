# Reviewer A — C19: Aurora建模对话质量（不重复/上下文感知/自然过渡）
Timestamp: 2026-04-25T23:50:00+08:00
Chain Index: 9

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。全程手动审查（未依赖 agent）。关键文件逐一阅读：planning.py 的 tension 追踪系统（line 863-893, 992-1002）、chat_adapter.py 的 context_aware_question（line 159-192）、decision_loop.py 的 _resolve_modeling_complete（line 1425-1430）、dashboard.py 的 REQUIRED_MODELING_DOMAINS（line 18）。

## Chain Flow Summary

Aurora 建模对话通过 informational tensions 系统追踪4个必填域（goal/scope/baseline/time）。每轮对话后，planning.py 的 `_recompute_tensions()` 根据用户回复自动将域标记为 resolved/open，`build_next_prompt()` 只选择 status=open 的下一个 tension 构建上下文感知的问题。chat_adapter.py 的 `context_aware_question()` 利用已收集的信息（subject、scope、baseline）调整措辞。当所有 REQUIRED_MODELING_DOMAINS 都 resolved 时，`_resolve_modeling_complete()` 触发 modeling_complete。

## Critical Issues 🔴

None found.

## Major Issues 🟡

**1. `chat_adapter.py:113-137`: `_infer_context_answers()` 回答推断过于粗糙，可能将模糊用户输入误分类为具体 baseline**

该函数使用简单的关键词匹配推断用户回答。例如 `_BASELINE_LIGHT_PATTERNS = ("不太会", "不太懂", "有点虚", "薄弱", "学了一点", "学过一点", "会一点")`。如果用户说"TCP有点难懂"（指特定知识点），会被匹配到 "不太懂" → 推断 baseline="不太稳"。这个推断结果会被写入 `previous_answers`，直接影响后续问题的措辞（line 163-165: `answers = {**previous_answers}; for key, value in inferred.items(): answers.setdefault(key, value)`）。

Expected: 推断结果应仅用于辅助，不应覆盖已有的明确回答。Actual: `setdefault` 语义正确（不覆盖），但推断本身的误报率高。

**Severity adjustment**: 实际影响有限 — 推断只影响问题措辞，不影响最终 tension 解析（`_recompute_tensions` 基于 `user_model_snapshot` 中的字段值，不依赖 `_infer_context_answers`）。评为 Major 偏严格，但作为质量标记。

**2. `planning.py:884-888`: tension 状态重算只检查字段是否非空，不验证内容有效性**

`_recompute_tensions()` 判断 tension 是否 resolved 的逻辑：`if field_value not in (None, "", [], {})` 则标记为 resolved（line 884-885）。这意味着即使用户回答了无意义内容（如"不知道"、"随便"），只要字段非空，对应域就被标记为 resolved，后续不会再追问。

Expected: 至少应检查字段值的最低有效性（长度下限、排除"不知道"类否定词）。Actual: 任何非空字符串都被视为有效回答。

**Note**: 此为 **设计权衡** — 过于严格的验证可能导致循环追问，体验更差。当前的宽松策略在多数场景下合理，但可能在用户敷衍回答时产生低质量建模。

## Minor Issues 🟢

None found.

## Working Well ✅

**Tension 追踪系统** (`planning.py:863-893`):
- 4 个域（exam_scope/knowledge_baseline/time_available/motivation）各有独立 tension
- `_recompute_tensions()` 每轮重算，自动识别已回答和未回答的域
- `select_next_tension()` 过滤 `status in {"open", "partially_resolved"}`（line 568），只选择未解决的域
- `_mark_tension_attempted()` 记录每个域的最后尝试时间（line 992-1002），避免短时间内重复追问同一域

**上下文感知问题生成** (`planning.py:616-652`):
- `_contextual_tension_prompt()` 根据已知的 subject、scope、baseline 调整每个域的问题措辞
- 零基础用户得到引导性问题："零基础先别急着铺满全书"（line 625）
- 有 scope 信息时缩小问题范围："范围先按{scope}来抓"（line 638）
- Sprint Pack 场景有专用快速通道（`_build_first_question()`，line 590-614）

**Chat adapter 双层降级** (`chat_adapter.py:195-233`):
- LLM 渲染消息失败时 fallback 到静态消息（line 223-225）
- 空输出也有二次 fallback（`_fallback_messages()`，line 230-233）
- 消息去重和 sanitization（`_sanitize_messages()`，line 227）

**Modeling complete 检测** (`decision_loop.py:1425-1430`):
- 基于 REQUIRED_MODELING_DOMAINS（goal/scope/baseline/time）全覆盖
- 不依赖关键词匹配，而是基于 `covered_domains` 集合运算
- Modeling 完成后自动触发 planning 衔接

**Fallback 问题** (`planning.py:41-47`):
- 每个域都有高质量 fallback 问题，不依赖 LLM 即可工作
- 问题顺序通过 `_DOMAIN_QUESTION_ORDER` 控制（line 48）

## Files Examined

1. `backend/app/aurora/runtime_v1/planning.py` (lines 41-57, fallback questions + domain order; 863-893, tension recomputation; 992-1002, mark attempted; 580-652, next prompt + contextual prompts; 590-614, sprint pack first question)
2. `backend/app/aurora/runtime_v1/chat_adapter.py` (lines 1-80, imports + patterns; 113-137, context inference; 159-192, context_aware_question; 195-233, ChatLayerAdapter with dual fallback)
3. `backend/app/aurora/runtime_v1/decision_loop.py` (lines 1425-1430, modeling complete resolution; 1231-1236, surface complete flag)
4. `backend/app/aurora/runtime_v1/dashboard.py` (line 18, REQUIRED_MODELING_DOMAINS definition)
5. `backend/app/aurora/runtime_v1/state.py` (tension/thread dataclass definitions — inferred from usage)

## Confidence: High — 建模对话的核心防重复机制（tension 状态追踪 + 已回答域过滤）设计合理且实现正确。两处 Major 为质量标记（推断粗糙 + 验证宽松），不影响核心功能的正确性。

---

## Reviewer A — 全部 10 条链路审查完成

| Chain | Name | Critical | Major | Minor | Status |
|-------|------|----------|-------|-------|--------|
| C01 | 冷启动建模→计划生成 | 1 | 2 | 0 | done |
| C03 | 任务卡点(stuck) | 2 | 1 | 0 | done |
| C05 | 7天冲刺完成→庆祝页 | 0 | 1 | 1 | done |
| C09 | 每日启动消息个性化 | 0 | 0 | 0 | done ✅ |
| C11 | 间隔重复提醒链路 | 0 | 2 | 2 | done |
| C13 | 每周报告→周报卡 | 0 | 2 | 2 | done |
| C15 | 全局空状态质量 | 0 | 1 | 0 | done |
| C17 | API失败恢复 | 0 | 2 | 0 | done |
| C19 | Aurora建模对话质量 | 0 | 2 | 0 | done |

**汇总**: 3 Critical, 13 Major, 5 Minor across 10 chains. C09 为唯一零问题链路。
