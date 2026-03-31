# Cognitive Nexus 整合策略与协议定义

## 1. 整合策略深度解析

### 1.1 Galaxy & Error Book 整合策略 (Visual & Logical Fusion)

*   **视觉层整合 (Visual Fusion)**:
    *   **"裂纹"特效**: 星图中的 `KnowledgeNode` 将根据关联的 `ErrorRecord` 数量和最近错误时间，渲染不同程度的“裂纹”或“黯淡”效果。这直观地告诉用户哪些知识点虽然曾经点亮，但现在变得脆弱。
    *   **热力图叠加**: 在 Galaxy 视图提供 "Error Heatmap" 模式，高亮显示错误频发的区域（如某一章的所有节点）。
    *   **双向跳转**:
        *   在 Galaxy 节点详情页，显示 "相关错题 (3)"，点击进入筛选后的 Error Book 列表。
        *   在 Error Book 详情页，显示 "知识锚点"，点击直接跳转到 Galaxy 视图并聚焦该节点。

*   **逻辑层整合 (Logical Fusion)**:
    *   **掌握度联动算法**:
        $$ NodeMastery = \alpha \times StudyHistory + \beta \times (1 - ErrorRate) $$
        当错题被录入时，直接降低关联节点的 Mastery Score。当错题被复习并标记为 "Easy" 时，Mastery Score 回升。
    *   **自动标签推荐**: 分析错题文本，利用 LLM 提取关键词，自动推荐 Galaxy 中已存在的相关节点作为标签。

### 1.2 Task & Cognitive Prism 整合策略 (Feedback Loop)

*   **实时反馈回路**:
    *   **Pre-Task Nudge (任务前助推)**: 在用户创建任务时，Prism 分析历史数据。如果用户经常在“周五下午”放弃“高难度”任务，系统会弹出提示：“检测到周五下午精力通常较低，建议将任务拆解或降低难度。”
    *   **In-Task Intervention (任务中干预)**: 专注时检测到频繁切换应用（通过埋点），Prism 推送：“你似乎有些分心，需要开启‘深度专注模式’吗？”
    *   **Post-Task Reflection (任务后反思)**: 任务结束时，不只是简单的“完成”，而是引导用户记录“情绪”和“精力消耗”。这些数据喂给 Prism 更新用户画像。

### 1.3 Chat & Context 整合策略 (Context-Awareness)

*   **动态上下文注入 (Context Injection)**:
    *   **Short-term**: 当前屏幕内容（Screen Context）。例如用户在看错题本，Chat 自动知道“这道题”指的是屏幕上的题。
    *   **Long-term**: 
        *   **Knowledge State**: “用户在‘线性代数’上比较薄弱。”
        *   **Behavior Pattern**: “用户喜欢被鼓励（Anime Persona）。”
        *   **Recent Activity**: “刚完成了一个 45 分钟的专注任务。”
    *   **实现**: 在每次对话前，`ChatService` 调用 `ContextManager.assemble_context(user_id)`，生成一段精简的 System Prompt 补充信息。

## 2. 跨模块通讯协议 (Inter-Module Protocol)

采用 CloudEvents 标准的 JSON 格式，通过 RabbitMQ Topic Exchange 分发。

### 2.1 事件总线主题结构
`sparkle.{domain}.{entity}.{action}`
例如: `sparkle.galaxy.node.updated`, `sparkle.task.session.completed`

### 2.2 核心事件 Payload 定义

#### A. Galaxy 事件
**Event**: `sparkle.galaxy.node.mastery_changed`
```json
{
  "id": "evt-uuid-1234",
  "source": "service.galaxy",
  "type": "sparkle.galaxy.node.mastery_changed",
  "time": "2023-10-27T10:00:00Z",
  "data": {
    "user_id": "user-uuid",
    "node_id": "node-uuid",
    "old_mastery": 0.4,
    "new_mastery": 0.2,
    "reason": "error_record_added", // or "study_session_completed"
    "trigger_id": "error-uuid" // 关联的触发源 ID
  }
}
```

#### B. Error Book 事件
**Event**: `sparkle.error.record.created`
```json
{
  "id": "evt-uuid-5678",
  "source": "service.error_book",
  "type": "sparkle.error.record.created",
  "time": "2023-10-27T10:05:00Z",
  "data": {
    "user_id": "user-uuid",
    "error_id": "error-uuid",
    "subject_id": 101,
    "linked_node_ids": ["node-uuid-a", "node-uuid-b"],
    "analysis_summary": "Calculation error in integration by parts."
  }
}
```

#### C. Task 事件
**Event**: `sparkle.task.completed`
```json
{
  "id": "evt-uuid-9012",
  "source": "service.task",
  "type": "sparkle.task.completed",
  "time": "2023-10-27T11:00:00Z",
  "data": {
    "user_id": "user-uuid",
    "task_id": "task-uuid",
    "plan_id": "plan-uuid",
    "duration_seconds": 2700,
    "focus_score": 0.85,
    "interruptions": 2,
    "completion_status": "completed", // or "abandoned"
    "user_feedback": {
      "energy_level": 3, // 1-5
      "difficulty": 4
    }
  }
}
```

## 3. 核心数据模型变更 (Schema Changes)

### 3.1 `backend/app/models/galaxy.py` (KnowledgeNode)
```python
# 新增字段以支持与错题本的快速关联和视觉渲染
class KnowledgeNode(BaseModel):
    # ... existing fields ...
    
    # 关联统计 (反范式化设计，减少聚合查询)
    total_error_count = Column(Integer, default=0)
    unresolved_error_count = Column(Integer, default=0)
    
    # 最近一次关联错题的时间 (用于计算"裂纹"新鲜度)
    last_error_at = Column(DateTime, nullable=True)
    
    # 关联错题 IDs (Array or JSONB) - 可选，视具体查询需求而定
    # linked_error_ids = Column(JSONB, default=list) 
```

### 3.2 `backend/app/models/cognitive.py` (BehaviorPattern)
```python
# 增强 Prism 对不同模块的洞察能力
class BehaviorPattern(BaseModel):
    # ... existing fields ...
    
    # 关联上下文: 该模式主要在哪些场景下触发
    # e.g., ["domain:task", "domain:error_review"]
    context_domains = Column(JSONB, default=list)
    
    # 触发条件 (JSON Logic)
    # e.g., {"time_of_day": "afternoon", "task_difficulty": ">3"}
    trigger_conditions = Column(JSONB, default=dict)
```

### 3.3 `backend/app/models/chat.py` (ChatMessage)
```python
# 增强对话记录的上下文回溯能力
class ChatMessage(BaseModel):
    # ... existing fields ...
    
    # 记录对话发生时的关键上下文快照 (Snapshot)
    # 这样历史对话可以还原当时的"语境"
    context_snapshot = Column(JSONB, nullable=True) 
    # {
    #   "active_task_id": "...",
    #   "focused_node_id": "...",
    #   "user_mood": "anxious"
    # }
```
