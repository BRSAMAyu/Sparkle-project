# Sparkle 目标感知知识闭环系统 — 产品与系统设计稿 v0.1

> **Goal-Aware Knowledge Loop with Aurora Adaptive Context/Harness Engineering**
> Original Date: 2026-04-26 | Author: BRSAMA + Claude Code

---

*(Note: This file preserves the complete original design document as provided by the user.
It serves as the canonical product vision. The master document references this file.)*

---

## 1. 定位

Sparkle 的个人知识库不应该被定义成：

```
用户上传文件 → AI 检索文件 → AI 回答问题
```

而应该定义成：

```
用户上传材料
→ 材料被结构化挂载到知识星图
→ 知识星图改变系统对考试/目标/能力差距的理解
→ Aurora 决定本轮是否调用这些材料
→ 标准层生成更好的解释、任务卡、计划和小测
→ 用户执行后的错因/反馈回流
→ 知识星图、用户模型、目标模型、自我模型、社群洞察继续更新
```

一句话：**别人让 AI 读你的资料；Sparkle 让资料进入你的目标闭环。**

---

## 2. 核心原则：资料不能直接污染上下文

> 资料进入系统，不等于资料进入上下文。

资料必须经过完整管道才能进入输出：
```
资料解析 → 分块 → 结构化摘要 → 概念/考点抽取 → 映射到知识星图节点
→ 质量评估 → 可检索索引 → Aurora ContextPlan 决策 → 才能进入某一轮输出
```

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

## 4. 模块职责

### 4.1 资料库 Source Library

每份资料不只是文件名，而是 Source Asset：
- 资料类型、课程、章节
- 覆盖的知识节点
- 考试价值、解析质量
- 可用于/不适合用于的用途
- 被哪些任务用过

### 4.2 知识星图 Knowledge Star Map

每个知识节点是小型状态容器：
- mastery（掌握度）、exam_weight（考试权重）、difficulty（难度）
- prerequisites（前置依赖）
- source_coverage（资料覆盖：哪些课件/题目覆盖了这个节点）
- mistake_clusters（常见错因）
- recommended_action（推荐动作）
- community_signal（社群共性信号）

### 4.3 Aurora Adaptive Context Engine

Aurora 控制每轮的上下文策略：
- 本轮要不要用资料？用哪类？用哪几段？
- 是否需要 RAG？只用星图摘要？引用用户选中文档？
- 是否调用小测/错因/社群数据？
- 是否写入模型？是否需要显性询问用户？

每轮生成 ContextPlan（详见核心对象定义）。

---

## 5. RAG 多级上下文策略

| Level | Mode | Description |
|-------|------|-------------|
| 0 | no_retrieval | 不检索资料 |
| 1 | graph_only | 只用知识星图节点摘要 |
| 2 | targeted_source_rag | 少量高相关资料片段 |
| 3 | task_bound_rag | 只检索当前任务卡绑定资料 |
| 4 | user_pinned_sources | 用户手动选择的资料必须参与 |
| 5 | deep_source_synthesis | 多资料综合 |
| 6 | community_aggregate_context | 匿名社群统计 |
| 7 | aurora_core_case_file | Aurora 完全态压缩 case file |

默认 Aurora 自动选择。用户可覆盖但不需要手动管理。

---

## 6. Aurora 调用 RAG 规则

### 必须调用
- 用户明确要求按课件/资料回答
- 当前任务卡绑定了资料
- 需要 course-specific grounding
- 需要引用证据
- 用户纠正系统

### 谨慎调用
- 用户问通用概念
- 用户状态已载
- 资料质量低
- 问题适合先诊断

### 不应该调用
- 资料和问题无关
- 用户问执行策略
- 上下文预算不足且收益低
- Aurora 判断资料会引入混乱
- 星图摘要已足够

**不用 RAG 也应该是可解释的 Aurora 决策。**

---

## 7. 用户控制体验

### 7.1 Source Tray
对话页的资料托盘：
```
本次回答资料策略：Aurora 自动选择

可参与资料：
☑ 第3章传输层课件    高相关
☐ 往年题 2023       中相关
☐ 全部课件          不建议：范围太大
```
三种模式：[自动] [只用我选的资料] [不要用资料]

### 7.2 资料选择作用域
- 只用于本次回答
- 用于当前任务卡
- 用于今天的冲刺
- 固定到这个目标

### 7.3 反向排除
```
[这份资料不要用于计网冲刺]
[只作参考，不作为考试依据]
[内容太乱，先别用]
```

---

## 8. Aurora 感知带升级

### 收拢态
```
Aurora · 已参考当前任务资料
Aurora · 本轮未调用课件
Aurora · 正在从知识星图取证
Aurora · 资料范围可能不完整
```

### 展开态
```
我参考了：当前任务卡 / 第3章课件拥塞控制部分 / 最近窗口变化错因
我没有参考：全部课件（范围太大）/ 往年题（先讲概念）
[改用往年题讲] [不要用课件] [查看证据]
```

---

## 9. Context Receipt（上下文回执）

每次重要回答后：
```
基于：当前目标 · 7天计网先过
      当前任务 · TCP拥塞控制专项
      资料 · 第3章课件 p32-p45
      错因 · 窗口变化混淆
      策略 · worked example 优先
```

点击展开解释"为什么用了这些"。

---

## 10. 知识星图节点设计

### 视觉层
- 节点大小：考试收益
- 节点亮度：当前优先级
- 节点颜色：掌握度
- 节点外环：资料覆盖程度
- 节点闪烁：当前任务相关
- 节点红点：重复错因
- 节点群体标记：社群共性薄弱点

### 节点详情页（五 Tab）
- **概览**: 为什么重要、你现在的状态、推荐动作
- **资料**: 覆盖资料、哪段最有用、是否帮助提升、资料缺口
- **错因**: 常见错因聚类、最近错误、模式分析
- **任务**: 相关任务卡、完成情况、后续建议
- **社群洞察**: 共性错因、相对难度、共享资源

---

## 11. 资料上传体验

### 处理过程可视化
```
我正在把这份资料接到你的计网知识星图上。

已识别：传输层
覆盖节点：TCP / UDP / 可靠传输 / 流量控制 / 拥塞控制
适合用途：概念压缩、任务卡、小测题、错因解释
可能不足：缺少完整往年题训练
```

### 资料卡
```
《第3章传输层课件》
已挂载：TCP/UDP区别 / TCP可靠传输 / 流量控制 / 拥塞控制 / 端口与套接字
我建议：先用它生成 Day2 传输层任务卡
但它不够覆盖子网划分和路由题

[用于当前冲刺] [生成概念压缩] [生成小测] [暂时只保存]
```

---

## 12. 社群闭环

### 责任伙伴
承诺 → 见证 → 外部观察 → 标记 external_observation_candidate → Aurora 显性确认

### 共性错因
匿名聚合 → 影响小测/任务模板/节点难度
用户看到："这个点不只是你容易错，同目标用户也常错"

### 共享资料
Community Resource Pool → 质量评分 → Aurora 推荐 → 用户确认后进入个人库

隐私边界：只匿名聚合 / 不暴露个人资料 / 不自动污染上下文

---

## 13. 完整用户体验剧本（Day 0-4）

### Day 0: 进入计网冲刺
用户："我7天后计网考试，基本没学，先别挂。"
→ Sparkle 引导上传课件+往年题+作业
→ 资料挂载到知识星图，识别覆盖/不足
→ 建议12分钟诊断小测

### Day 1: 生成任务卡
→ 最危险节点识别
→ 任务卡绑定具体资料片段
→ 用户感觉"它把文件变成了计划的一部分"

### Day 2: 用户问问题
→ Aurora 自动决定是否用资料
→ Context Receipt 显示决策
→ 用户可以"按课件重讲"

### Day 3: 社群信号
→ 匿名共性错因标注到节点
→ 不打扰，只在知识星图显示

### Day 4: Aurora 自我校准
→ 资料策略失效检测
→ 显性问用户："我看课件没用？还是概念没懂？"
→ 用户反馈改变后续 ContextPlan

---

## 14. 核心对象数据模型

### SourceAsset
```json
{
  "source_id": "", "title": "", "type": "slides|pdf|past_exam|notes|homework",
  "course": "", "goal_id": "", "quality_score": 0.0,
  "mapped_nodes": [], "recommended_uses": [], "not_recommended_uses": []
}
```

### ContextPlan
```json
{
  "retrieval_mode": "targeted_graph_rag",
  "source_scope": "auto|user_selected|task_bound|goal_bound",
  "must_load": [], "may_load": [], "do_not_load": [],
  "token_budget": 3600, "citation_required": true,
  "pollution_guard": "strict", "user_visible_receipt": true
}
```

### ContextReceipt
```json
{
  "used": [], "excluded": [], "allow_user_override": true, "actions": []
}
```

### CommunitySignal
```json
{
  "signal_id": "", "scope": "course|goal|cohort", "node_id": "",
  "signal_type": "common_mistake|resource_quality|commitment_checkin",
  "privacy_level": "aggregate_only", "can_affect_planning": true
}
```

### ModelWriteEvent
```json
{
  "source": "task_feedback|quiz|user_correction|partner_signal",
  "target_model": "knowledge|user|goal|situation|sparkle_self",
  "confidence": 0.62, "write_scope": "ephemeral|sprint|long_term_candidate",
  "needs_user_confirmation": true
}
```

---

## 15. Aurora 决策指标

```
request_source_need    - 用户请求是否需要资料 grounding
goal_specificity       - 是否和当前目标强相关
node_uncertainty       - 知识节点当前是否不确定
source_relevance       - 资料片段和问题是否相关
source_quality         - 资料质量是否足够
token_pressure         - 上下文预算是否紧张
pollution_risk         - 资料是否可能污染回答
user_pinned_sources    - 用户是否手动指定资料
task_binding           - 当前任务是否绑定资料
citation_need          - 是否需要可追溯依据
model_uncertainty      - 标准层是否对答案把握不足
strategy_phase         - 当前阶段（诊断/执行/复盘/考前24h）
community_permission   - 是否允许使用社群聚合信号
privacy_sensitivity    - 是否涉及私人资料
```

输出：用什么 / 不用什么 / 为什么 / 多少预算 / 是否告诉用户 / 是否允许覆盖

---

## 16. Demo 必须出现的10个体验点

1. 上传资料后，知识星图节点被点亮
2. 对话中能看到"本轮用了哪些资料/没用哪些资料"
3. 用户可以手动选择某份资料参与回答
4. Sparkle 能解释为什么不加载完整课件
5. 任务卡明确绑定资料
6. 小测错因写回知识节点
7. 下一次回答因为错因不同而改变策略
8. Aurora 状态带显示上下文决策
9. 混合时间轴能记录一次完整闭环
10. 社群至少展示一个匿名共性错因或共享资料推荐

---

## 17. 给 Code Agent 的执行口径

```
本阶段目标不是做普通 RAG 知识库，而是做 Goal-Aware Knowledge Loop。

用户上传的资料必须先进入 Source Library，再被解析为 SourceSlice，
并挂载到 Knowledge Star Map 节点。

资料不能默认污染每轮上下文。
每轮对话前，Aurora 必须生成 ContextPlan。

前端必须让用户感知这些决策：
- Aurora 状态带显示本轮是否调用资料
- Context Receipt 显示用了哪些/没用哪些
- Source Tray 允许用户选择资料参与本轮/当前任务/当前目标
- 知识星图节点显示资料覆盖、错因、任务和社群洞察
- 任务卡显示使用资料和完成后的状态更新

不要做成文件夹 + RAG。
要做成：资料 → 知识星图 → Aurora ContextPlan → AI 输出
→ 任务执行 → 错因反馈 → 模型更新 → 下一轮更好输出。
```

---

**文档结束** | 此文档是产品设计的唯一真值源。
