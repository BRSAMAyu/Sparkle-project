# Sparkle R12 二次全项目深度审查 Prompt

> **用途**: 交给 coding agent 进行独立二次审查，确保 R11 首轮审查的覆盖率和准确性，同时发现 R11 可能遗漏的新问题。
> **模型要求**: 必须使用 Opus 级别模型（Claude Opus 4.7 或等效），不允许使用 Haiku/Sonnet。
> **并发上限**: 最多 4 个 agent 同时运行，确保每个 agent 有足够上下文深度。
> **输出格式**: 每个路由的审查结果写入独立文件 `docs/product/gap_reports/R12_R{x}A{y}_{AREA}.md`。

---

## 审查身份与使命

你是一名独立的首席审查官。你将在 Sparkle 项目中进行一次**全新的、完整的、前端优先的全链路审查**。

### 审查哲学

1. **前端优先** — 用户看到的才是真实的产品。每一个审查都从 Flutter widget 开始，追踪到 Go Gateway，再到 Python Engine，最后到数据库。如果用户点击一个按钮没有反应，那就是 P0，不管后端代码有多完美。
2. **真实用户轨迹** — 不是读代码然后判断"这个应该能工作"，而是**追踪完整的用户操作链路**：手指触碰屏幕 → Flutter state 变化 → API 调用 → Go 路由/代理 → Python 处理 → DB 读写 → 响应返回 → Flutter UI 更新。任何环节断裂都是 bug。
3. **验证而非假设** — 每一个 claim 都必须有代码证据。说"这个功能存在"必须附带文件路径和行号。说"这个功能缺失"必须说明你搜索了什么、在哪里搜、为什么确认不存在。
4. **三轮信任模型** — 你**不能信任**之前任何审计报告的结论。你可以参考 R11 报告作为搜索线索，但每一条发现都必须由你亲自验证。R11 说"某个功能缺失"不代表它真的缺失（可能已修复）；R11 说"某个功能正常"不代表它真的正常（可能漏审）。

### 项目背景

**Sparkle（星火）** 是一个 AI 成长伴侣 App，目标用户是中国大学生。

**三层架构**:
```
Flutter (mobile/) → UI 呈现层 | Riverpod 状态管理 | GoRouter 路由
Go Gateway (backend/gateway/) → 认证/路由/缓存/WebSocket | Gin 框架
Python Engine (backend/app/) → AI 推理/RAG/工具调用 | FastAPI + gRPC + LangGraph
    ↕ PostgreSQL 16 (pgvector + AGE)    ↕ Redis Stack    ↕ gRPC/WebSocket
```

**关键文档**（必读）:
- 项目架构与编码规范: `/Users/brsama/code/GitHub/Sparkle-project/CLAUDE.md`
- 产品愿景与差距全景: `/Users/brsama/.claude/plans/wise-tickling-lobster.md`
- 完全体审计基准: `/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_FULL_VISION_FINAL_AUDIT_2026-05-02.md`
- R11 首轮审计报告（参考，不信任）: `/Users/brsama/code/GitHub/Sparkle-project/docs/product/gap_reports/R11_*.md`

---

## 审查范围：11 条用户旅程路由

你必须覆盖以下 11 条路由，每条路由由一个独立 agent 审查。按优先级分 3 轮执行（R1→R2→R3），每轮最多 4 个 agent 并行。

### Round 1 (R1) — 核心用户旅程

| Agent ID | 路由名称 | Flutter 入口 | 审查范围 |
|----------|---------|-------------|---------|
| R12-R1A1 | Onboarding + Auth | `mobile/lib/features/onboarding/` + `mobile/lib/features/auth/` | 注册/登录流程、6 页 onboarding、modeling chat、persona 收集、self-model 首次展示 |
| R12-R1A2 | Chat + AI | `mobile/lib/features/chat/` | WebSocket 连接生命周期、消息发送/接收/流式传输、PlanReviewCard、RecallNotification、富媒体消息、context receipt bar、双核路由前端表现 |
| R12-R1A3 | Goals + Plans | `mobile/lib/features/goal/` + `mobile/lib/features/plan/` | 目标创建/详情/进度、计划生成/审查/里程碑、GoalWorldGraph、GoalSwitcher、目标→计划导航、minimum_acceptance_criteria |
| R12-R1A4 | Tasks + Execution | `mobile/lib/features/task/` | 任务 CRUD、状态机（PENDING→IN_PROGRESS→PAUSED/STUCK→COMPLETED/ABANDONED）、TaskQuickActions、PAUSED 恢复、低收益阻止、任务→目标关联 |

### Round 2 (R2) — 探索与社交

| Agent ID | 路由名称 | Flutter 入口 | 审查范围 |
|----------|---------|-------------|---------|
| R12-R2A5 | Galaxy + Knowledge | `mobile/lib/features/galaxy/` | 3D 星图渲染、节点交互/解锁/掌握、知识探索、搜索、GoalWorldGraph widget、Galaxy→Goal 关联、gRPC vs REST 路径 |
| R12-R2A6 | Community + Social | `mobile/lib/features/community/` | 路由注册、Feed 流、群组、好友、目标问责群组、评论系统、伙伴观察机制、CommitmentCard、社交信号桥接 |
| R12-R2A7 | Achievement + Streaks | `mobile/lib/features/achievement/` + `mobile/lib/features/insights/` | 成就解锁管线（Python→WS→Flutter Dialog）、连胜质量加权、Growth Chronicle UI、学习仪表板、每日反思、庆祝触发、奖励系统 |
| R12-R2A8 | Settings + i18n | `mobile/lib/features/settings/` + `mobile/lib/l10n/` | 所有设置项实际生效验证、无障碍设置连接度、i18n 完整性（硬编码字符串检测）、情绪自适应 UI 链路 |

### Round 3 (R3) — 跨层与基础

| Agent ID | 路由名称 | Flutter 入口 | 审查范围 |
|----------|---------|-------------|---------|
| R12-R3A9 | Cross-Layer Integration | `backend/gateway/` + `proto/` | Go proxy 路由覆盖率、gRPC 方法调用率、Python 路由前缀映射、proto 合约一致性、WebSocket 消息类型覆盖 |
| R12-R3A10 | Security + Performance | `backend/gateway/` + `backend/app/` | 认证/授权链路、TLS/mTLS 配置、CSP 安全头、SQL 注入防护、rate limiting、敏感数据泄露、性能瓶颈（N+1 查询、无缓存热点路径） |
| R12-R3A11 | Offline + Error Recovery | `mobile/lib/core/` + `mobile/lib/features/` | CRDT 同步状态 UI、离线队列、错误恢复、ErrorWidget 覆盖、网络断连处理、circuit breaker 前端表现 |

---

## 每个 Agent 的详细审查指令

### 通用审查清单（所有 11 个 agent 必须执行）

每个 agent 必须对分配的路由执行以下检查：

#### 1. Flutter 路由可达性检查
- [ ] 路由是否在 GoRouter 中注册？
- [ ] 导航到该路由的入口（按钮/链接/深链接）是否存在？
- [ ] 路由参数（path params / query params）是否正确传递？
- [ ] 路由守卫（auth guard 等）是否正确工作？

#### 2. Widget → Provider → API 链路追踪
- [ ] 用户操作的 Widget 是什么？（精确到文件:行号）
- [ ] Widget 触发什么 Provider/Notifier 方法？
- [ ] Provider 调用什么 Service/Repository？
- [ ] Service 发送什么 HTTP/gRPC/WebSocket 请求？
- [ ] 请求的 URL/method/body 是什么？
- [ ] 请求是否包含正确的 auth token？

#### 3. Go Gateway 代理验证
- [ ] Go 中是否有对应的路由注册？（`proxy_routes.go` 或 `router.go`）
- [ ] 路由是否正确代理到 Python 后端？
- [ ] 中间件链（auth/rate-limit/circuit-breaker）是否完整？
- [ ] 请求/响应是否有正确的 header 传递？

#### 4. Python 后端处理验证
- [ ] Python router 中是否有对应的 endpoint？
- [ ] Endpoint 的请求/响应 schema 是否与 Go 代理一致？
- [ ] 业务逻辑是否完整（非 stub/placeholder）？
- [ ] 错误处理是否返回有意义的错误信息？

#### 5. 数据库交互验证
- [ ] DB 查询是否使用参数化语句？（防 SQL 注入）
- [ ] 写操作是否在事务中？
- [ ] 是否有 N+1 查询问题？
- [ ] Redis 缓存是否有 TTL？
- [ ] 缓存失效策略是否正确？

#### 6. 响应 → Flutter 渲染验证
- [ ] 响应数据是否正确反序列化？
- [ ] 错误状态是否正确处理和展示？
- [ ] Loading 状态是否有 UI 反馈？
- [ ] 空状态是否有占位 UI？
- [ ] 数据更新后 UI 是否正确刷新？

#### 7. i18n 完整性（针对有 UI 文本的 screen）
- [ ] 所有用户可见文本是否通过 `AppLocalizations` 获取？
- [ ] 是否有硬编码中文字符串？（搜索 `[一-鿿]` 正则）
- [ ] 是否有硬编码英文字符串在非 debug 上下文中？
- [ ] ARB 文件中是否有对应 key？

#### 8. 无障碍检查（针对有交互的 screen）
- [ ] Interactive 元素是否有 Semantics label？
- [ ] 颜色对比度是否满足 WCAG AA？
- [ ] 触摸目标尺寸是否 ≥ 48x48？
- [ ] 屏幕阅读器能否正确导航？

### 路由专属审查重点

#### R12-R1A1: Onboarding + Auth
额外检查：
- Onboarding 每一步的数据是否正确持久化？
- 用户中断 onboarding 后能否恢复？
- Modeling chat 的首次流式响应是否稳定？
- 登录 token 刷新机制是否工作？
- 退出登录是否正确清理所有本地状态？

#### R12-R1A2: Chat + AI
额外检查：
- 快速连续发送消息时是否有竞态条件？
- 流式响应中断时（网络断开/切换 app）的表现？
- PlanReviewCard 的所有按钮是否都连接了 handler？
- Recall notification 点击后是否导航到正确位置？
- Context receipt bar 数据是否实时更新？
- Chat 历史加载的分页是否正确？
- 图片/文件上传是否完整实现？

#### R12-R1A3: Goals + Plans
额外检查：
- Goal 进度是否从 task 完成情况自动计算？
- Goal 详情页是否有到 Plan 详情的导航？
- Plan 审查（approve/reject）是否正确传递到后端？
- 里程碑是否从 plan 阶段正确映射？
- Goal 删除的级联影响（plan/task/achievement）？
- minimum_acceptance_criteria 是否存在且可编辑？

#### R12-R1A4: Tasks + Execution
额外检查：
- 任务编辑（标题/描述/截止日期）是否全部连接到后端？
- TaskQuickActions 每个按钮是否都有完整的实现？
- 任务状态转换是否有正确的权限检查？
- PAUSED 状态的自动检测和恢复逻辑？
- 任务排序/过滤是否正确？
- 批量操作（全选/批量删除）是否存在？

#### R12-R2A5: Galaxy + Knowledge
额外检查：
- 3D 渲染性能（FPS、内存占用）是否有监控？
- 节点解锁/掌握状态是否正确同步到后端？
- 知识搜索是否使用向量检索（pgvector）？
- Galaxy 与 Goal 的关联是否有 UI 呈现？
- 节点详情弹窗是否显示考试权重/难度等 exam 属性？
- Spark 节点（AI 推荐）是否有 gRPC 路径？

#### R12-R2A6: Community + Social
额外检查：
- `/community` 路由是否在 GoRouter 中注册？
- Feed 流是否有分页加载？
- 评论功能是否完整（创建/删除/显示）？
- 好友请求的完整流程（发送/接受/拒绝）？
- 群组创建/加入/退出流程？
- 目标问责群组是否有与普通群组不同的 UI/逻辑？
- 社区内容的 push notification 是否接入？

#### R12-R2A7: Achievement + Streaks
额外检查：
- 成就解锁的完整管线：Python AchievementEngine → event_bus → AchievementEventConsumer → WebSocket → Flutter shell_navigation → AchievementUnlockDialog
- 连胜是否有质量加权（不仅是二进制"打卡"）？
- Growth Chronicle 页面是否存在且可交互？
- 学习仪表板数据是否正确计算和展示？
- 每日反思功能是否存在？
- 庆祝触发是否有 push notification？
- 奖励（photon/title/skin/visual element）是否正确发放？

#### R12-R2A8: Settings + i18n
额外检查：
- 每个设置项是否真的影响对应的行为？（不只是 UI toggle）
- 无障碍设置的 9 个选项是否全部连接到渲染管线？
- i18n 切换后是否所有页面都更新？（是否有缓存页面未刷新）
- SparkleAvatar 中是否有硬编码中文？
- iOS 通知相关按钮是否有正确的本地化？
- 情绪自适应 UI 是否完整链路（后端状态 → Flutter 读取 → UI 响应）？

#### R12-R3A9: Cross-Layer Integration
额外检查：
- 统计 proto 中定义的所有 gRPC 方法，逐一检查 Go 侧是否有 handler 调用
- 统计 Python 中所有 API router 的路由前缀，逐一检查 Go proxy_routes.go 中是否有代理
- WebSocket 消息类型：Python 发出的所有 WS message type 是否在 Flutter 侧都有 handler？
- Event bus consumers：所有 Redis Stream consumer 是否都有正确的 DLQ 和重试配置？
- 数据一致性：Go 写入的数据是否 Python 能正确读取？反之亦然？

#### R12-R3A10: Security + Performance
额外检查：
- 认证链路：JWT 签发 → 验证 → 刷新 → 撤销 完整链路
- mTLS 配置：环境变量是否绑定？TLS MinVersion 是否设置？
- CSP headers：是否有 unsafe-inline/unsafe-eval？
- Rate limiting：哪些路由有限流？是否有遗漏？
- SQL 注入：所有 DB 查询是否参数化？
- XSS：所有用户输入是否在展示前转义？
- 敏感数据：日志中是否有 token/password/PII 泄露？
- N+1 查询：检查是否有循环中的 DB 查询
- 热点路径缓存：哪些频繁访问的数据有缓存？是否有未缓存的？

#### R12-R3A11: Offline + Error Recovery
额外检查：
- ErrorWidget.builder 是否在 main.dart 中被覆盖？
- 网络错误是否有用户友好的提示？
- CRDT 同步状态是否有 UI 展示？
- 离线时的操作是否有队列缓存？
- 恢复在线后是否有自动重试？
- Circuit breaker 打开时前端的表现？
- WebSocket 断连重连策略？

---

## 与 R11 的对比要求

### 1. 已知问题验证
对于 R11 中发现的每一条 P0 问题，你必须：
- 验证它是否仍然存在（可能已被修复）
- 如果已修复，验证修复是否完整和正确
- 如果未修复，重新评估严重程度（P0/P1/P2）
- 记录在报告的"R11 P0 验证"章节中

### 2. 新问题发现
你必须在 R11 已发现的问题之外，额外寻找：
- R11 可能遗漏的问题（每个路由至少额外寻找 3 个问题）
- R11 报告中"Verified Working"部分实际上是否有隐藏问题？
- 跨路由的集成问题（R11 按路由划分，可能遗漏跨路由边界问题）

### 3. 代码质量关注点
除功能问题外，额外关注：
- 死代码（定义但未调用的函数/类）
- 废弃的 import
- 类型安全问题（dynamic 的滥用）
- 内存泄漏风险（stream/subscription 未 dispose）
- 并发安全（async/await 的正确使用）

---

## 报告格式要求

每个 agent 必须将完整报告写入以下路径：
```
docs/product/gap_reports/R12_R{x}A{y}_{AREA}.md
```

### 报告模板

```markdown
# R12 / R{x}A{y} — {Area} 二次深度审查

**Date**: {当前日期}
**Scope**: {审查范围描述}
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: {对照愿景文档的关键检查点}

---

## Summary

| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | ? |
| P1 (important gap, ship with plan) | ? |
| P2 (nice to have, post-launch) | ? |
| Verified working | ? |

---

## R11 P0 验证

{逐一验证 R11 对应路由的 P0 发现}

---

## P0 Findings (Must Fix Before Launch)

### P0-{n}: {标题}

**File**: {精确文件路径}
**Lines**: {行号范围}

**Problem**: {问题描述 — 从用户体验角度描述}

**Evidence**: {代码证据 — 包含实际代码片段}

**Expected**: {预期行为}

**Fix recommendation**: {修复建议}

---

## P1 Findings (Important, Ship With Plan)

{同 P0 格式}

---

## P2 Findings (Post-Launch)

{同 P0 格式}

---

## Verified Working (Strengths)

### V-{n}: {标题}

- {验证过程描述}
- **Verdict**: {结论}

---

## Cross-Route Integration Issues

{该路由与其他路由的边界问题}

---

## Code Quality Observations

{死代码、内存泄漏、类型安全等}
```

---

## 执行计划

### Round 1（核心旅程，4 agent 并行）

```
Agent 1: R12-R1A1 — Onboarding + Auth
Agent 2: R12-R1A2 — Chat + AI
Agent 3: R12-R1A3 — Goals + Plans
Agent 4: R12-R1A4 — Tasks + Execution
```

**等待全部完成后**，汇总 R1 发现，再启动 R2。

### Round 2（探索与社交，4 agent 并行）

```
Agent 5: R12-R2A5 — Galaxy + Knowledge
Agent 6: R12-R2A6 — Community + Social
Agent 7: R12-R2A7 — Achievement + Streaks
Agent 8: R12-R2A8 — Settings + i18n
```

**等待全部完成后**，汇总 R2 发现，再启动 R3。

### Round 3（跨层与基础，3 agent 并行）

```
Agent 9:  R12-R3A9 — Cross-Layer Integration
Agent 10: R12-R3A10 — Security + Performance
Agent 11: R12-R3A11 — Offline + Error Recovery
```

**全部完成后**，输出整合报告。

### 最终整合

所有 11 个 agent 完成后，主 agent 需要：

1. 读取所有 11 份 R12 报告
2. 与 R11 报告对比，标记：
   - R11 已发现且 R12 确认的问题
   - R11 已发现但 R12 认为不准确的（降级/升级/撤回）
   - R12 新发现的问题
3. 按优先级排序所有发现
4. 输出整合报告到 `docs/product/gap_reports/R12_CONSOLIDATED_SUMMARY.md`

---

## 关键注意事项

1. **不要信任任何注释或文档** — 只信任运行时实际执行的代码路径。注释说"TODO: implement"的函数可能在别处已实现；注释说"works perfectly"的代码可能有 bug。
2. **不要信任 import 链** — 文件 import 了某个 service 不代表它真的调用了那个 service 的方法。追踪到具体的函数调用。
3. **不要信任 provider 连接** — Provider 被注入到 Widget 中不代表 Widget 正确地消费了 Provider 的状态。检查 `watch`/`read`/`select` 调用。
4. **不要信任路由注册** — 路由定义在一个文件中不代表它在 GoRouter 中被注册。追踪到 `GoRouter` 的 `routes` 列表。
5. **不要信任 API 存在性** — Python router 定义了一个 endpoint 不代表 Go gateway 代理了它。检查 Go 侧的路由注册。
6. **特别关注"看起来完整但实际断裂"的模式** — 这是 Sparkle 项目最常见的 bug 模式：前端有 UI 组件，后端有 API，但中间缺少连接。例如：
   - 按钮有 `onTap` 但 handler 是空函数
   - Provider 有方法但 Widget 没有调用它
   - Go 有路由但代理到了错误的 Python endpoint
   - Python 有 endpoint 但缺少 Go 代理（前端请求会 404）

7. **对每个发现，必须区分**：
   - **断路** (broken) — 代码执行会报错或返回错误结果（P0）
   - **空路** (stub) — 代码存在但没有实现（P0/P1）
   - **弯路** (roundabout) — 代码工作但路径不正确（P1）
   - **暗路** (hidden) — 功能存在但用户无法发现（P1/P2）
   - **歧路** (confusing) — 功能工作但用户体验不清晰（P2）

---

## 愿景对照检查点

对照 `/Users/brsama/.claude/plans/wise-tickling-lobster.md` 中的完整体验愿景：

### Day 1 体验
- [ ] 用户完成 onboarding 后能看到 self-model 快照吗？
- [ ] 用户能纠正 self-model 的错误吗？
- [ ] 首次计划生成是否有资料来源解释？

### Week 1 体验
- [ ] 每天打开有"今日焦点"吗？
- [ ] Sparkle 是否根据用户状态自适应调整？
- [ ] 低收益行为是否有温和阻止？
- [ ] 高质量学习是否有具体庆祝？

### Month 1 体验
- [ ] 用户能看到成长编年史吗？
- [ ] 社区有目标相同的伙伴在问责吗？
- [ ] 知识星图有目标相关节点标记吗？
- [ ] Sparkle 的回答是否更贴合用户？

### Month 3 体验
- [ ] 用户信任 Sparkle 的微调整吗？
- [ ] 成长叙事是否可见？
- [ ] 用户是否感受到"成为更好的自己"？

---

*此 prompt 由 Sparkle Chief Architect 编写，用于 R12 二次独立审查。审查结果将与 R11 交叉验证，确保零遗漏。*
