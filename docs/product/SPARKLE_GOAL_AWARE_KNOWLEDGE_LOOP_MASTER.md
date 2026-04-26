# Sparkle 目标感知知识闭环系统 — 总指导文档

> **Master Document** | Version 1.0 | 2026-04-26
> **定位**: 本文档是整个 Goal-Aware Knowledge Loop 工作的唯一指导源。所有实现进度、改动记录、阶段验收均以子文档形式挂载于此。

---

## 0. 一句话定位

> **别人让 AI 读你的资料；Sparkle 让资料进入你的目标闭环。**

Sparkle 的个人知识库不是"上传文件 → AI 检索 → AI 回答"。
而是：用户上传材料 → 材料被结构化挂载到知识星图 → 知识星图改变系统对考试/目标/能力差距的理解 → Aurora 决定本轮是否调用这些材料 → 标准层生成更好的解释、任务卡、计划和小测 → 用户执行后的错因/反馈回流 → 知识星图、用户模型、目标模型、自我模型、社群洞察继续更新。

---

## 1. 竞争对手分析

| 维度 | ChatGPT Projects | Claude Projects | NotebookLM | Sparkle 目标 |
|------|-----------------|----------------|-----------|-------------|
| 资料组织 | 扁平文件 + 项目工作区 | 扁平文件 + 200K 上下文 | 多格式来源 + 笔记本 | **知识星图结构化挂载** |
| 上下文管理 | 用户手动 / 全塞 | 用户手动 / 全塞 | 用户选择来源 | **Aurora ContextPlan 自动决策** |
| 知识追踪 | 无 | 无 | 无 | **掌握度 + 考试权重 + 错因** |
| 学习闭环 | 无（只回答） | 无（只回答） | 总结 + 引用 | **任务卡 → 执行 → 错因回流 → 模型更新** |
| 社群 | 无 | 无 | 共享笔记本 | **匿名聚合信号 + 共享资源池** |
| 移动端 | 弱 | 弱 | 桌面优先 | **移动优先** |

**核心差异**: Sparkle 不是 workspace，是 goal loop。资料不是静态上下文，而是目标推进系统的一部分。

---

## 2. 核心原则

### 2.1 Context Membrane（上下文膜）

> 资料进入系统，不等于资料进入上下文。

用户上传的资料不能直接进入回答。必须经过：
```
资料解析 → 分块 → 结构化摘要 → 概念/考点抽取 → 映射到知识星图节点
→ 质量评估 → 可检索索引 → Aurora ContextPlan 决策 → 才能进入某一轮输出
```

### 2.2 Aurora 是调度器，不是开关

每轮对话前，Aurora 必须生成 ContextPlan：
- retrieval_mode: 从 8 级模式中选择
- must_load / may_load / do_not_load
- token_budget
- pollution_guard
- citation_required
- user_visible_receipt

### 2.3 普通用户不需要管理上下文

默认 Aurora 自动选择。但用户可以：
- 看见 Aurora 的决策（Context Receipt）
- 手动覆盖（Source Tray）
- 反向排除资料

---

## 3. 总体闭环架构

```
资料层     Source Library / Documents / Slides / Past Papers / Notes
    ↓
知识结构层  Knowledge Star Map / Concept Nodes / Exam Weight / Dependencies
    ↓
Aurora层   ContextPlan / Retrieval Policy / Strategy Policy / Model Write Policy
    ↓
AI输出层   Conversation / Task Card / Quiz / Explanation / Report
    ↓
用户行动层  Completion / Time Cost / Accuracy / Mistakes / Feedback / Corrections
    ↓
状态回流层  KnowledgeState / UserModel / GoalModel / SituationModel / SparkleSelfModel
    ↓
社群时间轴  Hybrid Timeline / Partner Signals / Cohort Insights / Shared Resources
    ↓
再次影响    Knowledge Star Map + Aurora Context Decisions + Future Plans
```

---

## 4. 核心对象定义

### 4.1 SourceAsset（用户资料）
```json
{
  "source_id": "", "title": "", "type": "slides|pdf|past_exam|notes|homework",
  "course": "", "goal_id": "", "owner": "user|community|partner",
  "visibility": "private|shared|community_public", "quality_score": 0.0,
  "parsed_status": "pending|parsed|failed", "mapped_nodes": [],
  "recommended_uses": ["concept_explanation","task_material","quiz_generation"],
  "not_recommended_uses": []
}
```

### 4.2 SourceSlice（可检索片段）
```json
{
  "slice_id": "", "source_id": "", "location": "p32-p45",
  "summary": "", "concepts": [], "knowledge_nodes": [],
  "evidence_type": "definition|example|exercise|teacher_emphasis|past_exam",
  "noise_risk": "low|medium|high"
}
```

### 4.3 KnowledgeNodeEvidence（资料-节点挂载）
```json
{
  "node_id": "", "evidence_id": "", "source_slice_id": "",
  "relation_type": "explains|example_of|tests|prerequisite|teacher_emphasis",
  "confidence": 0.82
}
```

### 4.4 ContextPlan（Aurora 上下文计划）
```json
{
  "retrieval_mode": "targeted_graph_rag",
  "source_scope": "auto|user_selected|task_bound|goal_bound",
  "must_load": [], "may_load": [], "do_not_load": [],
  "token_budget": 3600, "citation_required": true,
  "pollution_guard": "strict", "user_visible_receipt": true,
  "reason_for_user": "我只参考了当前任务相关资料，避免完整课件污染解释。"
}
```

### 4.5 ContextReceipt（上下文回执）
```json
{
  "used": ["当前任务卡", "第3章课件 p32-p45", "最近TCP窗口错因"],
  "excluded": [{"item": "完整传输层课件", "reason": "范围太大"}],
  "allow_user_override": true,
  "actions": ["按课件重讲", "改用往年题", "不要用这份资料"]
}
```

---

## 5. RAG 8 级模式

| Level | Mode | Description |
|-------|------|-------------|
| 0 | no_retrieval | 不检索，只用对话和基础知识 |
| 1 | graph_only | 只用知识星图节点摘要 |
| 2 | targeted_source_rag | 少量高相关资料片段 |
| 3 | task_bound_rag | 只检索当前任务卡绑定资料 |
| 4 | user_pinned_sources | 用户手动选择的资料必须参与 |
| 5 | deep_source_synthesis | 多资料综合，用于计划/范围/复盘 |
| 6 | community_aggregate_context | 匿名社群统计+共性错因+共享资源 |
| 7 | aurora_core_case_file | Aurora 完全态，用压缩 case file |

---

## 6. Aurora 调用 RAG 规则

### 必须调用
- 用户明确要求按课件/资料回答
- 当前任务卡绑定了资料
- 需要 course-specific grounding（考试范围、老师重点）
- 需要引用证据
- 用户正在纠正系统（"你是不是没看我上传的文件？"）

### 谨慎调用
- 用户问通用概念
- 用户状态已载（课件细节会让解释更复杂）
- 资料质量低
- 问题适合先诊断

### 不应该调用
- 资料和问题无关
- 用户问执行策略而不是学科内容
- 上下文预算不足且资料收益低
- Aurora 判断资料会引入混乱
- 已有知识星图摘要足够回答

**重点：不用 RAG 也应该是可解释的 Aurora 决策。**

---

## 7. 前端页面设计要点

### 7.1 资料库 → "目标资料库"
每份资料显示：覆盖节点 / 被哪些任务用过 / 生成过哪些小测 / 质量如何

### 7.2 对话页四部件
- Aurora 状态带（上下文决策）
- Source Tray（目标感知资料托盘）
- Context Receipt（用了什么/没用什么/为什么）
- 单一输入框

### 7.3 知识星图节点五 Tab
概览 / 资料 / 错因 / 任务 / 社群洞察

### 7.4 任务卡
必须显示：使用资料 / 为什么用 / 卡住时调用什么 / 完成后更新什么

---

## 8. 社群闭环

### 8.1 责任伙伴
承诺 → 见证 → 外部观察反馈 → 标记为 external_observation_candidate → Aurora 显性确认

### 8.2 共性错因
匿名聚合 → 影响小测题型/任务模板/节点难度 → 用户看到"同目标用户也常错"

### 8.3 共享资料
Community Resource Pool → 质量评分 → Aurora 推荐是否加入个人库 → 用户确认后才进入

---

## 9. 实施计划

### Phase 1: 闭环连通（P0） ✅ COMPLETE
- [x] Upload → 处理进度通知 → 节点发现 → 通知 → Draft Review 路由打通
- [x] Context Receipt MVP — 回答底部显示"基于：X / 未使用：Y"
- [x] retrieval_intent.py 升级为 ContextPlan 结构
- [x] 知识节点详情页显示挂载资料
- **进度文档**: [phase1_progress.md](./SPARKLE_KNOWLEDGE_LOOP_PHASE1_PROGRESS.md)

### Phase 2: Aurora Context Engineering（P1） ✅ COMPLETE
- [x] ContextPlan 写入 routing_decision_log
- [x] Aurora 状态带显示上下文决策
- [x] Source Tray 升级（目标感知资料托盘）— 5 模式: auto/userSelected/taskScope/goalScope/off
- [x] 资料选择作用域（本次/任务/目标）— document_context_scope 端到端传递
- [x] LLM-powered 节点建议 — exam_weight + recommended_action
- [x] 资料质量反馈影响检索排序 — 已有完整闭环
- **进度文档**: [phase2_progress.md](./SPARKLE_KNOWLEDGE_LOOP_PHASE2_PROGRESS.md)

### Phase 3: 护城河闭环（P2） ✅ COMPLETE
- [x] 社群共性错因 → 知识节点标注 — Celery 定时 + API 按需
- [x] 共享资料推荐流程 — GET /community/recommended-resources
- [x] 混合时间轴记录 ContextPlan 因果轨迹 — GET /galaxy/context-plan/timeline
- [x] Aurora 自我校准 — 连续错题检测 + 校准问题注入 ContextPlan
- [x] 资料卡显示覆盖/用途/有效性 — 质量指示 + drafts pending
- [x] 知识星图节点五 tab — 概览/资料/错因/任务/社群洞察
- **进度文档**: [phase3_progress.md](./SPARKLE_KNOWLEDGE_LOOP_PHASE3_PROGRESS.md)

---

## 10. 现有基础设施审计

| 层 | 现有文件 | 状态 | 备注 |
|----|---------|------|------|
| 资料上传 | `backend/app/api/v1/documents.py` | ✅ | presigned upload + confirm + status |
| 文档解析 | `backend/app/core/ingestion/ingestion_service.py` | ✅ | PDF/DOCX/PPTX/MD/TXT/Image+OCR |
| RAG 检索 | `backend/app/orchestration/graph_rag.py` | ✅ | HyDE + BM25+RRF + CRAG + mastery rerank |
| 检索意图 | `backend/app/orchestration/retrieval_intent.py` | ✅ | 8-level ContextPlan + 5-scope source_scope |
| Aurora Kill Switch | `backend/app/services/aurora_doc_context_kill_switch_service.py` | ✅ | off/shadow/live |
| 节点挂载 | `backend/app/models/galaxy.py` KnowledgeNodeDocument | ✅ | join table exists |
| Galaxy API | `backend/app/api/v1/galaxy.py` | ✅ | drafts/review/attach/detach |
| 节点资料 Provider | `mobile/.../node_source_materials_provider.dart` | ✅ | 数据层完成 |
| Citation Strip | `mobile/.../assistant_citation_strip.dart` | ✅ | Context Receipt bar integrated in chat_bubble |
| 群组知识库 | `mobile/.../group_knowledge_base_view.dart` | ✅ | UI 完成 |
| Gateway 路由 | `backend/gateway/internal/handler/galaxy_handler.go` | ✅ | 所有端点已注册 |

---

## 11. 执行规范

1. 每次改动后 git commit
2. 每个 Phase 有独立进度文档，挂载于此
3. 所有改动需自审两遍
4. 不偏离本设计愿景
5. 优先复用现有代码，不重复造轮子

---

## 12. 设计稿原文

完整产品设计稿见: [design_v0.1.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_DESIGN_V01.md)

---

**文档维护者**: Claude Code (自主执行模式)
**最后更新**: 2026-04-26
