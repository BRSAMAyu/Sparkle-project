# Aurora 实现对齐文档

> **日期**: 2026-04-26
> **范围**: 交互式建模 · 第二层交互体 · 前端体验流
> **方法**: 代码级审计（非文档推测），每个判定都有文件+行号证据

---

## 一、总览：三大模块实现状态

| 模块 | 状态 | 一句话 |
|------|------|--------|
| 交互式建模 | ✅ 完整可用 | 从建模启动→建模完成→自动进入规划，全链路通 |
| 第二层交互体（Aurora） | ⚠️ 后端完整，前端有缺口 | 11个API端点中7个未通过Go网关代理 |
| 前端体验流 | ⚠️ 核心可用，入口不够明显 | 状态栏+校准面板+核心会话都工作，但用户发现路径弱 |

---

## 二、交互式建模

### 2.1 建模能否启动？

**判定：✅ FULLY_WORKING**

**证据链：**
1. 前端 `modeling_chat_screen.dart:318` 发送 `aurora_surface: 'aurora_modeling'`
2. 后端 `service.py:73-80` 通过 `AURORA_RUNTIME_MODE_SURFACES` 映射解析 surface
3. `plan_turn()` 执行完整的决策循环：DashboardReadout → DecisionLoop → ChatLayerAdapter
4. 通过标准 WebSocket chatStream 返回，包含 `modeling_complete` 元数据
5. 5个建模域全覆盖：`goal, scope, baseline, time, motivation`

**实际体验：**
- 用户进入 → Aurora 问第一个问题（goal域）→ 用户回答 → Aurora 追问 → ... → 所有域覆盖 → `modeling_complete=true`

### 2.2 多消息并行

**判定：⚠️ PARTIALLY_WORKING**

- 后端支持返回多条消息（`AuroraRuntimeTurnPlan.messages` 是 list）
- `ChatLayerAdapter.render()` 最多3条消息，`multimessage_allowed` 由 wake_policy 控制
- **限制**：多条消息是顺序流式返回的，不是真正的并行（同时展示）

**缺失**：前端没有同时展示多条 Aurora 消息的 UI 组件。消息仍然是一条一条渲染。

### 2.3 主动式（Proactive）

**判定：⚠️ PARTIALLY_WORKING**

**已实现：**
- `schedule_wake` 决策动作（decision_loop.py:25）
- `AuroraWakeScheduler` 可以安排未来唤醒（wake_scheduler.py:40-83）
- Daily startup 消息（service.py:201-301）
- 回归上下文（comeback-context endpoint）

**缺失：**
- 没有找到后台 worker 执行定时唤醒的循环。`schedule_wake` 写入了调度记录，但没有消费者自动触发
- 用户只能通过主动打开 App 看到daily startup，不会被推送通知唤醒

### 2.4 时间感知

**判定：✅ FULLY_WORKING**

- 考前24h 特殊策略（service.py:999-1051）
- 睡眠守卫 23:00-06:00（decision_loop.py:314-322）
- 按冲刺模式区分冷却模板：14d/7d/48h/24h（state.py:649-662）
- 剩余天数影响策略密度（service.py:1729-1733）

### 2.5 状态建模

**判定：✅ FULLY_WORKING**

- `AuroraRuntimeStore` 持久化到 Redis（24h TTL）
- `AuroraState` 跨回合追踪：tensions, intents, threads, activity_profile
- 先前状态在后续回合加载并合并（service.py:638-660）
- 活动档案策略持续累积（service.py:473-476）

### 2.6 自适应工程

**判定：✅ FULLY_WORKING**

- `AuroraDecisionLoop` 通过 LLM 决策（decision_loop.py:806-837）
- 按surface/考试紧迫度设置策略默认值（decision_loop.py:1575-1644）
- 陈旧策略检测触发重新校准（service.py:716-747）
- 策略偏好5轮后持久化（service.py:2270-2349）

---

## 三、前端体验流

### 3.1 标准对话 → Aurora 切换

**判定：⚠️ PARTIALLY_WORKING**

**当前入口路径：**

```
标准对话页面
├── StatusAwarenessBar（顶部状态栏）
│   ├── 折叠状态：显示 "Aurora" 标签 + 一句话状态
│   ├── 轻度展开：显示摘要 + 证据 + 操作按钮
│   └── 深度展开：4个facet卡片（关于你/关于目标/关于现在/关于我的判断）
│
├── ContextualCorrectionBar（AI消息后的修正按钮）
│   ├── 后端有预测选项时 → 显示语义化按钮
│   └── 后端无预测选项时 → 显示固定按钮（方向不对/更短/练习/重新校准）
│
└── 无主动入口
    └── 用户无法从聊天界面主动发起 Aurora 交互
```

**问题：** 用户必须等到状态栏或修正条出现才能与 Aurora 交互。没有明显的"进入 Aurora 模式"按钮。

### 3.2 状态栏6态体验

**判定：✅ FULLY_WORKING**

| 状态 | 颜色 | 展示内容 | 用户操作 |
|------|------|----------|----------|
| `sensing` | 灰色 | "感知中" | 查看详情 |
| `calibrated` | 绿色 | 校准置信度 | 查看详情 |
| `risk_found` | 警告黄 | "发现偏差" | 深度校准 / 查看详情 |
| `needs_confirm` | 信息蓝 | "需要确认" | 深度校准 / 查看详情 |
| `calibration_available` | 品牌色 | "可唤醒校准(X次)" | 唤醒校准 / 快速校准 |
| `cooling_down` | 灰色 | "冷却中(XX分)" | 快速校准 |

### 3.3 校准面板（L1-L2 轻校准）

**判定：✅ FULLY_WORKING**

5步流程全部实现：
1. 观察（Observation）→ 展示 Aurora 观察到的内容
2. 判断（Judgment）→ 展示 Aurora 的判断
3. 不确定性（Uncertainty）→ 承认不确定
4. 建议（Suggestion）→ 给出建议
5. 确认（Confirm）→ 用户选择确认选项

退出后触发 `onConfirm` 回调，刷新 Aurora 状态。

### 3.4 核心会话（L3 深度校准）

**判定：⚠️ 后端完整，网关未通**

**前端实现状态：** FULLY_WORKING（代码完整）
- `aurora_core_session_sheet.dart` 有完整的生命周期管理
- 启动/响应/关闭都调用真实后端
- 多轮对话、预测选项、自由文本输入都实现
- 遥测记录

**但是：** Go 网关只代理了 4/11 个 Aurora 端点。以下端点不通：
- `POST /aurora/core-session/start` ❌
- `POST /aurora/core-session/respond` ❌
- `GET /aurora/core-session/current` ❌
- `POST /aurora/core-session/{id}/close` ❌
- `GET /aurora/predicted-options` ❌
- `POST /aurora/telemetry/chip-selected` ❌
- `GET /aurora/daily-startup` ❌

### 3.5 建模 → 规划桥接

**判定：✅ FULLY_WORKING**

完整流程：
1. Aurora 建模完成 → `modeling_complete=true`
2. 前端自动触发 `_autoStartPlanning()`
3. 显示桥接状态组件："正在生成你的第一份冲刺计划..."
4. 后端接收 `from_modeling_complete=true` 上下文
5. Galaxy 基线 → 难度映射 → 生成计划
6. 导航到计划详情页

---

## 四、后端 API 完整性

### 11个端点状态

| 端点 | Python后端 | Go网关代理 | 前端调用 |
|------|-----------|-----------|---------|
| `GET /control-surface` | ✅ 真实数据 | ✅ | ✅ |
| `GET /modeling-status` | ✅ 真实数据 | ✅ | ✅ |
| `GET /calibration-cards` | ✅ 真实数据 | ✅ | ✅ |
| `POST /calibration-cards/{id}/respond` | ✅ 真实数据 | ✅ | ✅ |
| `GET /daily-startup` | ✅ 真实数据 | ❌ 未代理 | ✅ 有调用代码 |
| `GET /comeback-context` | ✅ 真实数据 | ❌ 未代理 | ✅ 有调用代码 |
| `GET /telemetry/summary` | ✅ 真实数据 | ❌ 未代理 | ✅ 有调用代码 |
| `POST /core-session/start` | ✅ Redis持久化 | ❌ 未代理 | ✅ 有调用代码 |
| `POST /core-session/respond` | ✅ Redis持久化 | ❌ 未代理 | ✅ 有调用代码 |
| `GET /core-session/current` | ✅ Redis持久化 | ❌ 未代理 | ✅ 有调用代码 |
| `POST /core-session/{id}/close` | ✅ Redis持久化 | ❌ 未代理 | ✅ 有调用代码 |
| `GET /predicted-options` | ✅ 动态生成 | ❌ 未代理 | ✅ 有调用代码 |
| `POST /telemetry/chip-selected` | ✅ 写入Redis | ❌ 未代理 | ✅ 有调用代码 |

### 数据来源

| 数据 | 来源 | 是否真实 |
|------|------|---------|
| 4个facet（user/self/scene/goal_model） | ProfileContextService + AuroraRuntimeStore + PostgreSQL | ✅ 真实 |
| 6态band状态 | 根据facet状态实时计算 | ✅ 真实 |
| 预测回复选项 | PredictedReplyOptionEngine 动态生成 | ✅ 真实 |
| 能量级别 L0-L3 | AuroraEnergyStore Redis | ✅ 真实 |
| 唤醒资格 | 配额+冷却策略计算 | ✅ 真实 |

---

## 五、需要完善的事项

### P0 阻塞项

| # | 事项 | 影响 | 工作量 |
|---|------|------|--------|
| 1 | **Go网关代理补全**：将 Aurora 路由组改为通配符 `aurora.Any("/*path", h.proxyWithHeaders)` 或逐个添加9个缺失端点 | L3核心会话、预测选项、遥测全部不可用 | 30分钟 |

### P1 体验缺口

| # | 事项 | 影响 | 工作量 |
|---|------|------|--------|
| 2 | **Aurora主动入口**：在聊天页面添加可发现的 Aurora 入口（如工具栏按钮或长按触发） | 用户无法主动进入Aurora模式 | 2小时 |
| 3 | **唤醒调度执行器**：`schedule_wake` 写入了调度但没有后台消费者执行 | Aurora 无法主动联系用户 | 4小时 |
| 4 | **多消息并行UI**：前端没有同时展示多条Aurora消息的UI组件 | 多消息退化为顺序展示 | 3小时 |

### P2 优化项

| # | 事项 | 工作量 |
|---|------|--------|
| 5 | 状态栏动画打磨（展开/收起过渡更丝滑） | 1小时 |
| 6 | 核心会话退出动画 + 校准结果摘要卡片优化 | 2小时 |
| 7 | 预测选项的 model_write_effect 遥测闭环（前端选择后发送到后端） | 1小时 |
| 8 | 冷却状态下添加"设置提醒"功能 | 2小时 |

---

## 六、已验证的Vision Gap修复状态

Vision Gap修复计划的6个Gap全部已实现：

| Gap | 描述 | 状态 |
|-----|------|------|
| 1 | 建模→规划自动桥接 | ✅ 完整实现（modeling_chat_screen.dart + orchestrator.py） |
| 2 | Galaxy基线→规划难度 | ✅ 完整实现（_mastery_to_difficulty + _classify_baseline_from_galaxy） |
| 3 | 成就信号→AI上下文 | ✅ 完整实现（achievement_signals 字段 + _extract_achievement_signals） |
| 4 | 动机域建模 | ✅ 完整实现（motivation 已加入 CORE_MODELING_DOMAINS） |
| 5 | 决策循环选择性感知 | ✅ 刚激活（_infer_action_hint + _ACTION_CONTEXT_MASK） |
| 6 | 信息张力重要性说明 | ✅ 完整实现（_DOMAIN_IMPORTANCE + _enrich_tensions_with_importance） |

---

*文档结束。所有判定基于代码审计，非文档推测。*
