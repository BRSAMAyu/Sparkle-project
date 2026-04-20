# SPARKLE Aurora Stage 16 Rule Y Definition (2026-04-20)

> Rule ID: `Rule Y`
> 主题: 推断式画像写入治理
> 所属阶段: Stage 16 `WS-MWL-RULE`

---

## 一句话定义

**Rule Y**: AI 只能把 chat 等流量中高置信、可追溯、可衰减、可撤销的推断结果写入 `EpisodicMemory.inferred_extraction` 子通道，且不得冒充用户显式确认。

## 适用边界

- 仅作用于 `EpisodicMemory` 的 `inferred_extraction` 子通道
- 不覆盖 `explicit User Correction`
- 不授权写入结构化偏好、trait、技能、掌握度、Aurora 决策记录

## 强制四要素

每条 Rule Y 写入都必须携带：

1. `confidence`
   浮点 `[0, 1]`
2. `evidence_token`
   指向触发该推断的原始 chat turn / event id
3. `decay_policy`
   声明有效窗口，例如 `7d` / `30d` / `persistent`
4. `source_lane`
   固定为 `inferred_extraction`，不得复用 `explicit_correction`

## 与 Rule K / Rule P 的关系

- Rule Y 是 Rule K 在 chat-originated inferred write 上的子规则，不是替代
- Rule P 保持不变：用户显式纠正永远走 `User Correction` lane

## 允许的最小主张

Rule Y 允许的只是：

- “AI 从你最近的对话里推断出一条可能有价值的经历/上下文”

Rule Y 不允许的主张：

- “系统已经确认你的稳定人格特质”
- “系统已经把你的聊天推断升级为结构化偏好”
- “系统可以据此直接驱动 Router / Push / Accountability”

## 至少三类禁止场景

1. 把 chat 中的情绪波动写成结构化 trait
   例：把“我今天好烦”写成长期人格或稳定情绪标签
2. 把未确认的意图升级成结构化偏好
   例：把一次“我今天想简短一点”写成持久 `response_style`
3. 把推断写入没有证据锚点的结构化事实表
   例：把聊天里模糊提到的技能水平直接写入 mastery / profile
4. 在没有 decay / revoke 的情况下保留一次性上下文
   例：把“这周要赶 ddl”永久保留
5. 用 inferred lane 覆盖 explicit correction
   例：用户刚撤销某条 AI 推断，系统又用新推断把它写回来

## 执行含义

Rule Y 的实现必须同时保证：

- `default OFF`
- `readable`
- `declarable`
- `revocable`
- `kill-switchable`
- `non-consumable by downstream decision paths`

## Stage 16 内的裁定标准

若 Stage 16 无法同时满足上述治理条件，则允许退回 `Path B` 或 `Path C`，但不允许带着半成品 inferred write 继续推进到 Stage 17。
