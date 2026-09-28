# 前沿依据、采用与边界

这里的研究支持设计动机，不代替产品试验；本包自己的方案明确为提案。没有“超越所有系统”的证据。

## R01 · Effective context engineering for AI agents

Anthropic｜2025-09-29｜[原始来源](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

工程建议：上下文有限，按任务选择高信号资料；支持渐进加载。

**Sparkle选择：** 采用小而相关的context与来源；不能把少token自动等于更智能。

## R02 · MemRL: Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory

arXiv｜2026-02-12 v2｜[原始来源](https://arxiv.org/abs/2601.03192)

研究把稳定推理与可塑记忆分开，检索结合语义和环境反馈效用。

**Sparkle选择：** 借鉴效用选择；不照搬基准奖励到人的学习，不宣称Sparkle已有论文收益。

## R03 · Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models

arXiv / ICLR2026｜2026-03-29 v3｜[原始来源](https://arxiv.org/abs/2510.04618)

使用增量生成、反思、整理形成可演化context/playbook，避免反复整体改写丢细节。

**Sparkle选择：** 映射到受限经验卡与版本；不让线上模型任意改权限或系统prompt。

## R04 · Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects

arXiv｜2025-12｜[原始来源](https://arxiv.org/abs/2512.12818)

区分多种记忆信息并组织retain/recall/reflect过程。

**Sparkle选择：** 作为现有五层模型的对照，不重复造新的记忆数据库。

## R05 · Web Content Accessibility Guidelines 2.2

W3C｜2024-12-12 recommendation｜[原始来源](https://www.w3.org/TR/WCAG22/)

可测的对比、焦点、目标尺寸、缩放和替代操作要求。

**Sparkle选择：** 工程测关键条款；48dp为项目标准，不称是全部WCAG条款或已全面认证。

## R06 · CustomPainter.semanticsBuilder

Flutter API｜accessed 2026-09-28｜[原始来源](https://api.flutter.dev/flutter/rendering/CustomPainter/semanticsBuilder.html)

自绘图形的可访问语义需显式构建，不能假设像素画布自带节点。

**Sparkle选择：** 装饰与操作分开，星图有语义列表；不把所有原生控件画成一张图。

## R07 · Playing haptics

Apple HIG｜accessed 2026-09-28｜[原始来源](https://developer.apple.com/design/human-interface-guidelines/playing-haptics)

触觉使用一致的语义、短促、克制并让用户可关闭，与视觉声音互补。

**Sparkle选择：** 按回执统一反馈，支持平台差异；不证明模拟器可评价真实触感。

## R08 · Android haptics API reference

Android Developers｜accessed 2026-09-28｜[原始来源](https://developer.android.com/develop/ui/views/haptics/haptics-apis)

不同设备支持不同反馈能力，应选择语义接口并探测适配。

**Sparkle选择：** unsupported静默等价，不借长震动制造“有反馈”。

## R09 · Habitica — Gamify Your Life

Habitica｜accessed 2026-09-28｜[原始来源](https://habitica.com/)

官方产品把任务、习惯与角色、奖励、社交玩法结合。

**Sparkle选择：** 像素/RPG任务不是独创护城河；不复制惩罚机制和游戏资产。

## R10 · About Finch

Finch｜accessed 2026-09-28｜[原始来源](https://finchcare.com/about-finch)

官方产品把虚拟伙伴、目标、反思和陪伴式成长相连。

**Sparkle选择：** 视觉陪伴已有竞品；Sparkle应靠可校准学习协作而非更黏人的宠物。

## R11 · Generative AI without guardrails can harm learning: Evidence from high school mathematics

PNAS｜2025｜[原始来源](https://doi.org/10.1073/pnas.2422633122)

特定高中数学实验区分AI辅助练习与移除AI后的独立表现，提示工具设计影响技能获得。

**Sparkle选择：** 保留human_required和独立检验；不把该研究外推为本产品已提高大学生成绩。

## R12 · LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

arXiv｜2024-10｜[原始来源](https://arxiv.org/abs/2410.10813)

覆盖长期记忆中的多会话、时序、更新、抽取与拒答等能力。

**Sparkle选择：** 借鉴测试切片，另加行动效用；记忆问答高分不等于用户成长。

## R13 · Hidden in Memory: Sleeper Memory Poisoning in LLM Agents

arXiv｜2026-05｜[原始来源](https://arxiv.org/abs/2605.15338)

研究持久记忆可能将不可信输入转化为后续影响，提示来源权限必须保留。

**Sparkle选择：** 测试资料→反思→假用户偏好的污染链；不提供进攻性产品能力。

## R14 · Performance best practices

Flutter｜accessed 2026-09-28｜[原始来源](https://docs.flutter.dev/perf/best-practices)

关注布局/构建/绘制开销及昂贵saveLayer等路径，需实际profile。

**Sparkle选择：** 像素装饰需预算，不能用debug截图证明帧率。

## R15 · Effective harnesses for long-running agents

Anthropic｜2025-11-26｜[原始来源](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

长期agent需要持续状态、增量工作和可检查交接，而非仅一条长prompt。

**Sparkle选择：** 沿用当前fleet/worktree/证据，不再造一个多Agent管理平台。

## 我们提出的组合

把合法来源、历史效用、决策性澄清、六字段策略、真实回执与统一感官语义连成一条链，是针对Sparkle现有工程的设计综合，不声称原创科学定理或专利。首要实验是该组合是否赢过更简单的无历史基线。风险不是缺少最新术语，而是选用了无用经验、把代理指标当学习结果、用漂亮动效掩盖慢响应。
