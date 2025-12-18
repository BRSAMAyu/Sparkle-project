# Sparkle Agent Workflow 实施方案

> 从「对话即服务」到「对话即行动」的架构升级

## 目录

1. [设计概述](#1-设计概述)
2. [整体架构](#2-整体架构)
3. [元能力层设计](#3-元能力层设计tool-registry)
4. [智能编排层设计](#4-智能编排层设计orchestration-layer)
5. [后端接口设计](#5-后端接口设计)
6. [前端协议设计](#6-前端协议设计)
7. [错误处理与反馈循环](#7-错误处理与反馈循环)
8. [实施路线图](#8-实施路线图)

---

##已完成内容：
# Agent Workflow Implementation Summary
    2 
    3 This document summarizes the implementation of the AI Agent Workflow
      for the Sparkle application, covering both backend (FastAPI) and 
      mobile (Flutter) components, based on the provided design document.
    4 
    5 ## 1. Backend Implementation
    6 
    7 The backend changes focused on introducing a tool-calling mechanism 
      for the LLM, an orchestration layer to manage these tools, and an 
      updated chat API to integrate the new workflow.
    8 
    9 ### 1.1. Tool Registry (`backend/app/tools/`)
   10 
   11 *   **Directory Structure**: Created `backend/app/tools/` to house a
      agent-related tools.
   12 *   **`base.py`**: Defined core abstractions:
   13     *   `ToolCategory` (Enum): Categorizes tools (e.g., `TASK`, 
      `KNOWLEDGE`, `PLAN`, `QUERY`).
   14     *   `ToolResult` (Pydantic Model): Standardized format for tool 
      execution outcomes, including success status, data, error messages, 
      and frontend-specific `widget_type` and `widget_data`.
   15     *   `BaseTool` (Abstract Base Class): Provides a common interfac
      for all tools, requiring `name`, `description`, `category`, 
      `parameters_schema` (Pydantic Model), and an `execute` async method.
      It also includes a `to_openai_schema` method for LLM integration.
   16 *   **`schemas.py`**: Defined Pydantic models for tool parameters, 
      ensuring strict type validation and clear descriptions for LLM 
      understanding. This includes schemas for creating/updating tasks, 
      creating/linking/querying knowledge nodes, and managing plans.
   17 *   **`task_tools.py`**: Implemented task-specific tools:
   18     *   `CreateTaskTool`: Creates a single learning task. Adapted to
      use the existing `TaskService.create` method.
   19     *   `UpdateTaskStatusTool`: Modifies a task's status (e.g., 
      `in_progress`, `completed`, `abandoned`). Mapped status strings to 
      corresponding `TaskService` methods (`start`, `complete`, `abandon`)
   20     *   `BatchCreateTasksTool`: Creates multiple tasks at once.
   21 *   **`knowledge_tools.py`**: Implemented knowledge graph-specific 
      tools:
   22     *   `CreateKnowledgeNodeTool`: Creates a new knowledge node in t
      user's galaxy.
   23     *   `QueryKnowledgeTool`: Searches for existing knowledge nodes 
      using either keyword or semantic (vector) search.
   24     *   `LinkNodesTool`: Establishes relationships between two 
      knowledge nodes.
   25 *   **`registry.py`**: Manages all registered tools. Implemented as 
      singleton `ToolRegistry` to provide centralized access, allowing 
      dynamic retrieval of tools by name or category, and generating OpenA
      Function Calling schemas for LLM interaction.
   26 
   27 ### 1.2. Galaxy Service Enhancement (`backend/app/services/galaxy
      _service.py`)
   28 
   29 *   **`create_node`**: Added a method to `GalaxyService` to create 
      `KnowledgeNode` instances, including automatic initialization of 
      `UserNodeStatus` for the creating user and handling `subject_id` and
      `parent_node_id`.
   30 *   **`create_edge`**: Added a method to `GalaxyService` to create 
      `NodeRelation` instances, linking knowledge nodes.
   31 *   **`keyword_search`**: Added a method to `GalaxyService` to perfo
      keyword-based searches for knowledge nodes, complementing the existi
      `semantic_search`.
   32 *   **`semantic_search` Update**: Modified the existing `semantic_
      search` method to accept an optional `subject_id` parameter, enablin
      more focused vector searches.
   33 
   34 ### 1.3. LLM Service Update (`backend/app/services/llm_service.py`)
   35 
   36 *   **Dataclasses**: Introduced `LLMResponse` (for LLM text content 
      and detected tool calls) and `StreamChunk` (for handling different 
      types of streaming events, like text or tool call chunks).
   37 *   **`chat_with_tools`**: Implemented a method for synchronous LLM 
      interaction that supports OpenAI-compatible function calling, 
      returning the LLM's text response and any detected `tool_calls`.
   38 *   **`continue_with_tool_results`**: Added a method to feed tool 
      execution results back to the LLM, allowing it to generate a final, 
      context-aware natural language response.
   39 *   **`chat_stream_with_tools`**: Implemented a streaming interface 
      for LLM interaction, yielding `StreamChunk` events for text, partial
      tool calls, and complete tool calls, allowing for real-time processi
      and execution of tools. This ensures a responsive user experience.
   40 *   **Integration with Provider**: Ensured that the `chat_with_tools
      and `chat_stream_with_tools` methods correctly leverage the 
      `OpenAICompatibleProvider`'s underlying `AsyncOpenAI` client for 
      native tool calling capabilities.
   41 
   42 ### 1.4. Orchestration Layer (`backend/app/orchestration/`)
   43 
   44 *   **Directory Structure**: Created `backend/app/orchestration/` fo
      the intelligent orchestration components.
   45 *   **`prompts.py`**: Defined the `AGENT_SYSTEM_PROMPT` for the LLM,
      outlining its role, core principles (action-first, 
      query-before-create, structured output), tool usage guidelines, and 
      framework for including `user_context` and `conversation_history`.
   46 *   **`executor.py`**: Implemented `ToolExecutor` responsible for:
   47     *   Receiving LLM's tool call requests.
   48     *   Validating parameters against defined Pydantic schemas.
   49     *   Executing the corresponding tool's `execute` method.
   50     *   Returning standardized `ToolResult` objects.
   51 *   **`composer.py`**: Implemented `ResponseComposer` to:
   52     *   Consolidate LLM's text response and tool execution results.
   53     *   Extract and format data for frontend UI components (widgets)
   54     *   Report any errors from tool execution.
   55     *   Manage `requires_confirmation` and `confirmation_data` for 
      sensitive operations.
   56 
   57 ### 1.5. Chat API Update (`backend/app/api/v1/chat.py`)
   58 
   59 *   **`chat` Endpoint**: Transformed the synchronous `/chat` endpoin
      to an agent-mode API. It now orchestrates the LLM call with tools, 
      executes tools if suggested by the LLM, and composes a rich 
      `ChatResponse` that includes text, widgets, and tool results.
   60 *   **`chat_stream` Endpoint**: Updated the streaming `/chat/stream`
      endpoint to support real-time agent interactions. It processes 
      streaming `StreamChunk` events, executes tools as they are identifie
      and streams back text, tool statuses, and widget data to the fronten
   61 *   **`confirm_action` Endpoint**: Added a placeholder endpoint for 
      handling user confirmation of high-risk actions.
   62 *   **Helper Functions**: Refined `get_user_context`, 
      `get_conversation_history`, and `save_chat_message` to correctly 
      interact with the database, handling `UUID` for `session_id` 
      (conversation_id) and ensuring conversation history is properly 
      formatted for the LLM.
   63 
   64 ## 2. Mobile (Flutter) Implementation
   65 
   66 The mobile application's frontend was updated to dynamically render 
      content generated by the new agent workflow.
   67 
   68 ### 2.1. Data Models (`mobile/lib/data/models/chat_message_
      model.dart`)
   69 
   70 *   **`ChatMessageModel` Extension**: Extended the `ChatMessageModel
      to include new fields for agent workflow support: `widgets`, 
      `toolResults`, `hasErrors`, `errors`, `requiresConfirmation`, and 
      `confirmationData`.
   71 *   **New Models**: Defined supporting Pydantic models for frontend 
      consumption:
   72     *   `WidgetPayload`: Describes a UI widget to be rendered (type 
      and data).
   73     *   `ToolResultModel`: Mirrors the backend's `ToolResult` for 
      display.
   74     *   `ErrorInfo`: Captures tool execution errors and suggestions.
   75     *   `ConfirmationData`: Provides details for user confirmation 
      prompts.
   76 *   **Code Generation**: Ran `flutter pub run build_runner build 
      --delete-conflicting-outputs` to regenerate 
      `chat_message_model.g.dart` to reflect these changes.
   77 
   78 ### 2.2. API Interaction (`mobile/lib/data/repositories/chat
      _repository.dart`)
   79 
   80 *   **Stream Event Parsing**: Updated the `_parseEvent` method in 
      `ChatRepository` to correctly interpret and dispatch the new 
      `ChatStreamEvent` types (`TextEvent`, `ToolStartEvent`, 
      `ToolResultEvent`, `WidgetEvent`, `DoneEvent`, `UnknownEvent`) 
      received via SSE from the backend.
   81 
   82 ### 2.3. Dynamic UI Components (`mobile/lib/presentation/widgets/`)
   83 
   84 *   **`AgentMessageRenderer.dart`**: Created this central widget to 
      dynamically render different UI components based on the `widgets` 
      field in `ChatMessageModel`. It handles:
   85     *   Displaying standard text content.
   86     *   Delegating rendering to specific widgets (`TaskCard`, 
      `KnowledgeCard`, `TaskListWidget`, `PlanCard`).
   87     *   Displaying error messages received from the backend.
   88     *   Presenting interactive confirmation cards for high-risk 
      operations.
   89 *   **`TaskCard.dart`**: Implemented a dedicated widget for renderin
      individual task cards, displaying task details, status, and offering
      quick actions.
   90 *   **`KnowledgeCard.dart`**: Implemented a dedicated widget for 
      rendering knowledge node cards, showing title, summary, tags, and 
      mastery level.
   91 *   **`TaskListWidget.dart`**: Created a widget to display a list of
      tasks, typically used for batch task creation results.
   92 *   **`PlanCard.dart`**: Created a widget to display plan summaries.
   93 *   **`ConfirmationDialog.dart`**: Developed a reusable dialog for 
      user confirmation of potentially high-impact actions, displaying 
      action details and a preview of changes.
   94 
   95 ## Conclusion
   96 
   97 The implementation successfully establishes a robust AI Agent 
      Workflow, transforming the Sparkle application from a 
      "chat-as-a-service" model to a "chat-as-an-action" paradigm. This 
      foundation allows the AI tutor to directly manipulate learning tasks
      knowledge structures, and plans, significantly enhancing its 
      capability and user interaction model.
---

## 1. 设计概述

### 1.1 核心转变

| 维度 | 传统模式 | Agent Workflow 模式 |
|------|----------|---------------------|
| 交互流程 | 用户提问 → LLM 生成文本 → 用户阅读 | 用户意图 → LLM 规划 → 调用工具 → 系统执行 → 结构化结果 |
| LLM 角色 | 文本生成器 | 系统操作员（拥有"手脚"） |
| 输出形式 | Markdown 文本 | 结构化数据 + UI 组件 |
| 前端职责 | 渲染文本气泡 | 渲染文本 + 动态组件（卡片、图表等） |

### 1.2 设计原则

1. **原子性（Atomic）**：一个工具只做一件事
2. **幂等性（Idempotent）**：重复调用产生相同结果，利用现有 `idempotency.py`
3. **可观测性（Observable）**：工具执行结果可追踪、可调试
4. **渐进式（Progressive）**：MVP 阶段先实现核心工具，后续迭代扩展

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Flutter Mobile App                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  ChatScreen  │  │  TaskScreen  │  │  KnowledgeMapScreen      │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              AgentMessageRenderer (新增)                      │  │
│  │  - 解析 message.widget_type                                   │  │
│  │  - 分发到对应 Widget（TaskCard, PlanCard, KnowledgeNode...）  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │ HTTP/SSE
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                              │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    API Layer (/api/v1/chat)                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Orchestration Layer (新增)                        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │ │
│  │  │ ToolRouter  │  │ ToolExecutor│  │ ResponseComposer    │   │ │
│  │  │ (意图路由)   │  │ (工具执行)   │  │ (结果组装)          │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Tool Registry (元能力层)                          │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │ │
│  │  │ TaskTools    │ │ PlanTools   │ │ KnowledgeTools│          │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Service Layer (现有)                              │ │
│  │  task_service │ plan_service │ knowledge_service │ ...        │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Database (PostgreSQL + pgvector)                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 元能力层设计（Tool Registry）

### 3.1 目录结构

在 `backend/app/` 下新增 `tools/` 目录：

```
backend/app/
├── tools/
│   ├── __init__.py
│   ├── base.py              # 工具基类和注册器
│   ├── schemas.py           # 工具参数和结果的 Pydantic Schema
│   ├── task_tools.py        # 任务相关工具
│   ├── plan_tools.py        # 计划相关工具
│   ├── knowledge_tools.py   # 知识图谱相关工具
│   └── registry.py          # 工具注册表
```

### 3.2 工具基类定义

**文件：`backend/app/tools/base.py`**

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from enum import Enum

class ToolCategory(str, Enum):
    """工具分类"""
    TASK = "task"
    PLAN = "plan"
    KNOWLEDGE = "knowledge"
    QUERY = "query"
    
class ToolResult(BaseModel):
    """工具执行结果的统一格式"""
    success: bool
    tool_name: str
    data: Optional[Dict[str, Any]] = None      # 成功时返回的数据
    error_message: Optional[str] = None         # 失败时的错误信息
    widget_type: Optional[str] = None           # 前端渲染组件类型
    widget_data: Optional[Dict[str, Any]] = None  # 组件渲染数据
    suggestion: Optional[str] = None            # LLM 可用于自我修正的建议
    
class BaseTool(ABC):
    """
    工具基类
    所有元能力工具必须继承此类
    """
    name: str                           # 工具名称（唯一标识）
    description: str                    # 工具描述（LLM 理解用途）
    category: ToolCategory              # 工具分类
    parameters_schema: Type[BaseModel]  # 参数 Schema（Pydantic Model）
    requires_confirmation: bool = False # 是否需要用户确认（高风险操作）
    
    @abstractmethod
    async def execute(
        self, 
        params: BaseModel, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        """
        执行工具逻辑
        
        Args:
            params: 经过验证的参数对象
            user_id: 当前用户 ID
            db_session: 数据库会话
            
        Returns:
            ToolResult: 统一格式的执行结果
        """
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式
        兼容 Qwen/DeepSeek 的 OpenAI 兼容 API
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema.model_json_schema()
            }
        }
```

### 3.3 工具参数 Schema 定义

**文件：`backend/app/tools/schemas.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

# ============ 任务工具参数 ============

class TaskType(str, Enum):
    LEARNING = "learning"
    TRAINING = "training"
    ERROR_FIX = "error_fix"
    REFLECTION = "reflection"
    SOCIAL = "social"
    PLANNING = "planning"

class CreateTaskParams(BaseModel):
    """创建任务的参数"""
    title: str = Field(..., description="任务标题", max_length=100)
    description: Optional[str] = Field(None, description="任务详细描述")
    task_type: TaskType = Field(default=TaskType.LEARNING, description="任务类型")
    estimated_minutes: Optional[int] = Field(None, description="预估时长（分钟）", ge=1, le=480)
    subject_id: Optional[str] = Field(None, description="关联科目 ID")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    priority: int = Field(default=2, description="优先级 1-5，5 最高", ge=1, le=5)

class UpdateTaskStatusParams(BaseModel):
    """更新任务状态的参数"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="新状态: pending/in_progress/completed/abandoned")
    actual_minutes: Optional[int] = Field(None, description="实际耗时（完成时填写）")

class BatchCreateTasksParams(BaseModel):
    """批量创建任务的参数"""
    tasks: List[CreateTaskParams] = Field(..., description="任务列表", min_length=1, max_length=10)

# ============ 计划工具参数 ============

class PlanType(str, Enum):
    SPRINT = "sprint"    # 考试冲刺
    GROWTH = "growth"    # 长期成长

class CreatePlanParams(BaseModel):
    """创建计划的参数"""
    title: str = Field(..., description="计划名称")
    plan_type: PlanType = Field(..., description="计划类型")
    subject_id: Optional[str] = Field(None, description="关联科目 ID")
    target_date: Optional[datetime] = Field(None, description="目标日期（冲刺计划必填）")
    target_mastery: Optional[float] = Field(None, description="目标掌握度 0-1", ge=0, le=1)
    description: Optional[str] = Field(None, description="计划描述")

class GenerateTasksForPlanParams(BaseModel):
    """为计划生成任务的参数"""
    plan_id: str = Field(..., description="计划 ID")
    topic: str = Field(..., description="学习主题/知识点")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    task_count: int = Field(default=5, description="生成任务数量", ge=1, le=10)

# ============ 知识图谱工具参数 ============

class CreateKnowledgeNodeParams(BaseModel):
    """创建知识节点的参数"""
    title: str = Field(..., description="知识点标题")
    summary: str = Field(..., description="知识点摘要/核心内容")
    subject_id: Optional[str] = Field(None, description="所属科目 ID")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    parent_node_id: Optional[str] = Field(None, description="父节点 ID（用于构建层级）")

class LinkNodesParams(BaseModel):
    """关联知识节点的参数"""
    source_node_id: str = Field(..., description="源节点 ID")
    target_node_id: str = Field(..., description="目标节点 ID")
    relation_type: str = Field(..., description="关系类型: prerequisite/related/derived")

class QueryKnowledgeParams(BaseModel):
    """查询知识图谱的参数"""
    query: str = Field(..., description="搜索关键词或语义查询")
    subject_id: Optional[str] = Field(None, description="限定科目范围")
    limit: int = Field(default=10, description="返回结果数量", ge=1, le=50)
    use_vector_search: bool = Field(default=True, description="是否使用向量语义搜索")

# ============ 查询工具参数 ============

class GetUserContextParams(BaseModel):
    """获取用户上下文的参数"""
    include_recent_tasks: bool = Field(default=True, description="是否包含近期任务")
    include_active_plans: bool = Field(default=True, description="是否包含进行中的计划")
    include_error_records: bool = Field(default=False, description="是否包含错题记录")
    days_range: int = Field(default=7, description="查询天数范围", ge=1, le=30)
```

### 3.4 具体工具实现

**文件：`backend/app/tools/task_tools.py`**

```python
from typing import Any
from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreateTaskParams, UpdateTaskStatusParams, BatchCreateTasksParams
from app.services.task_service import TaskService

class CreateTaskTool(BaseTool):
    """创建单个学习任务"""
    name = "create_task"
    description = """创建一个新的学习任务卡片。
    当用户表达想要做某件学习相关的事情时使用，例如：
    - "帮我创建一个复习高数的任务"
    - "我想学习 Python，帮我规划一下"
    - "把刚才讨论的内容整理成任务"
    """
    category = ToolCategory.TASK
    parameters_schema = CreateTaskParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: CreateTaskParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            task_service = TaskService(db_session)
            task = await task_service.create_task(
                user_id=user_id,
                title=params.title,
                description=params.description,
                task_type=params.task_type.value,
                estimated_minutes=params.estimated_minutes,
                subject_id=params.subject_id,
                due_date=params.due_date,
                priority=params.priority
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_id": str(task.id)},
                widget_type="task_card",  # 前端渲染类型
                widget_data={
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "type": task.task_type,
                    "status": task.status,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat()
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请检查参数是否正确，或稍后重试"
            )

class UpdateTaskStatusTool(BaseTool):
    """更新任务状态"""
    name = "update_task_status"
    description = """更新任务的状态。
    当用户表达完成、放弃或开始某个任务时使用，例如：
    - "我完成了这个任务"
    - "把这个任务标记为进行中"
    - "放弃这个任务"
    """
    category = ToolCategory.TASK
    parameters_schema = UpdateTaskStatusParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: UpdateTaskStatusParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            task_service = TaskService(db_session)
            task = await task_service.update_task_status(
                task_id=params.task_id,
                user_id=user_id,
                status=params.status,
                actual_minutes=params.actual_minutes
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_id": str(task.id), "new_status": task.status},
                widget_type="task_card",
                widget_data={
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status,
                    "actual_minutes": task.actual_minutes
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请确认任务 ID 是否正确"
            )

class BatchCreateTasksTool(BaseTool):
    """批量创建任务"""
    name = "batch_create_tasks"
    description = """批量创建多个学习任务。
    当需要一次性创建多个相关任务时使用，例如：
    - "帮我制定本周的学习计划，包含 5 个任务"
    - "把这个知识点拆解成几个小任务"
    """
    category = ToolCategory.TASK
    parameters_schema = BatchCreateTasksParams
    requires_confirmation = True  # 批量操作需要确认
    
    async def execute(
        self, 
        params: BatchCreateTasksParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            task_service = TaskService(db_session)
            created_tasks = []
            
            for task_params in params.tasks:
                task = await task_service.create_task(
                    user_id=user_id,
                    **task_params.model_dump()
                )
                created_tasks.append({
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.task_type,
                    "status": task.status
                })
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_count": len(created_tasks)},
                widget_type="task_list",  # 任务列表组件
                widget_data={"tasks": created_tasks}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="批量创建失败，请检查参数或减少任务数量后重试"
            )
```

**文件：`backend/app/tools/knowledge_tools.py`**

```python
from typing import Any
from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreateKnowledgeNodeParams, LinkNodesParams, QueryKnowledgeParams
from app.services.knowledge_service import KnowledgeService

class CreateKnowledgeNodeTool(BaseTool):
    """创建知识节点（生成学习卡片的基础）"""
    name = "create_knowledge_node"
    description = """在知识星图中创建一个新的知识节点/学习卡片。
    当用户想要记录或整理知识点时使用，例如：
    - "把刚才聊的 Rust 所有权整理成卡片"
    - "帮我创建一个关于傅里叶变换的知识点"
    - "记录这个概念到我的知识库"
    """
    category = ToolCategory.KNOWLEDGE
    parameters_schema = CreateKnowledgeNodeParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: CreateKnowledgeNodeParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            knowledge_service = KnowledgeService(db_session)
            node = await knowledge_service.create_node(
                user_id=user_id,
                title=params.title,
                summary=params.summary,
                subject_id=params.subject_id,
                tags=params.tags,
                parent_node_id=params.parent_node_id
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"node_id": str(node.id)},
                widget_type="knowledge_card",
                widget_data={
                    "id": str(node.id),
                    "title": node.title,
                    "summary": node.summary,
                    "tags": node.tags,
                    "mastery_level": node.mastery_level,
                    "created_at": node.created_at.isoformat()
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="创建知识节点失败，请检查标题是否重复"
            )

class QueryKnowledgeTool(BaseTool):
    """查询知识图谱（LLM 先看再动）"""
    name = "query_knowledge"
    description = """搜索用户的知识图谱，查找已有的知识点。
    在创建新知识点之前，先调用此工具检查是否已存在相关内容。
    也可用于回答用户关于已学内容的问题。
    """
    category = ToolCategory.QUERY
    parameters_schema = QueryKnowledgeParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: QueryKnowledgeParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            knowledge_service = KnowledgeService(db_session)
            
            if params.use_vector_search:
                nodes = await knowledge_service.semantic_search(
                    user_id=user_id,
                    query=params.query,
                    subject_id=params.subject_id,
                    limit=params.limit
                )
            else:
                nodes = await knowledge_service.keyword_search(
                    user_id=user_id,
                    query=params.query,
                    subject_id=params.subject_id,
                    limit=params.limit
                )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "count": len(nodes),
                    "nodes": [
                        {
                            "id": str(n.id),
                            "title": n.title,
                            "summary": n.summary[:200],  # 截断摘要
                            "mastery_level": n.mastery_level
                        }
                        for n in nodes
                    ]
                },
                widget_type=None  # 查询结果不直接渲染，供 LLM 参考
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e)
            )

class LinkNodesTool(BaseTool):
    """关联知识节点"""
    name = "link_knowledge_nodes"
    description = """建立两个知识点之间的关联关系。
    关系类型包括：
    - prerequisite: A 是 B 的前置知识
    - related: A 和 B 相关
    - derived: B 由 A 推导/衍生
    """
    category = ToolCategory.KNOWLEDGE
    parameters_schema = LinkNodesParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: LinkNodesParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            knowledge_service = KnowledgeService(db_session)
            edge = await knowledge_service.create_edge(
                user_id=user_id,
                source_id=params.source_node_id,
                target_id=params.target_node_id,
                relation_type=params.relation_type
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "edge_id": str(edge.id),
                    "source_id": params.source_node_id,
                    "target_id": params.target_node_id,
                    "relation": params.relation_type
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请确认两个节点 ID 是否正确"
            )
```

### 3.5 工具注册表

**文件：`backend/app/tools/registry.py`**

```python
from typing import Dict, List, Optional
from .base import BaseTool, ToolCategory

# 导入所有工具
from .task_tools import CreateTaskTool, UpdateTaskStatusTool, BatchCreateTasksTool
from .knowledge_tools import CreateKnowledgeNodeTool, QueryKnowledgeTool, LinkNodesTool

class ToolRegistry:
    """
    工具注册表
    管理所有可用工具，提供查询和调用接口
    """
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_all_tools()
        return cls._instance
    
    def _register_all_tools(self):
        """注册所有工具"""
        tools = [
            # 任务工具
            CreateTaskTool(),
            UpdateTaskStatusTool(),
            BatchCreateTasksTool(),
            # 知识图谱工具
            CreateKnowledgeNodeTool(),
            QueryKnowledgeTool(),
            LinkNodesTool(),
            # TODO: 添加更多工具
            # CreatePlanTool(),
            # GenerateTasksForPlanTool(),
            # GetUserContextTool(),
        ]
        for tool in tools:
            self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """根据名称获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """按分类获取工具"""
        return [t for t in self._tools.values() if t.category == category]
    
    def get_openai_tools_schema(self) -> List[dict]:
        """
        获取所有工具的 OpenAI Function Calling 格式
        用于发送给 LLM
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """
        生成工具描述文本，用于 System Prompt
        """
        lines = ["你可以使用以下工具来帮助用户：\n"]
        for tool in self._tools.values():
            lines.append(f"- **{tool.name}**: {tool.description}")
        return "\n".join(lines)

# 全局单例
tool_registry = ToolRegistry()
```

---

## 4. 智能编排层设计（Orchestration Layer）

### 4.1 目录结构

```
backend/app/
├── orchestration/
│   ├── __init__.py
│   ├── router.py          # 意图路由器
│   ├── executor.py        # 工具执行器
│   ├── composer.py        # 响应组装器
│   └── prompts.py         # System Prompt 模板
```

### 4.2 System Prompt 设计

**文件：`backend/app/orchestration/prompts.py`**

```python
AGENT_SYSTEM_PROMPT = """你是 Sparkle 星火的 AI 学习导师，一个智能学习助手。

## 你的角色
你不仅能回答问题，更重要的是你能**通过工具直接操作系统**，帮助用户管理学习任务、构建知识图谱、制定学习计划。

## 核心原则
1. **行动优先**：当用户表达想要做某事时（如"帮我创建任务"、"整理成卡片"），不要只是文字建议，而是直接调用工具执行
2. **先查后建**：创建知识节点前，先用 query_knowledge 检查是否已有相关内容
3. **结构化输出**：尽可能通过工具生成结构化数据（任务卡片、知识卡片），而非纯文本

## 意图识别指南
根据用户意图选择合适的工具：

| 用户意图 | 应调用的工具 |
|---------|------------|
| 创建/规划/安排学习任务 | create_task 或 batch_create_tasks |
| 整理/记录/总结知识点 | create_knowledge_node |
| 查找已学过的内容 | query_knowledge |
| 关联两个知识点 | link_knowledge_nodes |
| 标记任务完成/放弃 | update_task_status |

## 工具调用规范
- 参数必须符合 Schema 定义
- 如果缺少必要信息，先向用户询问
- 工具调用失败时，根据 suggestion 尝试修正

## 当前用户上下文
{user_context}

## 对话历史
{conversation_history}
"""

def build_system_prompt(user_context: dict, conversation_history: str) -> str:
    """构建完整的 System Prompt"""
    return AGENT_SYSTEM_PROMPT.format(
        user_context=format_user_context(user_context),
        conversation_history=conversation_history
    )

def format_user_context(context: dict) -> str:
    """格式化用户上下文"""
    lines = []
    if context.get("recent_tasks"):
        lines.append(f"近期任务: {len(context['recent_tasks'])} 个")
    if context.get("active_plans"):
        lines.append(f"进行中计划: {len(context['active_plans'])} 个")
    if context.get("flame_level"):
        lines.append(f"火花等级: {context['flame_level']}")
    return "\n".join(lines) if lines else "暂无上下文信息"
```

### 4.3 工具执行器

**文件：`backend/app/orchestration/executor.py`**

```python
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from app.tools.registry import tool_registry
from app.tools.base import ToolResult

class ToolExecutor:
    """
    工具执行器
    负责解析 LLM 的工具调用请求并执行
    """
    
    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        """
        执行单个工具调用
        
        Args:
            tool_name: 工具名称
            arguments: LLM 提供的参数（JSON）
            user_id: 用户 ID
            db_session: 数据库会话
            
        Returns:
            ToolResult: 执行结果
        """
        tool = tool_registry.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"未知工具: {tool_name}",
                suggestion="请检查工具名称是否正确"
            )
        
        # 验证参数
        try:
            validated_params = tool.parameters_schema(**arguments)
        except ValidationError as e:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"参数验证失败: {str(e)}",
                suggestion="请检查参数格式是否正确"
            )
        
        # 执行工具
        result = await tool.execute(validated_params, user_id, db_session)
        return result
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        user_id: str,
        db_session: Any
    ) -> List[ToolResult]:
        """
        批量执行工具调用（按顺序）
        
        Args:
            tool_calls: 工具调用列表，格式为 OpenAI function_call
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        results = []
        for call in tool_calls:
            result = await self.execute_tool_call(
                tool_name=call["function"]["name"],
                arguments=call["function"]["arguments"],
                user_id=user_id,
                db_session=db_session
            )
            results.append(result)
        return results
```

### 4.4 响应组装器

**文件：`backend/app/orchestration/composer.py`**

```python
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult

class ResponseComposer:
    """
    响应组装器
    将 LLM 文本回复和工具执行结果组装成统一的 API 响应
    """
    
    def compose_response(
        self,
        llm_text: str,
        tool_results: List[ToolResult],
        requires_confirmation: bool = False,
        confirmation_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        组装最终响应
        
        Args:
            llm_text: LLM 生成的文本回复
            tool_results: 工具执行结果列表
            requires_confirmation: 是否需要用户确认
            confirmation_data: 确认操作的数据
            
        Returns:
            统一的 API 响应结构
        """
        # 提取所有需要渲染的组件
        widgets = []
        for result in tool_results:
            if result.success and result.widget_type:
                widgets.append({
                    "type": result.widget_type,
                    "data": result.widget_data
                })
        
        # 提取错误信息
        errors = [
            {
                "tool": r.tool_name,
                "message": r.error_message,
                "suggestion": r.suggestion
            }
            for r in tool_results if not r.success
        ]
        
        response = {
            "message": llm_text,
            "widgets": widgets,
            "tool_results": [r.model_dump() for r in tool_results],
            "has_errors": len(errors) > 0,
            "errors": errors if errors else None,
        }
        
        # 需要用户确认的操作
        if requires_confirmation:
            response["requires_confirmation"] = True
            response["confirmation_data"] = confirmation_data
        
        return response
```

---

## 5. 后端接口设计

### 5.1 Chat API 升级

**文件：`backend/app/api/v1/chat.py`（升级）**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.llm_service import LLMService
from app.tools.registry import tool_registry
from app.orchestration.executor import ToolExecutor
from app.orchestration.composer import ResponseComposer
from app.orchestration.prompts import build_system_prompt

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # 前端传递的额外上下文

class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    widgets: List[Dict[str, Any]] = []        # 需要渲染的组件列表
    tool_results: List[Dict[str, Any]] = []   # 工具执行结果
    has_errors: bool = False
    errors: Optional[List[Dict[str, str]]] = None
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Agent 模式的聊天接口
    支持工具调用和结构化响应
    """
    llm_service = LLMService()
    tool_executor = ToolExecutor()
    response_composer = ResponseComposer()
    
    # 1. 构建上下文和对话历史
    user_context = await get_user_context(db, current_user.id)
    conversation_history = await get_conversation_history(
        db, current_user.id, request.conversation_id
    )
    
    # 2. 构建 System Prompt
    system_prompt = build_system_prompt(user_context, conversation_history)
    
    # 3. 调用 LLM（带工具定义）
    llm_response = await llm_service.chat_with_tools(
        system_prompt=system_prompt,
        user_message=request.message,
        tools=tool_registry.get_openai_tools_schema()
    )
    
    # 4. 处理工具调用
    tool_results = []
    if llm_response.tool_calls:
        tool_results = await tool_executor.execute_tool_calls(
            tool_calls=llm_response.tool_calls,
            user_id=str(current_user.id),
            db_session=db
        )
        
        # 5. 将工具执行结果反馈给 LLM，获取最终回复
        final_response = await llm_service.continue_with_tool_results(
            tool_results=[r.model_dump() for r in tool_results]
        )
        llm_text = final_response.content
    else:
        llm_text = llm_response.content
    
    # 6. 组装响应
    response = response_composer.compose_response(
        llm_text=llm_text,
        tool_results=tool_results
    )
    
    # 7. 保存消息到数据库
    await save_chat_message(
        db=db,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        user_message=request.message,
        assistant_message=llm_text,
        tool_results=tool_results
    )
    
    return ChatResponse(**response, conversation_id=request.conversation_id or "new")

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式聊天接口（SSE）
    适合长回复场景，实时展示 LLM 生成内容
    """
    async def event_generator():
        llm_service = LLMService()
        tool_executor = ToolExecutor()
        
        # 构建上下文
        user_context = await get_user_context(db, current_user.id)
        system_prompt = build_system_prompt(user_context, "")
        
        # 流式调用 LLM
        async for chunk in llm_service.chat_stream_with_tools(
            system_prompt=system_prompt,
            user_message=request.message,
            tools=tool_registry.get_openai_tools_schema()
        ):
            if chunk.type == "text":
                # 文本块：直接发送
                yield f"data: {json.dumps({'type': 'text', 'content': chunk.content})}\n\n"
            
            elif chunk.type == "tool_call":
                # 工具调用：执行并返回结果
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': chunk.tool_name})}\n\n"
                
                result = await tool_executor.execute_tool_call(
                    tool_name=chunk.tool_name,
                    arguments=chunk.arguments,
                    user_id=str(current_user.id),
                    db_session=db
                )
                
                yield f"data: {json.dumps({'type': 'tool_result', 'result': result.model_dump()})}\n\n"
                
                # 如果有 widget，单独发送
                if result.widget_type:
                    yield f"data: {json.dumps({'type': 'widget', 'widget_type': result.widget_type, 'widget_data': result.widget_data})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/chat/confirm")
async def confirm_action(
    action_id: str,
    confirmed: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    确认高风险操作
    用于需要用户二次确认的工具调用
    """
    # 从缓存/数据库获取待确认的操作
    pending_action = await get_pending_action(action_id)
    
    if not pending_action:
        raise HTTPException(status_code=404, detail="操作不存在或已过期")
    
    if not confirmed:
        return {"status": "cancelled", "message": "操作已取消"}
    
    # 执行实际操作
    tool_executor = ToolExecutor()
    result = await tool_executor.execute_tool_call(
        tool_name=pending_action["tool_name"],
        arguments=pending_action["arguments"],
        user_id=str(current_user.id),
        db_session=db
    )
    
    return {"status": "executed", "result": result.model_dump()}

# ============ 辅助函数 ============

async def get_user_context(db: AsyncSession, user_id: str) -> dict:
    """获取用户上下文信息"""
    # TODO: 实现获取用户近期任务、计划等
    return {
        "recent_tasks": [],
        "active_plans": [],
        "flame_level": 1
    }

async def get_conversation_history(
    db: AsyncSession, 
    user_id: str, 
    conversation_id: Optional[str]
) -> str:
    """获取对话历史"""
    # TODO: 从数据库获取历史消息
    return ""

async def save_chat_message(
    db: AsyncSession,
    user_id: str,
    conversation_id: Optional[str],
    user_message: str,
    assistant_message: str,
    tool_results: list
):
    """保存聊天消息"""
    # TODO: 实现消息持久化
    pass

async def get_pending_action(action_id: str) -> Optional[dict]:
    """获取待确认的操作"""
    # TODO: 从 Redis 或数据库获取
    return None
```

### 5.2 LLM Service 升级

**文件：`backend/app/services/llm_service.py`（新增方法）**

```python
from typing import List, Dict, Any, AsyncIterator, Optional
from dataclasses import dataclass
import httpx
import json

@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[List[Dict]] = None
    finish_reason: str = "stop"

@dataclass
class StreamChunk:
    type: str  # "text" | "tool_call"
    content: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Optional[Dict] = None

class LLMService:
    """
    LLM 服务
    支持工具调用（Function Calling）
    """
    
    def __init__(self):
        self.api_base = settings.LLM_API_BASE_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL_NAME
    
    async def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        带工具调用的聊天
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            tools: OpenAI 格式的工具定义
            conversation_history: 对话历史
            
        Returns:
            LLMResponse: 包含文本和工具调用的响应
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"  # 让模型自动决定是否调用工具
                },
                timeout=60.0
            )
            
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            
            return LLMResponse(
                content=message.get("content", ""),
                tool_calls=message.get("tool_calls"),
                finish_reason=choice["finish_reason"]
            )
    
    async def continue_with_tool_results(
        self,
        tool_results: List[Dict]
    ) -> LLMResponse:
        """
        将工具执行结果反馈给 LLM，获取最终回复
        """
        # 构建工具结果消息
        tool_messages = []
        for result in tool_results:
            tool_messages.append({
                "role": "tool",
                "tool_call_id": result.get("tool_call_id", ""),
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        # TODO: 继续对话获取最终回复
        # 这里需要维护对话状态
        pass
    
    async def chat_stream_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]]
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天（支持工具调用）
        
        Yields:
            StreamChunk: 文本块或工具调用
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                },
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        
                        # 文本内容
                        if "content" in delta and delta["content"]:
                            yield StreamChunk(
                                type="text",
                                content=delta["content"]
                            )
                        
                        # 工具调用
                        if "tool_calls" in delta:
                            for tool_call in delta["tool_calls"]:
                                if "function" in tool_call:
                                    yield StreamChunk(
                                        type="tool_call",
                                        tool_name=tool_call["function"]["name"],
                                        arguments=json.loads(
                                            tool_call["function"]["arguments"]
                                        )
                                    )
                    except json.JSONDecodeError:
                        continue
```

---

## 6. 前端协议设计

### 6.1 数据模型扩展

**文件：`mobile/lib/data/models/chat_message_model.dart`（升级）**

```dart
import 'package:json_annotation/json_annotation.dart';

part 'chat_message_model.g.dart';

@JsonSerializable()
class ChatMessageModel {
  final String id;
  final String conversationId;
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime createdAt;
  
  // 新增：Agent Workflow 支持
  final List<WidgetPayload>? widgets;        // 需要渲染的组件
  final List<ToolResultModel>? toolResults;  // 工具执行结果
  final bool? hasErrors;
  final List<ErrorInfo>? errors;
  final bool? requiresConfirmation;
  final ConfirmationData? confirmationData;

  ChatMessageModel({
    required this.id,
    required this.conversationId,
    required this.role,
    required this.content,
    required this.createdAt,
    this.widgets,
    this.toolResults,
    this.hasErrors,
    this.errors,
    this.requiresConfirmation,
    this.confirmationData,
  });

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) =>
      _$ChatMessageModelFromJson(json);

  Map<String, dynamic> toJson() => _$ChatMessageModelToJson(this);
}

@JsonSerializable()
class WidgetPayload {
  final String type;  // 'task_card' | 'knowledge_card' | 'task_list' | 'plan_card'
  final Map<String, dynamic> data;

  WidgetPayload({required this.type, required this.data});

  factory WidgetPayload.fromJson(Map<String, dynamic> json) =>
      _$WidgetPayloadFromJson(json);

  Map<String, dynamic> toJson() => _$WidgetPayloadToJson(this);
}

@JsonSerializable()
class ToolResultModel {
  final bool success;
  final String toolName;
  final Map<String, dynamic>? data;
  final String? errorMessage;
  final String? widgetType;
  final Map<String, dynamic>? widgetData;

  ToolResultModel({
    required this.success,
    required this.toolName,
    this.data,
    this.errorMessage,
    this.widgetType,
    this.widgetData,
  });

  factory ToolResultModel.fromJson(Map<String, dynamic> json) =>
      _$ToolResultModelFromJson(json);

  Map<String, dynamic> toJson() => _$ToolResultModelToJson(this);
}

@JsonSerializable()
class ErrorInfo {
  final String tool;
  final String message;
  final String? suggestion;

  ErrorInfo({required this.tool, required this.message, this.suggestion});

  factory ErrorInfo.fromJson(Map<String, dynamic> json) =>
      _$ErrorInfoFromJson(json);
}

@JsonSerializable()
class ConfirmationData {
  final String actionId;
  final String toolName;
  final String description;
  final Map<String, dynamic> preview;

  ConfirmationData({
    required this.actionId,
    required this.toolName,
    required this.description,
    required this.preview,
  });

  factory ConfirmationData.fromJson(Map<String, dynamic> json) =>
      _$ConfirmationDataFromJson(json);
}
```

### 6.2 动态组件渲染器

**文件：`mobile/lib/presentation/widgets/agent_message_renderer.dart`（新增）**

```dart
import 'package:flutter/material.dart';
import '../../data/models/chat_message_model.dart';
import 'task_card.dart';
import 'knowledge_card.dart';
import 'confirmation_dialog.dart';

/// Agent 消息渲染器
/// 根据消息中的 widgets 字段动态渲染不同类型的组件
class AgentMessageRenderer extends StatelessWidget {
  final ChatMessageModel message;
  final Function(String taskId)? onTaskAction;
  final Function(String actionId, bool confirmed)? onConfirmation;

  const AgentMessageRenderer({
    Key? key,
    required this.message,
    this.onTaskAction,
    this.onConfirmation,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 1. 文本内容（如果有）
        if (message.content.isNotEmpty)
          _buildTextBubble(context, message.content),
        
        // 2. 渲染所有 widgets
        if (message.widgets != null && message.widgets!.isNotEmpty)
          ...message.widgets!.map((widget) => _buildWidget(context, widget)),
        
        // 3. 错误提示（如果有）
        if (message.hasErrors == true && message.errors != null)
          _buildErrorCard(context, message.errors!),
        
        // 4. 确认操作（如果需要）
        if (message.requiresConfirmation == true && 
            message.confirmationData != null)
          _buildConfirmationCard(context, message.confirmationData!),
      ],
    );
  }

  Widget _buildTextBubble(BuildContext context, String text) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(text),
    );
  }

  Widget _buildWidget(BuildContext context, WidgetPayload widget) {
    switch (widget.type) {
      case 'task_card':
        return TaskCard(
          data: widget.data,
          onAction: onTaskAction,
        );
      
      case 'knowledge_card':
        return KnowledgeCard(data: widget.data);
      
      case 'task_list':
        return TaskListWidget(tasks: widget.data['tasks'] as List);
      
      case 'plan_card':
        return PlanCard(data: widget.data);
      
      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(widget);
    }
  }

  Widget _buildErrorCard(BuildContext context, List<ErrorInfo> errors) {
    return Card(
      color: Theme.of(context).colorScheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.warning_amber, 
                     color: Theme.of(context).colorScheme.error),
                const SizedBox(width: 8),
                const Text('操作遇到问题'),
              ],
            ),
            const SizedBox(height: 8),
            ...errors.map((e) => Text('• ${e.message}')),
          ],
        ),
      ),
    );
  }

  Widget _buildConfirmationCard(
    BuildContext context, 
    ConfirmationData data
  ) {
    return Card(
      color: Theme.of(context).colorScheme.tertiaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '需要确认',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(data.description),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => onConfirmation?.call(data.actionId, false),
                  child: const Text('取消'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => onConfirmation?.call(data.actionId, true),
                  child: const Text('确认执行'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUnknownWidget(WidgetPayload widget) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Text('Unknown widget type: ${widget.type}'),
      ),
    );
  }
}
```

### 6.3 任务卡片组件

**文件：`mobile/lib/presentation/widgets/task_card.dart`（升级）**

```dart
import 'package:flutter/material.dart';

/// 任务卡片组件
/// 用于在聊天中显示 AI 生成的任务
class TaskCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final Function(String taskId)? onAction;

  const TaskCard({
    Key? key,
    required this.data,
    this.onAction,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final taskId = data['id'] as String;
    final title = data['title'] as String;
    final description = data['description'] as String?;
    final taskType = data['type'] as String;
    final status = data['status'] as String;
    final estimatedMinutes = data['estimated_minutes'] as int?;
    final priority = data['priority'] as int? ?? 2;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: () => onAction?.call(taskId),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题行
              Row(
                children: [
                  _buildTypeIcon(taskType),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _buildStatusChip(context, status),
                ],
              ),
              
              // 描述
              if (description != null && description.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              
              // 底部信息
              const SizedBox(height: 12),
              Row(
                children: [
                  // 预估时间
                  if (estimatedMinutes != null) ...[
                    Icon(Icons.timer_outlined, size: 16, 
                         color: Theme.of(context).hintColor),
                    const SizedBox(width: 4),
                    Text('$estimatedMinutes 分钟'),
                    const SizedBox(width: 16),
                  ],
                  // 优先级
                  ...List.generate(
                    priority,
                    (_) => Icon(Icons.star, size: 14, color: Colors.amber),
                  ),
                  const Spacer(),
                  // 快捷操作按钮
                  if (status == 'pending')
                    TextButton.icon(
                      onPressed: () => _startTask(context, taskId),
                      icon: const Icon(Icons.play_arrow, size: 18),
                      label: const Text('开始'),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypeIcon(String type) {
    IconData icon;
    Color color;
    
    switch (type) {
      case 'learning':
        icon = Icons.menu_book;
        color = Colors.blue;
        break;
      case 'training':
        icon = Icons.fitness_center;
        color = Colors.orange;
        break;
      case 'error_fix':
        icon = Icons.bug_report;
        color = Colors.red;
        break;
      case 'reflection':
        icon = Icons.psychology;
        color = Colors.purple;
        break;
      default:
        icon = Icons.task_alt;
        color = Colors.grey;
    }
    
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(icon, size: 20, color: color),
    );
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    Color color;
    String label;
    
    switch (status) {
      case 'pending':
        color = Colors.grey;
        label = '待办';
        break;
      case 'in_progress':
        color = Colors.blue;
        label = '进行中';
        break;
      case 'completed':
        color = Colors.green;
        label = '已完成';
        break;
      case 'abandoned':
        color = Colors.red;
        label = '已放弃';
        break;
      default:
        color = Colors.grey;
        label = status;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }

  void _startTask(BuildContext context, String taskId) {
    // TODO: 导航到任务执行页面
  }
}
```

### 6.4 SSE 流式消息处理

**文件：`mobile/lib/data/repositories/chat_repository.dart`（升级）**

```dart
import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import '../models/chat_message_model.dart';

class ChatRepository {
  final Dio _dio;

  ChatRepository(this._dio);

  /// 流式聊天（SSE）
  Stream<ChatStreamEvent> chatStream(String message, String? conversationId) {
    final controller = StreamController<ChatStreamEvent>();
    
    _startSSEConnection(
      message: message,
      conversationId: conversationId,
      controller: controller,
    );
    
    return controller.stream;
  }

  Future<void> _startSSEConnection({
    required String message,
    String? conversationId,
    required StreamController<ChatStreamEvent> controller,
  }) async {
    try {
      final response = await _dio.post<ResponseBody>(
        '/api/v1/chat/stream',
        data: {
          'message': message,
          'conversation_id': conversationId,
        },
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );

      final stream = response.data!.stream;
      String buffer = '';

      await for (final chunk in stream.transform(utf8.decoder)) {
        buffer += chunk;
        
        // 解析 SSE 事件
        while (buffer.contains('\n\n')) {
          final eventEnd = buffer.indexOf('\n\n');
          final eventStr = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);
          
          if (eventStr.startsWith('data: ')) {
            final dataStr = eventStr.substring(6);
            try {
              final data = json.decode(dataStr);
              controller.add(_parseEvent(data));
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
      
      controller.close();
    } catch (e) {
      controller.addError(e);
      controller.close();
    }
  }

  ChatStreamEvent _parseEvent(Map<String, dynamic> data) {
    final type = data['type'] as String;
    
    switch (type) {
      case 'text':
        return TextEvent(content: data['content'] as String);
      
      case 'tool_start':
        return ToolStartEvent(toolName: data['tool'] as String);
      
      case 'tool_result':
        return ToolResultEvent(
          result: ToolResultModel.fromJson(data['result']),
        );
      
      case 'widget':
        return WidgetEvent(
          widgetType: data['widget_type'] as String,
          widgetData: data['widget_data'] as Map<String, dynamic>,
        );
      
      case 'done':
        return DoneEvent();
      
      default:
        return UnknownEvent(data: data);
    }
  }
}

// 事件类型定义
abstract class ChatStreamEvent {}

class TextEvent extends ChatStreamEvent {
  final String content;
  TextEvent({required this.content});
}

class ToolStartEvent extends ChatStreamEvent {
  final String toolName;
  ToolStartEvent({required this.toolName});
}

class ToolResultEvent extends ChatStreamEvent {
  final ToolResultModel result;
  ToolResultEvent({required this.result});
}

class WidgetEvent extends ChatStreamEvent {
  final String widgetType;
  final Map<String, dynamic> widgetData;
  WidgetEvent({required this.widgetType, required this.widgetData});
}

class DoneEvent extends ChatStreamEvent {}

class UnknownEvent extends ChatStreamEvent {
  final Map<String, dynamic> data;
  UnknownEvent({required this.data});
}
```

---

## 7. 错误处理与反馈循环

### 7.1 自我修正机制

当工具执行失败时，将错误信息反馈给 LLM 进行自我修正：

```python
# backend/app/orchestration/error_handler.py

class AgentErrorHandler:
    """
    Agent 错误处理器
    实现自我修正和人机协作
    """
    
    MAX_RETRY_COUNT = 2  # 最大重试次数
    
    async def handle_tool_error(
        self,
        llm_service: LLMService,
        tool_result: ToolResult,
        original_request: dict,
        retry_count: int = 0
    ) -> ToolResult:
        """
        处理工具执行错误，尝试自我修正
        """
        if retry_count >= self.MAX_RETRY_COUNT:
            return tool_result  # 超过重试次数，返回原始错误
        
        # 构建修正提示
        correction_prompt = f"""
工具 {tool_result.tool_name} 执行失败。
错误信息：{tool_result.error_message}
建议：{tool_result.suggestion}

请分析错误原因，并使用修正后的参数重新调用工具。
原始参数：{json.dumps(original_request, ensure_ascii=False)}
"""
        
        # 让 LLM 分析并重试
        retry_response = await llm_service.chat_with_tools(
            system_prompt="你是一个工具调用修正助手，请根据错误信息修正参数后重新调用。",
            user_message=correction_prompt,
            tools=tool_registry.get_openai_tools_schema()
        )
        
        if retry_response.tool_calls:
            # 递归执行修正后的调用
            return await self.handle_tool_error(
                llm_service,
                await execute_tool_call(...),
                retry_response.tool_calls[0],
                retry_count + 1
            )
        
        return tool_result
```

### 7.2 高风险操作确认流程

```
┌──────────────────────────────────────────────────────────────┐
│                      User Request                            │
│        "删除所有已完成的任务"                                 │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    LLM 意图识别                              │
│        识别为高风险操作: batch_delete_tasks                  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                 工具检查 requires_confirmation               │
│                       返回 Draft 状态                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    前端显示确认卡片                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ⚠️ 需要确认                                           │ │
│  │  即将删除 15 个已完成任务，此操作不可撤销               │ │
│  │                                                        │ │
│  │              [取消]         [确认删除]                  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                              │
             ┌────────────────┴────────────────┐
             │                                 │
        用户取消                           用户确认
             │                                 │
             ▼                                 ▼
    返回 "操作已取消"               POST /chat/confirm
                                              │
                                              ▼
                                      执行实际删除
                                              │
                                              ▼
                                    返回执行结果
```

---

## 8. 实施路线图

### 8.1 阶段划分（MVP 优先）

| 阶段 | 时间 | 目标 | 交付物 |
|------|------|------|--------|
| **Phase 1** | Week 1-2 | 基础框架搭建 | 工具基类、注册表、基础 API |
| **Phase 2** | Week 3-4 | 核心工具实现 | 任务工具 + 知识图谱工具 |
| **Phase 3** | Week 5-6 | 前端适配 | 动态组件渲染、SSE 支持 |
| **Phase 4** | Week 7-8 | 完善与测试 | 错误处理、确认流程、集成测试 |

### 8.2 Phase 1 详细任务

**Week 1：后端框架**

| 任务 | 负责人 | 预估时间 |
|------|--------|----------|
| 创建 `tools/` 目录结构 | - | 0.5h |
| 实现 `BaseTool` 基类 | - | 2h |
| 实现 `ToolRegistry` | - | 2h |
| 实现 `ToolExecutor` | - | 3h |
| 单元测试 | - | 2h |

**Week 2：API 升级**

| 任务 | 负责人 | 预估时间 |
|------|--------|----------|
| 升级 `LLMService` 支持 Function Calling | - | 4h |
| 升级 `/chat` API | - | 3h |
| 实现 `/chat/stream` SSE 接口 | - | 4h |
| API 测试 | - | 2h |

### 8.3 MVP 优先级工具列表

**P0（必须实现）**
- `create_task` - 创建任务
- `create_knowledge_node` - 创建知识卡片
- `query_knowledge` - 查询知识图谱

**P1（应该实现）**
- `update_task_status` - 更新任务状态
- `batch_create_tasks` - 批量创建任务
- `link_knowledge_nodes` - 关联知识节点

**P2（可以延后）**
- `create_plan` - 创建计划
- `generate_tasks_for_plan` - 为计划生成任务
- `get_user_context` - 获取用户上下文

### 8.4 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 工具调用不稳定 | 高 | 1. 使用宽容模式解析 2. 增加重试机制 3. 回退到纯文本响应 |
| Flutter 代码生成问题 | 中 | 提前测试 `build_runner`，文档化常见问题 |
| SSE 连接管理复杂 | 中 | 使用成熟的 SSE 库，增加重连逻辑 |
| MVP 时间紧张 | 高 | 严格按 P0/P1/P2 优先级执行，非核心功能延后 |

---

## 附录 A：完整目录结构变更

```
backend/app/
├── tools/                    # [新增] 元能力层
│   ├── __init__.py
│   ├── base.py              # 工具基类
│   ├── schemas.py           # 参数 Schema
│   ├── task_tools.py        # 任务工具
│   ├── knowledge_tools.py   # 知识图谱工具
│   ├── plan_tools.py        # 计划工具（P2）
│   └── registry.py          # 工具注册表
├── orchestration/            # [新增] 编排层
│   ├── __init__.py
│   ├── prompts.py           # System Prompt
│   ├── executor.py          # 工具执行器
│   ├── composer.py          # 响应组装器
│   └── error_handler.py     # 错误处理
├── api/v1/
│   └── chat.py              # [升级] 支持工具调用
├── services/
│   └── llm_service.py       # [升级] 支持 Function Calling

mobile/lib/
├── data/models/
│   └── chat_message_model.dart  # [升级] 新增 widgets 字段
├── presentation/widgets/
│   ├── agent_message_renderer.dart  # [新增] 动态组件渲染
│   ├── task_card.dart               # [升级] 支持卡片数据
│   └── knowledge_card.dart          # [新增] 知识卡片
├── data/repositories/
│   └── chat_repository.dart         # [升级] SSE 支持
```

---

## 附录 B：接口速查表

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/chat` | POST | Agent 聊天（工具调用） |
| `/api/v1/chat/stream` | POST | 流式聊天（SSE） |
| `/api/v1/chat/confirm` | POST | 确认高风险操作 |

---

**文档版本**: v1.0  
**最后更新**: 2025-01-XX  
**作者**: Claude + Sparkle Team