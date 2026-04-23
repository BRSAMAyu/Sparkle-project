# 深度审计 #54 — Prompt Assembly 系统提示词组装完整链路

> **日期**: 2026-04-25 05:15
> **模块**: Prompt Assembly — 用户上下文 → 提示词模板渲染 → LLM 系统提示词
> **范围**: `prompts.py` (1,876 行) + `agent_profiles.py` (828 行) + `context_pack.py` (872 行) + `context_builder.py` (954 行) + `orchestrator.py` (1,619 行) + `dual_core_router.py` (235 行)
> **总计**: 6 个文件, 6,384 行
> **审计员**: Claude Deep Auditor (Round 54)

---

## 审计范围

Prompt Assembly 是 AI 所知用户信息的**唯一瓶颈**。它从一个分层管道（context_builder → context_pack → context_focus → prompts）组装系统提示词，但存在严重的数据丢失、安全漏洞和结构问题。

**数据利用率评分: ~62%** — context_builder 产生的约 25 个上下文字段中，仅约 17 个实际渲染到提示词模板。错误数据、成就数据、日历数据和行为数据的主要子系统在提示词层面是死代码。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/app/orchestration/prompts.py` | 1,876 | 系统提示词组装核心：模板渲染 + 段拼接 + token 预算 |
| `backend/app/core/agent_profiles.py` | 828 | Agent 角色模板 + `.format(**kwargs)` |
| `backend/app/core/context_pack.py` | 872 | ContextPackBuilder：记忆层上下文 (tiktoken 预算) |
| `backend/app/orchestration/context_builder.py` | 954 | ContextBuilder：聚合 25 个字段到 user_context_payload |
| `backend/app/orchestration/orchestrator.py` | 1,619 | FSM 状态机，调用 build_system_prompt() |
| `backend/app/orchestration/dual_core_router.py` | 235 | 双核路由决策 → prompt_instruction 属性 |

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  数据源 (已收集)                                                        │
│  DB: user profile, preferences, analytics, active_plans, tasks         │
│  DB: cognitive patterns, seed library, knowledge summary, focus stats  │
│  DB: error_summary, recent_errors, recent_mastery_changes (死数据)     │
│  DB: achievements, calendar, capsules, notifications, photons (死数据) │
│  Redis: conversation history (pruned), session state                   │
│  gRPC: Go Gateway overlay context                                      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  context_builder.py (_build_user_context)                               │
│  收集 ~25 字段到 user_context_payload dict                              │
│  包括 error_summary, recent_errors (已收集但从未转发到 prompt)          │
│  returning_context → session_state_mixin (部分使用)                     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  context_pack.py (ContextPackBuilder.build)                             │
│  独立路径：preferences, goals, episodic_memories                        │
│  使用 tiktoken 做 token 预算                                            │
│  输出: ContextPack.to_prompt_context() dict                            │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  prompts.py (build_system_prompt) — 瓶颈层                             │
│                                                                         │
│  接收: user_context + conversation_history + plan_context              │
│        + intent + dual_core + context_focus 等                          │
│                                                                         │
│  规范化: _normalize_user_context()                                      │
│  渲染: ~17 个 section 通过 section_map                                  │
│  预算: _apply_prompt_budget() 按层级 token 限制                         │
│  输出: format_map() 填充模板字符串                                      │
│                                                                         │
│  ❌ P0-1: .format_map() 值内容未消毒 — prompt injection               │
│  ❌ P0-2: Graph 节点完全绕过此系统 — 零用户上下文                     │
│  ⚠️ P1-5: Token 预算用 len/4 估算 vs tiktoken 实际计数               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷（2 项）

#### P0-1: `.format_map()` 值内容未消毒 — Prompt Injection 持续存在
**文件**: `prompts.py:1039, 1060, 1090` + `agent_profiles.py:167`
**严重性**: P0 — 4/7 注入向量接收用户可控数据，无任何清洗

```python
# prompts.py:1039-1060 — _SafeFormatDict 仅防 KeyError，不清洗值内容
prompt = base_prompt.format_map(
    _SafeFormatDict(
        user_context=formatted_user_context,  # 含用户昵称、偏好
        intent_instruction=...,               # 含用户消息分类
        plan_context=...,                     # 含用户创建的计划标题/目标
        ...
    )
)
```

**具体向量**:
- `formatted_user_context` — 含用户昵称、偏好描述
- `plan_context` — 含用户创建的计划标题、目标、任务文本
- `seed_library` — 含用户订阅的问答示例
- `conversation_history` — 含用户聊天消息内容

**P0-1b**: `agent_profiles.py:167` 使用原始 `str.format(**kwargs)` 而非 `_SafeFormatDict`，甚至缺少 KeyError 保护。

**修复方向**: 添加 `_sanitize_for_prompt()` 函数，在插入前剥离 `{`、`}`、`##` 等结构化 prompt 标记。

---

#### P0-2: Graph 专家节点完全绕过 Prompt Assembly — 零用户上下文
**文件**: `backend/app/agents/graph/nodes/*.py` (5 个节点)
**严重性**: P0 — 专家模式下 AI 完全不了解用户

```python
# error_analyst.py:14-52 — 典型节点，硬编码中文提示词，零上下文
def _build_system_prompt(state: SparkleState, *, planning: bool) -> str:
    if planning:
        prompt = "你是纠错专家（规划模式）。\n..."
    else:
        prompt = "你是纠错专家，擅长定位错误根因...\n..."
    return prompt  # 从不访问 state.context_data["user_context"]
```

**受影响节点**: time_tutor.py, error_analyst.py, exam_oracle.py, deep_analyst.py, galaxy_guide.py

**对比**:

| 上下文 | 主模板 | 专家节点 |
|--------|--------|----------|
| 用户偏好 | ✅ 渲染 | ❌ 从不 |
| 计划上下文 | ✅ 渲染 | ❌ 从不 |
| 认知洞察 | ✅ 渲染 | ❌ 从不 |
| 对话历史 | ✅ 渲染 | ❌ 仅原始消息 |
| 双核路由 | ✅ 渲染 | ❌ 从不 |

**修复方向**: 重构图节点调用 `build_system_prompt()` 或至少注入 `state.context_data["user_context"]`。

---

### P1 — 重要问题（5 项）

#### P1-1: Error Book 数据已收集但从未到达 Prompt — 完全死数据
**文件**: `context_manager.py:42-43, 155-156` (已收集) vs `prompts.py` (从未访问)

`CognitiveContext` 模型包含 `error_summary` 和 `recent_errors` 字段，经查询、结构化、存储后，`_normalize_user_context()` 从未提取。用户错题模式和掌握进度对 AI 完全不可见。

---

#### P1-2: `returning_context` 已构建但从未注入 Prompt
**文件**: `context_builder.py:355-729` (已构建) vs `prompts.py` (从未渲染)

系统构建了丰富的"回归上下文"（离开时间、最后完成的任务、逾期任务、欢迎语），但如果存在 context_focus briefing，回归上下文被静默丢弃。用户不活跃后返回时丢失个性化回归体验。

---

#### P1-3: `MODE_SYSTEM_PROMPTS` 4 个模板 ~200 行重复代码
**文件**: `prompts.py:270-590`

4 个模式模板（standard/deep_analysis/study_plan/error_diagnosis）中约 200 行是逐字重复的：相同 18 个 `{placeholder}` 段 + 相同 8 点"核心原则"。更新时需在 4 处修改，任何遗漏导致行为分化。

**修复方向**: 抽取共享基础模板 + 模式特有追加段。

---

#### P1-4: Token 预算估算使用 `len/4` 启发式而非实际 tokenizer
**文件**: `prompts.py:73-74`
**严重性**: P1 — 中文文本系统性低估 token 数

```python
def _estimate_prompt_tokens(text: str) -> int:
    return max(1, len(str(text or "")) // 4)
```

假设 1 token = 4 字符。中文每个字符约 1-2 token（非 0.25），导致中文 prompt 被过度裁剪。对比 `context_pack.py` 使用 `tiktoken` 实际计数。

---

#### P1-5: `context_pack` 与 `prompts.py` Token 预算系统冲突
**文件**: `context_pack.py` (tiktoken) vs `prompts.py` (len/4)

两套独立 token 预算系统：context_pack 用 tiktoken 裁剪记忆数据 → prompts.py 用 len/4 再次裁剪整个 payload。使用不同计数方法导致双重过度修剪。

---

### P2 — 改进建议（7 项）

#### P2-1: 所有提示词模板硬编码中文 — 零 i18n 支持
**文件**: `prompts.py:177-590` 全部模板
**关联**: Round #47 i18n 盲区十连

#### P2-2: `_normalize_user_context` 30+ 手动 `get()` 调用 — 无类型化访问
**文件**: `prompts.py:1639-1716`
**关联**: Round #52 P1-5 getattr 模式

#### P2-3: `_format_conversation_history` 非锚定消息截断 100 字符
**文件**: `prompts.py:1269-1272`
中文 100 字符约 50 token，丢失用户详细问题内容。

#### P2-4: `_is_query_plan_related` 仅匹配中文关键词
**文件**: `prompts.py:1770-1786`
英文查询 "what's my task progress?" 返回 False，计划上下文段被抑制。

#### P2-5: `_TIER_PROMPT_BUDGET` 仅覆盖 6 个 tier — 高端模型获得最紧凑 prompt
**文件**: `prompts.py` tier 映射
`plus`/`pro`/`max`/`specialist` 无预算条目，回退到默认 2800。最强模型获得最紧凑 prompt，适得其反。

#### P2-6: `context_pack` evidence_summary 仅在"无目标且无记忆"时渲染
**文件**: `prompts.py:1602-1634`
有目标或有记忆的用户永远看不到证据摘要，逻辑反直觉。

#### P2-7: Prompt 快照采样使用 `random.random()` 不可种子化
**文件**: `prompts.py:1852`
不可复现，同一会话两次调用可能不同采样，调试困难。

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 用户输入 prompt injection 清洗 | ❌ | P0-1: 值内容未消毒 |
| 收集数据全部渲染到 prompt | ❌ | P1-1/P1-2: error/returning 数据死代码 |
| Token 预算存在 | ⚠️ | 存在但估算器错误 (P1-4) |
| 预算与模型上下文窗口匹配 | ❌ | 高 tier 模型无预算条目 (P2-5) |
| 模板 DRY（无重复） | ❌ | 200 行重复 4 次 (P1-3) |
| i18n 支持 | ❌ | 全部硬编码中文 (P2-1) |
| 类型化数据访问 | ❌ | 30+ 手动 get() (P2-2) |
| 专门 prompt 路径共享上下文 | ❌ | Graph 节点零上下文 (P0-2) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 2 |
| P1 | 5 |
| P2 | 7 |
| **总计** | **14** |

---

## 修复优先级建议

1. **P0-1** (值内容未消毒) — 添加 `_sanitize_for_prompt()` — ~15 行
2. **P0-2** (Graph 节点零上下文) — 重构节点注入 user_context — ~50 行
3. **P1-4** (Token 估算) — 导入 tiktoken 替换 len/4 — ~10 行
4. **P1-1** (Error data 死代码) — 连接 error_summary 到 normalize + 段渲染 — ~30 行
5. **P1-3** (模板重复) — 抽取共享基础模板 — ~200 行重构
6. P1-2/P1-5/P2 项 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (format_map 值未消毒) | Round #14 P0-2 (f-string injection) | `_SafeFormatDict` 仅修复 KeyError，值内容仍不安全 |
| P0-2 (Graph 节点零上下文) | Data Utilization Analysis (5.0/10) | 数据利用率 62%，专家模式更差(0%) |
| P1-1 (Error data 死代码) | Round #18 Error Book + Data Analysis | 错题本数据收集完整但 prompt 层断裂 |
| P1-4 (len/4 估算) | Round #53 P1-7 (CJK token 估算) | 同一问题在 Go Gateway 和 Python 两层都存在 |
| P2-1 (硬编码中文) | Round #47 i18n 盲区 + Round #52 P1-1 (50+ 中文字符串) | 系统性 i18n 缺失 |
| P2-2 (手动 get()) | Round #52 P1-5 (getattr 20+ 次) | 整个编排层缺乏类型化 schema |
| P2-4 (仅中文关键词) | Round #52 P2-2 (full_response 中文检测) | LLM 输出语言检测依赖中文字符串 |
