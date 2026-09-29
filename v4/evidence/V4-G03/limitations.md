# V4-G03 limitations — 已知边界与登记项

## L-1 行为面登记（stop-condition：行为语义缺陷超风格面→登记不顺手修）

L10 规格句「记忆清空有明确说明和**可查询进度**，不被 3 次/天解释预算限制」——mobile 侧现无「记忆清空+进度查询」用户流（全库检索 `清空记忆/clearMemory/memoryWipe` 零命中；现存的更改/忘记均为单条操作走 U03/I06 链）。清空流本体是行为交付，不属本卡风格面范围；本卡已确保其前置文案面（预算说明/操作行）对比度达标。**建议登记 FIX/Q 卡裁决清空流的交付归属**。

## L-2 DS 层潜在面（家族面未触发，归 DS 收敛卡）

- SemanticPill **brand tone 在 classic-dark panel 面 4.40:1**、全 tone 在 classic-light/-dark **surfaceTertiary 面最低 3.94–4.32:1**——家族内存档面（memory_panel/why_this/understanding/evidence badge）只落 card/panel/secondary 面，全部 ≥4.51 达标；超出面集的组合属 DS 层（selected 态 0.18 同批，前任已登记）。修法需 container-pair 令牌（onContainer），不属本卡。
- semantic_pill 为 core/design 共享 owner：本卡沿用前任 alpha 收口（0.05/0.18），未再动 owner 结构。

## L-3 golden 形态边界

- 「确定性 golden」按 F05 判例交付为 env 门控确定性采集（PNG+语义 dump，同 build 同 seed）+ CI 可失败语义钉，**非 matchesGoldenFile 像素基线**——依据 V3-FIX-368 判例：异构渲染环境下像素基线产生假红/毁真源（dashboard golden 家族已改环境守卫）。若审查裁决需像素 golden，须先指定基线签发机。
- 证据 PNG 字形为测试环境 Ahem 块形（F04/F05 同先例）；语义 dump 正文跨档全同（语义不变量的直接实证），档位身份由头行令牌值承载。

## L-4 advisory 守卫登记

`scripts/check_hardcoded_strings.sh`（非 rule_guard_manifest 成员）对 diff 文件报 advisory 中文注释告警，exit=0。权威 I18N 覆盖守卫 PASS。命中行为注释/既有文案残留（含前任已 l10n 化文件的注释），注释清理不属风格面，未清。

## L-5 范围边界

- 全量守卫套件（backend python 系）未跑——本卡为 mobile UI 风格面，按 G 卡标准跑受影响域守卫（L10N-PARITY/I18N/UI-TOKENS/repeat）+ 分域回归；全量守卫基线归属集成卡。
- 深度走查覆盖家族三模块全部 presentation 面（16 产品文件 diff + 走查零 diff 面）；`curiosity_capsule_screen`/`memory_detail_screen` 走查无缺陷零 diff（字号/取色/对比度达标）。
- 预览通道外决策项零发现（stop-condition 3 未触发）；连续未改善反例零（stop-condition 2 未触发）。

## L-6 断点续跑形态

前任 dirty=19 全数继承（含其对 semantic_pill/aurora/cognitive/memory 的 11 组修复），本次盘点逐组复算确认有效后保留；前任方案缺陷 2 处就地修正（R6 首帧闪、R10 棘轮越线）；前任遗漏 8 处补修（R1–R5/R7–R9）。「前任已修/续跑修复」逐项标注见 diff_or_evidence_only.md §1。
