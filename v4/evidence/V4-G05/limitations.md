# V4-G05 · limitations

## 前任遗留测试缺陷（本次已修，非产品缺陷）

1. **庆祝对话框吸收拖拽**：G05 宿主 `freshThemeManager` 的 `SharedPreferences.setMockInitialValues` 会覆盖 setUp 注册的 shared_preferences 通道 mock，使首报里程碑庆祝（AchievementUnlockDialog，barrierDismissible）真实弹出并吸收全部拖拽——滚动位恒 0，雷达永不挂载。U13 测试不受影响（其通道 mock 恰好命中已解锁旗）。修复：报告宿主测试以 `initialPrefs: {'mirofish_milestone_v1:firstReport': true}` 源头消弹。
2. **常驻 ModalBarrier 角点补偿反噬**：树内存在常驻 ModalBarrier（非对话框），前任「barrier>1 才点」条件永假→对话框从未被关闭；续跑初版的角落补点分支又因常驻 barrier 每轮多泵 300ms，把雷达展开动画（400ms）在退出前老化为终值。修复：撤除 barrier 补偿，依赖源头消弹。
3. **控制组时序前提失效**：前任控制组假定「1ms 泵保持动画早段」——实际雷达挂载帧图例即可读；且雷达图例文本为 progress 驱动数值（挂载帧实测 49%→72%→80%→82%），存在可断言的中段真值。修复：撤 1ms 泵改 100ms 弹道泵 + 挂载帧断言（exit ≤100ms，实测非终值）+ settle 终值等价（S01 判例同构）。

## 登记未修（超风格面 / 低风险观察项）

1. `cognitive/presentation/widgets/pattern_card.dart`（PatternCard）：全仓无消费方（死代码），其 shade700 图标/brandPrimary 卡底为旧呈现式样；不删不修（登记给仓库整洁流程）。
2. `pattern_list_screen.dart:135` 空态插画图标 prismPurple@0.59：装饰性插画（空态文案承载语义），ACCESSIBILITY 装饰豁免，未动。
3. `learning_forecast_screen.dart:182` 错误框 errorContainer@0.7 底：cs.error 文本于其上四风格复算 ≥4.5:1（A 组实测通过），未动。
4. 胶囊 tab 选中指示的「tint+描边」式样：描边宽度取 Border.all 默认 1.0，视觉密度可由后续设计评审微调（对比度已四风格达标）。

## 证据边界

- 三读面×四风格证据为 widget 级宿主截图（360×800 逻辑，2x PNG）+ 文本语义树，非真机截图；卡片为 normal 档，HEAVY 截图矩阵归 Q05。
- 图表区分度专项为 token 公式层数值复算（F06 判例公式）+ 虚线形状双编码钉，未做感知实验。
- 复盘 hub 仅 quiet 抽查 + hero 渐变钉；其余三风格由 A 组 token 对覆盖。

## Errata (leader, 2026-09-30, R1 C1/C2 收口)
- C1：A 组 41 对系公式级守卫，产品码回退保护由 B/E widget 钉承载（测试头「修复点回退都会在此失败」声明收窄为公式面）。
- C2 已闭：tab 选中指示补 widget 回退钉 curiosity_capsule_tab_border_f569style_test.dart（断言 TabBar.indicator BoxDecoration tint@0.14+全强度描边；mutation 删描边→红/还原→绿双向实证）；jobs pill 面由 B 组公式钉+后续 Q05 视觉面兜底。
- O1-O3 注释数值偏宽处（overview pill 四风格口径/jobs ≥4.85→4.76）按本勘误为准。
