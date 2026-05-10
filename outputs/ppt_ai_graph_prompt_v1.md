# AI 生图 Prompt — Sparkle 图编排目标实现系统 + 北极星场景

## 使用建议

- **适用模型**: Midjourney v6 / DALL-E 3 / Ideogram / Flux Pro
- **宽高比**: 16:9（PPT 横版）
- **风格关键词**: isometric illustration, tech startup pitch deck, clean flat design, white background

---

## Prompt（英文版，可直接用于生图）

### 主 Prompt

```
A clean, professional infographic for a startup pitch deck, 16:9 aspect ratio, on a pure white background, in a modern flat isometric illustration style with soft gradient colors (deep blue #1a1a2e, electric purple #6c5ce7, warm orange #f39c12, mint green #00b894, coral pink #e17055).

LEFT SIDE (40% width) — "Graph-Based Goal Achievement Engine":
An elegant architecture diagram showing THREE interconnected flowcharts arranged vertically, each inside a rounded rectangle card with subtle shadow:

CARD 1 (top, label "Chat Graph"):
A small horizontal flow: [User Message] → circle "Router" → branches into 3 paths:
- Path A: [Single Expert] → [Generate] → [Review] → END (labeled "Fast Path")
- Path B: [Multi-Expert] → [Collaborate] → [Aggregate] → END (labeled "Smart Route")
- Path C: [Tool] → [Execute] → [Review] → loop back (labeled "Action Loop")
A small icon of a brain with routing arrows sits next to the Router node.

CARD 2 (middle, label "Expert Network"):
A circular node graph showing 6 expert nodes arranged in a circle:
- Math (Σ icon), Science (🔬 icon), Code (</> icon), Writing (✎ icon), Knowledge Map (🌐 icon), Study Coach (🎯 icon)
- All nodes connect to a central hub labeled "Dynamic Router"
- Lines between experts glow when "active", showing collaboration paths

CARD 3 (bottom, label "Planning Graph"):
A simple linear flow: [Goal Input] → [Decompose] → [Prioritize] → [Plan Output]
With a "feedback loop" arrow going from Plan Output back to Decompose, labeled "Adapt"

A vertical dashed line separates left and right sides, with small data-flow arrows crossing from left to right at multiple points, suggesting the engine feeds into the user journey.

RIGHT SIDE (60% width) — "7-Day Exam Sprint — User Journey":
A horizontal timeline running from left to right across the right panel, showing 7 days as 7 circles connected by a glowing progress line that changes color from red (Day 1: "Zero Knowledge") through orange (Day 3-4: "Core Concepts") to green (Day 7: "Exam Ready ✓").

Above the timeline, 3 key moments are highlighted with callout boxes:

MOMENT 1 (Day 1, top callout):
"Knowledge Gap Scan" — A small illustration of a radar/scanner sweeping over a knowledge map, highlighting RED gaps (unknown) vs GREEN areas (known). Text label: "Finds minimum passing path, NOT full syllabus coverage"

MOMENT 2 (Day 3-4, top callout):
"Adaptive Expert Routing" — A small illustration of the 3 collaboration modes as icons:
- Sequential chain icon: A→B→C (labeled "Build foundation step by step")
- Parallel icon: three arrows diverging then converging (labeled "Cover weak spots simultaneously")
- A debate icon: two arrows pointing at each other (labeled "Resolve confusion from multiple angles")

MOMENT 3 (Day 6-7, top callout):
"Exam Simulation & Reinforcement" — A small illustration of a progress bar nearly full, with error patterns being flagged and corrected in real-time.

Below the timeline, a bold statement box with dark background:
"Result: Zero-knowledge → Exam-passing in 7 days"
"AI finds the SHORTEST PATH through knowledge graph — not comprehensive learning, but MINIMUM VIABLE PASSING PATH"

At the very bottom of the right side, 3 small metric cards in a row:
- "40% less study time" (icon: clock with arrow down)
- "2.3x knowledge retention" (icon: brain with upward arrow)
- "Adapts every session" (icon: refresh cycle)

Overall style: clean, modern, minimalist. No cluttered text. Soft shadows. The color palette uses blue/purple for technology elements and warm orange/green for user-facing elements. The left side feels technical but approachable; the right side feels human and achievement-oriented. Designed for a professional investor pitch deck.
```

---

### 简化版 Prompt（如果主 Prompt 太长被截断）

```
Professional pitch deck infographic, 16:9, white background, flat isometric style.

LEFT 40%: "AI Engine Architecture" — Three stacked cards showing:
1) Chat routing flowchart with branches for single-expert fast path, multi-expert collaboration, and tool execution loops
2) Expert network as a circular node diagram with 6 AI specialists connected to a central router
3) Planning graph with goal decomposition and adaptive feedback loop
Data flow arrows cross from left to right.

RIGHT 60%: "7-Day Exam Sprint Journey" — Horizontal timeline with 7 day-circles connected by a color-gradient progress line (red→orange→green). Three callout moments above the timeline:
Day 1: "Knowledge Gap Scan — finds minimum passing path, not full syllabus"
Day 3-4: "Adaptive Expert Routing — sequential/parallel/debate modes auto-selected"
Day 7: "Exam Ready — shortest path through knowledge graph"
Below timeline: bold result box "Zero-knowledge → Exam-passing in 7 days"
Three metric cards at bottom: "40% less study time", "2.3x retention", "Adapts every session"

Colors: deep blue #1a1a2e, purple #6c5ce7, orange #f39c12, green #00b894. Clean, modern, minimalist, investor-ready.
```

---

## 设计意图说明（给设计团队参考）

### 视觉叙事逻辑

**左侧（引擎）** 讲 "怎么做到"：
- 三张图的架构简化为三张卡片，各用一条主线表达
- Chat Graph → 强调"路由"和"三条分支"
- Expert Network → 强调"多专家协作"
- Planning Graph → 强调"自适应反馈环"

**右侧（体验）** 讲 "做到了什么"：
- 7天时间线是最直观的叙事载体
- 三个关键时刻对应系统三个核心能力
- 底部数据卡提供可信度

### 为什么强调 "Minimum Viable Passing Path"

这是 Sparkle 与竞品的核心差异：
- **ChatGPT/Clafta**: 给你全部内容，你自己找重点
- **Sparkle**: 扫描你的知识盲区 → 在知识图谱上找最短通关路径 → 只学你需要学的

这不是"偷懒学习"，而是 **图论中的最短路径问题** —— 把考试通过视为在知识图谱上从"零基础"到"及格线"的最短路径搜索。多专家协作（sequential/parallel/debate）是搜索过程中针对不同类型知识瓶颈的最优策略。

### 配色逻辑

| 区域 | 颜色 | 含义 |
|------|------|------|
| 技术架构（左） | 深蓝 #1a1a2e + 紫 #6c5ce7 | 智能、专业、技术感 |
| 用户旅程（右） | 橙 #f39c12 → 绿 #00b894 | 从挑战到成功的渐进 |
| 数据/结果 | 深色底 + 亮色字 | 高对比度，投资人对数字敏感 |

---

## 中文版 Prompt（如果用国产模型生图）

```
一张专业的创业路演PPT信息图，16:9横版，纯白背景，扁平等距插画风格。

左侧占40%，标题"AI图编排引擎"：
三个圆角卡片纵向排列：
卡片1"对话路由图"：用户消息→路由器→三条分支（单专家快速路径/多专家协作/工具执行循环）
卡片2"专家网络"：6个AI专家节点围绕中心路由器排列，协作时连线发光
卡片3"规划图"：目标输入→分解→排序→计划输出，带自适应反馈箭头
左侧向右侧有数据流箭头穿过虚线分隔

右侧占60%，标题"7天急救学习旅程"：
水平时间线从左到右7个圆点，连线颜色从红→橙→绿渐变
三个标注气泡：
第1天"知识盲区扫描——找到最小通关路径，而非全覆盖"
第3-4天"自适应专家路由——自动选择串行/并行/辩论模式"
第7天"考试就绪——知识图谱上的最短路径"
时间线下方深色结果框："零基础→7天通过考试"
底部三个指标卡："节省40%学习时间"、"2.3倍知识留存"、"每次对话自适应"

配色：深蓝#1a1a2e、紫色#6c5ce7、橙色#f39c12、绿色#00b894。风格简洁现代，适合投资人路演。
```
