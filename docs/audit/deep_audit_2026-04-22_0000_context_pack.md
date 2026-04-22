# 深度审计：Context Pack 上下文组装与注入链路

> 日期：2026-04-22 00:00
> 范围：`context_manager.py` 聚合 → `context_builder.py` 合并 → `prompts.py` 组装 → `standard_workflow.py` 注入 LLM 的完整路径

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: context_manager 与 orchestrator 重复获取相同数据，每请求双倍 DB 查询
- **位置**: `backend/app/core/context_manager.py:157-166` vs `backend/app/orchestration/context_builder.py` (orchestrator 调用路径)
- **问题**: context_manager 并行获取 7 个维度（tasks、focus、achievements、errors、metrics、community、calendar），随后 context_builder 再次独立查询 tasks（:536-558）、plans（:561-583）、focus_service（:586）、analytics（:530）
- **影响**: 每次聊天请求对同一用户执行 2 轮 DB 查询获取重叠数据；高并发下 DB 连接池压力大；两轮查询间数据可能不一致（如任务状态刚变更）
- **证据**:
  ```
  context_manager.py:159 → _get_task_profile(uid, db)    # 获取 tasks + focus
  context_builder.py:536 → queries tasks from DB directly  # 再次获取 tasks
  context_builder.py:586 → focus_service.get_today_stats() # 再次获取 focus
  ```
- **修复**: context_builder 应直接复用 context_manager 的 CognitiveContext，而非重复查询；或合并为单一获取入口

#### P0-2: community_context 被 context_manager 获取但从未注入 prompt，浪费 DB 查询
- **位置**: `context_manager.py:164` (获取) vs `prompts.py:2541-2796` (渲染)
- **问题**: community_context 在 context_manager 的 7 个并行查询中被获取（含 N+1 查询 bug），但 `_render_user_context_content()` 从未引用该字段
- **证据**:
  ```python
  # context_manager.py:164 — 获取 community 数据
  _with_session(lambda db: self._get_community_profile(uid, db)),

  # prompts.py:2541-2796 — 搜索 "community_context" → 无渲染调用
  # 仅 social_context 有条件渲染 (prompts.py:2727-2735)
  # 但 social_context 与 community_context 是不同字段
  ```
- **影响**: 每次请求浪费 1 个并行 DB 连接 + N+1 查询开销，数据从未到达 LLM
- **修复**: (1) 在 `_render_user_context_content` 中渲染 community_context（社区活跃度、冲刺进度等），或 (2) 如果暂不需要 AI 感知社群状态，从并行查询中移除该维度

#### P0-3: context_manager 社群查询存在 N+1 问题，随群组数线性增长
- **位置**: `backend/app/core/context_manager.py:555-574`
- **问题**: sprint 类型群组在循环内逐个执行 SQL 查询
  ```python
  for member, group in rows:
      if group_type == "sprint":
          claim_counts = await self.db.execute(...)  # 每个 sprint group 一次查询
  ```
- **影响**: 用户加入 5 个 sprint group → 5 次额外 DB 查询；大量用户同时请求时 DB 压力显著
- **修复**: 预先批量查询所有 sprint group 的 claim_counts，用 IN 子句或 JOIN 替代循环内查询

---

### P1 — 重要问题（6 项）

#### P1-1: social_context 永远为空字典，Stage 17 预留但无数据源
- **位置**: `context_manager.py:209`
  ```python
  social_context={},  # Always empty - no service fills this field
  ```
- **问题**: CognitiveContext 定义了 social_context 字段但从不填充；prompts.py 有条件渲染逻辑但永远不触发
- **影响**: social→router 路径声称已连接但实际为死代码
- **修复**: 移除空 social_context 字段，或在 social_read_enabled 时填充真实数据

#### P1-2: context_manager 无输出大小限制，依赖 prompts.py 后置截断
- **位置**: `context_manager.py:189-216`
- **问题**: CognitiveContext 不限制任何字段的大小（tasks 列表、errors 列表等），仅部分查询有 `.limit(5)`
- **影响**: 极端情况下 context_manager 输出可达数十 KB，prompts.py 的 token budget 需大幅截断，浪费了获取成本
- **修复**: 在 context_manager 入口添加总大小预算（如 8KB），超限时按优先级裁剪

#### P1-3: prompts.py 中大量硬编码限制值，无法按环境调优
- **位置**: `prompts.py` 多处
  ```python
  # :2606
  limit = 3 if context_level == "light" else 5
  # :2628
  pain_limit = section_caps.get("recent_pain_points") or (1 if context_level == "light" else 3)
  # :2717
  memory_limit = section_caps.get("episodic") or (1 if context_level == "light" else 5)
  # :3001
  normalized["active_goals"] = [g for g in canonical_insight.goals[:3]]
  ```
- **影响**: 无法通过配置调整不同 tier 用户的上下文深度，必须改代码
- **修复**: 迁移到 settings.py 配置项，支持环境变量覆盖

#### P1-4: Context 缓存 TTL 5 分钟可能导致 prompt 引用过时状态
- **位置**: `context_manager.py:76`
  ```python
  CACHE_TTL_SECONDS = 300  # 5 minutes
  ```
- **问题**: 用户完成任务、解锁成就、产生新错题后，AI 仍使用 5 分钟前的旧上下文
- **影响**: AI 回复与用户当前状态脱节（"恭喜你完成XX"但用户已完成很久）
- **修复**: (1) 关键事件（TaskCompleted, AchievementUnlocked, ErrorCreated）触发缓存主动失效 (2) 或缩短 TTL 到 60s

#### P1-5: 缓存读写失败静默处理，性能退化无感知
- **位置**: `context_manager.py:259-261, 270-271`
  ```python
  except Exception as e:
      logger.warning(f"Cache get failed for user context: {e}")
      return None  # 静默降级到全量查询
  ```
- **影响**: Redis 抖动时所有请求走 DB 全量查询，但无 Prometheus 指标追踪
- **修复**: 添加 `sparkle_context_cache_miss_total` / `sparkle_context_cache_error_total` 指标

#### P1-6: _SafeFormatDict 静默吞没模板占位符缺失
- **位置**: `prompts.py:42-45`
  ```python
  class _SafeFormatDict(dict):
      def __missing__(self, key: str) -> str:
          logger.warning("Prompt template missing placeholder value: {}", key)
          return f"{{missing:{key}}}"  # AI 看到 {missing:field_name}
  ```
- **问题**: 模板变量缺失时，LLM 收到 `{missing:user_context}` 等原始占位符，可能误解为指令
- **修复**: 添加 Prometheus 计数器 + CI 测试验证所有模板占位符有对应值

---

### P2 — 改进建议（4 项）

#### P2-1: 截断策略不一致 — 仅 error question 有字符截断
- **位置**: `context_manager.py:308`
  ```python
  "question_preview": e.question_text[:50] if e.question_text else "Image Question"
  ```
- **问题**: 只有错题问题文本截断到 50 字符，task title、plan title 等长文本字段未截断
- **修复**: 统一截断策略，所有用户输入文本字段限制在合理长度（如 100 字符）

#### P2-2: profile_context 全量获取但仅部分字段被提取
- **位置**: `context_manager.py:164` (获取完整 profile_context) vs `prompts.py:2859-3018` (仅提取部分字段)
- **问题**: 完整 profile payload 可能包含 AI 不需要的敏感或冗余字段
- **修复**: 在 context_manager 层做字段裁剪，仅传递 AI 需要的子集

#### P2-3: context_data 中 20+ 控制字段从不注入 prompt，但持续累积
- **位置**: `orchestrator.py:1098-1213` — session_feedback_signal, adaptation_records, preference_learnings 等
- **问题**: 这些字段在 FSM 状态中累积（已达 20+ 字段），增加内存占用但从不被 LLM 使用
- **修复**: 区分"控制字段"和"上下文字段"，控制字段在 FSM turn 结束时清理

#### P2-4: prompts.py 29+ section 的优先级和权重缺乏集中管理
- **位置**: `prompts.py:1193-1221` (优先级) + `prompts.py:60-86` (预算比)
- **问题**: section 优先级和 token 预算比例分散在不同 dict 中，新增 section 时容易遗漏
- **修复**: 合并为统一的 section_registry，每个 section 声明自己的优先级、预算比、feature flag

---

### 合规项（4 项）

1. **7 维度并行获取** ✅ — asyncio.gather 并行调用 7 个数据源，无串行瓶颈
2. **Token 预算系统完备** ✅ — prompts.py 实现了 tier-based budget + section priority + 两轮裁剪
3. **社区字段白名单防护** ✅ — COMMUNITY_CONTEXT_ALLOWED_FIELDS 严格限制输出字段
4. **遥测覆盖率追踪** ✅ — `_mark_rendered` 追踪 11 个高价值字段的收集/渲染/丢弃状态

---

## 数据流图

```
用户发送消息
  ↓
Orchestrator (FSM INIT → THINKING)
  │
  ├── [路径A] context_manager.get_user_context(uid)
  │   ├── 并行: profile, errors, tasks, metrics, community, achievement, calendar
  │   │          ⚠️ community 查询含 N+1 bug
  │   ├── 合并为 CognitiveContext (14 字段)
  │   ├── 缓存 5min (preference_version 失效)
  │   └── social_context = {} 永远为空 ⚠️
  │
  ├── [路径B] context_builder._build_user_context()  ⚠️ 与路径A重叠
  │   ├── 再次查询 tasks, plans, focus, analytics
  │   ├── 调用 user_service.get_context()
  │   └── 合并为 user_context_payload
  │
  ├── _merge_user_contexts(A, B) → 合并
  │
  ↓
prompts.py: build_system_prompt()
  │
  ├── _render_user_context_content()
  │   ├── 渲染: identity, analytics, preferences, knowledge, errors ✅
  │   ├── 渲染: mastery, achievement, tasks, focus ✅
  │   ├── 渲染: calendar ✅
  │   ├── 渲染: social_context (条件) ✅
  │   ├── 未渲染: community_context ⚠️ 死数据
  │   └── _mark_rendered() → 遥测
  │
  ├── 29+ section 模板组装
  │   ├── Token budget 两轮裁剪
  │   └── _SafeFormatDict 静默处理缺失变量
  │
  ↓
standard_workflow.py → generation_llm.chat_stream_with_tools(system_prompt)
  │
  ↓
LLM 接收最终 prompt (受 token budget 裁剪)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | context_manager 与 orchestrator 重复查询 | 合并获取入口，context_builder 复用 CognitiveContext | 中（~150 行重构） |
| P0-2 | community_context 获取但从未渲染 | 在 prompts.py 添加渲染 或 从并行查询移除 | 低（~30 行） |
| P0-3 | 社群查询 N+1 | 批量查询替代循环内查询 | 低（~20 行 Python） |
| P1-1 | social_context 永远为空 | 移除死代码或填充真实数据 | 低（~10 行） |
| P1-2 | context_manager 无输出大小限制 | 添加 8KB 总预算 + 按优先级裁剪 | 中（~50 行） |
| P1-3 | 硬编码限制值 | 迁移到 settings.py | 低（~40 行迁移） |
| P1-4 | 缓存 TTL 5min 过长 | 关键事件触发缓存失效 | 中（~60 行） |
| P1-5 | 缓存失败无指标 | 添加 Prometheus counter | 低（~10 行） |
| P1-6 | SafeFormatDict 静默吞没 | 添加 counter + CI 测试 | 低（~15 行） |
