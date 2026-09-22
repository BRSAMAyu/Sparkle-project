# Sparkle 设计语言规范 v0.9 · 验收条款集

> 配套：`v3-output/DL-R3/SPEC.md`（条款号 A#.# 对应 SPEC §# 章）｜ 2026-09-22 ｜ 零代码改动
> 性质：规范「不是文档而是纪律」的执行面。每章拆两类条款：
> - **机检**：写成 lint/guard 规则的输入描述 + 示例违规代码（实施时落 `scripts/guards/`，接 `run_all_rule_guards.sh` 与 `rule_guard_manifest.tsv`；ratchet 基线只降不升，`--update-baseline` 仅净删后刷新——沿用 UX-COMP 既有模式）。
> - **人审**：人工评审单条目（设计评审会逐项过，一票否决项标 ⛔）。
> 门禁生效时点：G1–G7 新守卫批 2 落地；标注「立即」的条款自规范合入即生效（新代码零容忍）。

---

## A0 · 使命与气质（SPEC §0）

**机检**
- A0.1【立即】参赛材料叙事检查：`rg -n "品类空位|无人占位|四合一.*事实" docs/competition/` 应零命中（H3 处置：四合一只能以「方向假设」表述）。违规示例：`docs/competition/xx.md` 写「"四合一"是我们验证过的品类空位」。
- A0.2（批 3 后可机检）每屏挂载的面板类常驻组件计数 ≤ 预算（并入 G7 面积守卫）。

**人审**
- A0.3 ⛔ 任何新功能进入某屏前，PR 描述必须回答：「它服务于该屏哪个必达项（≤2 之列）？」不答不评。
- A0.4 温度类改动（新增动画/装饰/人格文案）必须归入三层模型之一（语言层/高光时刻/底座），落在「底座」的一律驳回。

---

## A1 · 色彩系统（SPEC §1）

**机检**
- A1.1【立即·已有守卫】`check_ui_design_tokens_ratchet.py` colorLiteral：features 内 `Color(0x` 计数只降不升（基线现值 103）。违规示例：`dashboard_screen.dart` 新增 `Color(0xFF825D49)`。
- A1.2【立即】`Colors.` 原生色引用禁新增（同守卫扩展 pattern `\bColors\.(?!white|black|transparent)`，白名单 E5 测试目录）。
- A1.3【立即】冷色准入：features 内非 galaxy 文件出现 `0xFF[0-5]\w{2}[6-9ABCEF]\w{3}` 类蓝青紫色相字面量即告警（启发式，兜底人审 A1.8）。违规示例：快捷 chip 新增 `Color(0xFF5B7CFA)` 底色。
- A1.4（批 2）G6 对比度机检：脚本对 `SparkleColors` 每个模式（normal/highContrast/colorBlindFriendly × light/dark）全量组合跑 WCAG 相对亮度公式；文字对 <4.5:1、图形对 <3:1 输出清单；空清单才放行。示例违规输出：`textSecondary(0xFF6C655D) on surfaceTertiary(0xFFE7DED4) = 4.32:1 < 4.5`。
- A1.5【立即】`DS.accent` 引用禁新增（@Deprecated 别名，pattern `\bDS\.accent\b`；存量 ratchet）。违规示例：新文件 `color: DS.accent`。
- A1.6（批 2）中性层 seed 回归：算法生成的 S0–S3 值与 batch-1 快照（0xFFFCF8F3 / 0xFFF8F4EF / 0xFFF1EBE4 / 0xFFE7DED4）逐对 ΔE≤2；超限清单入设计评审。
- A1.7（批 2）`material_color_utilities` 引入后，`SparkleColors.light/dark` 工厂内手写字面量行数只降不升（ratchet）。

**人审**
- A1.8 ⛔ 冷色使用口诀评审：每个冷色件回答「它在替系统说话还是替设计说话？」——替设计说话的驳回（AI 状态/数据可视化/确认动作之外一律禁）。
- A1.9 卡与底区分靠色阶不靠阴影：新增卡面若同时带 S1 底 + 明显投影，驳回（阴影只给浮起件）。
- A1.10 卡片不套卡片：嵌套 SparkleCard/GraphiteCardSurface 的布局截图评审，嵌套 >1 层驳回（留白分组替代）。
- A1.11 灰度可辨：选中态截图转灰度后仍可辨（人工目检，对照 §1.4.3）。
- A1.12 每屏可点 chip ≤6、AI 答后 chip ≤3：golden 截图目检。

---

## A2 · 动效系统（SPEC §2）

**机检**
- A2.1（批 2·G1）`check_motion_token_convention.py`：features 内 `Duration(milliseconds: N)`，N 不在白名单 {50,80,100,120,150,200,250,300,320,350,400,450,480,500,600,650,700} 即违规。违规示例：
  ```dart
  // 违规：非阶梯值 260ms
  AnimatedContainer(duration: const Duration(milliseconds: 260), ...)
  ```
- A2.2（批 2·G1）禁曲线引用：pattern `\bCurves\.(elasticOut|bounceOut|elasticInOut)\b` 全仓零容忍（除 animation_token.dart 退役标记注释）。违规示例：`AnimationSystem.spring = Curves.elasticOut`（现存行，批 2 删除）。
- A2.3【立即】`createBreathingController` 引用禁新增（现存 motion.dart:97 定义保留至批 2 删除；新调用即违规）。
- A2.4（批 2）M4/M5 误用检测：`motionToken: SparkleMotionTokenV3.large|narrative` 出现在非手势驱动文件（路由表/onboarding/galaxy 仪式 白名单外）即告警。违规示例：普通设置页转场 token=large。
- A2.5（批 2）删除清单核验：`rg -c "createBreathingController" mobile/lib` = 0；`hero` 时长映射值 = 650（narrative 档）；splash 编排总时长 ≤400ms（`splash_screen.dart` 中 Interval 总和断言测试）。
- A2.6【立即】SparkleConfetti 每屏挂载 ≤1（并入 G7：`SparkleConfetti(` 单文件计数 ratchet）。违规示例：task_execution_screen + feedback_dialog 各挂一份（U-01 Step6 前的历史形态）。
- A2.7【立即】`GlobalParticleCounter` 旁路检测：粒子系统绕过 counter 直接发射（pattern：粒子发射构造不引用 maxParticles）——批 2 审计，新粒子代码立即零容忍。
- A2.8（批 2）PulseScope `maxActiveSlots` 断言 = 1（单测固定，改动需设计评审签字）。

**人审**
- A2.9 ⛔ 签名位唯一性：除 signature_check（§2.4）外任何完成时刻动效驳回； Things 式规格评审（≤300ms/可打断/Success 触觉三要素齐备）。
- A2.10 ⛔ 0.25Hz 复活审查：任何循环动画频率换算 ≤0.5Hz（周期 ≥2s）驳回，无例外（对照 HIG 0.2Hz 敏感带与「同屏持续源 ≤1」双条款）。
- A2.11 可打断性：评审时实际打断每个新动画（动画中途点按/返回），出现「必须等它播完」即驳回。
- A2.12 触觉因果对：新触觉无对应视觉伴随、或纯彩蛋（无因果）驳回；触觉表外新增场景需先改表（SPEC §2.3）。

---

## A3 · 排版与密度（SPEC §3）

**机检**
- A3.1【立即·已有守卫】fontSize 字面量只降不升（`check_ui_design_tokens_ratchet.py`，存量 1293 处）。违规示例：新文件 `fontSize: 18`。
- A3.2【立即·G4 扩展】l10n 硬编码中文：`Text('...中文...')` 字面量禁新增（`check_i18n_coverage.py` 扩展扫描 features）。违规示例：`Text('今日无任务')` 不走 arb。
- A3.3（批 2·G5）标题角色截断：`maxLines: 1` + `TextOverflow.ellipsis` 与标题 role 组合（`style: context.typo.title/headline/subtitle` 同表达式）即告警。违规示例：
  ```dart
  // 违规：卡标题单行截断
  Text(goal.title, maxLines: 1, overflow: TextOverflow.ellipsis,
       style: context.typo.subtitle)
  ```
- A3.4（批 1）文案长度配对表机检（arb 层）：zh 文案超角色上限（chip 键 ≤6 字 / placeholder 键 ≤14 字 / 按钮键 ≤8 字——按 key 前缀约定 `*Chip*/*Hint*/*Button*` 分类）清单输出，批 1 清偿后入 CI。

**人审**
- A3.5 ⛔ 标题/正文截断目检：golden 截图逐屏扫「…」结尾的标题级文本，出现即驳回（chip/caption 除外）。
- A3.6 行高抽检：chat 消息与长解释行高 <1.5 驳回（中文正文 1.6 正典）。
- A3.7 大字喊话：标题级字号连续 ≥3 行的排版驳回（S4 复发检查）。
- A3.8 横滚 chip 条末位渐隐/边缘提示存在性目检（V10 类）。

---

## A4 · 组件语法与四态（SPEC §4）

**机检**
- A4.1【立即·已有守卫】parallelClass：私有 `_*Chip|Pill|Badge|Capsule|Empty|Error|Loading` 类禁新增（UX-COMP 守卫现存 pattern）。违规示例：`class _QuickActionPill extends StatelessWidget`。
- A4.2【立即·已有守卫】rawChip/rawButton/rawSpinner ratchet（基线只降不升）。
- A4.3（批 1）空态禁悬空主 CTA：`EmptyState`/`CompactEmptyState` 使用处传 primary CTA 时，linter 要求同文件存在数据非空断言路径（静态近似：`isEmpty` 分支内出现 `SparkleButton(variant: primary)` 即违规）。违规示例：
  ```dart
  // 违规：空态里挂确认主按钮（minimum_criteria_card.dart:76-99 历史形态）
  if (thresholds.isEmpty)
    EmptyState(title: '还没有最低达标线',
      action: SparkleButton(label: '确认', variant: ButtonVariant.primary))
  ```
- A4.4（批 1）错误态裸异常检测：错误展示组件的 message 参数直传 `error.toString()` / `exception` 变量即违规。违规示例：`CustomErrorWidget(message: e.toString())`。
- A4.5（批 1）AI 内容禁预填结论：流式开始前（`ChatRunPhase == sending`）渲染非骨架答案容器——chat 域 golden 断言（sending 相位不得出现完整段落文本 widget）+ 代码评审。
- A4.6（批 2）骨架贴布局：golden 前后帧对比（骨架帧 vs 内容帧），块位置偏差 >24dp 记违规清单入评审。
- A4.7【立即】确认按钮可见性：`确认|保存` 文案按钮与确认对象非同屏（跨文件无法静态判，批 1 用 A4.3 覆盖 + 人审 A4.9）。

**人审**
- A4.8 ⛔ 控件层级三分法评审：每屏主操作（primary 填充钮）≤1；完成类与展开类控件视觉权重并排的布局驳回（S14 复发检查）。
- A4.9 ⛔ 空态三要素评审：为何空 + 单一 CTA + 指向创建动作；「点击展开/收起」类操作指令副标题驳回（S11 复发检查）。
- A4.10 错误态三句式评审：人话+影响+怎么办；「Oops」「Unsupported operation」类文案出现即最高级驳回（S12 复发检查）。
- A4.11 回归态评审：回归首屏截图——>2 卡、首动作非低难度复习、出现横幅轰炸任一即驳回。
- A4.12 折叠卡/导航卡 affordance 区分目检（chevron 旋转 vs 「›」恒向，S15 复发检查）。

---

## A5 · 空间纪律（SPEC §5）

**机检**
- A5.1（批 3·G7）chat 面积近似守卫：`chat_screen.dart` build 树中常驻非会话子组件（白名单：输入条/胶囊/过程折叠）计数 >0 告警（目标 ≥70% 由人审 A5.6 实测确认）。
- A5.2（批 2）特效层计数：`visual_renderer` 挂载层 ≤1（home layers 白名单外新增挂载即违规）。
- A5.3【立即】gradient ratchet：features 内 `LinearGradient(|RadialGradient(` 计数只降不升，每屏 >2 人审（静态按文件近似）。
- A5.4（批 3）home 首屏结构断言：widget test——「今日下一步/指挥台」卡在 CustomScrollView 首屏 viewport 内（折叠线上方）、「理解你」卡带 collapse 状态位。示例违规：understanding_snapshot_card 无 collapse 字段（现状）。

**人审**
- A5.5 ⛔ 系统件三形态评审：新增任何 AI 主动性 UI，必须归入内联微件（≤40dp）/收件箱/阶段胶囊之一；chat 常驻区新面板一票驳回（S8 复发检查）。
- A5.6 chat 面积实测：运行时截图测量气泡流面积占比 ≥70%（回归接管屏触发瞬间除外）。
- A5.7 装饰预算查账：新装饰 PR 附当前屏账本快照（层数/粒子/glow/gradient/持续源），超限先减后加，不减驳回（AUDIT §7 根因④的终止机制）。

---

## A6 · 文案与数据呈现（SPEC §6）

**机检**
- A6.1（批 1·G2）枚举直出：`label: \w+\.(status|priority|unit)\b` 模式禁新增。违规示例：`_InfoChip(label: data.goal.status)`（goal_detail_screen.dart:249 历史形态）。
- A6.2（批 1·G2）时间直出：DateTime 变量经字符串插值进展示层（pattern：`'...${' + DateTime 类型变量 + '...'` 于 Text/label 上下文）禁新增。违规示例：`'截止: ${c.dueAt}'`（pending_commitments_section.dart:55 历史形态）。
- A6.3（批 1·G2）机器指标：label 上下文 `toStringAsFixed` 禁新增（Q 值 pill 类）。违规示例：`'Q ${q.toStringAsFixed(2)}'`。
- A6.4（批 1）词典覆盖断言：lexicon 全量条目单测——每个 domain×raw 有 labelZh/labelEn 非空、tone ∈ PillTone；`Lexicon.lookup` 未命中回落原值并上报（灰名单非崩溃）。
- A6.5（批 1）置信度三档：AI 输出含「把握|置信」+ 百分号数字即违规（chat 消息 golden/后端模板断言；三档文案表外表述人审）。
- A6.6【立即·并入 G4】「Oops / something went wrong」英文错误文案零命中（`rg -n "Oops|something went wrong" mobile/lib`）；测试数据命名直出（`hex[:8]` 拼接展示字段）批 1 清库后零命中。

**人审**
- A6.7 ⛔ 失败不羞辱：文案评审一票否决——比较句（「别人都在…」）、追责句（「你又…」）、倒计时逼债句（「已落后 N 天」）出现即驳回（E-P2）。
- A6.8 ⛔ 数字准入：每个新数字回答三问（用户状态？单一事实源？UI 教过口径？）——任一「否」驳回或降为三档人话（C-07）。
- A6.9 Aurora 语气四条抽检：结论先行、幽默 ≤1 处/屏不拿学习内容开玩笑、不装懂、推动作不下判断。
- A6.10 结束权：「今天到此为止」出口在长会话/效率档下可达（人工走查）。

---

## A7 · 交互流程（SPEC §7）

**机检**
- A7.1（批 4）推送频率单测：24h 窗口内常规类 >1 条、全类周计数 >5、静默时段（23:00–8:00 默认档）发送尝试——三类用例断言拒绝。
- A7.2（批 4）目标函数断言：推送 bandit 的 reward 函数代码评审+单测——reward 只含 response/complete 信号，DAU/session 打开类信号接入即测试失败。
- A7.3（批 4）分步能力门控单测：置信度 <0.60 时路由不产出分步模板（降级直答+核对提示）。
- A7.4（批 4）连胜安全网边界用例：冻结耗尽断签、补签窗口过期、月冻结重置——三用例断言文案走不羞辱模板表（表外人审）。
- A7.5（批 1）S7 单一事实源断言测试：task_board_provider / goal_detail_provider / experience provider 三处「今日任务」读取同源 provider（widget test：注入 3 任务样例，三屏展示口径一致——「今日 N 个」无互斥）。

**人审**
- A7.6 答疑分档走查：三类意图（快问/显式要答案/应试默认）各 3 条真实提问走查——分步规格（3–5 步/每步 ≤3 句/第 2 步后出口）与直答路径正确。
- A7.7 效率档提示非强制：NS 创建时提示可关且不静默改档（走查）。
- A7.8 星图工作视图走查：「下一个建议碰」chip 恰 1 个；标签重叠区不可读即驳回（S5 复发）。
- A7.9 仪式模式触发面走查：仅成就/回顾/onboarding 首见可入全局；退出顺畅。
- A7.10 收件箱 IA 走查：Aurora 确认队列不再出现在 chat 常驻区（S8 复发）；三分组齐全。

---

## A8 · 屏级蓝图（SPEC §8）

> 每屏验收 = 必达项达成（人审）+ Top5 改动对应条款（机检引用前文）+ 冒烟清单。批量执行时点：批 1（文案/状态）/批 3（结构）分波验收。

| 屏 | 必达项验收（人审，两问） | 机检引用 |
|---|---|---|
| A8.1 home | ①打开首屏 3 秒内可说出「今天该干什么」并一步触达？②能一句话发起任务？ | A5.4/A5.1/A2.5（首帧）/A6.4/A7.5 |
| A8.2 chat | ①气泡流 ≥70%？（实测 A5.6）②等待期有阶段+预期+可取消？ | A4.5/A4.3（chip ≤3→A1.12）/A3.3（顶栏）/A6.6（V13） |
| A8.3 goal | ①健康度与 goal/home 交叉一致？②下一步 CTA 唯一？ | A6.1/A4.3/A7.5/A6.5 |
| A8.4 task | ①「今日」口径三屏一致？②勾选即完成 ≤2 步？ | A7.5/A4.8/A2.6/A6.4 |
| A8.5 memory | ①今日重现入口存在且每日变化？②无机器话直出？ | A6.2/A6.3/A4.6/A6.4 |
| A8.6 galaxy | ①工作视图回答「下一个该碰什么」？②加载/空/错误三态可辨（实测注入三态）？ | A7.8/A7.9/A2.7/A2.8/A6.6 |
| A8.7 profile | ①进度数字过 A6.8 三问？②图表有轴/单位/口径？ | A3.1/A1.3/A6.4 |
| A8.8 settings | ①改开关即生效且无假保存钮？②无障碍入口唯一？ | A4.7/A4.12/A2.3（触觉开关） |
| A8.9 onboarding | ①首见全局星图仪式出现一次且退出落工作视图？②≤5 步到 home？ | A3.4（placeholder ≤14 字）/A2.4（M5 预算） |

**通用冒烟清单（每批回归必过；红线：不许改坏可用功能）**：
1. 9 surfaces 进入/返回/深链各一次；
2. 每屏一次主操作（发消息/勾任务/建目标/确认承诺/切档）；
3. 断网→恢复一次（错误态+重试+现场保留）；
4. reduce-motion 开关开启全屏走查（静帧降级）；
5. `flutter test` + `pytest` 全绿；golden 差异逐屏人审签字。

---

## A9 · 门禁与工具链（SPEC §9）

**机检**
- A9.1（批 2）G1–G7 守卫全部登记 `rule_guard_manifest.tsv` 且 `bash scripts/run_all_rule_guards.sh` 全绿；任一新守卫基线存在（无「新守卫带空基线放行存量」情况）。
- A9.2（批 2）debug 面板五项功能存在性断言（token 切换/取色器/慢放/预算仪表/golden 快照）——集成测试各一条。

**人审**
- A9.3 ⛔ 迁移纪律：合并窗口前检查 untracked 交付物备份（仓库纪律）；每批 `--update-baseline` diff 审阅（只降不升）。
- A9.4 新旧对比评审：每批迁移用 debug 面板逐屏切换对比，视觉变化必须映射到具体规范条款号，映射不出的变化驳回。

---

## A10 · 迁移路线（SPEC §10）

**机检**
- A10.1 批次门：批 2 迁移开闸前，批 1 全部工作包验收单签字（ACCEPTANCE A6/A7/A4 对应条款全绿）——CI 里程碑标签断言。
- A10.2 回归验证点脚本化：每批 PR 模板勾选冒烟清单（A8 通用 5 项）；golden 差异报告作为 PR 必附产物。

**人审**
- A10.3 ⛔ 功能回退红线：任一批次验收中出现可用功能回退（主链路阻塞/数据丢失/状态错乱），整批停止合入，回退策略执行（flag 回切），修复后重验。
- A10.4 TRIAGE 对接复核：TRIAGE 合入时核对 §10.5 三动作执行（已修复项移出施工范围/勘误吸收/批次清单对接）。

---

## 附：条款统计与实施优先级

| 类型 | 数量 | 落地载体 |
|---|---|---|
| 机检·立即生效 | 14 | 现有守卫扩展（G4/G5 部分、ratchet 新维度） |
| 机检·批 1 | 9 | G2 词典守卫 + 断言测试 |
| 机检·批 2 | 12 | G1 motion 守卫 + G6 对比度 + golden 管道 |
| 机检·批 3/4 | 7 | G7 面积守卫 + 行为单测 |
| 人审 | 27 | 设计评审单（PR 模板附一票否决项 ⛔ 共 14 条） |

一票否决项（⛔）速览：A0.3 必达项不答不评 ｜ A1.8 冷色口诀 ｜ A2.9 签名位唯一 ｜ A2.10 0.5Hz 以下循环 ｜ A3.5 标题截断 ｜ A4.8 主操作唯一/控件分级 ｜ A4.9 空态三要素 ｜ A4.10 错误态三句式 ｜ A5.5 系统件三形态 ｜ A5.7 预算先减后加 ｜ A6.7 失败不羞辱 ｜ A6.8 数字三问 ｜ A9.3 基线只降不升 ｜ A10.3 功能回退红线。

*验收条款集完。零代码改动、零 /tmp 驻留、未 commit/push。*
