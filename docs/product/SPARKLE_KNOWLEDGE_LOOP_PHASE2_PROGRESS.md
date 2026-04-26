# Phase 2: Aurora Context Engineering — 进度文档

> **Parent**: [MASTER.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_MASTER.md)
> **Status**: PENDING | Depends on: Phase 1

---

## 目标
让 Aurora 每轮生成完整 ContextPlan，前端可感知。

## Tasks

### 2.1 ContextPlan 一等对象
- [ ] ContextPlan dataclass 写入 routing_decision_log
- [ ] 每轮结束后持久化，可用于时间轴回溯
- [ ] 与 retrieval_decision_log 合并

### 2.2 Aurora 状态带显示上下文决策
- [ ] 新增 context_decision 状态
- [ ] 收拢态："Aurora · 已参考当前任务资料"
- [ ] 展开态：显示 used/excluded/actions

### 2.3 Source Tray 升级
- [ ] 替代现有 studyMaterialsEnabled toggle
- [ ] 三模式：自动 / 只用我选的 / 不要用资料
- [ ] 资料选择作用域：本次/任务/目标
- [ ] 反向排除功能

### 2.4 LLM-powered 节点建议
- [ ] 替代纯余弦相似度
- [ ] 用 LLM 提取概念/考点
- [ ] 生成有意义的节点名、描述、关键词
- [ ] 建议新节点间关系

### 2.5 资料质量反馈影响检索
- [ ] citation feedback → quality_score 更新
- [ ] quality_score 作为检索排序因子
- [ ] 低质量资料降权

---

## Commits
*(to be filled)*
