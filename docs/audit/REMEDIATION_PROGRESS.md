# Sparkle AI 系统审计修复 — 工作进度跟踪

> **开始日期**: 2026-05-15
> **基线报告**: `docs/audit/00_MASTER_SUMMARY_AI_SYSTEM.md` (Round 1-7, 21 子报告)
> **范围**: 第零、一、二梯队问题（不含第三梯队大型重构）
> **执行人**: Chief Architect 主 agent

---

## 工作规范

1. **小步迭代**: 每个修复独立 commit，提交信息标注问题编号（如 `fix(sec): R5-P0-6 ...`）
2. **真实性验证**: 修复前用 Explore agent 或 grep 确认问题在当前代码中真实存在
3. **双重审查**: 修复后先 Opus agent 独立审查 → 主 agent 自我审查 5 点清单
4. **不破坏现有功能**: 必要时跑 lint/test，最少跑变更范围的快速校验
5. **本文档实时更新**: 每完成一条立即更新进度表与决策日志

---

## 修复批次规划

### Batch 0 — 跨租户数据泄露 & 认证（最紧急）
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 0.1 | R5-P0-6 | GraphRAG graph_search/find_learning_path/find_related_concepts Cypher 缺 user_id 过滤 | 待修复 | - |
| 0.2 | R7-P0-1 | Galaxy create_edge 无节点所有权验证 | 待修复 | - |
| 0.3 | R7-P0-2 | get_node_neighbors / get_node_with_context 无用户隔离 | 待修复 | - |
| 0.4 | R6-P0-7 | retrieval_service.keyword_search user_id 参数被忽略 | 待修复 | - |
| 0.5 | R7-P0-3 | 群排行越权（非成员可查） | 待修复 | - |
| 0.6 | R7-P0-4 | 私信绕过拉黑 (UserBlock 未查) | 待修复 | - |
| 0.7 | R7-P0-5 | 离线消息 mark_as_sent/failed 不验证归属 | 待修复 | - |
| 0.8 | R7-P0-6 | /broadcast 无速率限制 | 待修复 | - |

### Batch 1 — 身份链 / PII / gRPC 信任边界
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 1.1 | SEC-3 / R5-P0-1 | gRPC user_id 可被 protobuf body 覆盖 metadata | 待修复 | - |
| 1.2 | SEC-2 | gRPC 无独立认证（API Key 跳过用户验证） | 待修复 | - |
| 1.3 | SEC-1 | PII 未脱敏直接发给外部 LLM | 待修复 | - |
| 1.4 | SEC-4 / R2-04 | privacy.py:58 异步上下文 run_until_complete 崩溃 | 待修复 | - |
| 1.5 | R5-P0-2 | 安全告警仅日志，不阻断 | 待修复 | - |
| 1.6 | R5-P0-3 | 7 个方法完全不检查 user-id | 待修复 | - |

### Batch 2 — AI 决策架构 / 内容安全
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 2.1 | R6-P0-6 | L2 DecisionLoop user_message 未净化（prompt 注入） | 待修复 | - |
| 2.2 | R6-P0-4 | L1 should_escalate 未传递到 L2 | 待修复 | - |
| 2.3 | R6-P0-5 | L1 快速路径无内容安全检查 | 待修复 | - |
| 2.4 | R6-P0-1 | 审查跳过条件过宽 | 待修复 | - |
| 2.5 | R6-P0-2 | EnhancedAgent 生产用硬编码模拟数据 | 待修复 | - |
| 2.6 | R6-P0-3 | ReviewerAgent 异常时自动放行 | 待修复 | - |
| 2.7 | R6-P0-8 | pending_actions TTL 5 分钟过短 | 待修复 | - |

### Batch 3 — 成本/健康控制
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 3.1 | R4-P0-1 | report_model_failure/success 全代码库无调用点 | 待修复 | - |
| 3.2 | R4-P0-5 | cost_controller 未集成到 llm_router | 待修复 | - |
| 3.3 | R4-P0-2 | Predictive Service 绕过预算检查 | 待修复 | - |

### Batch 4 — 执行层 P0
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 4.1 | R7-P0-7 | _clear_failure_state 空操作 (降级永不解除) | 待修复 | - |
| 4.2 | R7-P0-8 | 分类缓存线程不安全 | 待修复 | - |

### Batch 5 — 闭环/反馈静默失败
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 5.1 | R2-01 | AchievementEngine 光子奖励 5 处静默丢失 | 待修复 | - |
| 5.2 | R2-02 | ProfileWriteService 事件发布静默失败 | 待修复 | - |
| 5.3 | R2-03 | AdaptiveReplanner 计划调整静默失败 | 待修复 | - |
| 5.4 | P0-4 (加重) | 情绪检测无否定词处理 + 自强化反馈环 | 待修复 | - |
| 5.5 | P0-2 | StateAggregator 内存缓存无上限保护 | 待修复 | - |

### Batch 6 — 数据合规
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 6.1 | R4-P0-3 | 用户删除无级联清理 (GDPR) | 待修复 | - |
| 6.2 | R4-P0-4 | 全局向量开关跨用户影响 | 待修复 | - |

### Batch 7 — 第一梯队余项
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 7.1 | P0-3 | DualCoreRouter cognitive_adjustments 硬编码中文 | 待修复 | - |
| 7.2 | P1-01 | Aurora PII Kill Switch 异步上下文失效 | 待修复 | - |

### Batch 8 — 第二梯队（P1 重要项）
| # | 编号 | 问题 | 状态 | Commit |
|---|------|------|------|--------|
| 8.1 | R2-06 | TaskEventConsumer 串行→并行 (195ms→60ms) | 待修复 | - |
| 8.2 | R4-P1-1 | FSM retrieval_node 空列表无保护崩溃 | 待修复 | - |
| 8.3 | R4-P1-4 | _FALLBACK_TIER_ORDER 缺 4 个 tier | 待修复 | - |
| 8.4 | R4-P1-5 | BehaviorPattern/CognitiveFragment 软删除未过滤 | 待修复 | - |
| 8.5 | R4-P1-2 | 多信号叠加后执行覆盖先执行 | 待修复 | - |
| 8.6 | R4-P1-3 | _apply_dual_core_routing 无整体超时 | 待修复 | - |
| 8.7 | R6-P1-4 | L0 静默小时 UTC 而非用户本地时区 | 待修复 | - |
| 8.8 | R6-P1-6 | tc.tool_name bug 致交叉审查永不触发 | 待修复 | - |
| 8.9 | R6-P1-7 | L3 配额硬编码 vs DAILY_QUOTA 不一致 | 待修复 | - |
| 8.10 | R7-P1-1 | 无界并行批处理 dispatch | 待修复 | - |
| 8.11 | R7-P1-3 | 信任引擎子串匹配误报 | 待修复 | - |
| 8.12 | R7-P1-4 | approval_policy="deny" 语义倒置 | 待修复 | - |
| 8.13 | R7-P1-5 | dispatch 无端到端超时 | 待修复 | - |
| 8.14 | R7-P1-6 | 失败执行 token 用量未追踪 | 待修复 | - |
| 8.15 | P1-07 | TaskEventConsumer 反馈阻尼系数动态化 | 待修复 | - |
| 8.16 | P1-10 | AchievementEventConsumer 缺 @reliable_consumer | 待修复 | - |
| 8.17 | P1-11 | Galaxy Error Gap Node 并发保护 | 待修复 | - |
| 8.18 | R6-P1-2 | auto_seed 无 PII 脱敏 | 待修复 | - |
| 8.19 | R6-P1-3 | L3 validate_entry 默认允许任意 wake reason | 待修复 | - |

---

## 进度统计

- 总待修复: **~55** 项
- 已完成: **0**
- 进行中: **0**
- 已 commit: **0**

---

## 决策日志

### 2026-05-15
- 创建工作进度文档，划分 9 个批次
- 决定按 Batch 0→7 顺序推进，每批内部按文件聚集减少上下文切换
- 每个 commit 前 grep/read 验证问题真实存在，避免基于过时审计修改
- 重大修复（涉及核心路径）使用 Opus agent 做 PR-level 独立审查

---

## 修复执行日志（每条完成后追加）

_(待第一个修复完成后填入)_

---
