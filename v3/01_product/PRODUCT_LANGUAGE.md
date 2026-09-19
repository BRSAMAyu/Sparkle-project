# Product Language — 用户语言，不说内部黑话

## 原则
1. 说用户正在做的事，不说系统内部对象；
2. 区分事实、观察、推测；
3. 避免心理诊断式语言；
4. 主动建议不道德评价；
5. 失败诚实；
6. 简短、具体、有下一步。

## 翻译表
| 内部术语 | 禁止直接显示 | 推荐表达 |
|---|---|---|
| Memory | 0 memories / correctable claims | `Sparkle 记住的事情` / `你可以修改这些理解` |
| inference | 用户画像推断 | `我根据最近几次行动有一个猜测` |
| confidence | 0.73 confidence | `我还不太确定` / `我比较确定`，详情可展开 |
| understanding_depth | 理解度 75% | `已确认 4 项 · 待确认 1 项` |
| RAG | 已召回知识块 | `参考了：OS.pdf 第…` |
| Agent run | run executing | `Sparkle 正在整理材料` |
| conflict | memory conflict | `你现在的说法和上次不同，要以这次为准吗？` |
| proactive trigger | goal stalled | `这个目标 3 天没推进；上次“先做样例”帮助过你，要这样继续吗？` |

## Aurora Tone
- 平等，不老师腔；
- 不过度热情；
- 不因用户失败就安慰模板化；
- 能说“我不确定”；
- 能说“这一次我不建议改计划”；
- 庆祝 outcome，不庆祝点击。
