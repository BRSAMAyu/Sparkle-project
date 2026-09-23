# Sparkle 设计语言与交互流程规范 v1.0

> 轮次：A 线 R3 · 统一设计语言规范起草 → **R4 红队修订定稿** ｜ 2026-09-22 ｜ 零代码改动（纯写作卡，代码现状为只读走查）
> 版本：**v1.0（定稿）**。修订依据：`v3-output/DL-R4/REVIEW.md`（21 条修订清单 P0×3/P1×10/P2×8 + 10 条升级条件，全部逐条处置，见 §12 修订记录与 `v3-output/DL-R3/REVISION_v1_0.md`）。v1.0 相对 v0.9 为纯文本修订级，框架未推翻。
> 依据链：`DL-R2/DECISIONS.md`（D1–D10 主会话裁决，**硬约束**；**含附录「H3 验证结果裁决更新」，同为硬约束**）＋ `DL-R2/CONFLICTS.md`（C-01～C-12、B-01～B-04、H1–H3）＋ `DL-R1-AUDIT/AUDIT.md`（S1–S20）＋ `DL-R1-EDU/RESEARCH.md`（E-P1～E-P15，学习场景原则）＋ `DL-R1-INTL/RESEARCH.md`（I-P1～I-P16，通用工艺原则）
> 读者：实施工程师（agent 或组员）。每条规范给「依据」标注；数值不给「适当/合理」，拿不准的给区间并标 **【定标待实测】**。
> 冲突顺序：DECISIONS（含 H3 附录）> 本规范 > CONFLICTS 裁决提案 > R1 报告原文。规范间残留矛盾由起草人裁决并标注（见 §11 起草人勘误）。
> 配套执行面：`v3-output/DL-R3/ACCEPTANCE.md`（每章验收条款：机检规则描述 + 人审清单）。
> 引用纪律：正文 file:line 一律标注时点（@commit），行号随树漂移，**以符号名为准**（§11.1）。

---

## §0 使命与气质

### 0.1 方向假设表述（硬条款）

「懂状态 + 会教 + 有温度 + 过程透明」**四合一是方向假设（direction hypothesis），不是品类空位事实（category-gap fact）**。H3 teardown（豆包爱学 + 有道 AI 老师四维拆解，250 条一手差评）**已裁决：部分成立**——「会教+有温度」两角已被竞品实质占位（四合一空位整体证伪），「懂状态（状态驱动）×过程透明（诚实/可解释）」双缺位实证成立；「用户是否买单」移交 H2（5–8 人卡片排序访谈 + fake-door）验证。在 H2 完成前，一切对外叙事（含 `docs/competition/` 参赛材料）禁写「品类空位无人占位」类断言；差异化主张统一采用「**错题本 2.0：静态收录 → 状态引擎**」表述。【依据：DECISIONS H3 处置＋附录 H3 裁决 #1/#2；CONFLICTS §C 空位校验】

**H3 后预算权重裁决（生效中）**：温度**降为及格线**（免费竞品已把温度抬到 4.8 分档），资源让位「记得住」；「诚实」定位签名特性且**落批 1**（§10.1 B1-6）。据此批 3/批 4 中 §7.2 仪式模式、§2.5 G-3 galaxy 豁免预算、§8.9 首见仪式的预算权重**显式下调一档**，状态与诚实层维持或上调。H2 真人访谈结果出来前，下调即生效；H2 若进一步证伪温度买单，仪式层降为薄层。【依据：DECISIONS 附录 H3 裁决 #3/#4；DECISIONS H2】

### 0.2 第一硬条款：每 surface 必达项 ≤2（H1 消解）

**本规范第一硬条款**：9 个 surface 各自的「必达项」（must-land items，同屏必须完成表达的价值主张）**≤2 个**；四角（懂状态/会教/有温度/过程透明）按屏分配，**不允许同屏全表达**。任何新增功能/面板/卡片进入某屏前，先回答：它服务于该屏哪个必达项？都不服务 → 不进；两个都服务但屏已满 2 → 排队或替换。此条款取代事后矩阵验证，是所有屏级设计评审的第一问。【依据：DECISIONS H1（结构性消解进规范）；CONFLICTS H1「四条宪法在同一块屏幕上打架」】

9 surface 必达项分配矩阵见 §8 开篇。

> **【v1.1 N1 增补 @A-SPEC，落地 @SPEC-GUARD】**：冲刺仪表盘（sprint surface）为**第 10 治理面**——`features/plan/presentation/screens/sprint_screen.dart`（冲刺屏）与 `features/home/presentation/widgets/exam_sprint_dashboard_card.dart`（home 内嵌冲刺仪表卡）合称 sprint surface，期末一周北极星主场景。必达项（≤2，与第一硬条款同制）：①剩余时间与今日完成度一眼可信（口径走 §9.4 单一事实源）②下一步动作单一 CTA。守卫落点：`check_ux_component_convention.py` 扫描根 +1 `features/plan/presentation`（§9.1 已同步）。【依据：§1.2 结构性发现；§0.2 矩阵无 sprint 行的空白；FLEET-BRIEF「冲刺完成度=sprint_task_ledger 唯一定义」】

### 0.3 气质定位

- **底层气质**：暖纸（calm/paper）+ 诚实（honest）。暖纸由色彩系统的 seed 承载（§1），诚实由四态规范（§4.5）与数字准入（§6.3）承载。对照 AUDIT §2 的判决：丑的主因是「系统性失控」而非「审美差」，底子保留、系统立规。
- **温度三层模型**（D1 的规范化表述，**H3 后权重已标注**）：
  1. **语言层（主战场，零面积成本）**：AI 人格、人话文案、结论+数字、失败不羞辱——§6。**H3 后权重：上调**（承载「诚实」签名特性，诚实三件套落批 1，DECISIONS 附录 #3）；
  2. **高光时刻（单次、短暂、有容器）**：签名完成动画（§2.4）、成就/回顾仪式视图（§7.2）、连胜安全网触发瞬间的「保住了」反馈（§7.4）——全 app 只有这三类。**H3 后权重：下调**（三类容器保留，触发面收敛，预算让位「记得住」）；
  3. **底座（常驻）零温度装饰**：常驻动画源同屏 ≤1（§2.6）、0.25Hz 呼吸删除（§2.5）、glow 只给唯一焦点（§5.4）。**H3 后权重：不变**。
  【依据：DECISIONS D1；CONFLICTS C-01 三层落法；DECISIONS 附录 H3 裁决 #3/#4】

### 0.4 北极星

期末一周效果最好（用户原话裁决）。任何规范条款与「一周备考用户的效率」直接冲突时，效率侧胜出，但必须走 §7.1 的效率档机制表达（提示切换，不静默降级）。【依据：DECISIONS 裁决依据行；DECISIONS D2 增补】

---

## §1 色彩系统

> 架构裁决：D6——暖米棕 seed + tonal palette（色调盘算法）生成 4 级表面阶 + 唯一交互 accent + 语义槽 ≤5（AI 信息=唯一冷色槽）+ 冷色准入规则。【依据：CONFLICTS C-06；AUDIT S1】

### 1.1 五层结构

| 层 | 内容 | 数量 | 生成方式 |
|---|---|---|---|
| L-A 中性层（surfaces） | 表面阶 4 级 + 描边 1 组 | 4+3 | 算法生成（tonal palette），禁手挑 |
| L-B 文字层 | 文字阶 3 级 + disabled | 3+1 | 算法生成，对比度达标 |
| L-C 交互层 | 唯一 accent（interactive accent） | 1 | 品牌色，只标可交互 |
| L-D 语义层 | 成功/警告/错误/信息(AI)/焦点 | **5 槽封顶** | 各槽固定色相，全局唯一含义 |
| L-E 冷色准入 | —— | 规则 | 冷色只能经 L-D 槽出现 |

### 1.2 中性层：4 级表面阶（tonal surface ladder）

| 级 | 语义 | 用途 | 现有落点（`tokens_v2/theme_manager.dart` SparkleColors） |
|---|---|---|---|
| S0 canvas（画布） | 最深/最底 | 页面背景 | `surfaceAmbient`（light 0xFFFCF8F3） |
| S1 base（基础面） | 页内卡片 | 默认卡面 | `surfacePrimary`（light 0xFFF8F4EF） |
| S2 raised（浮起面） | 悬浮/弹层/选中卡 | sheet、下拉、拖起卡 | `surfaceSecondary`（light 0xFFF1EBE4） |
| S3 elevated（高亮浮起面） | 最高强调容器 | 选中态容器、焦点卡 | `surfaceTertiary`（light 0xFFE7DED4） |

- **规则 1.2.1**：相邻级差必须可辨——S0/S1 亮度差 ≥3%、S1/S2 ≥3%、S2/S3 ≥4%（当前值已满足，算法生成时作为验收下界）。卡与底的区分靠**色阶**，不靠阴影；阴影只允许浮起件（dialog/sheet/拖拽中的卡）。【依据：AUDIT S1「层次靠猜」；I-P2 M3 tonal surface】
- **规则 1.2.2**：中性层值由 `material_color_utilities`（官方 Dart 实现，已在 Flutter 生态可用）以暖 seed 生成，seed 取暖棕 hue≈28、chroma≤12（保 calm/paper 不变灰）。批 2 落地时以现 batch-1 校准值（0xFFF8F4EF 族）为 seed 快照回归锚——算法输出与现值偏差 ΔE≤2 视为等价，超限需设计评审。【依据：CONFLICTS C-06 裁决＋steelman 驳回（算法已解决对比度保证）；I-P8】
  - **ΔE 度量口径（v1.0 增补，R4 P0-2）**：ΔE 采用 **CIEDE2000**（D65/2° 观察者，Lab 由 sRGB 线性化换算）。度量脚本落点 `scripts/design/check_surface_ladder_de.py`（输入=算法输出 S0–S3 四值 + batch-1 锚点四值，输出=逐对 ΔE 与 PASS/FAIL 清单），随 B2-2 同批交付并入 A1.6 机检——**脚本合入前 A1.6 不得宣称达成**。对齐过程：对每个锚点 hex 反推 HCT tone，算法侧取同一 tone 的输出值做逐对比较；「偏差」一律指本脚本输出，禁徒手目测或跨工具口径混用（`material_color_utilities` 本身不输出 ΔE，禁以其 tonal palette 近似替代判定）。
- **规则 1.2.3**：卡片不套卡片（nested cards 禁）。分组优先用留白（≥16dp）与对齐，其次用 S0/S1 换色，最后才是描边；描边对比度 ≤S1/S2 级差（结构「在而不吵」）。【依据：CONFLICTS C-01 引 INTL 原则 2；AUDIT S6/S10】

### 1.3 文字层

| 级 | 用途 | light 值（现有） | 对比度要求 |
|---|---|---|---|
| textPrimary | 标题/正文主体 | 0xFF171717 | ≥4.5:1 on S0–S2 |
| textSecondary | 次要说明/元数据 | 0xFF6C655D | ≥4.5:1 on S0–S1 |
| textTertiary | 辅助（新增槽，现用 textSecondary 兼） | 批 2 定标 【定标待实测】 | ≥4.5:1 on S0 |
| textDisabled | 禁用态（状态色，非层级） | 0xFFA49B90 | 豁免 |

- **规则 1.3.1**：三级封顶。现网「用透明度压文字」的写法（`Opacity`/`withOpacity` 作用于文本）视为第四级，禁新增；存量迁移。内容永远是最深的颜色（Things 原则）。【依据：INTL §1.1#1】

### 1.4 交互层：唯一 accent

- **规则 1.4.1**：`brandPrimary`（light 0xFF825D49，batch-1 校准 5.31:1）是**唯一交互色**——只允许出现在：可点击控件（按钮/链接/选中态）、品牌时刻（splash 标志、onboarding）。禁兼做：正文强调（用 textPrimary+字重）、图标装饰、非可点标签、进度条装饰。【依据：D6；AUDIT S1（棕色四任，HIG「同色双义」违规，INTL §4#3）；I-P3】
- **规则 1.4.2**：`brandSecondary` 退役为 AI 语义槽的派生来源（§1.5 info 槽），不再作为第二交互色。DS 里 `DS.accent => brandSecondary` 的别名（符号 `DS.accent`，design_system.dart:614 @9ca4cd0c，行号漂移以符号名为准）标 @Deprecated，新代码禁用（DL-SPEC `dsAccentAlias` 守卫已执行，基线 12 只降不升）。【落点：`core/design/design_system.dart`】
- **规则 1.4.3**：选中态可见性硬指标——选中与未选中控件在灰度截图下必须可辨（色彩不是选中态的唯一载体）：选中 = accent 容器（accent 14% alpha 底 + accent 1.5dp 描边 + 前置 check 图标，即 `SemanticPill.selected` 现行规格），未选中 = S1 底 + 1dp 描边（neutral300）。【依据：AUDIT S14/V7（onboarding 选中 chip 扫视难辨）；U-01 Step1 已建 selected 态 owner】

### 1.5 语义层：≤5 槽

| 槽 | 色相 | light 值（现有 batch-1 校准） | 准入内容 |
|---|---|---|---|
| success | 灰绿 sage | 0xFF456E52 | 完成、达成、在线 |
| warning | 琥珀 amber | 0xFF7D5C26 | 注意、临近截止、降级提示 |
| error | 陶土 terracotta | 0xFFA0483E | 失败、错误、逾期 |
| **info（AI 信息，唯一冷色槽）** | slate 蓝 | 0xFF48678D | AI 状态、AI 建议、确认请求、数据可视化主色 |
| focus | 现由 accent 兼任 | ——（批 2 评审是否独立） | 键盘/无障碍焦点环 |

- **规则 1.5.1**：槽位封顶 5。`PillTone` 六值映射：`info/success/warning/danger→error/neutral→中性层/brand→accent`，不加第七槽。任务类型色（taskLearning/taskTraining/taskReflection…）在**进度展示位**禁用（进度位只编码掌握度，B-02 裁决），仅允许动机层徽章/日历身份色引用，且须从语义槽派生（`Color.derive` 类）。【依据：CONFLICTS B-02 两层分离；INTL §1.6#2 chips 色语义封顶】
- **规则 1.5.2 冷色准入**：冷色（蓝/青/紫系）只允许经 info 槽出现，且只用于「系统在说话」的内容（AI 状态、数据可视化、确认动作）。禁装饰。现状越界冷色全部改造：home「50%」蓝 chip→语义重评（是 AI 判断→info 槽；是进度→中性层+字重）；profile「亮度 50%」与折线图→数据可视化走 info；chat 蓝底建议 chip→归 §4.2 chip 语法。**判定口诀：这个蓝色在替系统说话，还是在替设计说话？**【依据：D6；AUDIT S1「像从另一套设计里掉进来」；C-06#5】
  - **存量清偿目标（v1.0 增补，R4 P2-7）**：DL-SPEC `coldColorLiteral` 基线 **90 处/19 文件**（冻结于 d87d42ea，最大户 `visual_element_palette.dart` 31 处）为批 2 palette 迁移的清偿对象：批 2 验收含该基线**下降 ≥50%**，批 3 清零。降基线靠 token 化替换，不扩守卫启发式面（已知漏报：低饱和冷色 sat<0.15，见 A1.3）。扫描域（features）外已知单点：`app/routes.dart:113 @9ca4cd0c` 的 `Colors.grey`，登记 §10.5 台账，批 2 随 B2-2 顺手清。

### 1.6 对比度验收数字

| 对象 | 要求 | 依据 |
|---|---|---|
| 正文文字（<18pt） | ≥4.5:1（WCAG AA） | 批 1 校准已达标（≥5.3:1），保持 |
| 大字（≥18pt bold 或 ≥24pt） | ≥3:1 | WCAG AA Large |
| UI 组件边界/图形（图标、描边、图表线） | ≥3:1 | WCAG non-text |
| 选中态 | 选中容器 vs 背景 ≥3:1，且灰度可辨（§1.4.3） | AUDIT S14 |
| dark 模式 | 同规则；dark 文字主色 0xFFF4F1EB on 0xFF1A1A1E 已 ≥12:1 | 现值 |
| highContrast / colorBlindFriendly | 保留现有两套变体（Wong 2011 CB-safe 全保留） | theme_manager.dart:418–475 |

机检：对比度计算脚本纳入批 2 工具链（对 SparkleColors 全量组合跑 WCAG 公式，输出违规对清单）——见 ACCEPTANCE A1.7。

### 1.7 token 命名草案与替换映射策略（渐进迁移）

**原则：不改名、先立规，别名渐进。** 现有 `SparkleColors` 字段名保留为值层 owner；规范命名作为语义层文档先行，代码层新增 `context.colors` 语义别名（落点 `core/design/theme/sparkle_context_extension.dart`，属批 2 工作包 B2-2）。

| 规范名 | 现有 token（owner） | 迁移动作 |
|---|---|---|
| surface.canvas | `surfaceAmbient` | 别名 getter，不迁移字段 |
| surface.base | `surfacePrimary` | 同上 |
| surface.raised | `surfaceSecondary` | 同上 |
| surface.elevated | `surfaceTertiary` | 同上 |
| text.primary/secondary/tertiary | `textPrimary/textSecondary`（+新增 tertiary） | tertiary 新建 |
| accent | `brandPrimary` | 不动 |
| semantic.success/warning/error/info | `semanticSuccess/…/semanticInfo` | 不动（已是规范形） |
| galaxy.* | `galaxyBackground/galaxyShadow` + sector_config 局部调色 | 按 §7.2 锤内规范收编入口，E1 豁免维持 |

**新代码门禁分两段（v1.0 改写，R4 P0-1——v0.9「迁移期即生效」表述废除：语义别名 getter 现不存在，`context.colors` 现返回旧字段名 owner `SparkleColors`，语义名一个都不可用）**：

- **【立即】段**（自本规范合入即生效）：禁新增 `Color(0x…)` 字面量与 `Colors.*` 引用。由 ratchet 守卫执行：`check_ui_design_tokens_ratchet.py` colorLiteral（基线 103 只降不升）＋ DL-SPEC `colorsDotNative` 维（`mobile/lib` 域，白名单 white/black/transparent）。
- **【批 2 起】段**：语义别名 getter（`context.colors.surface.canvas` 等）随 **B2-2 合入 `sparkle_context_extension.dart`** 后，新代码取色只走语义名，旧字段名（`surfaceAmbient` 等）降为只读 owner。

两段生效时点均以守卫/别名合入 commit 为准，**不以本规范合入为准**。【依据：README CONVENTION 规则 2；AUDIT §7 交叉根因①；R4 P0-1】

---

## §2 动效系统

> 架构裁决：D7——单套 5 级阶梯 + elasticOut 全局除名 + 动量才准过冲（tap 100% 阻尼）+ lint 门禁与新旧对比面板同批强制。【依据：CONFLICTS C-08；AUDIT S16/S17/S20；TRIAGE §4 勘误（真冲突=路由转场内联映射 vs DS.motionDuration，motion.dart 本是别名）】

### 2.1 时长阶梯（5 级，唯一事实源）

**Owner：新建 `core/design/tokens_v2/motion_token_v3.dart`**（批 2 落地；落地前由本规范数值表为唯一口径）。现有 7 值 `SparkleMotionToken`（micro/quick/responsive/standard/deliberate/scene/hero）收敛映射如下：

| 级 | 规范名 | 带宽 | 正典值 | 曲线 | 用途 | 替代旧值 |
|---|---|---|---|---|---|---|
| M1 | micro | 100–150ms | **120ms** | `Curves.easeOut`（100% 阻尼） | tap 反馈、勾选、chip 选中、开关 | micro 120 / quick 150 / buttonTap 100 |
| M2 | standard | 200ms | **200ms** | `Cubic(0.2,0,0,1)`（M3 standard） | 页面内过渡、展开收起、列表项增删 | responsive 180 / standard 220 |
| M3 | emphasized | 300–350ms | **320ms** | 入场 `Cubic(0.05,0.7,0.1,1)`（emphasized-decelerate）；退场 `Cubic(0.3,0,0.8,0.15)`（emphasized-accelerate） | 卡片/面板展开、页面转场 | deliberate 300 / scene 400 |
| M4 | large | 450–500ms | **480ms** | 标准曲线；**须手势动量驱动**才可用 | 大区域转场、拖拽跟手补完 | pageTransition 350→改 M3 |
| M5 | narrative | 600–700ms | **650ms** | 非对称减速 | 仅 onboarding 入场、galaxy 仪式模式、成就回顾 | hero 620（非叙事用途删除） |

- **规则 2.1.1**：reverse 时长 ≤ forward（现路由转场表已符合，保留比例约 0.7）。【落点：`core/navigation/sparkle_route_transition.dart`（内联 switch 两份，符号 `forwardDuration/reverseDuration`）】
  - **reverse 取值唯一口径（v1.0 增补，R4 P1-2）**：reverse = forward×0.7 **吸附至白名单后的正典映射表**——M2 `200→140`、M3 `320→250`、M4 `480→350`、M5 `650→450`。**本表为唯一 reverse 口径，禁现场另算**（0.7×320=224、0.7×480=336 等非白名单值禁直写——它们会被 G1 抓为违规且不在正典集合）；M1 micro 反馈类不设独立 reverse（进出同长）。reverse 表值 {140,250,350,450} 为 G1 白名单的组成部分（§9.1），批 3 起白名单收窄为「正典值 ∪ reverse 表」。
- **规则 2.1.2**：M4 的「手势动量驱动」判定 = 动画初速度来自手势速度（drag/swipe velocity），tap/按钮触发一律 M1–M3。无动量驱动的 M4/M5 视为违规（对照 620ms hero 现状）。【依据：INTL §1.8「620ms 无手势驱动即超预算」】
- **规则 2.1.3 数值唯一**：`sparkle_route_transition.dart` 的两份内联 switch（forward/reverse 各一份数值表）删除，改调 motion_token_v3 单一映射（TRIAGE S16 修复落点：触达 ~2 文件）。`motion.dart`（别名类）与 `DS.motionDuration` 全部指向 v3 表。【依据：TRIAGE §4】
  - **迁移顺序固定（v1.0 增补，R4 P1-3）**：①新建 `motion_token_v3`（含 reverse 表）→ ②路由两份内联 switch 删除改调 v3 → ③`DS.motionDuration`/`motion.dart` 改为 v3 别名 → ④**G1 扫描域扩至 `core/navigation` 与 `core/design`**（④为②③的验收，不可省——当前 G1/DL-SPEC 只扫 features 域，`sparkle_route_transition.dart` 所在的 `core/navigation` 是 v0.9 守卫盲区，最大违规面的收敛动作不受任何守卫约束）。引用计数一律以 G1 守卫口径为准；正文「131 处 SparkleMotionToken 引用」为起草时点数（TRIAGE wt83 口径），现值已漂移（**172 refs @9ca4cd0c**），不作为验收数字。

### 2.2 曲线与阻尼规则

- **规则 2.2.1（WWDC803 阻尼规则，全 app 唯一过冲条款）**：动量手势（拖拽/轻扫有初速度）→ 允许 easeOutBack 级 80% 阻尼**一次**轻微过冲；一切 tap 驱动 → 100% 阻尼零过冲。弹跳是含义不是口味：过冲只允许出现在「教用户可以再用力」的教学信号位，默认不用。【依据：INTL §1.7 WWDC803 #4/#5；I-P5】
- **规则 2.2.2（elasticOut 除名）**：`AnimationSystem.spring = Curves.elasticOut` 与 `SparkleMotion.bounce = Curves.elasticOut`（motion.dart:45）全局除名——引用处按 2.2.1 重新归类（tap 驱动改 standard 曲线，动量驱动改 easeOutBack）。`bounceOut` 同除。【依据：D7；AUDIT S16「把弹性动画做成橡皮筋」】
- **规则 2.2.3（可打断）**：一切动画进行中必须可被新意图打断（AnimationController 重定向/反向，不 ignore 新输入）；任何交互不得「等动画播完才响应」。【依据：HIG Motion「let people cancel motion」；WWDC803 #2】

### 2.3 触觉语义表（全 app 一张表）

| 场景 | 触觉 | 视觉伴随 |
|---|---|---|
| 签名完成（§2.4） | `HapticFeedback.mediumImpact`（Success 语义） | 签名动画 |
| 选择器滑动/chip 选中 | `HapticFeedback.selectionClick` | M1 |
| 错误/失败 | `HapticFeedback.heavyImpact`（Error 语义） | 错误态（§4.5） |
| 进入专注/长按开始 | `HapticFeedback.lightImpact` | M2 |
| 滚动到顶/底 | 现有 scroll_edge_haptics 保留 | —— |

触觉必须可关（settings 无障碍区，§8 settings 蓝图；**验收条款 A2.13**：settings 屏存在触觉开关、默认开启、写入 provider 持久化）；默认强度低；禁无因果的彩蛋触觉。【依据：HIG Playing haptics「因果对」；INTL 原则 13；R4 P2-5】

### 2.4 签名位清单（全 app 唯一完成动画）

**全 app 完成时刻只有一个动效签名**：任务完成勾选动画。

| 参数 | 值 |
|---|---|
| 时长 | ≤300ms（正典 240ms：勾笔画绘制 180ms `Cubic(0.2,0,0,1)` + 容器 scale 0.95→1.0 60ms） |
| 可打断 | 是（完成态立即可见，动画只是确认） |
| 触觉 | Success（§2.3 表） |
| 使用范围 | 任务卡完成钮、目标里程碑、复习完成——同构复用，同一规格 |
| Owner | 新建 `core/design/widgets/signature_check.dart`；现有 `success_animation.dart`/`SparkleConfetti` 降级为 §2.5 庆祝专用 |

**边界条款（B-03 消解）**：HIG「高频交互不加动效」禁的是装饰性/常驻/等待型动效；本签名位属「短而准的确认性反馈」（≤300ms、可打断、不阻塞下一操作、配语义触觉），属于反馈不属于装饰。除此之外的一切高频操作零动效。【依据：CONFLICTS B-03；EDU 对照 Things 勾选（INTL §1.1#3）】

### 2.5 删除清单与降级清单

**删除清单（批 2 执行，机检可拦新增）**：

| # | 对象 | 现状落点 | 处置 |
|---|---|---|---|
| D-1 | 0.25Hz 常驻呼吸 | `motion.dart:97–104 createBreathingController`（4s/repeat reverse） | 删除。状态需要「活着」感 → 改为状态变化瞬间的**单次**脉冲（M2，≤1 次/事件） |
| D-2 | 非叙事 620ms hero | `tokens_v2/animation_token.dart:23 hero=620ms` | 归 M5 narrative，仅仪式场景可用（§2.1 表）；页面间 hero 用 M3 |
| D-3 | 900ms splash 编排 | `features/splash/presentation/screens/splash_screen.dart:28–29` | ≤400ms 一轮最短动画；TRIAGE 已证与 auth 判定并行不阻塞——保留并行，删冗余段（logo scale→title→subtitle→indicator 四段并一段） |
| D-4 | elasticOut/bounceOut 全局 spring | `tokens_v2/animation_token.dart:9–10`、`motion.dart:45` | §2.2.2 |

**降级清单**：

| # | 对象 | 现状 | 降级后 |
|---|---|---|---|
| G-1 | confetti | task 完成单 owner 挂载（Step6 已修双份） | 仅**里程碑**（周目标达成/目标完成/连胜安全网触发）单份 ≤600ms；普通任务完成只有签名勾选（§2.4），不放 confetti |
| G-2 | particle | home 5 层装饰、galaxy 147 粒 | 仅完成时刻/仪式模式单次爆发；受 `GlobalParticleCounter` 上限（默认 80/小屏 64/48/reduce-motion 0，已实现） |
| G-3 | glow | home 113 处引用 | 只给「当前唯一焦点」（正在进行的任务卡/仪式主节点），每屏 ≤1（galaxy 仪式模式 ≤2：主节点+选中节点）。**H3 后：galaxy 豁免预算随 §0.1 下调一档（优先砍 glow 顺序不变）** |
| G-4 | weather 层 | `weather_layer.dart` 零门控直通（TRIAGE S6 剩余半边） | 补 `PerformanceTier` 门控（对齐 background/effect/particle 层同规格） |
| G-5 | attention pulse | `pulse_scope.dart` maxActiveSlots=**2** | 改为 **1**（同屏持续动画源 ≤1 的机制化落点）；galaxy 仪式模式走独立预算不占此槽 |

【依据：D1/D7；CONFLICTS C-08 降级项；AUDIT S6/S17；INTL 原则 14/15；DECISIONS 附录 H3 裁决 #4】

### 2.6 同屏持续动画源 ≤1：计数口径

- **持续动画源定义**：任何**循环或无限时长**的动画驱动——repeat/reverse-repeat 的 controller、粒子发射器、shimmer 循环、painter 持续重绘（`repaint` listenable 驱动）、呼吸/脉动。**单次有限时长动画（M1–M5）不计数。**
- **计数规则**：每屏同时活跃的持续源 ≤1。shimmer 骨架在屏时占用该唯一名额（加载期通常无其他持续源，天然满足）；加载完成骨架消失，名额归还。
- **galaxy 豁免区合计预算**（锤内规范，仪式模式）：豁免不是免检——仪式模式同屏预算 = 持续源 **1**（星空缓转/闪烁二选一）+ particle ≤80（GlobalParticleCounter 口径）+ glow ≤2 + 节点入场 stagger 一次性（不计）。**工作视图（Tab 默认）持续源 = 0**（纯静态 + 交互瞬间动效）。合计预算超限时优先砍 glow，再砍 particle 密度，最后砍持续源——顺序固定。【依据：D5 增补「豁免区立锤内规范+同屏合计预算」；AUDIT S5/S17（豁免区从未做过同屏合计）；H3 后预算下调见 §0.1】

---

## §3 排版与密度

> 依据：INTL Typography 硬条款（正文 17pt 级、避细字重、最小字号、text styles 即节奏表）本地化；AUDIT S3/S4。

### 3.1 字号/字重/行高层级

Owner：`SparkleTypography`（`tokens_v2/theme_manager.dart`，符号 `SparkleTypography`/标准工厂，行号随树漂移见 §11.1）。**角色结构保留，数值重定标如下**（批 2 golden 快照后冻结；迁移为长尾批次）：

| 角色 | 字号 | 字重 | 行高 | 用途与约束 |
|---|---|---|---|---|
| display | 46 | w700 | 1.2 | **仅** onboarding 开场、成就仪式（§2.1 M5 场景）。禁用于内容屏 |
| headline | 28 | w700 | 1.3 | 页大标题（每屏 ≤1） |
| title | 22 | w600 | 1.3 | 卡组标题/区块标题 |
| subtitle | 19 | w600 | 1.4 | 卡标题 |
| body | 17 | w400 | **1.6** | **阅读型正文**：chat 消息、AI 解释、文章 |
| secondary | 15 | w400 | 1.5 | 列表正文/控件文字 |
| label | 13 | w500 | 1.4 | chip/标签/元数据 |
| caption | 12 | w400 | 1.4 | 时间戳/脚注。**全 app 最小字号** |

- **规则 3.1.1**：中文正文行高 1.5–1.7（body 1.6 正典）；单行标签 1.2–1.4。西文行高条款（HIG ~1.2）不适用于 CJK 正文。【定标依据：中文可读性共识；I-P9】
- **规则 3.1.2**：禁用 w300 及以下字重（中文细字重在低端屏发虚）；「强调」优先用 textPrimary+加粗，**禁**「加大加粗连排」——标题级字号连续 ≥3 行视为层级滥用（解 S4 大字喊话）。【依据：HIG Typography；AUDIT S4】
- **规则 3.1.3**：正文最老 17——chat 消息/长解释必须 body(17)；secondary(15) 只用于控件与列表，禁承载需阅读的 AI 输出。【依据：INTL §1.7 Typography「正文默认 17pt 级」】
- **规则 3.1.4**：`fontSize:` 字面量禁新增（存量 1293 处，features 全口径——TRIAGE S4；守卫 `check_ui_design_tokens_ratchet.py` 只降不升已覆盖）。

### 3.2 截断与折行策略（解 S3）

**方法论：最小容器宽度 × 最大文案长度配对表**。每个文本角色登记「容器最小宽（dp）/最大字符数（中文口径）/超限策略」三元组；l10n 文案入库时按最长 locale 校核（当前只有 zh/en，en 按字符数 ×1.6 估算——该估算值实现为 A3.4 脚本常数，调整需设计评审，见 R4 P1-10）。

| 角色 | 容器最小宽 | 最大长度 | 超限策略 |
|---|---|---|---|
| 页大标题（headline/title） | ≥200dp | 16 字 | **禁 ellipsis**——2 行上限（`maxLines:2`）+ 文案入库前按 16 字裁写 |
| 卡标题（subtitle） | ≥160dp | 20 字 | 2 行上限 + ellipsis 仅第 2 行末 |
| 顶栏标题 | ≥120dp | 16 字 | 2 行或缩写；**现状反例**：chat 顶栏「AI学习助手」在 Expanded 内 1 行截断成「AI…」（chat_screen.dart:1240–1247 @R3 时点），改为标题区占位 ≥120dp 或降级为无标题 |
| chip/pill | 64dp | **6 字** | 单行 ellipsis 允许（chip 是扫视件）；超 6 字的语义必须改写成 ≤6 字，禁只截不写 |
| 输入框 placeholder | 与输入框同宽 | **14 字** | placeholder 必须短于可容纳字数（现状反例：onboarding「例如：备考期末 / 学会Flutter」自身截断——arb:1141 缩为「例如：备考期末」） |
| 按钮文字 | —— | 8 字 | 禁 ellipsis；超限改文案不缩容器 |
| toast/通知条 | —— | 2 行 | 完整句允许，禁关键信息在第 2 行 |

- **规则 3.2.1**：单行 ellipsis 只允许出现在 label/caption/chip 三类扫视件；body/subtitle 及以上禁单行截断（宁可 2 行，不可「AI…」）。【依据：AUDIT S3「截断是没打磨的最快线索」】
- **规则 3.2.2**：可横向滚动的 chip 条（快捷条/建议条）末位必须留 ≥24dp 渐隐遮罩或边缘阴影提示「还有更多」；禁无提示硬截（V10「好奇…」反例）。【落点：`intent_prediction_bar.dart` 等】
- **规则 3.2.3 中文断词**：多行中文用默认 `softWrap`；中英混排处（如「学会Flutter」）禁手动空格断行；CJK 与拉丁混排行首禁出现标点（Flutter 默认避头尾已覆盖，禁用 `overflow: fade` 于多行文本——渐隐只用于 §3.2.2 横滚提示）。
- **规则 3.2.4 角色登记（v1.0 增补，R4 P1-10）**：新 arb key 必须携带角色后缀（`…Chip/…Hint/…Button/…Title/…Label`），无后缀机检告警（A3.4）；存量 key 由本配对表逐条登记角色（人审一次性，登记入 §10.5 台账），登记后按同规则限长。

### 3.3 密度

- 列表项最小高度 56dp、卡内边距 16dp、屏边距 16dp（现有 SparkleSpacing 阶梯内取值）；信息密度按「每屏 1 主角 + ≤3 支撑」排布（§0.2 必达项 ≤2 的视觉表达）。【依据：I-P1 内容优先；§8 各屏蓝图】

---

## §4 组件语法

> Owner 延续 U-01 收敛成果不推翻：`SemanticPill`/`TaskPill`/`SparkleButton`/`SparkleCard`/`EmptyState`/`CustomErrorWidget`/`SparkleSkeleton`/`AiStatusCapsule`（`core/design/components/atoms/`、`core/design/widgets/`）。本节为它们补语法规范与门禁扩展。

### 4.1 chip/pill 归一规则（解 S9）

- **规则 4.1.1 唯一 owner**：一切 chip/pill/badge/capsule 类小标签必须用 `SemanticPill`（语义/状态/筛选，含 selected/onDeleted）或 `TaskPill`（任务域）；私有 pill 类禁新增（守卫 parallelClass 已管；存量 178 私有类/119 文件按 §10 批 3 迁移，`status_awareness_bar.dart` 7 个 pill 类先行）。【依据：TRIAGE S9】
- **规则 4.1.2 选中态**：统一走 `SemanticPill.selected`（accent 容器+check 前置，§1.4.3），禁自造选中样式（现状四种样式混排——描边米色/蓝底浅填充/灰底填充/带图标不带图标——全部归一）。【依据：AUDIT S9】
- **规则 4.1.3 图标规则**：语义 pill（状态告知）可带 16px 图标；交互 chip（点了有动作）默认**不带图标**，靠文案；图标不是 chip 的装饰位。图标与文字间距 4dp。【依据：AUDIT S9「带图标/不带图标混排」】
- **规则 4.1.4 数量上限/屏**：同屏可点 chip ≤6；**AI 一条回答之后同屏 chip ≤3**（建议话术类，§7.1）；确认请求类不占 chip 名额（走收件箱/内联确认，§7.3）。【依据：AUDIT S9「一答十 chip」；CONFLICTS C-11（chips ≤3）】
- **规则 4.1.5 tone 准入**：PillTone 六值按 §1.5 映射；「brand」tone 仅用于 accent 语义（可交互/品牌），禁作状态色。

### 4.2 控件层级语法（解 S14/S15）

三类控件视觉语法必须可区分：

| 类 | 语法 | owner/规格 |
|---|---|---|
| 主操作（屏内唯一） | 填充 accent 实底 + textPrimary onAccent | `SparkleButton` variant=primary；**每屏 ≤1** |
| 次操作/展开 | 描边或浅填充 | variant=secondary/outlined/text |
| 导航/进入 | 无底色 + trailing chevron「›」 | 自绘规则：chevron 16px、textSecondary、右缘对齐 |

- **规则 4.2.1**：完成类控件（勾/「完成」）与展开类控件（chevron）**不得同视觉权重并排**——任务卡规格：完成钮带文字标签（现 task_card.dart 已改「完成」pill，保持）居右下主位；chevron 缩至 16px、textSecondary、置于卡右上角，热区独立 ≥44×44dp。【依据：AUDIT S14；TRIAGE S14「歧义减半，规范仍缺」】
- **规则 4.2.2 折叠卡 vs 导航卡**：折叠卡 chevron 竖排且点击时旋转 180°（M1 动画）；导航卡 trailing「›」恒定向右不旋转。两种卡禁止同款式同位（settings「无障碍」双卡反例，§8 settings）。【依据：AUDIT S15】
- **规则 4.2.3**：affordance 单一——一个控件只表达一种意图；「确认」按钮出现时其确认对象必须在同屏可见（解 S13 悬空确认）。【依据：AUDIT S11/S13】

### 4.3 空态规范（解 S11）

空态组件 owner：`EmptyState`/`CompactEmptyState`。内容三要素：

1. **为何空**（一句话，指向原因：「还没有最低达标线，设置后 Sparkle 才能帮你盯进度」）；
2. **单一 CTA**（可选，指向**创建该内容**的动作：「去设置达标线」）；
3. **禁悬空主按钮**——空无一物时禁出现「确认/保存」类确认钮（minimum_criteria_card.dart 历史「确认」钮块反例——**已落地修复 @B1-A**：按钮块条件改为 `!criteria.isConfirmed && criteria.thresholds.isNotEmpty`，空态取纯文案）；禁把操作指令当副标题（「点击展开/收起」反例——chevron 已表达）；
4. 空态不得与数据同屏混排打架（galaxy「还没有点亮掌握记录」叠在 147 节点上，V24 类）——空态只在**确认无数据**时出现（四态规范 §4.5）。【依据：AUDIT S11；CONFLICTS C-09 空态基线】

### 4.4 加载与骨架

- **规则 4.4.1**：骨架唯一 owner `SparkleSkeleton` 家族；**骨架必须贴最终布局**（块位置=内容位置，屏级骨架用 `SparkleCardSkeleton/SparkleListSkeleton/SparkleChatBubbleSkeleton` 组合出目标布局），禁统一灰块垫场。验收：骨架→内容切换无布局跳变（golden 前后帧对比，ACCEPTANCE A4.6——golden 管道自批 2 起，批 1 以手测替代，见 §10.2）。【依据：AUDIT S19；CONFLICTS C-09「结构已知数据加载」】
- **规则 4.4.2**：裸 spinner 禁新增于首屏主路径（守卫已管 rawSpinner）；>2s 的等待必须有阶段感（§4.5 AI 行 / §7.1）。
- **规则 4.4.3**：骨架 shimmer 是持续动画源，占 §2.6 唯一名额。

### 4.5 四态规范（D9 分工矩阵）

每个异步内容位必须实现四态：**加载（loading）/ 空（empty）/ 错误（error）/ 内容（content）**，外加 **回归（comeback）** 为一等状态。分工矩阵：

| 场景 | 范式 | 硬规格 |
|---|---|---|
| **本地可预测操作**（勾任务、开关、保存、拖拽排序） | **乐观 UI** | <100ms 响应底线性；成功**不庆祝**（静默成功，HIG「成功是预期，只需报忧」）；失败回滚 + 人话 toast + 重试按钮 |
| **AI 推理等待**（chat 首流、星图重算、记忆聚合） | **诚实分阶段** | 分期见 §7.1 流程；**AI 内容禁预填结论**——禁在流式前渲染疑似答案段落/假答案骨架；流式本身允许（token 到达即渲染，每个 token 都是真的） |
| **结构已知的数据加载** | **骨架贴布局** | §4.4 |
| **错误态** | **人话 + 重试 + 保留现场** | 模板三句式：「发生了什么（人话）＋影响什么＋怎么办（重试钮）」；禁裸异常文案（V25「Unsupported operation: …」类）；禁「Oops, something went wrong」英文直出（机检 A6.6 大小写不敏感）；重试必须保留用户已输入内容；owner `CustomErrorWidget`/`CompactErrorCard`（9 surfaces 现仅 9 处采用，私有 error 类遍地——批 1 迁移） |
| **回归时刻**（距上次打开 ≥72h【定标待实测，区间 48–96h】或连胜中断后回归） | **易赢 + 少东西 + 小礼物** | 首屏 ≤2 卡、首动作是低难度复习（复述昨日 1 个概念级）、问候含进度肯定（「回来啦，你的图论星图已点亮 12 个节点」）；禁堆功能、禁横幅轰炸。现状 ComebackBanner 是 chat 顶部 8 件之一（TRIAGE S8 清单），批 3 迁为独立回归接管屏 |

**错误态是四态规范的倾斜重点**（现状 1.7/5 全 app 最差项）。**诚实层是 H3 后的签名特性**（DECISIONS 附录 #3）：不确定时明说（§6.3 三档）、改口承认、推荐附一行「为什么是它」——见 §10.1 B1-6。【依据：DECISIONS D9；CONFLICTS C-09 全条 + steelman 驳回（禁的是预填结论非流式）；EDU 原则 5；AUDIT §5；DECISIONS 附录 H3 裁决 #3】

---

## §5 空间纪律

### 5.1 面积预算表

| 屏 | 预算条款 | 依据 |
|---|---|---|
| chat | **会话本体（气泡流）≥70% 屏高**；系统件（记忆/确认/模式/建议）全部撤出常驻区——改内联微件（消息旁 chip 级）或收件箱（§7.3） | D3；AUDIT S8（现状 25%） |
| home | 首屏「今天该干什么」入口（指挥台/今日下一步）**必须在折叠线上方**；「Sparkle 对你的理解」卡 ≤35% 首屏且可折叠；底部叠层 ≤2（Tab + 输入条；快捷 chip 并入输入条下游，§7.3） | AUDIT S10/V9；CONFLICTS C-11 |
| goal/task/memory | 每屏空态区块 ≤1 个常驻（多个空区合并为单一「从哪里开始」入口） | AUDIT S11（goal 3/5 区块是空态） |
| galaxy | 工作视图/仪式模式分离（§7.2）；控制件与画布同暗（§7.2 锤内规范） | D5 |
| 全局 | 常驻系统面板（与用户当前任务无关的面板）每屏 ≤1 | D3 撤出常驻区的外推 |

### 5.2 系统件收容规则

系统件（AI 主动性产生的 UI）只有三种合法形态：

1. **内联微件**：长在被描述对象旁边、chip 级高度（≤40dp）——记忆状态=消息旁「已记住 ✓」微型信号，不是顶部面板（INTL 原则 12「inline 是微件不是面板」）；
2. **收件箱**：`features/notification_center/` 为唯一聚合地——Aurora 确认队列、建议、预警按需取用，**禁注入 chat 常驻区**；
3. **阶段胶囊**：仅存在于等待期（§7.1），完成即消失。

【依据：D3/D8；CONFLICTS C-03 三级形态、C-10 第 5 条】

### 5.3 装饰预算数字账本

| 项目 | 上限 | 计数口径 | 机制落点 |
|---|---|---|---|
| 特效层/屏 | **1**（现 home 5 层：background/weather/particle/effect+renderer） | 挂载层计数 | `visual_renderer` 挂载点裁剪；层门控全覆盖（含 weather，§2.5 G-4） |
| 粒子/屏 | **80**（小屏 64/48，reduce-motion 0） | GlobalParticleCounter | 已实现，守卫化 |
| glow 焦点 | 1（galaxy 仪式 ≤2） | §2.5 G-3 | —— |
| gradient/屏 | ≤2 处且非核心流程 | ratchet 口径新维度 | A5.3 |
| confetti | 单份 ≤600ms，仅里程碑（§2.5 G-1） | 挂载计数 | SparkleConf_intensity 契约 |
| 持续动画源 | ≤1（§2.6） | PulseScope/手动 | PulseScope slots 2→1 |
| 装饰对比度 | 不得高于核心信息 | 人审 | DESIGN_DIRECTION 既有条款，本行使其可验收 |

预算是**硬约束**：新装饰进入某屏前查账，超额必须先减后加（「每轮只加不减」是 AUDIT §7 交叉根因④，此表为其终止机制）。【依据：AUDIT S6/S17；U-01 §4；INTL 原则 15】

---

## §6 文案与数据呈现

### 6.1 语言层温度（D1）

- **AI 人格**：Aurora。语气规格四条：①善意（帮忙不审判）；②简洁（先结论后展开；同一条消息幽默 ≤1 处且不拿学习内容开玩笑）；③不装懂（不确定就说，走 §6.3 三档）；④立场（「on your team」——站在用户一边，推动作不下判断）。【依据：EDU §一.8 Pi 配方＋「情绪陪伴是佐料」（§一.10 豆包）；CONFLICTS C-01 语言层主战场】
- **Flighty 式结论+数字**：一切状态播报=确定结论+带口径数字+最小动作。「图论梳理完成，计划进度 41%→44%」，禁「任务状态已更新」。【依据：INTL §1.5；EDU 三大面推送】
- **失败不羞辱红线**：禁「又没坚持」「你怎么才…」「别人都在学」类比较与追责；错误归因于系统/流程（「这个知识点安排得太密了，我调一下」），不归因于人格（「你太懒」）。文案评审一票否决项。【依据：EDU 原则 2（growth.design 把 user shaming 列为反模式）；CONFLICTS C-04 T0】
- **诚实三件套（H3 签名特性，落批 1，§10.1 B1-6）**：①不确定时明说（§6.3 三档承载）；②改口承认（用户指出错误/系统自己发现错误时，明确承认并修正——NORTHSTAR-LOOP1 GP-07「纠正保持 fail」为反面证据）；③推荐附一行「为什么是它」（推荐动作给一句理由，不是裸建议）。用户原话要的是「坦白自己的缺陷」，不是思维链展示——重心从「展示过程」移到「诚实呈现」。【依据：DECISIONS 附录 H3 裁决 #3；NORTHSTAR-LOOP1 GP-07/BP-2】
- **称呼与语域**：称「你」；禁「亲」「您」；禁感叹号连用（同句 ≤1）。
- **人格结束权**：AI 对话必须内置「今天到此为止，且你今天赢了」出口（§7.1 效率档与 §7.4），禁无限追问式粘性。【依据：EDU 原则 8；Character.AI 反面教材（EDU §一.9）】

### 6.2 禁直出清单（S2 负面清单，机检靶）

| # | 禁出对象 | 现状实例 |
|---|---|---|
| X1 | 英文枚举（status/priority/unit…） | goal「active」「normal」（已词典化 @B1-B，防复发靠 A6.1） |
| X2 | 类型字面量 | 「>= 1boolean」（引擎已改整句模板 @B1-B，防复发靠 A6.5/词典单测） |
| X3 | DateTime.toString() 直出 | 「2026-09-20 15:00:00.000」（修复靶 pending_commitments_section.dart:55 已落地 @B1-B，`date_formatting.dart` 唯一入口已建） |
| X4 | 调试命名与 hash | 「并发测试节点-5c2d9cff」（测试数据污染；隔离 fixture 已落地 @B1-A，存量清洗 BLOCKED 见 A6.6/§10.5） |
| X5 | 机器自我指标 | 「把握度约 41%」（→§6.3 三档；Q 值/前瞻置信度已人话化 @B1-B） |
| X6 | 裸异常/英文错误页 | 「Unsupported operation: …」「Oops, something went wrong」（机检 A6.6） |
| X7 | 中英混排半句 | 「0 条当前 session 记忆」 |
| X8 | 起止相同的时间 Range | 「09/20 13:59 - 09/20 13:59」（折叠为单点时间；`formatSceneTime` 已落地 @B1-B） |

【依据：AUDIT S2（severity 5）；TRIAGE §3 五例施工图（B1-A/B1-B 已清偿，防复发条款维持）】

### 6.3 C-07 数字准入三则

> 裁决：Flighty 式数字与 S2 禁例的分界线 = 数字的**主体**（你的进步 vs 我的内部慌乱）与**口径稳定性**。【依据：CONFLICTS C-07】

1. **准入**（三条同时满足才准出现数字）：①描述**用户的学习状态**（掌握度、剩余天数、计划健康度变化）；②口径有单一事实源（模式见 **§9.4**），且**跨账本对账无矛盾**（如任务账本 completed=2 vs sprint 仪表盘 completed=0，NORTHSTAR-LOOP1 BP-4 形态——v0.9 把本条写死为「§10 批 1 S7 修复」一次性事件，废除）；③语义被 UI 教过（首次出现有一句解释，或口径稳定到形成上下文）。
2. **禁出**：模型自我置信度、原始 enum/类型/时间戳、调试命名与 hash、无轴无单位的图表数字（AUDIT S4 装饰图表）。
3. **三档人话翻译表**（AI 内部不确定性必须表达时）：

| 内部置信度 | 展示文案 | 附带动作 |
|---|---|---|
| ≥0.75【定标待实测】 | 「我比较有把握」 | 直接给结论 |
| 0.50–0.75 | 「还在确认，供你参考」 | 结论 + 建议核对来源 |
| <0.50 | 「这部分我不确定，建议核对教材」 | 弱化结论 + 核对入口 |

不出百分比。完整数据（历史轨迹/口径）走 §7.1 过程折叠出口，不堵死信息。【依据：CONFLICTS C-07 裁决＋steelman 驳回（伪精度非透明）】

### 6.4 数据词典 schema（S2 施工图）

**结构**（每域一文件，共享基础设施一处；**已落地 @B1-B，以下为已实现形态**）：

```
lib/core/display/lexicon/
  lexicon.dart              # LexiconEntry 类型 + Lexicon.lookup(domain, raw) 唯一入口 + bandLabel 三档
  goal_status_lexicon.dart  # 域词典：goal.status / goal.priority / memory.record
  criterion_lexicon.dart    # 达标线人话组装/旧机话正则兜底 + unit 词映射
  memory_event_lexicon.dart # 事件动词词典（规则表 + arb 模板）
  date_formatting.dart      # 时间格式化唯一入口
```

**LexiconEntry schema（v1.0 改写，R4 P0-3——v0.9 的 `labelZh/labelEn` 双字段方案废除）**：

现行实现 `LexiconEntry{domain, raw, label}`，其中 **label 为 arb key 间接引用**（`typedef LexiconLabel = String Function(AppLocalizations l10n)`；zh/en 文案只存在于 arb，词典层零硬编码，双语由 arb 机制承载）。**禁止在词典内建 labelZh/labelEn 双字段**——Dart 内双字段必然散落硬编码，恰恰违反本节「禁散落硬编码」。`tone?/icon?/verbTemplate?` 为预留可选扩展字段，批 2+ 按需追加；新增字段必须可空，禁破坏既有域词典（verbTemplate 语义现由 `memory_event_lexicon.dart` 的规则表＋arb 模板承载）。

| 字段 | 类型 | 说明 | 示例 |
|---|---|---|---|
| domain | String | 数据域 | goal.status |
| raw | String | 后端原值（enum/事件名） | "active" |
| label | LexiconLabel | 人话文案（arb key 间接引用，禁散落硬编码） | →「进行中」/「Active」 |
| tone | PillTone?（预留） | 展示槽位（§1.5） | info |
| icon | IconData?（预留） | 语义图标（可选） | —— |
| verbTemplate | 规则表+arb 模板（预留形） | 事件→句模板（{title} 占位） | 「已完成「{title}」」 |

**criterion 标签组装链（v1.0 写死唯一 owner，R4 P0-3）**：现状为三方并存（均核验 @9ca4cd0c）：引擎 `experience_readouts.py:184 _criterion_label`（整句模板版，B1-B 落地；GOAL-ROUTER 超集生效后已无生产消费者，随批 1 收尾删除并迁移其单测）；mobile `experience_models.dart:206 _criterionLine`（重建机器形 `'$label >= $threshold$unit'`，GOAL-ROUTER 滚动兼容代码）；`criterion_lexicon.dart:20 humanizeCriterionLabel`（旧机话正则兜底）。**唯一组装链裁决**：

1. 引擎只下传**结构化原值**（threshold/unit/metric/label 原文）＋模板 key（proto/gRPC 字段透传原值，翻译在表现层——分层边界不破坏）；
2. mobile `criterion_lexicon` 为**唯一组装/兜底 owner**（arb 模板重建人话；旧机器形正则兜底）；
3. `experience_models._criterionLine` 的机器形重建**仅为旧引擎滚动兼容**，须在引擎超集形状全量生效后删除（登记 §10.5 台账）；
4. 任何新域接词典前先在本节登记组装 owner，**禁止出现第二个组装点**。

**时间格式规范**：相对优先（「今天 15:00」「3 天后」「昨天」），≥7 天落绝对（「9 月 20 日 15:00」）；禁毫秒；同日起止 Range 折叠为单点（X8）；唯一入口 `date_formatting.dart`，`'${c.dueAt}'` 类拼接禁新增（pending_commitments_section.dart:55 修复靶——已落地 @B1-B）。【依据：AUDIT S2/V21；TRIAGE §3#2；B1-B REPORT】

**正例与迁移**：`plan_context_summary.dart:398–423 _statusLabel` 是既有正例（plan 状态已词典化）；`goal_detail_l10n.dart` 与 arb 双重定义的清偿进行中——B1-A 迁今日任务 7 条＋清死定义 6 条、B1-B 迁任务状态/时间/数值子集 14 个 getter（委托式 `_arb.<key>`，见 §6.5-1），存量（约 40 条交互文案）随下一 copy 批迁完后**封档**（§6.5-2）。引擎侧同步：B1-B 已落地 `_criterion_label` 整句模板（unit=boolean→「完成「X」即达标」，与 arb `displayCriterionCompleteTemplate` 对齐）＋结构化下传；该 helper 在 GOAL-ROUTER 后的清理见本节组装链第 3 条。【依据：TRIAGE §3#1、§1.2 附注；B1-A/B1-B/GOAL-ROUTER REPORT】

**事件名→人话**：`domain=memory.event` 类，verbTemplate 承载（「completed {title}」→「已完成「{title}」」）；重复事件去重聚合后展示（V20 堆叠反例）。【依据：AUDIT S2；EDU §三 记忆面板「数据库 dump」反例】

### 6.5 arb 与 l10n 工程纪律（v1.0 新增，R4 P1-7——批 1 两卡踩坑的回灌裁决）

> 背景：批 1 两卡（B1-A/B1-B）实际踩坑四类：双卡撞 key 靠手工「错开声明」化解；`flutter gen-l10n` 生成物（git 跟踪）随 arb 必然冲突（GOAL-ROUTER §8 已目击并发会话制造 arb/生成物 UU 冲突窗口）；`goal_detail_l10n.dart` 私有 getter 与 arb 生成成员**同名遮蔽**（Dart extension getter 被 arb 实例成员静默遮蔽，靠测试才能发现死定义）；删 key 还是委托两卡用了两种模式。本节为这些坑立规。【依据：B1-A/B1-B REPORT；GOAL-ROUTER REPORT §8】

1. **委托式为默认（主会话裁决）**：私有词典→arb 迁移一律改委托（getter 体改 `_arb.<key>` 显式接收者，防扩展自解析），消费者零改动；**删 key 需两证**：全仓消费者普查为零 + 回归测试绿。同义双 key 去重留「语义正确者」，删「误拼者」，删除 commit 附普查 rg 输出。
2. **同名遮蔽禁令**：禁止新增与 arb 生成成员同名的 extension getter（静态不可见的双重定义）；存量 `goal_detail_l10n.dart` 余量迁完即封档，禁止新增成员。
3. **arb key 命名空间分配表**：新 key 一律 `<域><主题>*` 前缀（goalStatus*/goalPriority*/memoryRecordStatus*/memoryEvent*/display*/taskBoard*/goalDetail*…），分配表由主会话维护于本节；卡开工先领前缀、收工回写，**禁止两个未合入卡共用前缀族**（B1-A 领 `taskBoard*`/`goalDetail*` 子集、B1-B 领 `goalStatus*/goalPriority*/memoryRecordStatus*/display*/memoryEvent*`——「错开声明」自本条起为制度而非自觉）。
4. **arb 串行化窗口**：arb 是全舰队唯一最高冲突文件——**同时最多 1 张卡持 arb 编辑权**；后合并者负责重跑 `flutter gen-l10n` 解决生成物冲突，**生成物冲突一律 regenerate、禁止手拼**。
5. **机检（A6.11）**：同前缀族双 key 同文案（zh 相同）清单输出，ratchet 只降不升。

---

## §7 交互流程规范

### 7.1 答疑分档流程（D2 + 增补）

```
用户提问
   │
   ▼
意图判定（ChatOrchestrator 双核路由承接，前端零改动）
   │
   ├─ 快问/概念澄清（定义、事实、对比）──────────► 直答（结论先行，≤3 段）
   │                                                 （快问慢答=惩罚用户）
   ├─ 显式要答案（「直接给答案」「只要结果」）─────► 直答 + 一行「建议自己走一遍第 2 步」
   │
   └─ 应试/作业/刷题（默认语境）──────────────────► 分步引导（默认档）
                                                      │
                                        ┌─────────────┤
                                        │ 分步规格：3–5 步；每步 ≤3 句 + 1 个抓手问题；
                                        │ 步末「继续」；出口「直接给答案」在第 2 步后出现
                                        │ （不藏长按——大学生时间宝贵，出口可见但不在首屏抢戏）
                                        ▼
                              能力门控：分步置信度 <0.60【定标待实测】
                              → 降级直答 + 「这部分建议对照教材核对」
                              （引擎没把握不许装导师——WSJ 实测 Khanmigo 算错比给错答案更糟）
```

- **全局偏好档**：settings 新增「深学 / 效率」二选一，**默认深学**（深学=上表默认；效率=快问档扩至全部语境、答案直出+要点框）。【落点：`unified_settings_screen.dart` 学习偏好区；后端 `orchestration/` 提示词开关——批 4】
- **北极星建议**：NS-001 类冲刺计划创建时弹一次性提示「备考周期 ≤7 天，建议切换效率档」——**提示非强制**，不静默改档。【依据：DECISIONS D2 增补】
- **过程折叠**（与 D3 衔接）：完整思维链=回答消息上的「过程」折叠 chip，默认收起，点开抽屉展示（`reasoning_step_model.dart` 数据链已在）；分步引导天然承载「示范思维」的教学时刻。**H3 后重心校正**：三级透明裁决维持，但重心从「展示过程」移到「诚实呈现」（§6.1 诚实三件套）。【依据：CONFLICTS C-02/C-03；EDU 原则 12；DECISIONS 附录 H3 裁决 #3】

### 7.2 星图双视图（D5）

| | 工作视图（Tab 默认） | 仪式模式（事件触发） |
|---|---|---|
| 视角 | 当前学习目标的**局部邻域**（中心节点 + 1 跳，≤20 节点） | 全局宇宙 |
| 可读性 | 节点=掌握度亮度（Khan 分级语义：未学/学过/掌握）；推荐动作 chip ≤1（「下一个建议碰：X」） | 华美完整（现有粒子/辉光按 §2.6 豁免区预算） |
| 触发 | galaxy Tab 点入即此 | 成就达成 / 阶段回顾 / **onboarding 首见**（增补：首见全局仪式保留，首见惊艳是品牌资产） |
| 退出 | —— | 任一点按/滑动回工作视图；「回顾完整星图」入口常驻工作视图角落 |

**H3 后预算标注（v1.0 增补，R4 P1-1）**：仪式模式预算权重**下调一档**（§0.1）——触发面收敛为成就/回顾/onboarding 首见三类不再扩容；豁免区合计预算（§2.6）在下调档内执行，超限砍序不变（glow→particle→持续源）。工作视图不受影响。

**锤内规范**（豁免区的第二层规则）：
1. 标签碰撞消隐 pass——painter 新增标签重叠检测，重叠标签按掌握度+选中态优先级隐藏（2793 行 painter 现无此 pass，AUDIT S5「噪声汤」主因）；
2. 明暗一体——dark cosmic 画布上的控制件（底部导航/添加按钮）跟随沉浸：galaxy Tab 激活时 shell 底导航切 dark 变体（`shell_navigation.dart:242` @R3 时点落点），禁浅色件贴暗画布；
3. 统计泡不遮节点——半透明统计泡移至安全区，禁止叠在密度区节点上；
4. 「?」图标限未解锁节点（≤5 个/视角），未点亮节点默认弱显示不画问号；
5. 合计预算按 §2.6 豁免区口径。【依据：D5＋增补；AUDIT S5；EDU §三 知识星图（Obsidian local graph 正面证据）】

### 7.3 推送宪法执行细则（D8 五条落地）

| # | 宪法条款 | 执行规格 |
|---|---|---|
| 1 | 三律（类别/降频/一键最小动作） | 只推三类：损失预警、恰当时机、状态相关；每条推送点开直达「完成它」的最小动作（deep link 到具体任务，禁只开首页） |
| 2 | 频率上限 | 常规类 ≤1 条/日；损失预警类即时但单类 ≤1 条/日；全类周上限 5；静默 23:00–8:00（用户可改）；降频阶梯：同类连续 3 次不响应→2 条/周，连续 7 次→该类静默 |
| 3 | 文案模板 | `{结论}{口径数字}·{最小动作}`，正文 ≤24 字；例：「图论梳理完成，进度 41%→44%，点此看下一步」。数字受 §6.3 准入约束 |
| 4 | 目标函数显式化 | bandit 只准优化「单条推送响应率/完成率」；**永不优化 DAU/会话时长/打开总量**（B-01 缝合条款，写入推送服务代码注释与评审清单） |
| 5 | app 内主动性集中制 | Aurora 确认/建议/预警一律进 `notification_center` 收件箱；收件箱 IA：三分组（需你确认 / 建议 / 预警），需确认项首列；**S7 断言测试破绿即恢复推送降级仅安全类**（冻结提醒类），禁状态断言类推送（S7 已落地 @B1-A＋GOAL-ROUTER，本条转为回归红线条款） |

【依据：D8；CONFLICTS C-10；EDU §三 推送三律；AUDIT S7 前置；§10.5 台账 S7 行】

### 7.4 游戏化三档制清单（D4 + 安全网规格）

**前置硬依赖：S7 单一事实源修复先于任何 T1 上线**（拿「今天有没有任务」都说不准的数据做损失厌恶=拿随机失败做杠杆）——**S7 已落地**（引擎 `goal_today_view.py` SSOT＋GOAL-ROUTER 遮蔽修复，见 §10.5 台账）；T1 开闸条件转为「跨屏断言测试（A9.5）持续绿」。【依据：D4；CONFLICTS C-04】

**H3 后预算标注（v1.0 增补，R4 P1-1）**：连胜安全网属损失厌恶挂学习资产，**非温度层，T1 地位不变**；但 T1 文案预算不得扩为常驻庆祝氛围（T0 维持——双份 confetti 与常驻庆祝氛围禁做不变）。

**T1（首批可做）**：

| 项 | 规格 |
|---|---|
| 学习连胜 | 锚定「完成当日**最小**学习目标」（颗粒可自选小：1 个任务/10 分钟），非「打开 app」 |
| 安全网（无安全网不上线） | 冻结：每月自动 2 张，上限叠存 2 张；补签：断签 24h 内可补 1 次/周；断签瞬间文案不羞辱（「休息了一下，用一张冻结保住了连胜」>「你的连胜断了」） |
| 签名完成动画 | §2.4 唯一规格 |
| 诚实进度编码 | 进度展示位只编码掌握度（Khan 分级），禁时长/打卡表演；奖励点数（动机层）永不与进度位混排（B-02 两层分离） |
| 回归易赢 | §4.5 回归态规格 |
| 损失厌恶指向 | 只挂学习资产（节点掌握度/连胜/计划健康度）；禁付费品挂钩 |

**T2（缓做，有数据/基建再议）**：bandit 推送时机（需推送样本量）；联赛分组比较（需社交与活跃密度，且必须先分组后比较、可退出）；宝石下注类沉没成本（伦理敏感）。

**T0（禁做）**：双份 confetti 与一切常驻庆祝氛围；为打开/打卡等基础操作发积分；无安全网连胜；羞辱文案；奖励点数出现在进度展示位；无「今天到此为止」出口的玩法。

【依据：D4；CONFLICTS C-04/B-02/B-04；EDU §一.1 证据链＋「机制不可移植，成立条件才可移植」；DECISIONS 附录 H3 裁决 #4】

---

## §8 屏级蓝图（9 surfaces；v1.1 N1 增补第 10 治理面 sprint，见 §8.10）

> 每屏：必达项 ≤2（§0.2 矩阵落地）+ 首要改动 Top5（引罪状编号）+ 验收清单（条款号指向 ACCEPTANCE）。现状落点为真实文件路径。
> **实施状态（v1.0，R4 P1-9）**：Top5 各项的已落地/未开工状态统一见 **§10.5 实施状态台账**，本章不另维护副本；下文仅对已落地项就地标注【已落地】防重复立卡。

**必达项矩阵总览**：

| surface | 必达项（≤2） | 四角归属 |
|---|---|---|
| home | ①今天该干什么（一眼可动） ②一句话入口 | 懂状态 |
| chat | ①会话本体 ≥70% ②等待分期诚实 | 过程透明+会教 |
| goal | ①计划健康度一眼可信 ②下一步动作单一 CTA | 懂状态 |
| task | ①今日任务口径唯一 ②完成路径 ≤2 步 | 懂状态 |
| memory | ①今日重现入口 ②记忆人话呈现 | 懂状态 |
| galaxy | ①工作视图回答「下一个该碰什么」 ②加载/空/错误三态可辨 | 懂状态+有温度(仪式) |
| profile | ①画像与进度诚实 ②图表有轴有单位 | 懂状态 |
| settings | ①改即生效无需找保存 ②偏好与无障碍集中一处 | ——（系统屏） |
| onboarding | ①首见星图仪式 ②≤5 步到 home | 有温度 |
| sprint【v1.1 N1 增补】 | ①剩余时间与今日完成度一眼可信 ②下一步动作单一 CTA | 懂状态 |

### 8.1 home（`features/home/presentation/screens/dashboard_screen.dart`）

- 必达：①今天该干什么 ②一句话入口。
- Top5 改动：
  1. 首屏重排：指挥台（今日下一步+完成钮）升为第一卡、折叠线上方；「理解你」卡 ≤35% 首屏且可折叠/可关（V9/S10——understanding_snapshot_card 现无 collapse 逻辑）；
  2. 底部三叠层→两层：快捷 chip 并入输入条下游（§7.3 建议话术模式：点 chip=填入草稿+高亮发送键），导航直达类 chip 迁指挥台/Tab（C-11 裁决）；
  3. 装饰减配：特效层 5→1（§5.3 账本），weather 层补门控，首帧减配（装饰延后一帧+首屏卡槽懒加载，S20 剩余半边）；
  4. 大字简报重写：三行特粗→单行「结论+数字」（S4/S2：硬编码 FlSpot 装饰图表同批处理，statistics_card.dart:91–130 @R3 时点）；
  5. S7 口径接入：今日任务读单一事实源【已落地 @B1-A——引擎 `goal_today_view.py` SSOT，home `_next_task` 委托】。
- 验收：A8.1。

### 8.2 chat（`features/chat/presentation/screens/chat_screen.dart`）

- 必达：①会话本体 ≥70% ②等待分期诚实。
- Top5：
  1. 顶部 8 件系统组件（TRIAGE S8 清单：WorkingMemoryPanel/StatusAwarenessBar/UnderstandingDrawerButton/ResumeBanner/DualCoreModeChip/ReviewNodeBanner/DailyStartupRetryBanner/ComebackBanner）收敛：常驻 0——记忆降内联微件、确认进收件箱、模式条入 dock、横幅类进收件箱或回归屏；
  2. 等待期：阶段胶囊（ChatRunPhase.sending/streaming/finalizing 已有数据链，chat_state.dart:11–22 @R3 时点）默认可见；「检索→思考→生成」三阶段+预期时长（「通常几秒到十几秒」）+可取消；三点 `_TypingIndicator` 在胶囊可见时退役；
  3. 一答 chip ≤3（建议话术，§4.1.4）；确认请求走内联确认卡（对象可见，§4.2.3）；
  4. 顶栏标题 2 行策略（S3/V15）；历史回放引用空内容修复（V13）；
  5. 过程折叠 chip（§7.1）承接思维链展示，DeepSeek 式「过程给人看，结论进历史」。
- **备选位（候选条款，不占必达项）**：会话开场召回上次断点/上次错题【依赖 C 线闭环证据（wt86）确认后立卡；LOOP1 BP-2 已证需求（跨 session 私有上下文丢失、系统自述「没有完整记录」）；DECISIONS 附录 H3 裁决 #4「零竞品供给的第一动作候选」】。
- 验收：A8.2。

### 8.3 goal（`features/goal/presentation/screens/goal_detail_screen.dart`）

- 必达：①计划健康度一眼可信 ②下一步动作单一 CTA。
- Top5：
  1. S7 跨屏口径对齐（达标线/瓶颈/今日——读单一事实源）【已落地 @B1-A＋GOAL-ROUTER 18cd81b0——goal_router 超集生效，goal 详情屏四区块空态与 PUT 405 根治】；
  2. 空态悬空「确认」修复（minimum_criteria_card.dart）【已落地 @B1-A：按钮块条件 `!criteria.isConfirmed && criteria.thresholds.isNotEmpty`，3 用例红→绿】；
  3. enum 直出清零（status/priority 走词典，§6.4）【已落地 @B1-B：goal_status_lexicon 承载，防复发靠 A6.1】；
  4. 百分比收敛：四数打架（0%/0%/0%/7%）→1 个主数字（健康度）+2 个次级，全部走 §6.3 准入；
  5. 折线图三要素（轴/单位/口径），装饰图删除或补齐。
- 验收：A8.3。

### 8.4 task（`features/task/presentation/screens/task_list_screen.dart` 等）

- 必达：①今日任务口径唯一 ②完成路径 ≤2 步。
- Top5：
  1. 「今日」口径三源归一（dueDate 口径为事实源）【已落地 @B1-A：引擎 SSOT＋客户端 `tasksDueOn()` 单一定义点】；arb 双 key 去重【已落地 @B1-A：taskBoardTodayNoTasks 删除】；
  2. 头部「今日无任务」与正文「本周 3 个」的调和表达（V12：副标注「本周还有 3 个」）；
  3. 完成钮/chevron 分级（§4.2.1）；完成路径 ≤2 步（列表勾选即完成，不弹确认）；
  4. 庆祝降级：完成=签名勾选，confetti 只留里程碑（§2.5 G-1，task_execution_screen 单 owner 保持）；
  5. 加载统一骨架贴布局（S19）。
- 验收：A8.4。

### 8.5 memory（`features/memory/presentation/screens/memory_panel_screen.dart`）

- 必达：①今日重现入口 ②记忆人话呈现。
- Top5：
  1. 「今日重现」首卡（Readwise 式：每天 3 条最好的，一键升级自测卡）——EDU 三大面裁决的落地；
  2. 事件名/时间戳直出清零（status 词典、截止时间格式化、Q 值隐藏或释义、tags 词典化）【部分已落地 @B1-B：status/时间/Q 值/置信度已清偿；tags（自由文本，防误伤用户内容）随 memory 域下一卡连同引擎写入侧词典化】；
  3. 重复事件聚合（V20；事件动词词典已落地 @B1-B）；承诺过期态（pending_commitments_section 无 overdue 分支，S13——时间格式化半边已落地 @B1-B，overdue 分支未开工）；
  4. 待处理 ✓/✗ 一键裁决补确认对象与撤销（误触回滚）；
  5. 私有骨架迁移 SparkleSkeleton（:1728 @R3 时点）。
- 验收：A8.5。

### 8.6 galaxy（`features/galaxy/presentation/screens/galaxy_screen.dart`）

- 必达：①工作视图回答「下一个该碰什么」 ②三态可辨。
- Top5：
  1. D5 双视图落地（§7.2）：Tab 默认局部工作视图；仪式模式触发器（成就/回顾/onboarding 首见）；
  2. 标签碰撞消隐 pass（star_map_painter，§7.2 锤内规范 1）；
  3. shell 沉浸化（shell_navigation.dart:242 @R3 时点，dark 变体）；
  4. 状态机收尾：加载门已有（:415–421 @R3 时点），补错误态人话+契约守卫维持（FIX-52/53/54 保留）；引擎 SSE heartbeat（app/core/sse.py，30s ping）——V26 收尾；
  5. 豁免区预算账本接入守卫（§2.6；H3 后预算下调档见 §0.1）。
- 验收：A8.6。

### 8.7 profile（`features/user/presentation/screens/profile_screen.dart`）

- 必达：①画像与进度诚实 ②图表有轴有单位。
- Top5：
  1. 折线图三要素+真实数据（禁硬编码 FlSpot）；
  2. 冷色件归槽（亮度 50% chip→语义重评，§1.5.2）；
  3. 稀有度色与语义色分层维持（DS.profileRarity* 冻结不互替，U-01 Step5 现状保持）；
  4. 「点击展开/收起」文案替换（chevron 已表达，arb:12517 @R3 时点）；
  5. typography 迁移（Step5 已收编 20 处色字面量，字号字面量长尾）。
- 验收：A8.7。

### 8.8 settings（`features/user/presentation/screens/unified_settings_screen.dart`）

- 必达：①改即生效无需找保存 ②偏好与无障碍集中一处。
- Top5：
  1. 假保存钮治理【已落地 @B1-A：AppBar「确定」假提交钮删除，全页「改即生效」；1 用例护住】；
  2. 无障碍入口唯一化（双卡合并，§4.2.2 卡语法区分）；
  3. 新增「深学/效率」偏好档（§7.1）、触觉开关（验收 A2.13）、reduce-motion 尊重确认（§2.3）；
  4. 卡 affordance 语法统一（chevron=折叠、「›」=跳转）；
  5. typography/色 token 收尾迁移。
- 验收：A8.8。

### 8.9 onboarding（`features/onboarding/presentation/screens/interactive_onboarding_screen.dart`）

- 必达：①首见星图仪式 ②≤5 步到 home。
- Top5：
  1. placeholder 缩短（arb:1141 @R3 时点 →「例如：备考期末」，§3.2 表）；
  2. 目标创建一句话化（自然语言→结构，Fantastical 式；AI 引擎已有理解能力）；
  3. narrative 动效预算：入场编排走 M5（650ms 档），总时长 ≤3s 且可跳过——**H3 后预算下调一档**（§0.1）：编排段数与粒子用量按下调档执行，总时长上限与可跳过维持硬性；
  4. 效率档建议提示挂点（D2 增补，检测到 ≤7 天备考时限时）；
  5. 首见星图仪式（D5 增补）衔接：完成目标创建后一次性展示全局星图，随后落工作视图——**一次性触发维持（品牌资产），但仪式预算按下调档执行（§7.2）**。
- 验收：A8.9。

### 8.10 sprint（冲刺仪表盘，`features/plan/presentation/screens/sprint_screen.dart` + `features/home/presentation/widgets/exam_sprint_dashboard_card.dart`）【v1.1 N1 增补 @A-SPEC，守卫落地 @SPEC-GUARD】

- 必达：①剩余时间与今日完成度一眼可信（口径走 §9.4 单一事实源，服务端下传优先）②下一步动作单一 CTA。
- 结构说明：sprint surface 由两文件合称——冲刺屏本体 + home 内嵌冲刺仪表卡；四角归属懂状态。跨面派生值（剩余天数/完成度）全 app 单算（v1.1 N2）。
- 守卫：`check_ux_component_convention.py` 扫描根 +1 `features/plan/presentation`（2026-09 @SPEC-GUARD 落地，基线登记现值、ratchet 只降不升）；`features/community`、`features/leaderboard` 域另立卡评估，本条不动。
- 验收：A-SPEC V1.1 §5 改造 #7——守卫跑绿 + manifest 登记 + 新文件零容忍。

---

## §9 门禁与工具链

### 9.1 lint/guard 规则草案清单（对照现有 ratchet 模式扩展）

现有底座（维持，只降不升）：`check_ux_component_convention.py`（rawButton/rawSpinner/rawChip/parallelClass/colorLiteral，扫描根 9 surfaces＋v1.1 N1 增补 `features/plan/presentation` 共 10 治理面，plan 根基线登记 @SPEC-GUARD）＋ `check_ui_design_tokens_ratchet.py`（colorLiteral/fontSize 全仓）＋ **DL-SPEC `check_dl_spec_ratchet.py`（已落地 @B2-GUARDS：12 维守卫，基线冻结于 d87d42ea，含 2 个批 2 维提前落地）**。扩展新维度：

| # | 守卫 | 扫描 pattern（描述） | 基线策略 | 抓的规范 |
|---|---|---|---|---|
| G1 | `check_motion_token_convention.py`（新建；**DL-SPEC offLadderDuration/bannedCurve/breathingController 三维已提前落地**） | features 内 `Duration(milliseconds: N)` 且 N∉白名单（带宽值白名单 {50,80,100,120,150,200,250,300,320,350,400,450,480,500,600,650,700}）。**白名单定性（v1.0，R4 P1-2）：存量宽限集合，永不新增**；新代码只准使用正典值 {120,200,320,480,650} 与 §2.1 reverse 表 {140,250,350,450}；**批 3 起白名单收窄为「正典值 ∪ reverse 表」，收窄前完成存量迁移**。另扫 `Curves.elasticOut|bounceOut` 引用与 `createBreathingController` 引用 | ratchet 冻结现值（offLadderDuration 基线 186 / bannedCurve 24 / breathingController 1），新文件零容忍 | §2.1/§2.2/§2.5 D-1 |
| G2 | `check_display_lexicon.py`（新建） | `label: \w+\.(status|priority|unit)` 直传模式；`DateTime` 变量经字符串插值进 Text（`'${' + 变量 + '}'` 且变量类型 DateTime）；`toStringAsFixed` 出现在 label 上下文 | 新文件零容忍+存量 ratchet | §6.2 X1/X3/X5 |
| G3 | chip 数量/屏（静态近似） | 单个 build 方法内可点 chip 构造调用计数 >6 | 阈值型（非 ratchet） | §4.1.4 |
| G4 | i18n 硬编码中文 | `Text('...中文...')` 字面量（DL-SPEC textHardcodedZh 维已落地，features 扫描，HEAD=0 零容忍） | 零容忍 | §6.2/§6.4 |
| G5 | ellipsis 滥用 | `maxLines:1` + `TextOverflow.ellipsis` 出现在标题角色（配合命名约定白名单 label/caption） | 人审抽样+新文件告警 | §3.2.1 |
| G6 | 对比度机检 | 对 SparkleColors 全量前景×背景组合跑 WCAG 公式，输出 <4.5:1（文字）/ <3:1（图形）对清单 | 阈值型，批 2 入 CI | §1.6 |
| G7 | 面积预算（辅助） | chat_screen 常驻子组件挂载数（AppBar/持久 panel 计数）；每屏 SparkleConfetti 挂载 ≤1（DL-SPEC confettiPerFile 维已落地：单文件 ≤1） | 阈值型 | §5.1/§2.5 G-1 |

规则：所有新守卫接 `scripts/run_all_rule_guards.sh` 与 `rule_guard_manifest.tsv` 登记；ratchet 基线只降不升，`--update-baseline` 仅净删后刷新（沿用 UX-COMP 既有纪律；DL-SPEC 守卫已内置拒绝抬升，需显式 `--allow-raise`）。**基线 JSON 共享态纪律（v1.0 增补，R4 P2-8）**：`dl_spec_ratchet_baseline.json` 视为 arb 同级共享态文件——持卡编辑 `mobile/lib` 的卡禁止同时刷基线，基线刷新由合并窗口的主会话统一执行。【依据：AUDIT §7 交叉根因①「owner 有、迁移无门禁」；INTL 原则 16；GOAL-ROUTER REPORT §8 并发树前科】

### 9.2 新旧对比 debug 面板需求（批 2 同批交付）

Linear 式工具链（INTL 原则 16），最低需求集：

1. **token 开关**：debug 抽屉里 MotionTokens v3/v1、色彩 batch-2/batch-1 一键切换（feature flag 并行，真机即时对比）；
2. **取色器**：运行时改 SparkleColors 值并即时生效（ThemeManager 已有 setColorBlindMode 等动态换色管道可复用，theme_manager.dart:127/202 @R3 时点）；
3. **动效慢放**：全局 0.25×/0.5× 时长缩放开关（评审动效用）；
4. **预算仪表**：当前屏特效层数/粒子数/持续源数/chip 数实时显示（对接 GlobalParticleCounter/PulseScope）；
5. **golden 快照**：迁移批前后自动截图对比（flutter golden），差异报告入验收。

### 9.3 迁移门禁

- 新代码禁引旧 token：`AnimationSystem.*` 直接引用冻结（现 42 refs 存量迁移）；`DS.motionDuration`/`motion.dart` 别名指向 v3 后不再接受新调用点（G1 守卫）；
- 新 UI 必过 README CONVENTION（owner 唯一规则不推翻，本规范 §4 为其语法扩展）；
- 每批迁移完成后 `--update-baseline` + golden 冻结。【依据：CONFLICTS C-08 顺序裁决（缺一即退回三套并存）】

### 9.4 口径单一事实源模式（v1.0 新增，R4 P1-8——回灌裁决：升入门禁章，不进 §4）

> **为何在 §9 不在 §4**（主会话裁决）：这是数据链纪律不是 UI 语法；§4 组件语法管「怎么显示」，本模式管「显示的数据从哪来」，owner 归门禁与工具链章，与 G1–G7 同层。已验证实例：B1-A（引擎域服务 `goal_today_view.py` 唯一取数、双面委托引用）＋ GOAL-ROUTER（「刻意引用而非复制，防止第三套口径漂移」＋超集形状单 owner）。

1. **单一产出**：同一业务口径（今日任务/健康度/掌握度/完成数）由**一个域服务函数唯一产出**；消费面委托引用（import，非复制）；同一次取数允许双投影（goal 屏与 home 卡各取所需字段），**禁止第二处重算**。跨屏断言测试为该口径的验收件（范本：`backend/tests/unit/test_goal_today_view.py`，14 用例）。
2. **注册可达性测试（防 router 遮蔽连坐）**：引擎新增/迁移端点必须带**注册面断言**（路由可达＋形状键集）——router 级去重（如 `_include_router_if_new` 按 (path, methods) 键集不重叠才整体挂载）会使一条路由冲突连坐整 router 死代码，且消费方按被遮蔽形状编写解析器时空态长期无人察觉（事故档案：GOAL-ROUTER REPORT §1——goal-detail GET 被 readouts 遮蔽、PUT 405 长期存在；范本：`backend/tests/unit/test_goal_detail_route_shadowing.py`，9 用例）。此为口径断裂的新根因类型，静态 linter 不可见，只能靠注册面断言拦截。
3. **跨账本对账**：口径不止在跨屏一致，还要跨账本一致（任务账本 vs sprint 仪表盘，NORTHSTAR-LOOP1 BP-4 形态：completed=2 vs completed=0）——S7 修复只是同域收敛，跨账本矛盾是同类问题的第二形态。§6.3 准入②按此改写（已同步）。
4. **验收**：A9.5（机检）；新口径入账前回答「谁是唯一产出函数、谁在委托引用、断言测试在哪」三问。

---

## §10 迁移路线

> 骨架：D10 批次（信任地基先行，工具链并行，落地即开闸）。每批带**验收条款**与**回退策略**。用户红线：**不许改坏可用功能**——每步带回归验证点，功能回归不过不迁移下一批。

### 10.1 批 1 · 信任地基（不动视觉；交付节奏确保两周内组员看到明确变化）

| 工作包 | 内容 | 验收（ACCEPTANCE 条款） |
|---|---|---|
| B1-1 S2 文案+数据词典 | TRIAGE §3 五例施工图全清（engine `_criterion_label` 整句模板 + 端侧词典 + arb 双 key 去重 + 测试污染清库）；lexicon 基建落地【**已落地 @B1-A/B1-B**，剩余：测试污染存量清洗 BLOCKED（A6.6）】 | A6.2/A6.4/A6.11 |
| B1-2 S7 单一事实源 | 「今日任务」dueDate 口径裁决为事实源；三 provider 对齐；跨屏断言测试【**已落地 @B1-A＋GOAL-ROUTER 18cd81b0**】 | A7.5/A9.5/A8.3 |
| B1-3 四态落地 | 空态禁悬空 CTA（minimum_criteria_card【已落地 @B1-A】）；错误态人话三句式迁移（CustomErrorWidget 存量替换）；骨架贴布局验收；等待胶囊默认可见策略（S18 收尾） | A4.3–A4.5（golden 断言 A4.6 延至批 2 补验） |
| B1-4 状态链收尾 | 假保存钮治理（S13【已落地 @B1-A】）；承诺过期态；V25/V24 实机回归验证；SSE heartbeat（V26 收尾） | A8.8/A8.6 |
| B1-5 S3 快修 | 配对表落地：placeholder 缩短、chat 顶栏标题、chip ≤6 字改写 | A3.2/A3.4 |
| B1-6 诚实语言三件套（v1.0 新增，R4 P1-1——DECISIONS 附录 #3 明令落批 1） | 不确定时明说（§6.3 三档已有，引擎提示词+端侧模板对齐）；改口承认（GP-07 纠正保持反例驱动）；推荐附一行「为什么是它」——引擎提示词 + 端侧模板 | A6.9/A7.6 |

**肉眼可见证据**：B1-1 文案批本身就是最大观感回收（AUDIT §6 判决「观感收益/成本比全榜第一」），两周内交付。
**回归验证点**：`cd backend && pytest`；`cd mobile && flutter test`；9 surfaces 手测清单（每屏冒烟：进入/加载/空态/一次主操作）；视觉零改动承诺——golden 差异检查自批 2 起（golden 管道批 2 才建），批 1 以手测冒烟替代（v1.0 勘正，R4 P2-6）。
**回退策略**：词典层为纯增量（lookup 失败回落原值），单文件可独立回滚；provider 对齐用 feature flag 包裹（`todaySingleSource` flag），异常即切回旧口径。

### 10.2 批 2 · 工具链与令牌重铸（与批 1 并行建造；批 1 落地即开闸迁移）

| 工作包 | 内容 | 验收 |
|---|---|---|
| B2-1 motion v3 | motion_token_v3 新建（含 reverse 表）；route_transition 内联映射收敛（TRIAGE S16：~2 文件；引用计数以 G1 守卫口径为准，见 §2.1.3）；elasticOut 除名；PulseScope 2→1 | A2.1–A2.3、§2.1.3 顺序①→④ |
| B2-2 色彩五层 | material_color_utilities 引入（seed 快照回归锚 §1.2.2）；**语义别名 getter（§1.7【批 2 起】段的生效件）**；冷色件归槽；coldColorLiteral 基线下降 ≥50%（§1.5.2）；ΔE 度量脚本交付 | A1.2–A1.7 |
| B2-3 门禁 | G1–G7 守卫入 manifest；CI 接入【DL-SPEC 12 维已提前落地 @B2-GUARDS，本包收尾全量】 | A9.1 |
| B2-4 debug 面板 | §9.2 五项最低需求 | A9.2 |
| B2-5 删除清单 | D-1~D-4（呼吸/620 hero 非Narrative 用途/splash ≤400ms/elastic） | A2.5 |

**回归验证点**：守卫全绿；golden 对比报告逐屏人审（视觉变化必须可解释为规范条款）；`flutter test` 全量。
**回退策略**：token 切换走 debug 面板 feature flag（§9.2-1），v3/v1 一键回切；单屏迁移单屏验收，禁全量一把梭。

### 10.3 批 3 · 结构重构

home 减法（§8.1）→ chat 面积重划（§8.2，D3 ≥70%）→ galaxy 双视图+消隐+沉浸化（§7.2）→ chip 存量 178 私有类迁移（status_awareness_bar 7 类先行）→ 回归接管屏（§4.5）。批 3 开工前置：G1 白名单收窄为「正典 ∪ reverse 表」（§9.1，收窄前完成存量迁移）。
**回归验证点**：每屏结构改动独立 PR+golden+手测冒烟；面积预算实测（胶囊/面板计数）。**回退**：屏级 feature flag（新旧屏共存一门），结构改动可整屏回退。

### 10.4 批 4 · 行为层

答疑分档（§7.1，orchestration 提示词+双核路由，前后端衔接）→ 游戏化 T1（§7.4，S7 已修，跨屏断言维持为前置）→ 推送宪法（§7.3，gateway/推送服务）→ 回归时刻编排（§4.5 尾项）。温度与仪式相关预算按 §0.1 H3 下调档执行。
**回归验证点**：分步正确性抽测（能力门控阈值定标）；推送频率表单测；连胜安全网边界用例（冻结耗尽/补签过期）。**回退**：行为开关全部 settings 可关+服务端 kill switch（对照 `check_rule_fme_kill_switch_registered.py` 既有模式）。

### 10.5 实施状态台账（v1.0 升级，R4 P1-9——每张卡合入后回写；TRIAGE 对接接口已完成历史使命）

> v0.9 本节为「与 TRIAGE 的对接接口」（三动作已随批 1 施工执行完毕：已修复项移出施工范围/勘误吸收 §2.1.3 与 §10.1 B1-2/批次清单对接）。v1.0 起本节升级为**实施状态台账**：状态取值 {未开工/施工中/已落地@commit|patch/BLOCKED}；§8 各屏 Top5 的状态位引用本表，不另维护副本。

| 条款/罪状号 | 状态 | 剩余量 |
|---|---|---|
| S7 单一事实源 | **已落地**（B1-A patch＋GOAL-ROUTER @18cd81b0） | 无（A9.5 断言纳入回归） |
| S11 空态悬空确认 | **已落地**（B1-A，3 用例） | 无 |
| S13 假保存钮 | **已落地**（B1-A，1 用例） | 无 |
| S2 五例＋词典基建 | **已落地**（B1-A/B1-B：5 词典文件＋52 arb key＋引擎模板） | 无（防复发条款维持） |
| arb 双 key 去重（taskBoardTodayNoTasks） | **已落地**（B1-A） | 无 |
| 测试污染清库（X4 存量 24 组） | **BLOCKED**（B1-A 只上报未执行——清洗 SQL 待主会话裁决后由 `scripts/devtools/` 一次性脚本执行；A6.6 相应标 BLOCKED） | 裁决门 |
| goal_detail_l10n.dart 存量迁移 | 施工中（B1-A 迁 7＋清死定义 6；B1-B 迁 14；余约 40 条交互文案） | 下一 copy 批迁完封档（§6.5-2） |
| DL-SPEC 守卫 12 维 | **已落地**（B2-GUARDS，基线冻结 @d87d42ea；含 A2.1/A2.2 两维批 2 项提前） | 批 2 B2-3 收尾全量入 CI |
| S12 SSE heartbeat | 未开工 | 批 1 B1-4 |
| memory tags 词典化 | 未开工（B1-B 申报防误伤用户内容） | memory 域下一卡 |
| 批 2 B2-1~B2-5 | 未开工（守卫 12 维已提前） | §10.2 |
| routes.dart Colors.grey 单点（§1.5.2） | 未开工（登记待清） | 批 2 随 B2-2 |

### 10.6 H2/H3 验证并行项（上报用户，不阻塞规范）

H3 teardown **已完成并裁决**（DECISIONS 附录：部分成立——四合一空位整体证伪、「懂状态×过程透明」双缺位实证成立；温度降为及格线；叙事改「错题本 2.0：静态收录 → 状态引擎」；「诚实」落批 1——本规范 §0.1/§0.3/§6.1/§7.2/§7.4/§8.9/§10.1 B1-6 已同步）。H2 卡片排序访谈（5–8 人×30min）+fake-door 建议与批 1 并行执行；结果决定仪式层是否进一步降为薄层（§0.1）。【依据：DECISIONS 附录；DECISIONS H2】

---

## §11 起草人勘误（规范间残留矛盾的自行裁决记录）

| # | 矛盾 | 裁决 |
|---|---|---|
| R1 | D7「standard 200ms」 vs 现网 AnimationSystem.standard=220ms（组件侧）与路由侧 200ms 并存 | 正典取 200ms（路由侧现值即 200，迁移量小）；220 作废进存量迁移 |
| R2 | §2.6 同屏持续源 ≤1 vs 现网 PulseScope maxActiveSlots=2 | 以规范 1 为准，PulseScope 改 1 列入批 2 B2-1（现 2 槽是存量，非裁决冲突） |
| R3 | C-08 降级清单「confetti 单份 ≤600ms 仅真完成」 vs C-04 T1「签名完成动画 ≤300ms」两者似同位 | 裁决为两级：任务完成=签名勾选 240ms（每次，§2.4）；confetti=里程碑庆祝 ≤600ms（低频，§2.5 G-1）。普通任务完成不再触发 confetti——此为对 U-01 Step6 现状（每完成单份 confetti）的**收紧**，非冲突 |
| R4 | INTL「正文 17pt」 vs 现网 body 16px | 阅读型正文定 17（chat/长文），控件正文 15——双轨是语义分层不是打架；16 从正典表中移除进迁移 |
| R5 | D5「onboarding 首见全局」 vs §7.2 工作视图为 Tab 默认 | 不矛盾：默认态=工作视图；onboarding 首见是**一次性仪式触发**，退出后永落工作视图。已在 §7.2 表注明 |
| R6 | AUDIT S20「900ms 在 auth 判定前开始跑」 vs TRIAGE 勘误「与 auth 并行不阻塞」 | 采 TRIAGE（并行已验证）；本规范 §2.5 D-3 只裁时长上限与冗余段合并，不改并行结构 |
| R7 | §1.7「迁移期即生效」门禁 vs 语义别名 getter 属批 2 才存在（R4 P0-1） | 门禁拆两段：【立即】段只禁字面量（守卫已能执行）；语义名段绑 B2-2 合入时点。已在 §1.7 改写 |
| R8 | §2.1.1「reverse ≈0.7×forward」比例式 vs G1 白名单（0.7×320=224 不在集合内，R4 P1-2） | 比例式降为实现指引，正典为 reverse 映射表（200→140、320→250、480→350、650→450），表值入 G1 白名单。已在 §2.1.1/§9.1 改写 |
| R9 | R4 P1-2 建议文本「就近向上取白名单（200→140…）」中 140 并非白名单成员 | 采「正典值 ∪ reverse 表」收窄口径化解（140 作为表值合法）；表为唯一口径、禁现场另算。见 R8 |

### 11.1 引用纪律（v1.0 新增，R4 P2-8）

正文 `file:line` 引用一律标注时点（`@commit` 或 `@R3 时点`）；v1.0 走查时统一刷新一次，此后**新文档少写行号、多写符号名**（写 `DS.accent` 而非 :610/:614）。行号漂移不免除条款效力——以符号名与规范描述为准。共享态文件（arb、`dl_spec_ratchet_baseline.json`）的并发编辑纪律见 §6.5-4 与 §9.1。

---

## §12 修订记录（v0.9 → v1.0）

> 依据 `DL-R4/REVIEW.md` 21 条逐条处置；明细见 `v3-output/DL-R3/REVISION_v1_0.md`。处置统计：**采纳 19 / 改写采纳 2（P1-2、P2-4）/ 不采纳 0**——21 条全部表态，无沉默跳过；P0×3 全部解决，P1×10 逐条落实，P2×8 全部采纳（其中 2 条改写采纳：P1-2 因 R4 建议文本自身含「140∉白名单」矛盾而改为「正典∪reverse 表」收窄口径；P2-4 以 widget test 断言替代「运行时截图测量」）。

| R4 条目 | 处置 | 落点 |
|---|---|---|
| P0-1 §1.7 门禁时序矛盾 | 采纳 | §1.7 改写为两段门禁；§11 R7 |
| P0-2 ΔE 无公式/工具/过程 | 采纳 | §1.2.2 增补 CIEDE2000＋脚本落点＋tone 对齐；A1.6 同步 |
| P0-3 §6.4 词典 schema 与实现冲突 | 采纳（附实现核验修正） | §6.4 schema 替换＋criterion 组装唯一 owner 链 |
| P1-1 H3 裁决未同步 | 采纳 | §0.1/§0.3/§6.1/§7.2/§7.4/§8.9/§10.1 B1-6/A0.1；候选条款入 §8.2 |
| P1-2 阶梯与 G1 白名单矛盾 | 改写采纳（reverse 表值入白名单收窄口径，解 R4 文本自身 140∉白名单矛盾） | §2.1.1/§9.1 G1/A2.1；§11 R8/R9 |
| P1-3 迁移顺序缺中间态守卫 | 采纳 | §2.1.3 顺序①→④＋引用计数纪律（现值 172 refs 已核验） |
| P1-4 A1.2 幽灵白名单 | 采纳 | A1.2 改写（E5 目录不存在，`mobile/test` 天然域外） |
| P1-5 A6.6 漏报＋清库无 owner | 采纳 | A6.6 大小写不敏感＋3 逃逸行入基线＋BLOCKED 门 |
| P1-6 A1.3 示意正则与实现不符 | 采纳 | A1.3 删正则，改述 HLS 判定实现口径 |
| P1-7 arb/l10n 纪律缺失 | 采纳 | 新增 §6.5（5 条）＋A6.11 |
| P1-8 单一事实源升 §9 | 采纳（批准裁决：升 §9 不升 §4） | 新增 §9.4（含注册可达性测试）；§6.3②/A7.5/A9.5 改写 |
| P1-9 §10.5 缺实施状态台账 | 采纳 | §10.5 升级台账＋首批 12 行回写；§8 状态位就地标注 |
| P1-10 A3.4 前缀机检空转 | 采纳 | A3.4 改角色后缀制；§3.2.4 新增 |
| P2-1 附录统计失实 | 采纳 | ACCEPTANCE 附录重刷＋口径说明（修订后再计数） |
| P2-2 A8 引用错位 | 采纳 | A8.2 V13 改挂 chat 域回归用例；A8.8 触觉开关改挂 A2.13 |
| P2-3 「3 秒」无操作定义 | 采纳 | A8.1 改写（可测半句交 A5.4，人审留主观半句） |
| P2-4 chat 面积无测量工具 | 改写采纳（widget test 断言为主、golden 为辅——「运行时截图测量」废除） | A5.6 改写 |
| P2-5 触觉开关无验收条款 | 采纳 | 新增 A2.13（settings 触觉开关机检）；§2.3 同步 |
| P2-6 B1-3 引批 2 手段 | 采纳 | §10.1 B1-3 验收改 A4.3–A4.5＋手测；§10.2 注 golden 自批 2 起 |
| P2-7 域外存量无下降目标 | 采纳 | §1.5.2 清偿目标（批 2 ≥50%、批 3 清零）；A1.2 域外单点登记 |
| P2-8 行号漂移＋基线共享态 | 采纳 | §11.1 引用纪律；§9.1 基线 JSON 共享态纪律 |

---

## 附录 A · 依据索引（本规范引用的全部编号）

- **DECISIONS**：D1（温度三层）、D2（答疑分档+效率档增补）、D3（三级透明+≥70%）、D4（三档制+S7 前置）、D5（双视图+豁免区预算+首见增补）、D6（色彩五层）、D7（动效阶梯+同批门禁）、D8（推送宪法五条）、D9（四态分工矩阵+回归态）、D10（四批次）；H1（必达项 ≤2 消解）、H2/H3（验证上报）；**附录（H3 验证结果裁决更新，2026-09-22 晚，硬约束）**。
- **CONFLICTS**：C-01～C-12、B-01～B-04、H1–H3（§C）。
- **AUDIT**：S1–S20、§2 丑的解剖、§3 卡的解剖、§4 效果不好解剖、§5 三件套打分、§6 最重 5 条、§7 交叉根因。
- **EDU 原则**（引用处简写 E-P#）：1 进步诚实、2 失败不羞辱、3 给台阶不给答案、4 连胜配安全网、5 回归时刻、8 退出完成感、9 可视化回答当下问题、12 过程可见、14 损失厌恶指向学习、15 低摩擦重启。
- **INTL 原则**（引用处简写 I-P#）：1 内容优先、2 结构被感受、3 颜色单义、4 动效 200–400ms 可打断、5 弹跳是含义、6 高频零动效、8 中性色算法生成、9 排版节奏、10 空态错误态人格、12 状态内联、13 触觉因果对、14 持续振荡禁忌、15 装饰用量纪律、16 工具链先行。
- **TRIAGE（wt83，已落地）**：§1 S7 三源对照、§2 S12 深挖、§3 S2 五例施工图、§4 S16 勘误、§5 批次草案、§6 口径申报。
- **实施证据（v1.0 新增）**：B1-A/REPORT（S7/S11/S13/测试污染隔离）、B1-B/REPORT（S2 五例＋词典基建）、B2-GUARDS/REPORT（DL-SPEC 12 维守卫）、GOAL-ROUTER/REPORT（路由遮蔽裁决＋注册可达性测试范本）、NORTHSTAR-LOOP1/REPORT（BP-2/BP-4/GP-07 反例证据）、DL-R4/REVIEW（本版修订清单）。

*规范完（v1.0 定稿）。产物：`v3-output/DL-R3/SPEC.md` + `v3-output/DL-R3/ACCEPTANCE.md` + `v3-output/DL-R3/REVISION_v1_0.md`。零代码改动、零 /tmp 驻留、未 commit/push。*
