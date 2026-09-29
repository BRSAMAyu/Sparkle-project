# V4-G05 一审 receipt（R1 独立审查）

- **审查者**：R1（独立会话，未参与 G05 实现）
- **日期**：2026-09-29
- **对象**：commit `e4df7419`（分支 `agent/v4/g05`，base `00d1543a`，worktree `/Users/brsama/code/GitHub/wtG05`，审查起点工作树干净；断点续跑交付，前任 9 源+1 测试脏文件全部保留在案）
- **方法**：只读审查 + 独立复跑 + 6 对四风格独立验算（自写 WCAG 亮度实现、同一 ThemeManager 令牌管道）+ 对照探针亲跑 + 3 处 mutation 亲跑（用后即还原，结束工作树干净）+ 豁免三处逐一复核；产物除本 receipt 外零落盘
- **总裁决**：**PASS_WITH_CHALLENGES**（普通风险单审通过；R1-C1/R1-C2 两项 revert 保护缺口与 R1-O1~O3 三项注记随 receipt 登记，均非阻塞，不碍销账）

---

## 1. 审查靶逐项下判

### 1.1 U13 契约零 diff（最重红线）— 通过

`git diff --name-only 00d1543a..e4df7419` = 15 个 lib/ 呈现文件 + 1 个测试 + 证据。契约消费层三文件（`insights/data/models/evidence_insight_card.dart`、`insights/data/repositories/evidence_insight_repository.dart`、`insights/presentation/providers/evidence_insight_provider.dart`）零触碰。diff 全文扫描：唯一新增类 `_LegendDashPainter`（图例虚线样例 CustomPainter）；无 Navigator/GoRouter/onTap/setState/Future 行为改动；`Text(` 仅缩进重排，字面文案零变化。E 组语义钉（撤回排除/证据不足/样本定义/可忽略行 + 禁百分比）四风格逐字在案。**红线未破。**

### 1.2 续跑交接完整性 — 通过

前任修复面逐处 diff 在位：heatmap 标题/统计图标 shade600→全强度（2 处）；pattern_list 四槽（类型章撤 tint、类型标签/描述/页脚→语义槽、方案 successLight→success）；directive_audit pill 0.1→0.05；forecast 图标 shade600→全强度（2 处）；evidence_card chip 0.08→0.05；return_case 图标 0.7→全强度；risk_observation neutral500→textSecondary + `_getRiskColor` 三分支 shade600→全强度；radar 对比系列 outline@0.7→textSecondary 实色（虚线 6/4 保持）；reduce-motion 等价 ×3（雷达展开/趋势描线 700ms/计数动画，`context.reduceMotion ? Duration.zero : …`）。无丢弃、无重复实现。

### 1.3 对比度守卫真实性 — 通过（数值逐位核实）

R1 独立验算（自写亮度公式，同令牌管道，四风格全算）：**6 对采样中 5 对旧值与交付自报值逐位一致**——编年史旧墨 cs.secondary 2.78（自报 2.78）、任务失败框旧 0.1 tint 4.45（4.45）、深度 pill 旧 0.12 4.49/4.50（4.49–4.50）、hub hero 旧 0.16 止点 4.37（4.37）、tab 旧 tint 边界 1.16/1.25/1.32/1.26（自报区间 1.16–1.32）、雷达对比 textSecondary/chartBg 4.81–6.90（4.81–6.90）。修复后状态全部 ≥ 阈值：pill 墨 textPrimary 6.53–14.42、失败框 0.05 底 4.76–6.66、深度 pill 4.95–6.64、hero 0.08 止点 4.90–8.05、tab 描边 capsuleAccent/s2 3.49–9.56（≥3.0 图形阈）。**对照探针亲跑通过**（旧公式 classic 确实低于阈值 11 处，守卫可失败非恒绿）；A 组守卫含 cs.primary/chartBg、warning/chartBg、textSecondary/chartBg 三对 3.0 下限在案。注记 O1：两处注释数值口径偏宽（见 §3）。

### 1.4 图表区分度三层防御 — 通过（第 1/2 层数值实证；第 3 层结构实证， revert 保护见 C2）

- **趋势次系列**：`_buildDashedSmoothPath`（PathMetrics 6/4 步长）+ 图例 `_LegendDashPainter` 虚线样例，形状双编码成立；次系列 warning/chartBg ≥3.0 守卫在 A 组。
- **雷达对比系列**：虚线 6/4（`_RadarChartPainter._drawDashedLine`）+ textSecondary 实色 4.81–6.90:1（R1 独立验算一致），旧 outline@0.7 = 1.83–1.93（<3.0，对照探针在案）。
- **tab 指示**：tint 0.14 填充 + 全强度 capsuleAccent 描边；边界对 3.49–9.56 ≥3.0，标签墨 textPrimary on tint 底 ≥4.5（A 组双对在案）。**但该修复点无任何回退检测钉（C2）。**

### 1.5 测试宿主 3 处修 — 判「测试装置合理化」，非掩盖产品缺陷

- **庆祝对话框**：`MirofishMilestoneService.celebrateIfFirstTime`（mirofish_milestone_service.dart:24-56）为真实产品行为——首报弹 AchievementUnlockDialog（barrierDismissible=true，prefs 键 `mirofish_milestone_v1:firstReport` 源头闸）。测试预置已解锁旗 = 合法 fixture 态；对话框吸收拖拽是模态标准行为，非产品缺陷。U13 测试不受影响（其通道 mock 恰含 `'flutter.'` 前缀同键）核实成立。
- **常驻 ModalBarrier**：`grep ModalBarrier lib/` 零命中——树内 barrier 是 Flutter 每路由自带的框架件，非产品码。撤除角点补偿（每轮 300ms 泵）是移除测试冗余，且明确为保 C 组挂载帧观察窗口，理由链在测试注释可追溯。
- **控制组**：撤 1ms 泵假设改「挂载帧断非终值 + settle 终值等价」比前任更强（对动画通道的活性证明），亲跑绿。注记 O3：挂载帧断言对慢机有边界抖动风险（≤100ms 退出 vs 400ms 动画），非阻塞。
- 三处修均使测试变严或等效，未发现任何被遮蔽的产品缺陷。

### 1.6 mutation 独立性 — M1 红 / M2 绿 / M3 绿（后两者构成 C1/C2）

| Mutation | 改动 | 结果 |
|---|---|---|
| M1 | evidence_insight_card.dart chip 0.05→0.14 | **20+1 红**（B 组 widget 钉命中，符合预期） |
| M2 | curiosity_capsule_screen.dart 撤 tab 描边 | **21/21 全绿**（无任何测试红——预登记建议「tab 描边删除→边界对红」不成立，见 C2） |
| M3 | capsule_jobs_screen.dart pill 0.05→0.15 | **21/21 全绿**（A 组为公式级守卫，产品码回退不可测，见 C1） |

三次 mutation 后均 `git checkout --` 还原，结束工作树干净（`git status` 空）。router_smoke/a11y_batch6a 等其余在库测试不覆盖被 mutate 面，M2/M3 全仓不可测结论成立。

### 1.7 回归与工具链 — 通过

R1 亲跑（全部 `--concurrency=1` 错峰）：`flutter analyze` 零 issue；g05 21/21；report/reviews/cognitive 20/20；insights 35 + widget 12 = **47/47**（与 run_manifest 计数一致）；q03 longtail 9/9。对照探针、C 组、控制组单独抽跑均绿。

### 1.8 登记未修 3 处豁免 — 三处全部正当

1. **pattern_card.dart（PatternCard）**：全仓（lib/+test/）零 import 方——死代码核实，登记给仓库整洁流程恰当，不动正确。
2. **pattern_list_screen.dart:135 空态图标 prismPurple@150/255≈0.59**：纯装饰插画，语义由空态标题/文案承载；ACCESSIBILITY_ASSETS 阈值条款限「正文/大字/非文字关键部件」，装饰件豁免口径成立。
3. **forecast:182 errorContainer@0.7**：R1 以真实 `colorScheme.errorContainer` 角色色复算（cs.error 文本于 errorContainer@0.7 叠 s1/ambient）= **4.90–6.68:1 四风格全 ≥4.5**，豁免成立。（R1 首算误用 semanticError@0.7 得 1.55–1.83，读源码纠正模型后推翻初判——留此存照。）

### 1.9 验收边界（挑战 1）— 口径成立

G05 卡 `no_duplicate_rule` 原文即「与 Q05 分工：G 系列做实现打磨（修到完备），Q05 做三端重卡审查（HEAVY 截图矩阵）——G 卡返绿使 Q05 审查有据可过」。widget 级宿主截图（360×800@2x + 语义树 11 对，sha256 抽 4 份与 manifest 逐位一致）+ limitations.md 明示「非真机截图；HEAVY 矩阵归 Q05」——分工有卡面授权、披露如实，口径成立。

---

## 2. 发现列表（编号裁决）

### R1-C1（P2·非阻塞）A 组守卫对「产品码回退」不可测，测试头注释声明过宽

- **位置**：mobile/test/core/design/g05_family_four_style_test.dart:363-365（「任一风格跌破阈值即红（调色板锚值漂移或修复点回退都会在此失败）」）
- **证据**：M3（capsule_jobs pill 0.05→0.15）21/21 全绿。A 组 41 对为公式级（测试内复刻修复后公式），能红于「调色板锚值漂移」，不能红于「产品码回退」；回退保护仅 B/E 组 widget 钉覆盖的子集（evidence chip/risk 徽章/heatmap 图标/pattern_list 四槽/hero 渐变）。
- **复现**：改 `capsule_jobs_screen.dart:152` alpha 0.05→0.15 → `flutter test test/core/design/g05_family_four_style_test.dart --concurrency=1` → 全绿。
- **结论**：修复本身真实在码（R1 独立验算证实），不碍本次销账；但「修复点回退都会在此失败」应收敛为「调色板漂移即红；widget 钉子集回退即红」，或为未钉修复点补 widget 钉。

### R1-C2（P2·非阻塞）tab 指示「tint+描边」修复零回退保护（预登记建议 mutation 未红）

- **位置**：mobile/lib/features/cognitive/presentation/screens/curiosity_capsule_screen.dart:83（`border: Border.all(color: DS.capsuleAccent)`）
- **证据**：M2 撤描边 21/21 全绿；A 组「胶囊tab指示边框 capsuleAccent vs s2 ≥3.0」为调色板属性对，与产品是否真画描边无关；全仓无其他测试断言该描边存在。
- **复现**：删 :83 行 → 同上跑 → 全绿。
- **结论**：双编码修复当前可静默回退。建议补一个 B 组式 widget 钉（断言 TabBar indicator decoration 含 capsuleAccent 边框）。同族缺口：趋势次系列虚线与雷达对比系列实色也无 widget 级回退钉（仅调色板对）。

### R1-O1（P3·注记）两处注释数值口径偏宽

- learning_insights_overview_screen.dart:376-378「四风格 3.95–4.44:1（<4.5:1）」——R1 复算 classic 3.95–4.36 + dusk 4.43–4.69 失败，但 paperDay 4.90–5.23、quiet 4.74–6.82 于旧公式**达标**；「四风格」读作全失败不准确（修复必要性仍成立，classic/dusk 失败足够）。
- capsule_jobs_screen.dart:151「0.05 起四风格 4.85–7.05」——R1 于 s2 底复算 classic = 4.76（仍 ≥4.5，守卫判值不受影响，自报下限略偏）。

### R1-O2（P3·注记）golden 覆盖与验收②字面差距（已披露）

- 验收②「四风格各有确定性 golden+语义钉」：证据卡与报告面 4×2=8 对齐全；pattern_card 仅 classic、review hub 仅 quiet（limitations.md 已披露「quiet 抽查」）。CI 语义钉层面 E 组对证据卡+报告四风格全跑、认知读面四风格 presence 在案。差异已披露、方向合理，登记即可。

### R1-O3（P3·注记）控制组挂载帧断言的慢机抖动风险

- 控制组依赖「scrollUntilMounted ≤100ms 退出 vs 400ms 展开动画」时序差；慢 runner 上挂载帧可能已近终值致偶发红。 bounded、失败方向为假红不假绿，非阻塞。

---

## 3. 命令与 exit code 清单

| 命令（cwd=wtG05/mobile，除注明） | 结果 |
|---|---|
| `git status` / `git rev-parse HEAD` / `git rev-parse 00d1543a` | 干净 / e4df7419 / 00d1543a |
| `shasum -a 256`（证据 PNG 抽 4 份 vs run_manifest） | 逐位一致 |
| `flutter analyze` | 0 issue, exit 0 |
| `flutter test test/core/design/g05_family_four_style_test.dart --concurrency=1` | 21/21, exit 0 |
| 同上 `--plain-name "对照探针"` | 1/1, exit 0 |
| 同上 `--plain-name "reduce-motion"` / `"控制组"` | 2/2、1/1, exit 0 |
| `flutter test` + R1 临时复算探针（6 对×4 风格+豁免 P8 修正，用后即删） | 数值见 §1.3/§1.8, exit 0 |
| M1 `0.05→0.14`（evidence chip）+ g05 套件 | 20+1 红 → 还原 |
| M2 撤 tab 描边 + g05 套件 | 21/21 绿 → 还原（C2） |
| M3 jobs pill `0.05→0.15` + g05 套件 | 21/21 绿 → 还原（C1） |
| `flutter test test/features/report test/features/reviews test/features/cognitive --concurrency=1` | 20/20, exit 0 |
| `flutter test test/goldens/q03_visual_qa/q03_visual_qa_longtail_test.dart --concurrency=1` | 9/9, exit 0 |
| `flutter test test/features/insights --concurrency=1` | 35/35, exit 0 |
| `flutter test test/widget/p2_06_lifecycle_directive_audit_test.dart --concurrency=1` | 2/2, exit 0 |
| `flutter test test/widget/insights_frontend_smoke_test.dart test/widget/learning_insights_navigation_test.dart --concurrency=1` | 10/10, exit 0 |
| 终态 `git status` | 干净（仅本 receipt 待提交） |

资源纪律：全部 flutter test `--concurrency=1`；磁盘 32Gi free。
