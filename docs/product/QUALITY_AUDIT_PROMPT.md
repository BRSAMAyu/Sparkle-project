# Sparkle 全系统深度质量审查 — 提示词

## 背景

你是一名独立的高级技术审计师，负责对 Sparkle（星火）项目进行全面深度质量审查。这不是合规性检查，而是站在用户和产品角度判断：**这个系统是否真正好用、稳定、值得信赖**。

之前的审查已产生了一些初步发现（见下方"已知问题"），但那些结论可能存在假阳性或遗漏。你的任务是**独立验证每一个发现，并发现之前没看到的问题**。

## 项目概况

Sparkle 是一个面向大学生的 AI 成长操作系统，采用三层架构：
- **Flutter**（前端 732 个 dart 文件）— 用户界面
- **Go Gateway**（24 个 go 文件 + 16 个中间件）— 认证、路由、缓存、WebSocket
- **Python Engine**（319+ 个 py 文件）— AI 逻辑、RAG、工具调用、双核路由

核心产品概念：
- **双核架构**: 执行核（目标→计划→任务→反馈）+ 认知核（用户画像→记忆→认知棱镜→个性化支持）
- **7 阶段成长环**: Sense → Clarify → Plan → Execute → Reflect → Reinforce → Adapt
- **Aurora 自适应内核**: 6 状态模型（sensing, calibrated, risk_found, needs_confirm, calibration_available, cooling_down）
- **校准系统**: 用户可以纠正 Aurora 的判断，系统生成校准收据（calibration receipt）

关键用户路径：用户发送消息 → Flutter WebSocket → Go Gateway → gRPC → Python Orchestrator → LLM → 流式响应返回

## 审查维度与具体要求

### 维度 1: Aurora 用户体验真实质量

不要检查代码是否存在，而是判断**用户实际感受到的体验是否真的好**。

**1.1 记忆系统的自然度**
- 读取 `backend/app/services/memory_service.py`，找到记忆在聊天中被引用的路径
- 读取 `backend/app/orchestration/orchestrator.py` 中记忆如何注入 prompt
- 判断：当 Aurora 说"我记得你之前说过..."时，这个引用是否自然？还是模板化的？具体的判断依据是什么？
- 读取 Flutter 侧 `memory_reference_receipt.dart`，判断记忆收据展示给用户的信息密度是否合适

**1.2 校准收据的诚实度**
- 读取 `backend/app/orchestration/aurora_calibration_processor.py`（或相关文件），理解校准处理后生成的 receipt 内容
- 判断：校准收据的"what_changed"、"why_changed"、"next_time"三个字段的内容是真实的 AI 反思，还是固定的模板文字？
- 在 `backend/app/orchestration/orchestrator.py` 中搜索 `calibration_receipt`，追踪收据是如何生成并传给前端的

**1.3 语言原则的实际执行**
- 读取 `backend/app/orchestration/aurora_language_principles.py`
- 读取 `backend/app/orchestration/prompt_assembler.py` 或类似文件，看语言原则如何注入到 LLM prompt 中
- 判断：这些原则是真正影响了 LLM 输出，还是只是写了但没被有效使用？
- 搜索测试文件验证：是否有测试确保 LLM 不会使用禁语（如"你真棒"、"加油"等）？

**1.4 校正闭环的完整性**
- 从用户点击校正 chip → Flutter 发送 `AuroraCorrectionPayload` → Go Gateway 转发 → Python 处理 → 返回 receipt → Flutter 展示，追踪完整链路
- 判断：用户校正后，下一次对话是否真的体现了校正效果？还是校正只是被记录但没有影响后续行为？
- 读取 `backend/app/state_aggregator/service.py`，检查校正信号是否进入了用户状态聚合

### 维度 2: 成长环路实现深度

**2.1 七阶段是否真的闭环**
- 对每个阶段（Sense → Clarify → Plan → Execute → Reflect → Reinforce → Adapt），读取对应的 Python 服务代码
- 判断：每个阶段是否有明确的输入/输出定义？是否有阶段间的衔接逻辑？
- 重点关注：Reflect（反思）和 Adapt（适应）阶段——这两个最容易做成空壳

**2.2 双核路由的实际决策质量**
- 读取 `backend/app/orchestration/dual_core_router.py`
- 读取路由的评分机制：`emotional_block=9.0, procrastination=8.0, cognitive_mode=7.0` 等权重
- 判断：这些权重是硬编码还是有自适应机制？在不同用户场景下（考试冲刺 vs 日常学习 vs 低谷期），路由决策是否真的不同？
- 读取 `backend/app/orchestration/ux_envelope.py`，判断路由结果是否真的改变了 UX 呈现

### 维度 3: 跨会话连续性

**3.1 回归体验的真实质量**
- 读取 Flutter 侧 `comeback_banner.dart`
- 读取 Python 侧生成回归上下文的服务代码（搜索 `comeback` 或 `return_context`）
- 判断：用户关闭 app 8 小时后回来，看到的上下文是否真的有用？还是泛泛的"欢迎回来"？
- 检查 4 个档位（silent_resume <30min, light_resume <8h, personalized_return, checkpoint_debrief >3d）是否有真实的差异化内容

**3.2 长期状态持久性**
- 检查 Aurora 核心会话状态（FSM）的存储方式：Redis TTL 30min
- 检查用户偏好、性格模型、学习风格等长期状态是否有持久化
- 判断：如果 Redis 突然重启，用户体验会退化到什么程度？

### 维度 4: 生产稳定性边界情况

**4.1 错误恢复的用户感知**
- 读取 `backend/gateway/internal/handler/chat_orchestrator.go` 和 `chat_orchestrator_chatflow.go`
- 当 Python gRPC 后端在流式传输中途崩溃时，用户在 Flutter 端看到什么？是友好的提示还是技术错误信息？
- 检查 `backend/app/core/safe_error_messages.py` 的错误映射是否完整

**4.2 WebSocket 连接管理**
- 读取 `chat_orchestrator_connections.go`
- 每个 WS 连接会启动几个 goroutine？是否有泄漏可能？
- 连接断开时是否正确清理所有资源？

**4.3 监控告警覆盖**
- 读取 `monitoring/sparkle_slo_alerts.yml`、`sparkle_production_baseline_alerts.yml`、`sparkle_t6_slo_alerts.yml`
- 列出当前所有告警规则
- 判断：是否有用户可感知的故障场景（如校正失败、Aurora 状态卡死、会话锁超时）没有被任何告警覆盖？

### 维度 5: Flutter 前端完成度

**5.1 可访问性**
- 搜索 `mobile/lib/features/chat/` 中所有 `GestureDetector`、`InkWell`、`IconButton` 等交互元素
- 搜索对应的 `Semantics(` 调用
- 计算：有多少交互元素缺少 Semantics 标签？
- 搜索 `liveRegion: true`，列出所有动态内容区域中缺少 liveRegion 的地方

**5.2 设计系统合规**
- 搜索 `mobile/lib/features/home/` 中所有 `Colors.white` 和 `Colors.black`
- 列出每个实例的文件名、行号、使用场景（背景色/文字色/混合色）
- 判断哪些是合理的（视觉特效混合色），哪些是真正的违规

**5.3 状态管理健壮性**
- 检查 Chat provider 中从后台恢复时是否有状态刷新逻辑
- 检查 `CalibrationReceiptChip` 的 dismiss 状态是否持久化（本地 state vs provider/disk）

## 已知问题（需要验证或推翻）

以下问题来自之前的初步审查，**你必须独立验证每个结论是否正确**：

1. `status_awareness_bar.dart` 中 3 处 chip minHeight 为 32dp（应为 44dp）
2. `calibration_receipt_chip.dart` 的 dismiss 状态仅用本地 `setState`，不持久化
3. `aurora_receipt_chip.dart` 完全没有 dismiss 机制
4. Home 模块有 23 处 `Colors.white` 硬编码
5. 监控缺少校准环路失败和熔断器打开的告警
6. 限流器 Redis 不可用时直接拒绝所有请求（无本地降级）
7. Aurora 核心会话状态仅 Redis 30min TTL（无 PostgreSQL 备份）

## 输出要求

**重要：你必须把完整报告写入文件，不要只返回文本。**

1. 把主报告写入 `docs/product/QUALITY_AUDIT_DEEP_REPORT.md`
2. 对每个你验证的问题，给出以下结构：

```markdown
### [FIX-XX] 问题描述

**验证结论**: 确认 / 推翻 / 部分正确

**问题背景**: 为什么这是一个问题，对用户的影响是什么

**当前代码**:
- 文件: `path/to/file.dart`
- 行号: XXX
- 具体代码片段

**修复建议**:
- 具体改成什么
- 需要注意的边界情况

**优先级**: P1（阻塞发布）/ P2（近期修复）/ P3（持续改进）
**预估工作量**: XS（<10分钟）/ S（<30分钟）/ M（1-2小时）/ L（半天+）
```

3. 对每个你新发现的问题，使用相同的结构
4. 最后给出一个按优先级排序的行动清单

## 审查原则

1. **只报告真实存在的问题** — 不要猜测，每条发现必须有代码证据（文件路径 + 行号）
2. **假阳性比假阴性更有害** — 如果你不确定一个问题是否存在，标注为"待确认"而不是直接报告
3. **站在用户角度** — 工程上的不完美如果不影响用户体验，优先级应降低
4. **关注影响，不是整洁度** — 代码风格问题不报告，除非它导致了真实的功能缺陷
5. **先验证再报告** — 对每个发现，先 grep/read 确认当前代码状态，再写结论
