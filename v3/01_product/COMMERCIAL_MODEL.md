# 商业模型与价值分层（工程版）

V3 不是商业定价最终版，但工程必须解除历史语义混用。

## 1. Entitlement 独立
`paid_plan / entitlement / quota` 与 `flame_level / photon / streak` 完全分离。

## 2. 免费层价值
免费用户必须体验完整核心价值闭环，不能因 fast tier 变成“看不懂我”的坏产品。
可限制：
- deep reasoning / agent runtime 次数；
- 大型文件与长期历史；
- 高成本多工具 run；
- 高级 analytics / export。

## 3. Pro 可售卖价值
优先按用户价值而不是模型名售卖：
- 更深 Goal Context；
- 更长可控记忆；
- Agent 协作额度；
- 高级 outcome analytics；
- 多项目/多材料；
- 更高成本的 deliberate planning。

## 4. 必须观测
- free requests 被能力 ceiling 降级的比例；
- 因额度无法完成的 high-value intent；
- 每个 WVPL 的模型成本；
- Agent/Human/Hybrid 的成本分布；
- 不能把 token consumption 当产品价值。
