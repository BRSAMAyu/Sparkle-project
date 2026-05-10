# AI 生图 Prompt — Sparkle 持续学习与个人方法资产沉淀

## 定位
路演 PPT 核心页（Slide 8 深化版），严肃路演汇报用。
评委要在**5秒内**看懂：系统怎么从用户行为中自动沉淀方法资产、怎么跨目标迁移、越用越懂你的完整闭环。

---

## 配色规范

```
背景：深蓝灰 #0F1B2D（沉稳、严肃、深色调）
主文字：#E8EDF3（浅灰白，保证可读性）
辅助文字：#8899AA（中灰蓝）
流程线/箭头：#4A90D9（正蓝）
核心高亮：#E8A838（琥珀金 — 标记蒸馏关键步骤）
成功色：#3DB88C（深翠绿 — 标记进化终点）
卡片底色：#1A2A3F（深蓝卡片，比背景浅一级）
卡片边框：#2A3F5A（极细，1px）
禁止：渐变、毛玻璃、发光特效、大面积白色
```

---

## 主 Prompt（英文）

```
A serious, information-dense infographic for a formal startup competition pitch deck. 16:9 aspect ratio. Dark navy background (#0F1B2D). Professional, authoritative tone — no playful elements, no soft gradients, no glassmorphism. Dense layout: every pixel earns its place. Chinese text throughout.

TOP BAR (8% height):
Left: section tag "创新点四" in small caps, #8899AA
Right: page indicator "08", #8899AA
Center: main title in #E8EDF3, 24pt: "持续学习引擎 — 越用越懂你的方法资产沉淀"

MAIN BODY — SPLIT INTO TWO COLUMNS, NO GAPS:

LEFT COLUMN (55% width):

A vertical flow diagram with 6 compact nodes connected by thin blue arrows (#4A90D9). Each node is a dark card (#1A2A3F, 1px border #2A3F5A) containing:
- Left: step number in a small circle
- Center: step name in bold #E8EDF3
- Right: one-line explanation in #8899AA

Step 1: ❶ "行为记录" — "任务结果、反馈、纠正全部被记录"
  ↓
Step 2: ❷ "自动归因" — "系统分析什么策略对你有效、什么无效"
  ↓
Step 3: ❸ "策略蒸馏" — "从成功经验中自动提炼可复用方法论"
  [This card has an amber gold left-border #E8A838, marking it as the core innovation]
  ↓
Step 4: ❹ "脱敏验证" — "自动剥离隐私，通过质量门后入库"
  ↓
Step 5: ❺ "技能结晶" — "高频有效策略升级为可复用技能"
  ↓
Step 6: ❻ "智能迁移" — "新目标自动继承已验证的最优策略"
  [This card has a teal left-border #3DB88C]
  ↓
  A curved return arrow loops from Step 6 back to Step 1, labeled "每轮对话自动触发"

RIGHT COLUMN (45% width):

TOP HALF — "用户视角：跨目标迁移实证"
A compact horizontal timeline with 3 milestones:

┌─────────────┐  ──→  ┌─────────────┐  ──→  ┌─────────────┐
│ 第1天·计网   │       │ 第30天·数据库 │       │ 第180天·考研  │
│ 系统推荐     │       │ 计网验证的策略│       │ 系统已积累：  │
│ 真题优先策略  │       │ 自动迁移过来  │       │ 真题驱动      │
│              │       │              │       │ 45min粒度     │
│              │       │              │       │ 先练后补理论   │
└─────────────┘       └─────────────┘       └─────────────┘

Below timeline, a single-line highlight in #E8A838:
"策略无需手动总结，系统在每次交互中自动积累并跨目标迁移"

BOTTOM HALF — "三层资产结构"
Three stacked compact cards, each one line:

Tier 1: "个人方法库" — 薄弱点·有效资料·最优任务粒度
Tier 2: "策略信念" — 贝叶斯置信度·有效性衰减·自动降级
Tier 3: "可迁移技能" — 跨目标复用·社区共享·8级晋升

BOTTOM BAR (6% height):
Full-width, centered, #E8EDF3, 13pt:
"用一年后，留下的不是聊天记录 — 而是一套关于'你怎么才能做成事'的可迁移方法论"

OVERALL STYLE: Dark, dense, serious. Think B2B enterprise pitch or government technology review — not consumer app. Every element has a reason. No decorative whitespace. Colors are muted and professional. The amber gold (#E8A838) appears exactly once (distillation step) and the teal (#3DB88C) appears exactly once (migration endpoint). Information density is high but hierarchy is clear through typography weight and color, not through spacing.
```

---

## 简化版 Prompt

```
Serious pitch deck infographic, 16:9, dark navy background #0F1B2D, formal startup competition style. Dense layout, no wasted space. Chinese text.

LEFT 55%: Vertical 6-step flow with dark cards (#1A2A3F) connected by blue arrows:
① 行为记录 → ② 自动归因 → ③ 策略蒸馏 [amber border #E8A838] → ④ 脱敏验证 → ⑤ 技能结晶 → ⑥ 智能迁移 [teal border #3DB88C]
Loop arrow from ⑥ back to ① labeled "每轮对话自动触发"

RIGHT 45% TOP: "跨目标迁移实证" — 3 compact timeline cards:
Day 1 计网→Day 30 数据库(自动迁移)→Day 180 考研(已积累3项策略)
Highlight: "策略无需手动总结，系统自动积累并跨目标迁移"

RIGHT 45% BOTTOM: "三层资产结构":
Tier 1 个人方法库 | Tier 2 策略信念(贝叶斯) | Tier 3 可迁移技能(8级晋升)

Bottom bar: "留下的不是聊天记录 — 而是关于'你怎么做成事'的可迁移方法论"

Style: dark, dense, authoritative. Amber accent on distillation step only. Teal accent on migration endpoint only. No gradients, no glass, no playful elements.
```

---

## 中文版 Prompt（通义万相 / 可灵）

```
严肃路演汇报用信息图，16:9横版，深蓝灰色背景（#0F1B2D），紧凑布局不浪费空间，专业权威风格。中文内容。

页面分左右两栏，无间隙：

左栏55%宽度：纵向6步流程图
6个深蓝卡片（#1A2A3F）通过蓝色细箭头（#4A90D9）纵向连接：
❶ 行为记录 — 任务结果、反馈、纠正全部被记录
❷ 自动归因 — 系统分析什么策略对你有效、什么无效
❸ 策略蒸馏 — 从成功经验中自动提炼可复用方法论【左侧边框琥珀金#E8A838标记核心技术】
❹ 脱敏验证 — 自动剥离隐私，通过质量门后入库
❺ 技能结晶 — 高频有效策略升级为可复用技能
❻ 智能迁移 — 新目标自动继承已验证的最优策略【左侧边框深翠绿#3DB88C】
第⑥步底部有一条弧形回路箭头指回第①步，标注"每轮对话自动触发"

右栏45%宽度，分上下两部分：

上部分"用户视角：跨目标迁移实证"
三个紧凑卡片横向排列，用箭头连接：
第1天·计网（系统推荐真题优先策略）→ 第30天·数据库（计网验证的策略自动迁移）→ 第180天·考研（已积累：真题驱动/45min粒度/先练后补理论）
下方一行琥珀金色高亮文字："策略无需手动总结，系统在每次交互中自动积累并跨目标迁移"

下部分"三层资产结构"
三行紧凑卡片堆叠：
第一层：个人方法库 — 薄弱点·有效资料·最优任务粒度
第二层：策略信念 — 贝叶斯置信度·有效性衰减·自动降级
第三层：可迁移技能 — 跨目标复用·社区共享·8级晋升

顶部标题栏：持续学习引擎 — 越用越懂你的方法资产沉淀
底部全宽一行："用一年后，留下的不是聊天记录 — 而是一套关于'你怎么才能做成事'的可迁移方法论"

整体风格：深色、紧凑、严肃、权威。像企业级技术评审或政府科技汇报PPT。琥珀金只出现在蒸馏步骤，深翠绿只出现在迁移终点。信息密度高但层次清晰。无渐变、无毛玻璃、无装饰性留白。
```

---

## 设计意图

### 为什么用深色

浅色 = 消费级产品展示。深色 = 技术实力展示。路演评委看的是系统能力，不是 UI 好不好看。深色背景配合紧凑布局传递"这是工程系统，不是 demo"的信号。

### 为什么紧凑双栏

单栏横向6步浪费纵向空间。左栏流程 + 右栏实证/资产，上下填满，一页讲完不需要翻页。

### 视觉锚点

整个页面只有两个颜色跳脱：琥珀金（策略蒸馏 = 核心技术创新）和深翠绿（智能迁移 = 用户价值终点）。评委视线自然被引导到这两个节点。

### 口播建议（40秒）

> "用一年后，Sparkle 留下的不是聊天记录。
> 左边是完整闭环：每次行为被记录、自动归因、策略蒸馏、脱敏验证、技能结晶、智能迁移——每轮对话自动触发。
> 右边是用户真实感知：计网验证的策略，30天后自动迁移到数据库；180天后考研，系统已经积累了这个人的方法资产。
> 三层结构：个人方法库、贝叶斯策略信念、可迁移技能。
> 用户不需要手动总结。系统在每次决策、反馈和纠正中自动积累。
> 越用越懂你——不是记住对话，而是理解你怎么才能做成事。"
