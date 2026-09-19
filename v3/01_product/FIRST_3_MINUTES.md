# First 3 Minutes — 第一眼惊艳不是特效

## 核心假设
第一眼惊艳来自 **“这个产品马上理解我正在做什么，并让我看到一个有价值的下一步”**，而不是 onboarding 动画。

## Screen 1 — Promise
文案方向：
- 标题：`把卡住变成下一步。`
- 副文案：`告诉 Sparkle 你最近真正想完成的一件事。我们一起把它推进到结果。`
- Primary：`开始我的目标`
- Secondary：`体验一个示例`

不要同时展示十个 feature icon。

## Screen 2 — Goal Capture
单个自然语言输入 + optional deadline/material。
支持直接粘贴课程/比赛/项目描述；如果系统能从文本提取，不让用户重复填表。

## Screen 3 — First Understanding
不是“我们已建立 75% 用户画像”。
展示：
- `我目前确认的目标`
- `我还不确定的一点`（如确有必要）
- `建议先做的一步`
- `为什么`

## Screen 4 — Action
Action Card：
- 产出；
- 预计时间；
- 完成证据；
- `你做 / Sparkle 做 / 一起做`；
- Start；
- `这个不合适`。

## Example Mode
体验示例可用现有“种子人生”，但必须：
- 顶部持续标识 `示例体验`；
- 禁止把 seed history 写入真实账户长期画像；
- 允许一键“用我的目标开始”；
- Demo Persona 的 Aurora 理解应通过可读条目展示，不用玄学百分比。

## Automated simulator acceptance
- fresh install / cleared state；
- 首屏 primary CTA 无滚动可见；
- 5 次不同 Persona 进入，不出现相同模板化 action；
- 3 分钟脚本以内到 Action；
- 所有 loading >500ms 有反馈；
- 错误不会回到空白页；
- 截图由视觉 Reviewer 按 rubric 打分。
