# LLM 降级系统全面审查报告

**审查日期**: 2026-03-17
**审查范围**: 所有 LLM 调用点、降级逻辑、模型优先级

---

## 一、系统架构概览

### 1.1 多层降级架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户请求入口                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 0: Demo Mode (演示模式)                              │
│  - DEMO_MODE=true 时，返回预设响应                          │
│  - 适用于竞赛演示，确保 100% 成功                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: LLMRouter (模型路由)                              │
│  - 根据 AgentRole + TaskType 选择模型                       │
│  - 支持 6 个 Tier 层级                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: LLMModelFallbackManager (模型级降级)              │
│  - 429/Rate Limit 检测                                      │
│  - 同 Tier 模型切换                                         │
│  - Tier 降级 (REASONING → STANDARD → FAST)                  │
│  - 指数退避重试                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Circuit Breaker (熔断器)                          │
│  - 失败阈值: 5 次                                           │
│  - 恢复时间: 30 秒                                          │
│  - Redis 分布式状态追踪                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Service Fallback (服务级降级)                     │
│  - safe_llm_call / safe_llm_json_call                       │
│  - 超时保护                                                 │
│  - 返回默认值                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 模型 Tier 层级

| Tier | 描述 | 模型列表 (按优先级) |
|------|------|-------------------|
| `FREE_FAST` | 免费快速响应 | glm-4.7-flash (非思考模式) |
| `FREE_REASONING` | 免费深度推理 | glm-4.7-flash (思考模式) |
| `FAST` | 付费快速响应 | xiaomi_chat, zhipu_flash |
| `STANDARD` | 付费标准模型 | zhipu_chat, deepseek_chat, dashscope_chat |
| `REASONING` | 付费推理模型 | zhipu_reason, deepseek_reason, dashscope_reason |
| `SPECIALIST` | 专家模型 | siliconflow_ocr, siliconflow_translate |

### 1.3 模型提供商

| Provider | 模型 | 特点 |
|----------|------|------|
| **Zhipu (智谱)** | GLM-4.7, GLM-4.7-Flash | 支持 clear_thinking 参数控制思考模式 |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | 编程能力强，推理模型稳定 |
| **XiaoMi** | MIMO | 快速响应，适合简单任务 |
| **DashScope** | qwen-plus, qwen-turbo | 阿里云通义千问，中文能力强 |
| **SiliconFlow** | Hunyuan MT | 腾讯混元翻译模型 |

---

## 二、服务 LLM 调用分析

### 2.1 已有完整降级保护的服务 ✅

| 服务 | 文件 | 降级策略 | 包装器 |
|------|------|----------|--------|
| VocabularyService | `vocabulary_service.py` | 返回空/默认值 | `vocabulary_llm` |
| AnalysisOrchestrator | `analysis/orchestrator.py` | 返回默认分析结果 | `analysis_llm` |
| OmniBarService | `omnibar_service.py` | 降级到 CHAT 模式 | `omnibar_llm` |
| SummarizationWorker | `summarization_worker.py` | 返回空字符串 | `summarization_llm` |
| STTService | `stt_service.py` | 返回原文 | `stt_llm` |
| PreferencesService | `preferences.py` | 返回错误提示 | `preferences_llm` |
| SpecialistAgents | `specialist_agents.py` | 返回友好错误 | `agent_llm` |
| CognitiveService | `cognitive_service.py` | 返回默认分析 | `cognitive_llm` |
| SufficiencyChecker | `sufficiency_checker.py` | 默认认为足够具体 | `sufficiency_llm` |
| RequestRouter | `request_router.py` | 降级到关键词匹配 | `router_llm` |

### 2.2 仍需添加降级保护的服务 ⚠️

| 服务 | 文件 | 方法 | 风险等级 | 状态 |
|------|------|------|----------|------|
| FocusService | `focus_service.py` | `get_session_coaching()` | 中 | ✅ 已修复 (focus_llm) |
| FocusService | `focus_service.py` | `breakdown_task_via_llm()` | 中 | ✅ 已修复 (focus_llm) |
| TranslationService | `translation_service.py` | `_translate_segment()` | 低 | ✅ 已有 fallback 到通用 LLM |
| KnowledgeService | `knowledge_service.py` | `_generate_hypothetical_answer()` | 低 | ✅ 已修复 (hyde_llm) |
| GraphRAG | `graph_rag.py` | `extract_entities()` | 低 | ✅ 已有 _simple_extract 降级 |
| SearchAgent | `search_agent.py` | `process()` | 中 | ✅ 已修复 (search_llm) |
| UnifiedIntentRouter | `unified_intent_router.py` | `_llm_classify()` | 中 | ✅ 已修复 (router_llm) |
| PlanTools | `plan_tools.py` | `_generate_plan_tasks_via_llm()` | 中 | ✅ 已修复 (plan_llm) |

### 2.3 核心服务 (高优先级保护)

| 服务 | 文件 | 降级策略 |
|------|------|----------|
| PlanReviewService | `plan_review_service.py` | ✅ 已有完整 fallback (_llm_review_fallback) |
| Orchestrator | `orchestrator.py` | ✅ 使用 LLMService 内置降级 |
| LLMService | `llm_service.py` | ✅ 核心降级层 (Demo Mode + Router + FallbackManager) |

---

## 三、降级策略分析

### 3.1 模型级降级流程

```
REASONING (zhipu_reason)
    │
    ├── 429/Error → 同 Tier: deepseek_reason
    │               │
    │               ├── 429/Error → 同 Tier: dashscope_reason
    │               │               │
    │               │               └── 429/Error → 降级到 STANDARD
    │               │
    │               └── ... → 降级到 STANDARD
    │
    └── ... → 降级到 STANDARD

STANDARD (zhipu_chat / deepseek_chat / dashscope_chat)
    │
    └── 最终降级 → FAST (xiaomi_chat / zhipu_flash)
                    │
                    └── 最终降级 → FREE_FAST (glm-4.7-flash)
```

### 3.2 服务级降级模式

```python
# 模式 1: 简单 fallback
result = await service_llm.call(messages, fallback="默认响应")

# 模式 2: JSON fallback
result = await service_llm.json_call(messages, fallback={"key": "default"})

# 模式 3: 超时保护
result = await service_llm.call(messages, timeout=10.0, fallback="...")
```

### 3.3 当前缺失的降级场景

1. **并发限制**: 当所有模型都达到并发上限时，缺乏队列等待机制
2. **配额耗尽**: 当所有付费模型配额耗尽时，自动切换到免费模型
3. **区域性故障**: 当某个 Provider 完全不可用时，自动切换到其他 Provider

---

## 四、服务优先级矩阵

### 4.1 响应时间要求

| 服务类型 | 超时设置 | 推荐模型 Tier |
|----------|----------|--------------|
| 意图路由 (Router) | 5s | FREE_FAST |
| 充分性检查 (Sufficiency) | 10s | FREE_FAST |
| STT 增强 | 10s | FAST |
| 词汇查询 (Vocabulary) | 15s | FREE_FAST |
| 偏好预览 (Preferences) | 15s | STANDARD |
| 认知分析 (Cognitive) | 30s | STANDARD |
| 计划审查 (PlanReview) | 45s | REASONING |
| 专家智能体 (Agents) | 45s | REASONING |

### 4.2 容错等级

| 等级 | 服务 | 行为 |
|------|------|------|
| **P0 必须成功** | Orchestrator, ChatService | 多层降级 + Demo Mode |
| **P1 优雅降级** | PlanReview, CognitiveAnalysis | 返回默认结果 + 日志 |
| **P2 可接受失败** | Preferences, Summarization | 返回错误提示 |
| **P3 可选功能** | VocabularyEnhancement | 静默失败，返回原始数据 |

---

## 五、服务包装器清单

### 5.1 已注册的服务包装器 (14个)

| 包装器 | 服务 | 超时 | 默认 Fallback |
|--------|------|------|---------------|
| `vocabulary_llm` | VocabularyService | 30s | 空定义/空数组 |
| `analysis_llm` | AnalysisService | 30s | 默认分析结果 |
| `omnibar_llm` | OmniBarService | 30s | `{"type": "CHAT"}` |
| `summarization_llm` | SummarizationService | 30s | 空字符串 |
| `stt_llm` | STTService | 10s | 原文 |
| `preferences_llm` | PreferencesService | 15s | 错误提示 |
| `agent_llm` | SpecialistAgents | 45s | 友好错误消息 |
| `cognitive_llm` | CognitiveService | 30s | 默认分析 |
| `sufficiency_llm` | SufficiencyChecker | 10s | `{"specific": True}` |
| `router_llm` | RequestRouter | 5s | `"chat"` |
| `focus_llm` | FocusService | 15s | 鼓励消息/空数组 |
| `search_llm` | SearchAgent | 10s | 无结果提示 |
| `plan_llm` | PlanTools | 30s | 空列表 |
| `hyde_llm` | HyDE (KnowledgeService) | 1.5s | 空字符串 |

### 5.2 降级优先级策略

```
服务请求 → LLMRouter (选择模型)
    │
    ├── 成功 → 返回结果
    │
    └── 失败 (429/Error) → LLMModelFallbackManager
            │
            ├── 同 Tier 模型切换
            │
            ├── Tier 降级 (REASONING → STANDARD → FAST → FREE_FAST)
            │
            └── 最终降级 → Service Fallback (返回默认值)
```

---

## 六、改进建议

### 6.1 架构优化 (P1)

1. **统一超时配置**: 将所有服务的超时时间集中管理
2. **配额感知路由**: 在选择模型时考虑剩余配额
3. **健康检查增强**: 定期检查各 Provider 可用性

### 5.3 监控增强 (P2)

1. **降级事件追踪**: 记录每次降级的触发原因和结果
2. **模型性能看板**: 展示各模型的延迟、成功率、成本
3. **告警机制**: 当降级频率超过阈值时发出告警

---

## 六、代码示例

### 6.1 添加新服务包装器

```python
# 在 llm_fallback_utils.py 中添加

focus_llm = LLMFallbackWrapper(
    service_name="FocusService",
    default_fallback="专注建议暂时不可用，请稍后重试。",
    default_json_fallback={"subtasks": []},
    timeout=15.0
)

search_llm = LLMFallbackWrapper(
    service_name="SearchAgent",
    default_fallback="搜索结果摘要暂时不可用。",
    timeout=10.0
)

plan_llm = LLMFallbackWrapper(
    service_name="PlanTools",
    default_fallback=[],
    default_json_fallback=[],
    timeout=30.0
)
```

### 6.2 在服务中使用

```python
# focus_service.py
async def get_session_coaching(self, ...):
    from app.services.llm_fallback_utils import focus_llm

    return await focus_llm.call(
        messages,
        fallback="继续专注，你做得很好！",
        temperature=0.7
    )
```

---

## 七、总结

### 当前状态

- ✅ **核心服务**: 完整的 4 层降级保护
- ✅ **14 个服务**: 已添加 `LLMFallbackWrapper` 保护
- ✅ **所有关键路径**: 已覆盖降级保护
- ⚠️ **配额管理**: 尚未实现自动切换

### 建议优先级

1. **本周**: 实现配额感知路由
2. **本月**: 增强监控和告警系统
