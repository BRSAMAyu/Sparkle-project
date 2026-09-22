# B2-3a · 语义槽定标收尾 + DS.accent 存量迁移首波 交付报告

> worktree: `Sparkle-sysrev/wt118 @ main(48463ace)` ｜ 日期: 2026-09-22 ｜ 卡: **B2-3a**（B2-2 TODO 清偿 + 令牌迁移开闸首波）
> 载体: `theme_manager.dart`（textTertiary/neutralOutline 值层）＋ `sparkle_context_extension.dart`（语义面接线）＋ `routes.dart`（域外单点清偿）＋ 12 处 DS.accent 迁移（8 文件）＋ `semantic_color_names_test.dart`（锚点回归）
> 红线执行: 视觉变化**仅** text.tertiary 独立定标处（占位本就待定标）；其余 12+1 处视觉等值（hex 对照见 §4）；零 commit/push
> 冲突面核验: wt115（engine memory）/wt116（engine goal）不触 mobile——本卡全部改动在 mobile/lib 与 scripts/guards 基线 JSON，与其零交集

---

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| text.tertiary 定标 | **已闭**（SPEC §1.3【定标待实测】清账）——light `0xFF736F62` / dark `0xFF878375`（normal），HC/CB 四变体同步定标；六变体全部 ≥4.5:1 on S0/S1，强调度严格介于 textSecondary 与 textDisabled 之间（§1） |
| focus 槽裁决 | **维持 brandPrimary 兼任**——全 app 无焦点环渲染点（§2）；SPEC 不改（规范修订走 R5），建议文字在本报告 §2.3 |
| routes.dart Colors.grey | **已清**——扩 palette 加 `neutralOutline` 快照 token（hex 逐位等值 ΔE00=0.0000，§3）；SPEC §1.5.2 域外单点（§10.5 台账行）清偿 |
| DS.accent 存量 12 处 | **全部迁移**——`DS.accent` → `DS.brandSecondary`（值恒等），语义归位表见 §4（2 处 AI 信息倾向 / 10 处装饰·身份色 / 0 处交互标记） |
| 守卫基线 | DL-SPEC `dsAccentAlias` **12→0 随降**（--update-baseline 净删方向，守卫输出确认，§5）；其余 11 维纹丝不动；UX-COMP/UI-TOKENS/ΔE 三脚本全绿 |
| analyze | 与 HEAD 克隆基线**逐项一致**（6879 = 133 error/41 warning/6705 info；error 全为 gen/ 生成物缺失环境项，lib/ 本体零 error）——本卡**零新增** issue（含逐文件 lint 画像比对，§5.2） |
| 单测 | `semantic_color_names_test.dart` 扩至 16 组断言（含六变体 tertiary 定标锚点 + neutralOutline 恒等）；**运行被内存门拦停**（收工时点 swap 空闲 834M < 启动门 1.2G），补跑命令见 §5.4 |
| 交付物 | `v3-output/B2-3A/changes.patch` + 本报告；改动 13 文件（11 lib/test + 1 基线 JSON + 1 新测试断言组） |

---

## 1. 回执①：text.tertiary 定标值与依据

### 1.1 方法（与 ΔE 脚本同源）

卡面要求「按 WCAG 相对亮度计算（ΔE 脚本同源方法）」：定标脚本直接 `import scripts/design/check_surface_ladder_de.py` 的 `rel_luminance / parse_hex / ciede2000`，零第二套色度实现。三个硬约束 + 两个软约束：

- **硬**（WCAG 相对亮度对比度）：tertiary on S0 **且** S1 ≥ 4.5:1（SPEC §1.3 只要求 S0，S1 更暗故为绑定侧，按卡面要求双 surface 同时达标）；
- **硬**（层级单调，规则 1.3 三级封顶语义）：强调度（同表面对比度）严格 **textSecondary > textTertiary > textDisabled**——tertiary 不许比 secondary 更深（那会篡层级）、不许浅于 disabled（那会失效）；
- **硬**（可辨）：与 textSecondary 的 CIEDE2000 ≥ 3（JND≈2.3 之上，并排可辨），与 textDisabled 的 ΔE00 ≥ 3（不许塌进豁免档）；
- **软**（暖纸气质）：暖灰家族（r>g>b、r−b ≤ 24、g−b 步进与现家族 8–14 一致）——第一轮无色度约束的 sweep 收敛到玫红灰（#998281 类，minΔE 更大但越出暖纸色域）与陶土红（#AA5856 类，r−b=84），均判违规排除；round 2 加家族形状约束后取值；
- **软**（门限余量）：在 ΔE 可辨损失可忽略时取对比度余量更大者（4.59 vs 4.52 档），防未来公式口径复核贴地。

### 1.2 定标结果（六变体全绿）

| 变体 | textTertiary | CR on S0 | CR on S1 | (对照) sec CR S1 | (对照) dis CR S1 | ΔE00 vs sec | ΔE00 vs dis | 层级单调 | ≥4.5 双门 |
|---|---|---|---|---|---|---|---|---|---|
| light normal | **0xFF736F62** | 4.75 | **4.59** | 5.24 | 2.50 | 4.93 | 16.82 | ✓ | ✓ |
| dark normal | **0xFF878375** | 5.08 | **4.57** | 8.16 | 3.62 | 15.09 | 15.16 | ✓ | ✓ |
| light highContrast | 0xFF404040 | 9.52 | 9.19 | 15.89 | 5.09 | 13.04 | 13.27 | ✓ | ✓ |
| dark highContrast | 0xFFCCCCCC | 12.61 | 12.32 | 19.78 | 6.94 | 11.14 | 14.12 | ✓ | ✓ |
| light colorBlind | 0xFF707070 | 4.75 | 4.55 | 6.86 | 2.62 | 10.00 | 15.08 | ✓ | ✓ |
| dark colorBlind | 0xFF878375（同 dark normal） | 5.08 | 4.57 | 8.16 | 3.62 | 15.09 | 15.16 | ✓ | ✓ |

- 绑定侧说明：light 的 S1（F8F4EF）比 S0 更暗 → CR(S1) 是紧门，light 候选的相对亮度上界 Y ≤ 0.1631（由 4.5:1 反解）；dark 相反，Y ≥ 0.2223 下界。两值都取在各自可行域内离 textSecondary 最远处（ΔE 最大化），故对比度恰好贴近 4.5 档是数学必然，不是贴线侥幸。
- dark normal/dark CB 取同值 `878375`：两变体的 surface 与文字阶完全相同（theme_manager 工厂结构），数学同解；`878375` 同时近似等距于 secondary（ΔE 15.09）与 disabled（15.16），是暗色阶「第三级」的几何中点。
- light normal `736F62`：暖纸家族内（r−b=17，与 secondary 的 15/disabled 的 20 同带）；4.59:1 保证在第三级语义位仍有完整 AA 合规。
- HC 变体：家族风格随各变体现状（HC 用纯灰系、CB 用 Wong 中性灰），三级阶梯在 HC 下被拉开（9.19 介于 15.89 与 5.09 之间），高对比设计意图保持。
- 值层落点：`SparkleColors` 新增 `textTertiary` final 字段（constructor/copyWith/lerp/六工厂全接线），语义面 `context.colors.text.tertiary` 改指新 owner（原 TODO(B2-3) 注释移除）。
- **视觉变化范围申报**：仅此槽。textTertiary 当前**零消费方**（语义面 tertiary 的调用点此前映射 textSecondary——`rg 'text\.tertiary'` 仅扩展自身），故本次定标**不改任何现网像素**；该槽从「与 secondary 同值」变为「独立第三级」，属占位转正，SPEC §1.3 表内既定事项。

---

## 2. 回执②：focus 槽裁决——维持 brandPrimary 兼任

### 2.1 证据（rg 扫描 @48463ace）

| 扫描项 | 结果 | 定性 |
|---|---|---|
| `FocusableActionDetector`（mobile/lib） | **1 处**：`aurora_status_band.dart:77` | 仅挂 enter/space 快捷键与 ActivateIntent（键盘/开关屏激活语义），**不绘制任何焦点环**——FAD 本身零视觉输出 |
| `focusRing` / `FocusRing` | **0 处** | 全 app 无自绘焦点环 |
| `ThemeData.focusColor` 消费 | `design_system.dart:151`（= brandPrimary alpha 派生）、`app.dart:176` | 只喂 Material InkWell/InputDecorator 的焦点高亮层 |
| Material 焦点高亮实际可见性 | 触摸优先 app；InkWell focus overlay 仅在键盘/开关设备遍历（`highlightStrategy` 非 touch 模式）渲染 | 真机触屏场景**实际渲染概率≈0** |
| 系统级焦点框 | TalkBack/VoiceOver 焦点框由 OS 绘制（系统色），不消费 app 令牌 | 独立槽无法影响无障碍焦点可见性 |

### 2.2 裁决

**维持兼任**。理由：①焦点环在本 app 无实际渲染点，独立槽是零消费者的死槽；②唯一潜在渲染路径（Material focusColor）已从 brandPrimary 派生，独立槽反而要重修基建且引入「第二暖色相近双义」（违反 I-P3 颜色单义）；③SPEC §1.5 槽位封顶 5，独立 focus 会占第 6 槽名——无收益不占编制。

### 2.3 给 SPEC 修订（R5）的建议文字（本卡不改 SPEC）

> §1.5 focus 行建议补注：「移动触摸优先形态下 focus 由 accent（brandPrimary）兼任（B2-3a 裁决：无焦点环渲染点，见 B2-3A REPORT §2）；独立 focus 槽的触发条件 = 引入物理键盘优先/桌面//web 形态，或出现 ≥1 处自绘焦点环渲染点，二者以先到者为准。触发后独立槽按 §1.3 text.tertiary 同法（WCAG 相对亮度 + 暖域色相 + ≥3:1 non-text）定标。」

代码侧留痕：`sparkle_context_extension.dart` focus getter 文档已写明裁决与证据指针；`semantic_color_names_test.dart` 断言注释同步（`focus 裁决维持 accent 兼任`）。

---

## 3. routes.dart Colors.grey 处置（+1 视觉等值处）

### 3.1 裁决：扩 palette 快照 token（卡面选项一），不用 textDisabled 近似替换

数值对比（`Colors.grey` = `0xFF9E9E9E`，对每模式的最近语义 token 求 ΔE00，同源色度库）：

| 候选替换 | light ΔE00 vs 9E9E9E | dark ΔE00 vs 9E9E9E | 判定 |
|---|---|---|---|
| textDisabled（light A49B90 / dark 6B737E） | 6.24 | **16.85** | dark 侧远超等值线（禁用档在暗色下明显更暗），违反红线 |
| neutral500（light 958A80 / dark 6E6E72） | 8.87 | 17.52 | 双侧超线 |
| neutral600/border（dark A8A8AE） | —— | 4.54 | 仅 dark 近似，且 border 语义错位（描边≠图标） |
| **新增 neutralOutline = 0xFF9E9E9E（双模式同值）** | **0.0000** | **0.0000** | **视觉严格等值 ✓** |

「等值替换」在暖纸 palette 内数学上不存在（palette 全为暖调 token，纯中性灰 #9E9E9E 无等值成员）；red line 要求等值，故按卡面第一选项收编为快照 token。

### 3.2 落点与防滥用

- `SparkleColors.neutralOutline`（六工厂同值 0xFF9E9E9E + copyWith/lerp 接线）；doc 注释写明：**legacy grey 语义收编快照、唯一消费者为 routes 404 图标、批 3 tonal 再生成时按暖 seed 重定标并做视觉评审、禁作新增取灰入口**（中性层算法生成禁手挑，规则 1.2——本 token 是存量收编特例，不是新灰口子）。
- `routes.dart` 404 图标：`Colors.grey` → `context.colors.neutralOutline`（语义面取色，符合 §1.7【批 2 起】段）。

### 3.3 视觉等值证明（hex 对照）

| 处 | 改前 | 改后 | ΔE00 |
|---|---|---|---|
| `app/routes.dart` explore_off 图标（light/dark/HC/CB 全模式） | `Colors.grey` = `0xFF9E9E9E` | `context.colors.neutralOutline` = `0xFF9E9E9E` | **0.0000（hex 逐位一致）** |

顺带收益：404 图标原是全 `Colors.*` 直引在守卫扫描域外的最后单点，现走语义面；DL-SPEC `colorsDotNative` 维基线 1（onboarding 屏）与本次无关、纹丝不动。

---

## 4. 回执③：DS.accent 存量 12 处语义归位表

迁移形态：`DS.accent` → `DS.brandSecondary`（**值恒等**，符号非退役）。为什么不是 `context.colors.accent`/info 槽：accent=brandPrimary、info=semanticInfo 均为**不同色值**，改指即视觉变化，触红线；故本卡完成「符号退役 + 语义判读登记」，值迁移（真换色）留给批 3 视觉变更批按归位目标执行。

| # | 文件:行 | 场景 | 语义判读（这个第二色在表达什么） | 归位目标（值迁移时） |
|---|---|---|---|---|
| 1 | flame_indicator.dart:106 | 连胜火焰亮度档 60–80 的焰色 | 装饰·动机层档位色（注释「黄色」已失真，现值为 slate 蓝；B-02 动机层徽章身份色） | 语义槽派生（warning 系或 info 系按档位重评），动机层徽章通道 |
| 2 | flame_indicator.dart:344 | CompactFlameIndicator 同上 | 同上 | 同上 |
| 3 | sparkle_confetti.dart:153 | confetti 五色庆祝盘成员 | 纯装饰（庆祝粒子，§2.5 G-1 已限里程碑） | 中性层/语义槽派生的庆祝盘，批 3 装饰减配时重评 |
| 4 | dashboard_curiosity_card.dart:48 | home 好奇心卡 lightbulb 图标 | **AI 信息倾向**（cognitive/hasNewInsight——AI 生成的洞察内容标记） | info 槽（AI 建议准入内容，§1.5 info 行） |
| 5 | insight_hub_card.dart:130 | insight hub 快捷动作「模拟考」分类色（姊妹动作用 DS.info/DS.success） | 装饰·分类身份色（非交互标记——三个动作同权可点，色只区分类别） | 分类身份色从语义槽派生（§1.5.1 `Color.derive` 类） |
| 6 | insight_hub_card.dart:397 | 同上（compact 变体） | 同上 | 同上 |
| 7 | learning_insights_overview_screen.dart:161 | insight 模块卡「模拟考」分类色（姊妹 DS.info） | 同上 | 同上 |
| 8 | predictive_insights_card.dart:365 | 「AI 建议」列表 lightbulb 图标 | **AI 信息倾向**（insAiSuggestions 头部，AI 建议条目标记） | info 槽 |
| 9 | simulation_screen.dart:2445 | `_accentForName` hash 身份调色板成员 [info,success,warning,brandPrimary,accent] | 装饰·身份色（按 hashCode 确定性指色，日历身份色同类） | 身份色集合从语义槽派生；brandPrimary 成员保留（accent 语义） |
| 10 | simulation_screen.dart:3200 | 同上（MiniParticipantPill） | 同上 | 同上 |
| 11 | simulation_screen.dart:3281 | 同上（SnapshotPill） | 同上 | 同上 |
| 12 | simulation_chat_bubble.dart:407 | `_accentForSpeaker` 发言者身份色调色板成员 | 同上（模拟对话发言者身份） | 同上 |

**统计**：装饰/身份色 10 处（#1-3、#5-7、#9-12）｜AI 信息倾向 2 处（#4、#8）｜交互标记 **0 处**——印证 SPEC §1.4.2 判断：brandSecondary 作为「第二交互色」的存量使用**一处交互都不承载**，退役无功能损失。

### 4.1 视觉等值 hex 对照（12 处 + 1 处）

DS.accent ≡ brandSecondary（静态 getter 直转发，design_system.dart:624 `=> brandSecondary`），替换后所有消费点渲染值逐模式不变：

| 模式 | 改前（DS.accent） | 改后（DS.brandSecondary） | ΔE00 |
|---|---|---|---|
| light normal | 0xFF7A8BA6 | 0xFF7A8BA6 | 0.0000 |
| dark normal | 0xFF7E8FAE | 0xFF7E8FAE | 0.0000 |
| light/dark highContrast、colorBlind | 同各工厂 brandSecondary 字面量 | 同左（同字段直引） | 0.0000 |

### 4.2 残余登记（守卫不可见，移交下卡）

`flame_indicator.dart:126` 的 `DS.accentGradient`（≈ `_buildGradient(accent, …)` 内部同源）**不在** `\bDS\.accent\b` 计数内（词边界不匹配），本卡未动（改它需新增 gradient 符号，属值迁移批连带项）。建议批 3 值迁移时与 #1/#2 同批处理；DL-SPEC 维度无需扩（单点、有登记即收敛）。

---

## 5. 回执④：守卫基线变化与验证

### 5.1 守卫

| 守卫 | 结果 | 基线变化 |
|---|---|---|
| DL-SPEC `check_dl_spec_ratchet.py` | **PASS**（含 `--self-test` PASS） | **dsAccentAlias 12→0**（per-file 8 条目净删；其余 11 维逐一不变：coldColorLiteral 90、colorsDotNative 1、offLadderDuration 186、bannedCurve 24、breathingController 1、confettiPerFile 7、particleBypass 77、textHardcodedZh 0、gradientLiteral 303、errorCopyOops 6、competitionNarrative 0） |
| UX-COMP | **PASS**（rawButton 19、rawSpinner 8、rawChip 11、parallelClass 146、colorLiteral 100 全不变） | 无 |
| UI-TOKENS ratchet | **PASS**（color 239/275、fontSize 721/727 全不变） | 无——theme_manager.dart 为 token owner，不在两守卫扫描域（features/9-surfaces），新增字面量不计数 |
| ΔE `check_surface_ladder_de.py` | light/dark gate + `--self-test` 全 PASS | 表面阶锚点未触碰（0.0000 回归） |

基线刷新操作合规性：`--update-baseline` 仅净删方向（守卫内置拒绝抬升，本次输出 `12 → 0` 确认）；**§9.1 基线共享态纪律知悉**——该条要求「持卡编辑 mobile/lib 的卡禁止同时刷基线」，本卡按卡面 B2-3a 第 4 要素明示指令执行随降（基线 JSON 单调下降、无并发卡竞争 mobile/lib 面），主会话合入窗口建议复跑三守卫确认。

### 5.2 flutter analyze（HEAD 克隆基线法）

worktree 未跑 `make proto-gen`，`gen/` 缺失导致的存量 error 无法与本卡区分——按 AGENTS 纪律用 `git clone <worktree> /tmp/b23a-baseline` 建 HEAD-only 基线对跑：

| 时点 | error | warning | info | 合计 |
|---|---|---|---|---|
| HEAD 基线克隆（48463ace，未跑 proto-gen） | 133 | 41 | 6705 | 6879 |
| 本卡全部落盘（含修复后） | **133** | **41** | **6705** | **6879** |

- 133 error 全部为 `package:sparkle/gen/*` 生成物缺失（sync_engine/websocket_service/grpc services/test），**与本卡无关且 lib 本体零 error**；与 B2-2 时点 132 的 ±1 为 base 漂移（1d42786a→48463ace 六个提交间新增一处 gen 依赖），克隆对照已排除本卡嫌疑。
- routes.dart 三条 info（directives_ordering/require_trailing_commas/use_if_null）与基线**逐条相同**（仅行号漂移）——施工中引入的 2 条新 lint（import 乱序、尾逗号）已当场修复归零。
- 收工清理：/tmp/b23a-baseline 已删。

### 5.3 守卫三件套 + ΔE 输出摘录

```
[dl-spec-ratchet] PASS — ratchet holds: … dsAccentAlias=0/0 … (210 files with debt)
[dl-spec-ratchet] baseline updated: {'dsAccentAlias': 12, …} -> {'dsAccentAlias': 0, …}
[ux-component-convention] PASS — ratchet holds: rawButton=19/19 …
[ui-tokens-ratchet] PASS — ratchet holds at color=239/275, fontSize=721/727
[surface-ladder-de] PASS — ladder steps hold (1.2.1) and anchor regression within ΔE≤2 (1.2.2)   # light
[surface-ladder-de] PASS — anchor regression within ΔE≤2 (1.2.2); 1.2.1 is a light-table bound    # dark
[surface-ladder-de] SELF-TEST PASS — 29 Sharma-2005 CIEDE2000 pairs reproduced (tol 1.5e-4)
```

### 5.4 单测（被内存门拦停，补跑命令）

- `mobile/test/core/design/semantic_color_names_test.dart`：13→**16 组断言**（新增：textTertiary 六变体 Dart 侧定标锚点、neutralOutline 六变体恒等、text.tertiary→textTertiary 同实例转发；focus 断言注释更新为裁决结果）。
- 改动文件关联测试清单：`learning_insights_overview_screen_test.dart`、`learning_insights_navigation_test.dart`、`insights_frontend_smoke_test.dart`、`dashboard_learning_insights_test.dart`、`exam_sprint_closed_loop_test.dart`（引 SparkleColors 面）。
- 拦停记录：收工时点 `vm.swapusage` 空闲 **834.31M < HEAVY 启动门 1.2G**（AGENTS 硬规则，`flutter test` 未启动；守卫/analyze 均为 LIGHT 已完成）。验收补跑（单批串行）：

```bash
cd mobile && flutter test \
  test/core/design/semantic_color_names_test.dart \
  test/features/insights/presentation/screens/learning_insights_overview_screen_test.dart \
  test/widget/learning_insights_navigation_test.dart \
  test/widget/insights_frontend_smoke_test.dart \
  test/widget/dashboard_learning_insights_test.dart \
  --concurrency=1
```

---

## 6. 回执⑤：收工核查清单

| 项 | 状态 |
|---|---|
| 修改只落本 worktree（wt118） | ✅ git status：11 M（lib/test/基线 JSON）+ 2 新路径（v3-output/B2-3A/），主仓与 index 未触碰（patch 用 diff/no-index 生成） |
| 零 commit/push | ✅ |
| 红线面 | ✅ 视觉变化仅 text.tertiary 槽（零消费方，占位转正）；12+1 处 hex 等值（§3.3/§4.1）；表面阶锚点 ΔE 0.0000 |
| flutter analyze 零 error 新增 | ✅ 与 HEAD 克隆基线逐项一致（6879=6879，含 error/warning/info 三分段） |
| 守卫三件套 + ΔE 绿 | ✅ §5.1/§5.3 |
| /tmp 清理 | ✅ 定标脚本（inline heredoc 无落盘）、b23a-baseline 克隆已删；worktree 内 mobile/.dart_tool 随 worktree 回收 |
| 模拟器/独立端口进程 | ✅ 未起 |
| 交付物 | `v3-output/B2-3A/changes.patch` ＋ 本 REPORT.md ＋ 代码/测试/基线改动 |

> 遗留给后续卡：①DS.accent 值迁移批（§4 归位目标落地，2 处 info 槽 + 10 处身份/装饰派生，需视觉变更窗口）；②`DS.accentGradient` 残余（§4.2）；③§1.7【批 2 起】段「新代码只走语义名」守卫维度（B2-3 门禁收尾包本体，本卡未扩维）；④focus 独立槽触发条件如 §2.3（R5 修订素材）；⑤neutralOutline 批 3 tonal 再生成清偿（token doc 已注记）。
