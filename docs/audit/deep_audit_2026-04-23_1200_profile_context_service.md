# 深度审计 #60 — ProfileContextService 用户画像域统一读模型完整链路

> **日期**: 2026-04-23 12:00
> **模块**: ProfileContextService — 用户画像统一读接口 → Redis 缓存 → ContextManager → ContextBuilder → Prompt 注入
> **范围**: `profile_context_service.py`（353 行）+ `profile_context.py`（69 行，Pydantic 模型）+ `context_manager.py`（312 行调用）+ `profile_transparency.py`（API 消费）+ `context_builder.py`（policy_signals 映射）
> **审计员**: GLM-5.1 executor (Session continuation, 第十一次唤醒)

---

## 审计范围

ProfileContextService 是 Sparkle 用户画像域的**统一读模型**。所有需要读取用户画像的消费方（AI 上下文注入、透明度 API、推荐引擎）都应通过 `get_profile_context()` 获取结构化数据，而非直接查询底层模型。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/profile_context_service.py` | 353 | 统一读模型：聚合偏好+知识+认知 |
| `core/profile_context.py` | 69 | Pydantic 模型定义（5 个嵌套类） |
| `core/context_manager.py` | 312 | 消费方：构建 CognitiveContext |
| `api/v1/profile_transparency.py` | 660+ | 消费方：用户透明度 API |
| `orchestration/context_builder.py` | 954 | 消费方：AI 上下文注入 |

---

## 数据流图

```
用户画像变更 (偏好写入/知识学习/认知模式更新)
  │
  ├── ProfileWriteService → DB 写入 ✅
  │   └── ⚠️ 不清除 ProfileContextService 缓存 (P0-1)
  │
  ├── AI 请求到达 → ContextBuilder → ContextManager
  │   └── ProfileContextService.get_profile_context()
  │       ├── Redis 缓存检查 (TTL 300s) ✅
  │       ├── ⚠️ 缓存 miss → 4 串行 DB 查询 (P1-1)
  │       ├── _get_preferences() → PreferenceService
  │       ├── _get_knowledge_summary()
  │       │   ├── avg mastery score
  │       │   ├── weak spots (5)
  │       │   ├── recent mastery changes (5)
  │       │   ├── active subjects (5)
  │       │   └── ⚠️ fallback: 伪造 old_mastery=42.0-delta (P0-2)
  │       └── _get_cognitive_summary()
  │           ├── active patterns (5, confidence≥0.5)
  │           ├── policy_signals via PATTERN_POLICY_MAP
  │           ├── risk_signals via RISK_SIGNAL_MAP
  │           └── dominant_pattern_type
  │
  ├── 输出: ProfileContext.to_prompt_context()
  │   └── ⚠️ 无 token 预算/截断 (P1-5)
  │
  └── 缓存写入 Redis ✅
      └── ⚠️ DB 查询失败时不缓存 → 每次请求重试 (P1-3)
```

---

## 审计发现

### P0 — 严重缺陷（2 项）

#### P0-1: 缓存清除声明与实现不一致 — 偏好/知识/认知变更时缓存不清除，数据陈旧可达 5 分钟
**文件**: `profile_context.py:15` (文档声明) + `profile_context_service.py` (无清除逻辑)
**严重性**: P0 — 用户偏好变更后 AI 最长 5 分钟仍使用旧偏好

```python
# profile_context.py:15 — 文档声明:
# "缓存策略：Redis，TTL 5 分钟，在偏好/知识/认知变更事件时清除"

# profile_context_service.py — 全文搜索:
# grep "delete|clear|invalidat|remove.*cache" → 零匹配
# 实际上没有任何主动清除缓存的代码
```

**验证**: 
- ProfileWriteService 写入偏好时不调用 ProfileContextService 的任何缓存清除方法
- KnowledgeNode/StudyRecord 更新时不触发缓存清除
- BehaviorPattern 更新时不触发缓存清除
- 唯一的缓存过期机制是 Redis TTL (300s)

**影响**: 
1. 用户在「设置」中修改学习偏好（如 "不要在晚上提醒我"）→ AI 在 5 分钟内仍使用旧偏好
2. 用户完成知识节点学习 → AI 在 5 分钟内不知道掌握度已变化
3. 认知模式被检测到 → AI 在 5 分钟内不知道新模式

**修复**: (1) ProfileWriteService 写入后调用 `redis.delete(f"user:profile_context:{user_id}")` (2) 或在 EventBus 消费 `ProfilePreferenceUpdated` 和 `KnowledgeNodeUpdated` 事件时清除缓存

---

#### P0-2: Fallback 掌握度数据伪造 — `old_mastery=max(0.0, 42.0 - delta)` 硬编码基线
**文件**: `profile_context_service.py:280-288`
**严重性**: P0 — AI 决策基于伪造的历史数据

```python
# :280-288 — fallback 路径（StudyRecord 不存在时）
recent_changes.append(
    MasteryChange(
        node_id=f"derived:{index}",     # ← 伪造 ID
        node_name=node_name,
        old_mastery=max(0.0, 42.0 - delta),  # ← 硬编码 42.0
        new_mastery=max(0.0, 42.0),          # ← 硬编码 42.0
        changed_at=changed_at,
    )
)
```

**问题**:
1. `42.0` 是一个完全任意的数字，不代表任何实际的掌握度
2. 当 `delta > 42.0` 时，`old_mastery` 变为 0.0，暗示用户从零开始
3. `node_id=f"derived:{index}"` 不是真实节点 ID，下游如果用此 ID 查询会失败
4. 如果 fallback 实际上被触发（新用户无 StudyRecord），AI 会看到虚假的掌握度变化数据

**修复**: 当 StudyRecord 不存在时，返回空列表而非伪造数据。让 AI 知道"无历史数据"比"虚假数据"更安全。

---

### P1 — 重要问题（5 项）

#### P1-1: `_get_knowledge_summary` 4+2 串行 DB 查询 — 可并行化
**文件**: `profile_context_service.py:152-295`
**严重性**: P1 — 性能瓶颈

```python
# 4 个串行查询 + 2 个可能的 fallback 查询
avg_stmt = select(func.avg(...))       # 查询 1
weak_stmt = select(...).limit(5)       # 查询 2
change_stmt = select(...).limit(5)     # 查询 3
subject_stmt = select(...).limit(5)    # 查询 4
# fallback:
fallback_mastery = await report_tools  # 查询 5 (可能)
fallback_timeline = await report_tools # 查询 6 (可能)
```

4 个主查询完全独立，可用 `asyncio.gather()` 并行。当前串行执行导致每次缓存 miss 时延迟 ~4× 单次查询时间。

---

#### P1-2: PATTERN_POLICY_MAP 查找不一致 — normalized key 可能不匹配 DB 存储
**文件**: `profile_context_service.py:320-321, 350-352`
**严重性**: P1 — 策略信号映射失效

```python
# :320-321
normalized = self._normalize_pattern_name(name)  # 调用 canonical_pattern_key()
signals = list(self.PATTERN_POLICY_MAP.get(normalized, []))  # 查找映射

# :350-352
@staticmethod
def _normalize_pattern_name(name: str) -> str:
    return canonical_pattern_key(name)  # 外部函数，行为不透明
```

PATTERN_POLICY_MAP 使用 13 个特定 key（如 "planning_optimism"），但 `canonical_pattern_key()` 的规范化逻辑可能产生不同格式。如果 DB 中存储的模式名与 MAP key 不完全匹配（大小写、空格、下划线/连字符差异），查找返回空列表，policy_signals 为空。

---

#### P1-3: 查询失败时结果不缓存 — 每次请求重试失败的 DB 查询
**文件**: `profile_context_service.py:121-136`
**严重性**: P1 — DB 压力放大

```python
# :121-136 — 缓存写入仅在 get_profile_context 末尾
context = ProfileContext(...)  # 构建完整结果

if self.redis:
    await self.redis.setex(cache_key, self.CACHE_TTL_SECONDS, ...)  # 仅成功时缓存

return context
```

如果 `_get_knowledge_summary` 的某个子查询失败（被 try/except 捕获），部分字段为空，但整体结果仍然会被缓存。然而，如果 Redis 写入本身失败（:136 except），结果完全不缓存，**每次请求都触发全部 DB 查询**。

**修复**: 对 Redis 写入失败添加短期内存缓存（如 30s），避免连续失败时的查询风暴。

---

#### P1-4: `to_prompt_context()` 无 token 预算 — 全量注入 AI prompt
**文件**: `profile_context.py:67-68`
**严重性**: P1 — prompt 膨胀

```python
def to_prompt_context(self) -> dict[str, Any]:
    return self.model_dump(mode="json")  # 全量序列化，无截断
```

5 个 weak spots × (node_id + node_name + mastery + last_attempt_at) + 5 个 mastery changes + 5 个 active patterns × (pattern_name + pattern_type + confidence + policy_signals[0-2]) + risk_signals + active_subjects + preferences 全部注入 prompt。估计占用 500-1000 tokens。

对比 context_pack.py 使用 tiktoken 做 token 预算裁剪，ProfileContext 完全无预算控制。

---

#### P1-5: `_get_preferences` 字段名误导 — "explicit" 实际包含 inferred
**文件**: `profile_context_service.py:140-150`
**严重性**: P1 — 语义不一致

```python
merged = dict(inferred)    # 从 inferred 开始
merged.update(explicit)    # explicit 覆盖
return {
    "explicit": merged,     # ← 字段名是 "explicit" 但包含 inferred
    "inferred": inferred,   # ← 原始 inferred
    ...
}
```

下游消费方如果认为 `preferences["explicit"]` 仅包含用户显式设置的偏好，会错误地也将推断偏好视为显式偏好。

---

### P2 — 改进建议（3 项）

#### P2-1: Redis fail-open — Redis 不可用时每次请求都查 DB
**文件**: `profile_context_service.py:112-119, 132-136`

Redis 读取和写入都有 try/except 静默吞错。Redis 故障期间，300s TTL 的保护完全消失，每次请求执行 4+ 次 DB 查询。

---

#### P2-2: 硬编码限制值 (5) 不可配置
**文件**: `profile_context_service.py:36-39`

```python
WEAK_SPOT_LIMIT = 5
CHANGE_LIMIT = 5
PATTERN_LIMIT = 5
SUBJECT_LIMIT = 5
```

对于深度分析模式可能需要更多数据点，但无法按模式调整。

---

#### P2-3: `get_profile_context` 不验证 user_id 是否存在
**文件**: `profile_context_service.py:110`

UUID 格式由类型系统保证，但如果 user_id 对应的用户不存在，所有查询返回空集。服务静默返回空 ProfileContext 而非报错。

---

## 合规项（5 项）

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Pydantic 模型定义 | ✅ | ProfileContext + 5 个嵌套模型，字段完整 |
| Redis 缓存层 | ✅ | 读缓存 + 写缓存，TTL 300s |
| DB 查询异常保护 | ✅ | 每个 try/except 捕获异常并记录日志 |
| 读/写分离 | ✅ | ProfileContextService 只读，ProfileWriteService 只写 |
| 文档注释 | ✅ | profile_context.py 有清晰的架构说明 |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 2 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **10** |

---

## 修复优先级建议

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 缓存不清除 | 写入路径后调用 redis.delete | 低（~5 行） |
| P0-2 | 伪造掌握度数据 | 移除 fallback，返回空列表 | 低（~5 行） |
| P1-1 | 串行 DB 查询 | asyncio.gather 并行化 | 中（~30 行） |
| P1-4 | 无 token 预算 | 添加截断或由 prompts.py 控制 | 中 |
| P1-5 | 字段名误导 | 改为 "merged" | 低（~3 行） |
| P1-2 | PATTERN_POLICY_MAP 不匹配 | 添加测试验证 key 匹配 | 中 |

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (缓存不清除) | Round #3 P0-1 (EventBus maxLen 不清除) | 缓存失效机制缺失的系统性问题 |
| P0-2 (伪造数据) | Round #58 P0-1 (event dict 零校验) | 数据完整性：宁可缺数据不可造假 |
| P1-1 (串行查询) | Round #44 (State Aggregator) | 聚合服务的并行化改进机会 |
| P1-4 (无 token 预算) | Round #54 P1-4 (Token 预算 len/4) | Token 预算在多个层级不一致 |
| P1-5 (字段名误导) | Round #52 P1-5 (无类型化 schema) | 命名语义不一致导致下游误用 |

---

## Chris (Session 5) 复核 — 2026-04-23

> 逐项验证 P0 发现对主项目当前代码 (`/Users/brsama/code/GitHub/Sparkle-project/`)。

### P0 验证

| 原始发现 | 文件 | 行号 | 当前状态 | 结论 |
|----------|------|------|---------|------|
| P0-1 缓存不清除 | `profile_context_service.py` | 全文 | **FALSE** — `profile_event_consumer.py:74,107,117,126` 在 4 种事件类型下调用 `_invalidate_profile_context_cache()` 清除 `user:profile_context:{user_id}` | **FALSE** |
| P0-2 伪造掌握度数据 | `profile_context_service.py` | :280-288 `old_mastery=max(0.0, 42.0 - delta)` | 代码未变 | **CONFIRMED** |

### P0-1 FALSE 详解

审计报告声称 "grep delete/clear/invalidat 零匹配"。实际上 `profile_event_consumer.py` 在以下事件中清除缓存:
- `profile.preference.updated` (:74)
- `profile.preference.deleted` (:107)
- `knowledge.updated` (:117)
- `behavior.pattern.updated` (:126)

这些事件通过 EventBus 消费链路正确触发，覆盖了偏好/知识/认知三大域的变更。报告遗漏了 `profile_event_consumer.py` 这个关键文件。

### P1 抽样验证

| 发现 | 结论 |
|------|------|
| P1-1 串行 DB 查询 | **CONFIRMED** — :159-230 四个查询仍为串行 |

### 总结

P0-1 为 FALSE（缓存清除存在于 `profile_event_consumer.py`，审计遗漏了消费方）。P0-2 (伪造掌握度) CONFIRMED。报告整体质量中等——数据流图准确但遗漏了关键的缓存清除路径。
