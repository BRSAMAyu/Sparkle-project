# Stage 28 NLP Bias Calibration

更新时间：2026-04-21

## 样本

| 语言 | 风格 | 文本摘要 | 期望方向 |
| --- | --- | --- | --- |
| zh-CN | structured_planner | 喜欢先拆步骤、按清单推进 | `conscientiousness +` |
| en-US | social_energized | 与人头脑风暴会补能量 | `extraversion +`, `agreeableness +` |
| ja-JP | quiet_reflective | 需要安静独处，也乐于尝试新想法 | `openness +`, `extraversion -` |
| es-ES | steady_low_dramatic | 偏好稳定节奏，不易因变化失衡 | `conscientiousness +`, `neuroticism -` |
| ar | warm_collaborative | 喜欢清晰目标下与人合作并维持团队平稳 | `agreeableness +`, `conscientiousness +` |

## 当前基线
- 样本数：5
- 目标门：跨文化偏差率 `< 10%`
- 连续 3 日超门限时：自动关闭 `AURORA_TRAITS_NLP_MODE`

## 约束
- 单次 LLM 调用只产生 observation candidate，不直写 trait。
- 仅使用本人文本，不做跨用户聚合。
- 输出仅描述倾向，不输出类型化判断标签。
