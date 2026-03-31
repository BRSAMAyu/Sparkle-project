这是一份经过系统整合的《Sparkle v2.3 改版实施指南：全能主页与认知棱镜》。

这份文档将我们之前讨论的“高密度仪表盘”、“全能输入岛”、“心境天气”以及“认知棱镜”整合成了一个完整的通过逻辑，不仅包含UI设计，还包含了背后的业务逻辑和技术实现路径。

你可以直接将其作为 **PRD (产品需求文档)** 分发给 Cursor/Windsurf 等 AI 编程助手，或直接发给开发团队。

---

# Sparkle v2.3 改版实施指南：全能主页与认知棱镜

**版本**：v2.3 (Conversational Dashboard & Cognitive Prism)
**文档状态**：Ready for Implementation
**核心目标**：将 App 从“工具集合”重构为“AI 驱动的成长伴侣”。主页不再是列表，而是对话的起点和状态的驾驶舱。

---

## 1. 核心设计理念 (Design Philosophy)

1. **Conversational First (对话优先)**：所有的输入（任务、想法、吐槽、求助）统一通过底部的“全能输入岛”进入，由 AI 意图识别分流。
2. **Dashboard Visualization (仪表盘化)**：主页采用 Bento Grid（便当盒）网格布局，高密度展示“当前状态”，而非让用户在列表中迷失。
3. **Introspective (内省)**：不仅记录“做了什么”，更通过【认知棱镜】记录“为什么没做好”，关注行为模式。

---

## 2. 🏠 新版主页架构 (The Cockpit)

### 2.1 视觉风格 (Visual Identity)

* **主题**：Deep Space (深空)。背景为深蓝至黑色的径向渐变，模拟星空。
* **材质**：Glassmorphism (毛玻璃)。所有卡片具备半透明、模糊背景和微弱的边框光晕。
* **动效**：Rive 动画驱动的“心境天气”和“专注火苗”。

### 2.2 布局结构 (Layout Stack)

主页由上至下分为三个层级：

#### A. 顶部：心境天气系统 (Inner Weather Header)

* **功能**：即时反馈用户的“长期计划健康度”与“今日状态”。
* **交互**：背景全宽动态天气，前景展示今日核心聚焦。
* **天气映射逻辑**：
* ☀️ **晴空**：本周计划完成率 > 80% 且今日无逾期。
* ☁️ **多云/雾**：计划进度落后，或连续 2 天未复习。
* 🌧️ **雷雨**：检测到临近 DDL 且未开始，或“焦虑”闪念增多。
* ☄️ **流星雨**：今日专注时长突破历史记录 / 攻克高难度节点。



#### B. 中部：Bento Grid 仪表盘 (Body)

采用 `StaggeredGridView` (交错网格) 布局，包含以下模块：

1. **🔥 专注入口 (Deep Dive Card)** [占 2x2 或 2x1]
* 展示：实时燃烧的火苗（强度随今日时长变化）。
* 文案：“今日专注 3h 20m”。
* *Action*：点击直接进入【专注驾驶舱】（无缝转场）。


2. **💎 认知棱镜 (Cognitive Prism Card)** [占 1x1]
* 展示：本周生成的“定式关键词”（如 #畏难逃避）。
* 状态：如果有新的 AI 归因报告生成，卡片边缘呼吸闪烁。
* *Action*：点击查看详细归因图表。


3. **🏃 冲刺进度 (Sprint Card)** [占 1x1]
* 展示：当前“期末冲刺”或“考研计划”的环形进度条 + 剩余天数。


4. **📝 下一步行动 (Next Actions)** [占 2xN]
* 展示：紧凑列表，仅显示**未来 3 小时内**需要做的 Top 3 任务。
* 设计：极简条目，不显示 checkbox，点击标记完成。



#### C. 底部：全能输入岛 (The Omni-Bar)

* **位置**：底部悬浮，替代传统的 BottomNavigationBar。
* **形态**：常态为胶囊型输入框，输入时展开。
* **功能**：所有交互的唯一入口。

---

## 3. 核心功能详述

### 3.1 🕹️ 全能输入岛 (Omni-Bar) 交互逻辑

这是 v2.3 的灵魂。用户无需思考“我要去哪里创建任务”，只需思考“我想说什么”。

**交互流程**：

1. **Input**: 用户在底部输入文字或语音（例如：“烦死了，高数作业写不完”）。
2. **Classifier (AI 分流)**：前端先调用轻量级分类接口（或 Regex），后端通过 LLM 确认意图。
3. **Action Dispatch (分发)**：
* **Case A: 闪念/情绪** (意图：吐槽、焦虑、灵感)
* *UI 反馈*：输入框泛起紫色光晕，文字化作粒子被吸入主页的【认知棱镜】卡片。
* *Result*：存入 `cognitive_fragments` 表，不打断用户流程。


* **Case B: 任务指令** (意图：创建待办)
* *UI 反馈*：生成一张 Task Card 飞入【下一步行动】区域。
* *Result*：解析时间、标题，写入 `tasks` 表。


* **Case C: 复杂辅导** (意图：提问、规划、知识)
* *UI 反馈*：界面向上推移，底部扩展为全屏聊天窗口 (Chat Screen)。
* *Result*：开启多轮对话模式。





### 3.2 🧘 专注模式：驾驶舱 (Deep Dive Cockpit)

点击主页火苗进入。这是一个**“停留型”**界面，旨在替代物理书桌上的工具。

* **HUD 风格**：全黑背景，高对比度荧光绿/蓝线条。
* **组件 (Widgets)**：
* **量子时钟**：视觉化的倒计时圆环。
* **AI 伴读 (Sidekick)**：侧边微型输入框。输入“贝叶斯定理”，弹出一个半屏卡片解释概念。*（用完即走，不进入聊天页）*
* **数字结界**：
* 开关：一键屏蔽通知（调用原生 DND API）。
* 白噪音：内置雨声/咖啡馆声音混合器。





### 3.3 🧠 认知棱镜 (Cognitive Prism)

* **隐式捕捉**：若任务 `Actual Time` > `Estimated Time` * 1.5，系统自动记录一次“规划偏差”。
* **显式捕捉**：通过 Omni-Bar 收集的“吐槽”。
* **归因卡片 (Weekly Report)**：
* AI 每周日晚生成。
* 内容结构：
* **定式名称**：🚫 “最后时刻的赌徒”
* **症状**：总在 DDL 前 1 小时极限操作。
* **处方**：下周尝试“5分钟起步法”。





---

## 4. 技术实施路径 (Implementation Guide)

### Phase 1: 基础设施 (Backend & Database)

1. **Schema 更新**：
* 创建 `cognitive_fragments` (存储闪念/行为数据)。
* 创建 `behavior_patterns` (存储 AI 分析后的定式)。
* 更新 `user_preferences` 以存储天气映射阈值。


2. **API 开发**：
* `POST /api/v1/omnibar/dispatch`: 核心分流接口。接收文本，返回 `action_type` (CAPSULE | TASK | CHAT) 和处理结果。
* `GET /api/v1/dashboard/status`: 聚合接口，一次性返回天气状态、火苗强度、Top 3 任务、冲刺进度。



### Phase 2: 全能输入岛 (Frontend - Mobile)

1. **Omni-Bar Widget**：
* 实现复杂的动画状态机（Idle, Typing, Loading, Success_Animation）。
* 集成 `Speech-to-Text` 插件。


2. **意图响应逻辑**：
* 前端需要处理“粒子吸入动画”（针对闪念）和“卡片飞入动画”（针对任务）。



### Phase 3: 仪表盘与专注模式 (Frontend - Mobile)

1. **Bento Grid 布局**：
* 使用 `flutter_staggered_grid_view` 包。
* 封装通用的 `GlassCard` 组件（统一毛玻璃效果）。


2. **天气动效**：
* 引入 `rive` 或 `lottie` 资源文件。
* 编写 `WeatherService` 前端逻辑，根据后端返回的状态切换动画。


3. **专注驾驶舱**：
* 实现白噪音播放器 (`audioplayers`)。
* 调用原生平台通道 (Platform Channels) 控制勿扰模式。



### Phase 4: 认知棱镜逻辑 (AI Logic)

1. **Prompt Engineering**：
* 编写用于“意图分类”的 Prompt (Router Agent)。
* 编写用于“行为归因”的 Prompt (Psychology Agent)。


2. **定时任务**：
* 设置每周日的 Crontab，触发归因分析并生成 Push 通知。



---

## 5. 开发 Prompt 参考

*你可以使用以下 Prompt 指导 Agent 编写代码：*

**针对主页 UI 开发：**

> "请基于 Flutter 编写一个新的 `HomeScreen`。背景使用深色径向渐变。布局使用 `flutter_staggered_grid_view` 实现 Bento Grid。顶部是一个名为 `WeatherHeader` 的组件，中部包含 `FocusCard`, `PrismCard`, `SprintCard`。底部放置一个自定义的悬浮 `OmniBar` 组件。所有卡片需应用 Glassmorphism 风格。"

**针对 Omni-Bar 后端逻辑：**

> "请在 FastAPI 中实现 `/omnibar/dispatch` 接口。它接收用户文本，使用 LLM 判断意图。如果意图是情感宣泄，存入 `CognitiveService` 并返回 'CAPSULE'；如果是明确的任务指令（如'明天提醒我...'），调用 `TaskService` 创建任务并返回 'TASK'；其他情况返回 'CHAT'。"

---

此方案已准备好进入开发阶段。建议优先完成 **Backend Schema** 和 **Omni-Bar** 的核心交互，这是新体验的基础。Sparkle v2.3 Implementation Progress Report

  ✅ Completed Tasks

  Backend Development (Phase 1: Infrastructure)

   1. User Model Update: Modified backend/app/models/user.py to add the weather_preferences column, which will store
      user-specific thresholds for the "Inner Weather" system.
   2. OmniBarService Implementation: Created backend/app/services/omnibar_service.py. This service is responsible
      for:
       * Receiving user text input.
       * Utilizing LLMService to classify the intent of the input (as a TASK, CAPSULE, or CHAT).
       * Dispatching the request to the appropriate backend service (TaskService for task creation, CognitiveService
         for capturing cognitive fragments).
   3. DashboardService Implementation: Created backend/app/services/dashboard_service.py. This service aggregates
      various user-specific data to present a holistic view for the dashboard, including:
       * A simplified calculation of the "Inner Weather" status.
       * Retrieval of flame levels and brightness from the User model.
       * Fetching details of active sprint plans.
       * Retrieving the top 3 pending tasks ("Next Actions").
   4. OmniBar API Endpoint: Created backend/app/api/v1/omnibar.py to expose the omnibar/dispatch endpoint, allowing
      the frontend to send user input for classification and processing.
   5. Dashboard API Endpoint: Created backend/app/api/v1/dashboard.py to expose the dashboard/status endpoint,
      providing the frontend with all necessary data to render the new dashboard.
   6. API Router Registration: Updated backend/app/api/v1/router.py to include the newly created omnibar and
      dashboard API routers, making the new endpoints accessible.

  Mobile Frontend Setup (Phase 2 Initial Steps)

   1. `flutter_staggered_grid_view` Dependency: Added flutter_staggered_grid_view to mobile/pubspec.yaml to enable
      the flexible Bento Grid layout for the new home screen.
   2. API Endpoints Update: Modified mobile/lib/core/network/api_endpoints.dart to include constants for
      omnibarDispatch and dashboardStatus, ensuring the frontend can correctly reference the new backend endpoints.
   3. OmniBarRepository Implementation: Created mobile/lib/data/repositories/omnibar_repository.dart, providing a
      clean interface for the frontend to interact with the backend's OmniBar API.
   4. DashboardRepository Implementation: Created mobile/lib/data/repositories/dashboard_repository.dart, offering a
      dedicated repository for fetching dashboard status data from the backend.
   5. OmniBar Widget: Created mobile/lib/presentation/widgets/home/omnibar.dart. This widget includes a text input
      field, basic loading state, and logic to call the OmniBarRepository and handle the returned action type
      (navigate to chat, show task created message, or show capsule captured message).
   6. BentoGrid Widget: Created mobile/lib/presentation/widgets/home/bento_grid.dart, a reusable widget that
      leverages flutter_staggered_grid_view to facilitate the flexible grid layout of dashboard cards.

  📝 Remaining Tasks

  Mobile Frontend Development (Phase 2: Omni-Bar & Dashboard Setup)

   1. Implement `DashboardProvider`:
       * Create a Riverpod provider (mobile/lib/presentation/providers/dashboard_provider.dart) that uses
         DashboardRepository to fetch and manage the dashboard status data. This provider will expose the weather,
         flame status, sprint progress, and next actions to other widgets.
   2. Implement `WeatherHeader` Widget:
       * Create mobile/lib/presentation/widgets/home/weather_header.dart.
       * This widget will consume the weather data from the DashboardProvider to dynamically display the "Inner
         Weather" status. Initially, it will use static icons/colors mapped to the weather types (sunny, cloudy,
         rainy).
   3. Refactor `HomeScreen` (`mobile/lib/presentation/screens/home/home_screen.dart`):
       * Remove Existing Dashboard Content: Replace the current _DashboardTab's CustomScrollView content.
       * Integrate `BentoGrid`: Use the newly created BentoGrid widget as the primary layout for the dashboard.
       * Place `WeatherHeader`: Position the WeatherHeader prominently at the top of the dashboard.
       * Create Placeholder Cards: Implement the core dashboard cards as simple widgets and place them within the
         BentoGrid. These will include:
           * Focus Entry Card: Placeholder for the "Deep Dive Card" (flame animation, focus time).
           * Cognitive Prism Card: Placeholder for the "Cognitive Prism" (weekly patterns, status).
           * Sprint Progress Card: Placeholder for displaying active sprint plan progress.
           * Next Actions Card: Placeholder for displaying the top 3 upcoming tasks.
       * Position `OmniBar`: Integrate the OmniBar widget at the bottom of the Scaffold, ensuring it floats above
         other content and acts as the primary input. A Stack widget can be used within the Scaffold's body to
         achieve this floating effect.
  Mobile Frontend Development (Phase 3: Dashboard & Focus Mode UI Enhancements)

   1. Create Detailed Dashboard Cards:
       * `FocusCard` Widget: Develop a dedicated widget to visualize the "burning flame" animation (using Lottie if
         Rive is too complex for initial integration) and display the user's daily focus time.
       * `PrismCard` Widget: Create a widget to display the "Cognitive Prism" insights, such as "定式关键词" (fixed
         patterns) and a breathing animation for new AI attribution reports.
       * `SprintCard` Widget: Enhance the sprint card to show a circular progress bar for the active sprint plan and
         remaining days until the target date.
       * `NextActionsCard` Widget: Implement a compact list to display the top 3 pending tasks, allowing quick
         interactions (e.g., tap to mark complete).
   2. OmniBar Animations: Add more refined animations for the OmniBar to expand, collapse, and show loading/success
      states, aligning with the "Capsule泛起紫色光晕" and "Task Card飞入" descriptions.
   3. Native DND Integration (Stretch Goal): Explore and implement platform channels to control the device's "Do Not
      Disturb" (DND) mode when the user enters the "Focus Cockpit."
   4. Rive/Lottie Animations for Weather/Flame (Stretch Goal): Integrate more complex Rive or Lottie animations for
      the "Inner Weather Header" and "Focus Flame" to enhance visual appeal.

  This structured approach ensures that the core functionality of Sparkle v2.3 is built incrementally, allowing for
  continuous testing and refinement.


  