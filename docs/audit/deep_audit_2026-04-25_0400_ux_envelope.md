# 深度审计 #52 — UX Envelope 展示适配层完整链路

> **日期**: 2026-04-25 04:00
> **模块**: UX Envelope — AI 回复展示风格适配 + 阻塞温度调节 + Next Actions 生成 + 记忆更新信号
> **范围**: `ux_envelope.py`（1,682 行）+ `execution_engine.py` 调用点 + Flutter 消费端
> **审计员**: Claude Deep Auditor (Round 52)

---

## 审计范围

`UXEnvelopeBuilder` 是 Sparkle AI 回复的"最后一英里"——在 LLM 生成回复后、发送给 Flutter 客户端之前, 决定回复的展示方式: 标题、语气、下一步行动建议、阻塞恢复策略、信心等级。它将 AI 回复从"原始文本"转化为"结构化展示包"。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/app/orchestration/ux_envelope.py` | 1,682 | UX 展示适配核心 |
| `backend/app/orchestration/execution_engine.py:786,808` | ~5 | 调用入口 |
| `backend/app/orchestration/orchestrator.py:135` | 1 | stale import (`# noqa: F401`) |

**总计**: 1 核心文件 (1,682 行) + 2 个调用点

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LLM Response → UXEnvelopeBuilder.build() → Flutter Metadata          │
│                                                                         │
│  输入 (12 个参数):                                                      │
│    user_message, full_response, final_state, executable_plan,           │
│    route_decision, include_references, file_ids,                        │
│    execution_validation, conversation_context, plan_context,            │
│    user_context_payload                                                 │
│                                                                         │
│  处理流程:                                                              │
│    1. chat_mode 提取 (:231) → _get_profile (:234)                       │
│       ❌ P1-1: 7 种模式 profile 硬编码中文, 无 i18n                    │
│                                                                         │
│    2. presentation_style_decision (:236-242)                            │
│       ✅ 基于 verbosity/tone/exploration 信号决策                       │
│       ⚠️ P2-1: 关键词匹配依赖小写中文字符串精确匹配                    │
│                                                                         │
│    3. completion_state (:250) → _completion_state                       │
│       ✅ 基于 execution_validation 判断完成状态                         │
│                                                                         │
│    4. recovery_state (:251-260)                                         │
│       ✅ 9 种 failure_kind 分类                                          │
│                                                                         │
│    5. blocked_state (:261-276)                                          │
│       ❌ P0-1: _local_state 无界增长 → 内存泄漏                       │
│       ✅ Redis 有 TTL (30天)                                            │
│                                                                         │
│    6. confidence_band (:278)                                            │
│       ✅ 多源置信度聚合                                                 │
│                                                                         │
│    7. conversation_stage (:279-288)                                     │
│       ⚠️ P2-2: full_response 内容匹配硬编码中文关键词                   │
│                                                                         │
│    8. 输出组装 (:300-418)                                               │
│       → ux_turn + ux_result + ux_followthrough + ux_sources             │
│       + 5 个可选段                                                      │
│       ❌ P1-2: 输出为 dict[str, dict], 无 schema/类型契约              │
│       ❌ P1-3: 3 个 feature flag 控制不同输出段                        │
│                                                                         │
│    9. to_metadata_map (:420-425)                                        │
│       → JSON 序列化 → gRPC metadata → Flutter                          │
│       ❌ P1-4: envelope 可达 ~5KB JSON → metadata 膨胀                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: `BlockedPresentationHistoryStore._local_state` 无界增长 — Redis 不可用时内存泄漏
**文件**: `ux_envelope.py:108, 134-137`
**严重性**: P0 — 长时间运行的服务进程 OOM 风险

```python
# :108 — 本地回退存储
class BlockedPresentationHistoryStore:
    def __init__(self) -> None:
        self._local_state: dict[str, dict[str, Any]] = {}  # ← 无大小限制

# :134-137 — Redis 不可用时的 fallback
    except Exception:
        pass  # ← Redis 失败静默, 进入本地存储

    payload = self._local_state.get(key) or {"count": 0}
    count = int(payload.get("count") or 0) + 1
    self._local_state[key] = {"count": count, "last_seen_at": now}  # ← 永不清理
```

**问题**: 当 Redis 不可用时, 每次 `record()` 调用都向 `_local_state` 添加/更新条目. Key 格式为 `ux:blocking:{user_id}:{failure_kind}`, 即每个用户 × 每种 failure_kind 产生一个条目.

**增长估算**:
```
假设 10K 活跃用户, 每人平均 2 种 failure_kind:
  10,000 × 2 = 20,000 条目
  每条目 ~100 bytes (key + JSON payload)
  ≈ 2MB (可控)

但 _local_state 永不清理:
  - 用户永远不删除 (无 LRU/LFU/TTL)
  - 30 天后仍有用户首次 blocked → 持续增长
  - Redis 恢复后本地数据不回写也不清除 → 双重存储
```

**加剧因素**: `UXEnvelopeBuilder` 是模块级单例 (`ux_envelope_builder`), 其 `_blocked_history_store` 在整个进程生命周期内存在.

**修复方向**: (1) `_local_state` 添加 `maxsize` 限制 (如 LRU cache 10000 条目); (2) Redis 恢复后清除本地数据; (3) 添加 TTL 到本地条目 (如 1 小时过期清理).

---

### P1 — 重要问题

#### P1-1: 50+ 个硬编码中文字符串 — 零 i18n 支持
**文件**: `ux_envelope.py` 全文 (140-806 行密集区域)
**严重性**: P1 — 国际化完全阻断

```python
# :141-151 — 标准 profile (中文硬编码)
"standard": PresentationProfile(
    mode_label="标准对话",                                          # 中文
    companion_frame="我先给你一个直接可用的回答，再补充依据和下一步。", # 中文
    blocked_title="继续前我还需要一点补充",                          # 中文
    blocked_message="我已经抓到问题主轴，但还缺一个关键上下文...",    # 中文
)

# :569-574 — 阻塞标题 (中文硬编码)
if blocked_temperature == "gentle":
    return "别急，我还差一点点信息，就能继续帮你收敛。"

# :589-606 — 温度消息 (8 种 × 3 种温度 = 24 个硬编码中文字符串)
direct_messages = {
    "missing_input": "还缺一个关键信息。补上后我就直接继续。",
    "tool_failure": "有步骤执行失败了。先补条件，或让我换一种做法。",
    ...
}
```

**量化**: 搜索 `"引导` + `"别急` + `"我先用` + `"先把` + `"下一步` 等模式, 估计 **50-60 个硬编码中文字符串**. 如果需要支持英文或其他语言, 需要重构所有这些字符串.

**修复方向**: 提取为 i18n 资源文件 (`locales/zh-CN/ux_messages.yaml` + `locales/en/ux_messages.yaml`), 运行时根据用户语言偏好加载.

---

#### P1-2: 输出结构为无类型 `dict[str, dict]` — Python-Flutter 契约无保障
**文件**: `ux_envelope.py:379-418`
**严重性**: P1 — 接口稳定性风险

```python
# :379-384 — 返回值是裸 dict
envelope: dict[str, dict[str, Any]] = {
    "ux_turn": ux_turn,
    "ux_result": ux_result,
    "ux_followthrough": ux_followthrough,
    "ux_sources": ux_sources,
}

# :386-416 — 5 个可选段 (条件性添加)
if orchestration_summary: envelope["orchestration_summary"] = ...
if ux_evolution: envelope["ux_evolution"] = ...
if continuity_banner: envelope["continuity_banner"] = ...
if mode_explanation: envelope["mode_explanation"] = ...
if collaboration_summary: envelope["collaboration_summary"] = ...
```

**问题**:
1. 返回值为 `dict[str, dict[str, Any]]`, 无 dataclass/Pydantic schema 验证
2. 可选段的存在取决于运行时条件, Flutter 端无法静态知道哪些 key 可能存在
3. 内部值类型混合: `str`, `int`, `list[dict]`, `dict` — 无文档化的类型契约
4. Flutter 端通过 `metadata['ux_turn']` 解析 JSON, 任何 key 重命名都是静默断裂

**修复方向**: 定义 `UXEnvelope` dataclass + `to_dict()` 方法, 同时生成 Dart 模型类.

---

#### P1-3: 3 个 Feature Flag 碎片化控制输出 — 客户端行为不可预测
**文件**: `ux_envelope.py:243, 289, 311, 330, 366, 707`
**严重性**: P1 — 运维复杂度

```python
# 3 个独立 feature flag 控制不同输出段:
if settings.ENABLE_ADAPTIVE_PRESENTATION:           # Flag 1
    UX_PRESENTATION_STYLE_TOTAL.labels(...).inc()

if settings.ENABLE_ADAPTIVE_PRESENTATION or settings.ENABLE_UX_PRESENTATION_METADATA:  # Flag 1 || Flag 2
    ux_turn["presentation_style"] = style_decision.style_variant

if settings.ENABLE_BLOCKED_TEMPERATURE or settings.ENABLE_UX_PRESENTATION_METADATA:    # Flag 3 || Flag 2
    ux_result["blocked_reason"] = recovery_state["failure_kind"]

if not settings.ENABLE_ADAPTIVE_PRESENTATION:       # Flag 1 否定
    return profile.next_actions_title                # 跳过自适应标题
```

**问题**: 3 个 flag 的组合产生 2³ = 8 种可能的输出形态. Flutter 客户端需要处理所有 8 种组合, 但无法从服务端获知当前启用了哪些 flag.

**修复方向**: 在 envelope 中添加 `"capabilities": {"adaptive_presentation": true, ...}` 字段, 让 Flutter 知道哪些特性可用.

---

#### P1-4: `to_metadata_map` 将整个 envelope JSON 序列化到 gRPC metadata — 体积膨胀
**文件**: `ux_envelope.py:420-425`, `execution_engine.py:808`
**严重性**: P1 — gRPC header 大小限制风险

```python
# :420-425 — 每个顶层 key 独立 JSON 序列化
def to_metadata_map(self, envelope: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        key: json.dumps(value, ensure_ascii=False)
        for key, value in envelope.items()
        if value
    }

# execution_engine.py:808 — 写入 gRPC response metadata
response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))
```

**问题**: envelope 包含 4-9 个顶层段, 每段独立 JSON 序列化后作为 gRPC metadata value. 估算:
- `ux_followthrough` 含 `next_actions` (最多 4 个 StructuredAction) ≈ 1-2KB
- `ux_result` 含多个字符串 ≈ 0.5KB
- 全部段合计 ≈ 3-5KB JSON

gRPC 默认 metadata header 大小限制为 8KB (某些实现 16KB). 如果 envelope 超过限制, 整个 gRPC 响应会被截断或拒绝.

**修复方向**: (1) 将 envelope 放入 response body 而非 metadata; (2) 或添加 envelope 体积限制和裁剪逻辑.

---

#### P1-5: `getattr(final_state, "context_data", {})` 模式 20+ 次无类型安全 — 脆弱耦合
**文件**: `ux_envelope.py` 多处 (:230, :453, :551, :620, :807 等)
**严重性**: P1 — 维护风险

```python
# 20+ 处使用此模式
context_data = getattr(final_state, "context_data", {}) or {}
chat_mode = str(context_data.get("chat_mode") or CHAT_MODE_STANDARD)
```

`final_state` 参数类型为 `Any`, 实际是 LangGraph FSM 的 state dict. 任何对 FSM state 结构的重构都会静默破坏 UX envelope 的行为 (返回空默认值而非报错).

**修复方向**: 定义 `FinalState` Protocol/TypedDict 声明所需字段.

---

### P2 — 改进建议

#### P2-1: 关键词匹配依赖精确中文字符串 — 脆弱的信号检测

```python
# :31-44 — 硬编码中文关键词集合
NEGATIVE_USER_SIGNAL_KEYWORDS = {
    "崩溃", "焦虑", "压力", "学不进去", "撑不住", "烦", ...
}
```

用户使用近义词 (如"很紧张"替代"焦虑")、英文、或口语表达 (如"头大") 时, 信号检测完全失效.

---

#### P2-2: `_conversation_stage` 用 `full_response` 内容检测阶段 — 耦合 LLM 输出语言

```python
# :649 — 检测 full_response 中的中文字符串
any(token in full_response for token in ("第一步", "开始", "执行", "今天先"))
```

如果 LLM 用英文回复 ("Let's start with the first step"), 阶段检测失效.

---

#### P2-3: `_intent_summary` 截断到 80 字符 — 中文字符截断可能在 UTF-8 边界断裂

```python
# :755 — 简单字符截断
compact = compact[:80] + ("..." if len(compact) > 80 else "")
```

Python 的 `str[:80]` 按 Unicode 码点截断, 不会破坏 UTF-8, 但可能在 emoji 或组合字符中间截断.

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| Prometheus 指标 | ✅ 6 个 Counter (PRESENTATION_STYLE/STAGE_DETECTED/BLOCKED_TEMPERATURE/BLOCKED_HISTORY_HIT/NEXT_ACTION_GENERATED/NEXT_ACTION_FALLBACK) |
| Redis 阻塞历史持久化 | ✅ 30 天 TTL, count + last_seen_at |
| Feature Flag 控制 | ✅ 3 个独立 flag 渐进式启用 |
| 展示模式覆盖 | ✅ 7 种 chat_mode + expert:: 动态生成 |
| 置信度多源聚合 | ✅ validation_score → plan_confidence → route_confidence 三级回退 |
| 温度分级 | ✅ guided/direct/gentle 三级阻塞温度 |
| 恢复消息 9 种分类 | ✅ missing_input/tool_failure/timeout/blocked/partial_tool_failure/expert_degraded/limited_evidence/provider_unavailable/none |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 1 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **9** |

---

## 修复优先级建议

1. **P0-1** (_local_state 无界增长) — 添加 maxsize 限制 + 过期清理 — ~15 行
2. **P1-5** (getattr 无类型安全) — 定义 FinalState TypedDict — ~30 行
3. **P1-4** (metadata 体积膨胀) — 添加体积限制或移入 response body — ~20 行
4. **P1-1** (50+ 硬编码中文) — i18n 资源提取 — ~100 行重构 (低优先级)
5. **P1-2** (输出无 schema) — UXEnvelope dataclass — ~50 行
6. P1-3/P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P1-1 (50+ 硬编码中文) | Round #47 i18n 盲区十连 | UX Envelope 是 i18n 盲区的重灾区 — 每个 PresentationProfile 含 8 个中文字符串 × 7 种模式 = 56 个待国际化字符串 |
| P1-2 (输出无 schema) | Round #5 P1-5 (chat_mode 魔术字符串) | 同一模式: Python-Flutter 接口用字符串约定而非类型化契约 |
| P1-5 (getattr Any) | Round #9 Dual-Core Router (22→10 字段重构) | FSM state 结构重构时 UX Envelope 的 getattr 链静默降级而非报错 |
| P0-1 (_local_state 无界) | Round #33 Celery Task Queue | 同一模式: 本地内存 fallback 不设限 → 进程级内存泄漏 |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十四次唤醒 (Round #60 并行复核)
> **复核方式**: 代码验证
> **复核员**: Claude Deep Auditor (Re-Review)

### 文件状态确认

| 文件 | 审计时行数 | 当前行数 | 行号偏移 | 状态 |
|------|-----------|---------|---------|------|
| `backend/app/orchestration/ux_envelope.py` | 1,682 | 1,682 | 0 | 无变化 |
| `backend/app/orchestration/execution_engine.py` (调用点) | :786, :808 | :786, :808 | 0 | 无变化 |
| `backend/app/orchestration/orchestrator.py` (stale import) | :135 | :135 | 0 | 无变化 |
| `backend/app/config/settings.py` (feature flags) | 未引用 | :528-531 | — | 新增确认 |
| `backend/tests/unit/test_ux_envelope.py` | 未引用 | 365 行 | — | 已有完整测试覆盖 |

### 逐项复核

#### P0-1: `_local_state` 无界增长 — 确认 STILL OPEN

**行号**: :108 (`_local_state` 声明), :134-137 (Redis fallback 写入)
**当前代码状态**: 与审计报告完全一致,无任何修复。

- :108 `self._local_state: dict[str, dict[str, Any]] = {}` — 无 maxsize、无 LRU、无 TTL
- :131 `except Exception: pass` — Redis 失败静默,直接走本地存储
- :136 `self._local_state[key] = {...}` — 永不清理
- 模块级单例 `ux_envelope_builder` (:1682) 意味着进程生命周期内持续积累
- 无过期清理机制,无 Redis 恢复后回写/清除逻辑

**复核结论**: P0 仍然成立。修复建议 (maxsize + TTL + Redis 恢复清除) 未实施。

---

#### P1-1: 50+ 硬编码中文字符串 — 确认 STILL OPEN

**行号**: :140-208 (7 种 PresentationProfile), :431-442 (expert:: 动态 profile), :569-574 (blocked headline), :589-606 (temperature messages), :668-683 (companion frame variants), :693-698 (next actions titles), :709-744 (stage titles), :753-766 (intent summaries), :777-795 (result headlines), :1011-1048 (plan_ready actions), :1080-1116 (blocked actions), :1118-1150 (completed actions), :1152-1183 (reflect actions), :1185-1238 (explore actions), :1248-1276 (default labels), :1485-1510 (ux evolution), :1585-1590 (evidence summary), :1598-1620 (continuity banner)

**量化更新**: 逐段重新计数,硬编码中文字符串实际数量约 **70-80 个** (原报告估计 50-60 个偏低), 包括:
- 7 种 `_MODE_PROFILES` × ~8 个字段 = ~56 个
- `expert::` 动态 profile = ~8 个
- `_blocked_headline` = 3 个
- `_temperature_adjusted_failure_message` (direct + gentle 各 ~8) = ~16 个
- `_companion_frame_variant` = ~6 个
- `_base_next_actions_title` = 3 个
- `_next_actions_title` stage_titles = ~18 个
- `_result_headline` = ~8 个
- `_intent_summary` = ~6 个
- `_build_stage_actions` 各阶段 label = ~20 个
- `_default_next_action_labels` = ~18 个
- `_ux_evolution` headline/summary = ~4 个
- `_evidence_summary` = 3 个
- `_continuity_banner` = ~3 个
- `_retry_options` 动态补充 = ~4 个

**复核结论**: P1-1 仍然成立且比原估计更严重 (70-80 > 50-60)。零 i18n 支持。

---

#### P1-2: 输出结构为无类型 dict — 确认 STILL OPEN

**行号**: :379-418 (envelope 组装), :420-425 (to_metadata_map)
**当前代码状态**: 与审计报告完全一致。

- :379 `envelope: dict[str, dict[str, Any]]` — 仍为裸 dict,无 dataclass/Pydantic schema
- 4 个固定段 (ux_turn, ux_result, ux_followthrough, ux_sources) + 5 个可选段 (orchestration_summary, ux_evolution, continuity_banner, mode_explanation, collaboration_summary) + 1 个新增可选段 (`session_adaptation`, :414-416)
- `to_metadata_map` (:420-425) 仍逐段 JSON 序列化到 gRPC metadata

**新增发现**: 审计报告提到 5 个可选段,当前代码实际有 **6 个可选段** — `session_adaptation` (:414-416) 未在原报告中提及。这使得 envelope 的体积风险进一步增大。

**复核结论**: P1-2 仍然成立。可选段从 5 个增加到 6 个。

---

#### P1-3: 3 个 Feature Flag 碎片化 — 确认 STILL OPEN

**行号**: :243, :289, :311, :330, :366, :707 (代码); :528-531 (settings.py)
**当前代码状态**: 3 个 flag 全部存在且均为 `False` (默认关闭)。

```python
# settings.py:528-531
ENABLE_ADAPTIVE_PRESENTATION: bool = False
ENABLE_STRUCTURED_NEXT_ACTIONS: bool = False
ENABLE_BLOCKED_TEMPERATURE: bool = False
ENABLE_UX_PRESENTATION_METADATA: bool = False
```

**补充发现**: 实际有 **4 个** flag 影响输出 (原报告说 3 个), `ENABLE_STRUCTURED_NEXT_ACTIONS` 也控制 `_next_actions` 和 `_retry_options` 的输出格式 (:940-990, :1392-1403)。这使得组合从 2^3=8 增加到 2^4=16 种可能的输出形态。

**复核结论**: P1-3 仍然成立且更严重 (4 个 flag, 16 种组合, 非原报告的 3 个 flag 8 种)。

---

#### P1-4: `to_metadata_map` 体积膨胀 — 确认 STILL OPEN

**行号**: :420-425, execution_engine.py:808
**当前代码状态**: 与审计报告一致。

- `to_metadata_map` 仍然逐段 JSON 序列化,无体积限制或裁剪
- envelope 现有 4+6=10 个可能的段 (因 session_adaptation 新增),体积上限比原估计更高
- execution_engine.py:808 `response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))` 未变

**复核结论**: P1-4 仍然成立。风险随新增可选段 (session_adaptation) 略有增加。

---

#### P1-5: `getattr(final_state, "context_data", {})` 脆弱耦合 — 确认 STILL OPEN

**行号**: :230, :453, :551, :620, :807, :1410, :1455, :1466, :1513, :1523, :1534, :1613, :1623, :1655, :1673
**当前代码状态**: 模式完全未变。

重新统计 `getattr(final_state, "context_data", {})` 出现次数: **15 处** (原报告估计 "20+")。
另外 `getattr` 对其他对象的使用: `getattr(executable_plan, "tool_calls", None)` (:769, :810, :1261), `getattr(route_decision, "reason", "")` (:874, :857), `getattr(executable_plan, "agents_involved", [])` (:1547)。

**复核结论**: P1-5 仍然成立。`final_state` 参数类型为 `Any`,所有 context_data 访问通过 `getattr` + 空默认值,静默降级而非报错。

---

#### P2-1: 关键词匹配依赖精确中文字符串 — 确认 STILL OPEN

**行号**: :31-44 (NEGATIVE_USER_SIGNAL_KEYWORDS)
**当前代码状态**: 12 个关键词集合,与审计报告一致。

```python
NEGATIVE_USER_SIGNAL_KEYWORDS = {
    "崩溃", "焦虑", "压力", "学不进去", "撑不住", "烦",
    "累", "难受", "痛苦", "沮丧", "低落", "不想",
}
```

**复核结论**: P2-1 仍然成立。无近义词扩展、无语义匹配。

---

#### P2-2: `_conversation_stage` 用 full_response 内容匹配 — 确认 STILL OPEN

**行号**: :649
**当前代码状态**: 与审计报告一致。

```python
any(token in full_response for token in ("第一步", "开始", "执行", "今天先"))
```

**复核结论**: P2-2 仍然成立。LLM 英文回复将导致阶段检测失效。

---

#### P2-3: `_intent_summary` 截断 — 确认 STILL OPEN

**行号**: :755
**当前代码状态**: 与审计报告一致。

```python
compact = compact[:80] + ("..." if len(compact) > 80 else "")
```

**复核结论**: P2-3 仍然成立。Python `str[:80]` 按 Unicode 码点截断不破坏 UTF-8, 但可能在 emoji/组合字符中间截断。

---

### 合规项复核

| 检查项 | 审计状态 | 复核状态 |
|--------|---------|---------|
| Prometheus 指标 | 6 个 Counter | 确认 6 个 Counter, 无变化 |
| Redis 阻塞历史持久化 | 30 天 TTL | 确认 `TTL_SECONDS = 60 * 60 * 24 * 30` (:105) |
| Feature Flag 控制 | 3 个独立 flag | 修正: 实际 4 个 flag (增加 `ENABLE_STRUCTURED_NEXT_ACTIONS`), 全部默认 False |
| 展示模式覆盖 | 7 种 + expert:: | 确认 7 种静态 + expert:: 动态 + execution_delegate (共 8 种基础模式) |
| 置信度多源聚合 | 三级回退 | 确认 validation_score -> plan_confidence -> route_confidence (:814-828) |
| 温度分级 | guided/direct/gentle | 确认 (:559) |
| 恢复消息分类 | 9 种 | 确认 missing_input/tool_failure/timeout/blocked/partial_tool_failure/expert_degraded/limited_evidence/provider_unavailable/none |

### 新增发现 (本次复核)

#### NF-1: `session_adaptation` 可选段未在原报告中
**行号**: :414-416, :1622-1639
原报告列出 5 个可选段,实际代码有 6 个。`_session_adaptation` 方法 (:1622-1639) 从 `context_data.session_feedback_signal` 提取信号并返回一个 dict。这增加了 P1-4 (metadata 体积) 的风险。

#### NF-2: `execution_delegate` 模式 profile 未在原报告的 7 种模式列表中
**行号**: :196-208, :428-429
`_MODE_PROFILES` 包含 `execution_delegate` 作为第 8 种模式,当 `execution_validation.execution_suggestion` 存在时自动切换 (:232-233)。原报告数据流图提到 "7 种 chat_mode + expert:: 动态生成",实际应为 8 种 + expert::。

#### NF-3: 测试文件覆盖良好
`backend/tests/unit/test_ux_envelope.py` (365 行) 包含 7 个测试用例,覆盖核心 sections、mode-specific headlines、tool failure recovery、preference learning、evolution highlights、structured actions (monkeypatch)、blocked temperature escalation。测试质量较高但未覆盖 `_local_state` 无界增长场景 (P0-1 无回归测试)。

### 总体复核结论

| 级别 | 原报告数量 | 复核确认 | 状态变化 |
|------|-----------|---------|---------|
| P0 | 1 | 1 | 无变化,未修复 |
| P1 | 5 | 5 | 无变化,未修复; P1-1 数量上调, P1-3 flag 数量上调 |
| P2 | 3 | 3 | 无变化,未修复 |
| 新增 | 0 | 0 | 无新 P0/P1/P2, 3 个观察性补充 (NF-1/2/3) |
| **总计** | **9** | **9** | **全部 STILL OPEN** |

**所有 9 项审计发现均未修复。代码自审计以来无变更。行号完全无偏移。**
