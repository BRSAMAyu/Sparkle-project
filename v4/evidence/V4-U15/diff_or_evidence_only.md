# V4-U15 — diff_or_evidence_only

## 结论一句话

长尾家族清点与风格一致性闭合按「no_duplicate_rule 差量举证」交付：仓内现状已被在先卡片（U07 LABS 入口摘除、F 线 DS 权威、UI-TOKENS 冻结棘轮、EE-G5 工具骨架）收口到卡面要求，本卡**零产品码差量**，差量 = 1 个 14 用例守卫套件把清点矩阵、repeat=49 移交基线、LABS/HIDDEN 不可达、主题真源单一、LABS 调色板消费面五道闭合**钉成棘轮**（每组一正一反），另交付 43 模块逐项处置表与本页一致性差异分级表（修复 0 / 登记 5）。

## 差量明细（相对 base 90275dc4 = 开卡时 main HEAD）

产品码：**0 文件改动**（objective「对所有尚未由U卡覆盖的活跃表面迁移」的现存面已满足——逐模块证据见 §2 清点矩阵；LABS/HIDDEN 只检查不泄露入口 = C 组机器钉；旧皮肤硬编码/不一致加载空态 = 逐模块核查无越阈值项，登记面见 §3）。

测试（1 新文件，14 用例，`flutter analyze` 零 issue）：

- `mobile/test/widget/u15_longtail_closure_guard_test.dart`（新，+543）——
  - **A±** 43+1 模块清点 exact match：features 目录集合 == MODULE_MATRIX
    canonical_count=43 + `learning`（V4-U10 学习旅程承载目录，goal 携参进入；
    MATRIX onboarding_note 判例同构：有明确承载归属不另算第 44 模块）；
    反例：幽灵目录/遗漏模块具名判负。
  - **B±** repeat 棘轮：现存 `.repeat(` 文件集 ⊆ FIX-569/S01R1 冻结基线集
    （49 路径）且总数 ≤ 49——只允许清理（出集，显式改基线常量 = 可见
    diff，同 UI-TOKENS `--update-baseline` 流程），不允许新增（入集判负）；
    反例：新增文件/超基数双通道判负 + 注释行不计数口径钉。
  - **C±** LABS/HIDDEN 不可达：C1 reflection（HIDDEN）路由零导航调用方
    （注册面 app/routes.dart 除外）；C2 孤儿组件 SeedLibraryDashboardCard
    （含 `/seed-libraries` push）零 lib 消费点（V3-FIX-360 已移出仪表盘
    配置，钉死不复活）；C3 CORE 12 文件字面 LABS 路径 push 零命中（既有
    符号级 nav 契约的字面补强，不重复其断言）；三面各配合成反例。
  - **D±** 主题真源单一：U15 八模块（intent/mirofish/reflection/seed_library/
    simulation/theater/visual_elements/tools）零 `ThemeExtension<`/
    `ThemeData(`/`ColorScheme(` 声明——tokens_v2 → theme → context.* 唯一
    真源（MASTER_DESIGN §4）；反例：合成声明具名判负。
  - **E±** LABS 调色板消费面冻结：visual_element_palette 模块外消费方 ⊆
    冻结集 {community 成就分享卡（U11 面）}——44 色本体在 UI-TOKENS 冻结
    基线内（LABS 域内容资产），本棘轮封其溢出扩散；反例：新增消费方判负。

与既有守卫的关系：`nav_decontextualization_contract_test`（CORE 面 12 文件
符号级 LABS 入口禁令）与 `check_ui_design_tokens_ratchet.py`（UI-TOKENS
冻结基线）原样全绿零改动——验收③「原guard棘轮只降不升」的现存棘轮零触碰；
本套件只补其未盖面。无 RF-06 三冲突面/routes 注册改动/backend/proto/迁移/
gen 产物触碰。

## §1 repeat 动效清点 = 49（FIX-569/S01R1 强制移交对照）

**复跑数 = 49 文件 / 91 调用点**（`grep -rln "\.repeat(" mobile/lib
--include="*.dart"` @ agent/v4/u15 6eaf6b3a；剥注释复核后 91 处代码级命中）。

**与 S01 移交清单对照**：对 S01 base `d57a7aa8` 以 `git grep -l "\.repeat("
d57a7aa8 -- mobile/lib` 复跑 = **49 文件，路径集与本卡 49 完全 1:1（零新增/
零退出）**。即 S01 自述 48 系少记 1（其一审 R1 代码级复核结论），真实基线
在其开卡时即为 49；本卡复跑集合零漂移。移交条件①按复跑数 49 取数，闭合。

**门控分级（代理口径：文件内 reduce-motion/disableAnimations/
resolveSparkleMotionTokens/SemanticMotion 关键词引用计数，非逐动画审计）**：

- 有门引用：22 文件 / 48 调用点；
- 无门引用：**27 文件 / 43 调用点**（与 S01「约半数无门」一致）。

**清尾优先级登记（P1 = 无门引用 + 高可见/全屏，摘自 S01 limitation #1 并
复跑确认在册；P2 = 其余无门；P3 = 有门引用维持）**：

| 优先级 | 文件（调用点） | 备注 |
|---|---|---|
| P1 | home/weather_guide_screen（2） | 全屏天气粒子——「全屏粒子」最大存量候选 |
| P1 | core-design stepper_indicator（2） | DS 分子件，多屏复用放大面 |
| P1 | core-design flame_indicator（4） | 0 外部消费点（可评估直接退役） |
| P1 | achievement 族 8 文件（17） | 无门屏族（contract/detail/streak_details/streak_indicator 等） |
| P1 | theater 2 文件（2） | LABS 域但全屏图形 |
| P1 | visual_elements card/preview_dialog（6） | LABS 域 |
| P2 | chat 族 7 文件（8）、community 2（2）、galaxy 2（3）、home focus_card/weather_header/particle_layer/unified_omni_bar（6）、task task_protocol_panel（1）、core animation_lifecycle_mixin/scene_atmosphere_layer（2）、aurora session_sheet（1） | 无门引用，局部组件级 |
| P3 | 有门引用 22 文件（48） | motion/F06/S01 体系内维持 |

清尾归属：motion-policy owner + 各 face owner（achievement/chat/community/
galaxy/home/task 多为已收口他卡面，逐面会签后推进）；每清一文件 = 棘轮
下降，须显式下调 `kRepeatBaseline49`/`kRepeatRatchetMax`（diff 可见）。
本卡不改他卡已收口的动画实现（不擅动他卡裁决面）。

## §2 43 模块清点矩阵（acceptance①：每模块 explicit disposition）

清点基准：MODULE_MATRIX.json canonical_count=43；features 目录 44 =
43 矩阵 + learning（U10 学习旅程承载，SCREEN_FAMILIES「星图/学习/错题/
资料」家族邻接；onboarding_note 判例：承载归属明确不另算模块）。
**exact match：无幽灵目录、无遗漏模块**（A 组机器钉 + 下表逐项）。

处置图例：〔他卡已收〕= 模块面由所列卡收口且有已审证据；〔U15 复核〕= 本卡
在 6eaf6b3a 逐项核验面；〔U15 登记〕= 本卡登记差异（见 §3）。

| # | 模块 | 状态 | V4 卡 | U15 处置（6eaf6b3a 实证） |
|---|---|---|---|---|
| 1 | achievement | CONTEXTUAL | D04,U12 | 他卡已收。U15 复核：5 屏 3 件在册；repeat P1 族 8 文件登记 §1 |
| 2 | aurora | CORE | F03,I01,I03,I04,I05,U02,S01,P01 | 他卡已收。U15 复核：session_sheet repeat=1 无门引用登记 §1 P2 |
| 3 | auth | CORE | U06,U14 | 他卡已收（U06 在航）。U15 复核：目录在位、零本卡差异面 |
| 4 | calendar | CONTEXTUAL | U08 | 他卡已收。U15 复核：目录在位、零 repeat/零硬编码色 |
| 5 | chat | CORE | F04,F06,I06,I09,D01,U07,S02 | 他卡已收。U15 复核：repeat P2 族 7 文件登记 §1 |
| 6 | cognitive | CORE | I02,I05,D03,D05,U03,U13 | 他卡已收（U13 在航）。U15 复核：目录在位 |
| 7 | community | CONTEXTUAL | U11,P02 | 他卡已收。U15 复核：bonfire/community_widgets repeat P2 登记；**E 组：achievement_share_card 为 LABS 调色板唯一模块外消费方（冻结钉）** |
| 8 | document | CONTEXTUAL | U10 | 他卡已收。U15 复核：目录在位 |
| 9 | documents | CONTEXTUAL | U10 | 他卡已收。U15 复核：目录在位 |
| 10 | error_book | CONTEXTUAL | I07,U10 | 他卡已收。U15 复核：目录在位 |
| 11 | experience | CONTEXTUAL | F03,I05,D01,D02,U13 | 他卡已收（U13 在航）。U15 复核：目录在位 |
| 12 | file | CONTEXTUAL | U10,P02 | 他卡已收。U15 复核：目录在位 |
| 13 | focus | CONTEXTUAL | U09,S02 | 他卡已收。U15 复核：flip_clock/star_background repeat P2 登记 |
| 14 | galaxy | CORE | F04,F06,D03,D04,D06,U05 | 他卡已收。U15 复核：galaxy_edge/graphrag repeat P2 登记 |
| 15 | goal | CORE | I01,U01,U08 | 他卡已收。U15 复核：learning 旅程入口（携参契约）在位 |
| 16 | home | CORE | F04,F05,D01,U01 | 他卡已收。U15 复核：C2 孤儿 SeedLibraryDashboardCard 钉死（§3-2） |
| 17 | insights | CORE | D02,D05,U13 | 他卡已收（U13 在航）。U15 复核：C3 守卫清单面零字面 LABS push |
| 18 | **intent** | CONTEXTUAL | I03,I09,**U15** | **本卡**。0 呈现面文件（纯 data+provider）；消费方=chat intent_preview_dialog/intent_analysis_button（U07 面）；无屏/无路由/无 LABS 泄露面；零 repeat/零硬编码色/零主题声明。处置=差量举证，无可迁移 UI 面 |
| 19 | knowledge | CONTEXTUAL | I06,D04,D06,U05,U10 | 他卡已收。U15 复核：目录在位 |
| 20 | leaderboard | CONTEXTUAL | U12 | 他卡已收。U15 复核：self-anchor 唯一裁决路由面（nav 契约钉）原样 |
| 21 | memory | CORE | I02,I06,D03,U03,P02 | 他卡已收。U15 复核：目录在位 |
| 22 | **mirofish** | LABS | **U15** | **本卡**。模块仅 milestone 庆祝服务（非入口面）；消费方=report（firstReport）+theater/simulation（LABS 域内）；无屏/无路由注册。处置=维持 LABS：服务不构成泄露入口，登记口径（§3-4） |
| 23 | notification_center | CONTEXTUAL | U14,P01 | 他卡已收。U15 复核：LABS 类型深链兜底通知中心（U07 口径）原样 |
| 24 | openclaw | CONTEXTUAL | I08,U04 | 他卡已收。U15 复核：目录在位 |
| 25 | photon | CONTEXTUAL | U12 | 他卡已收。U15 复核：受限兑换出口原样（rewards 边界 6/6） |
| 26 | plan | CORE | U08 | 他卡已收。U15 复核：目录在位 |
| 27 | **reflection** | HIDDEN | **U15** | **本卡**。路由注册在案（/reflection/summary）+ **零导航调用方（C1 机器钉）**=HIDDEN 不可达证据；屏用 core LoadingIndicator+l10n 一致。处置=维持 HIDDEN（深链可达性归 notification/深链 owner，登记 §3-4） |
| 28 | report | CONTEXTUAL | D05,U13 | 他卡已收（U13 在航）。U15 复核：C3 守卫清单面零字面 LABS push；mirofish 里程碑消费在册 |
| 29 | reviews | CONTEXTUAL | I07,U10 | 他卡已收。U15 复核：目录在位 |
| 30 | **seed_library** | LABS | **U15** | **本卡**。U07 已摘 chat/home 活跃入口（nav 契约 6/6 复跑）；LABS 域内 marketplace/list 自洽；**孤儿组件 SeedLibraryDashboardCard（含 /seed-libraries push）零 lib 消费点（C2 钉）**；路由注册保留（深链面）。处置=维持 LABS + 登记孤儿组件归属（§3-2） |
| 31 | settings | CORE | F01,F06,I10,U14,S02,S03 | 他卡已收。U15 复核：C3 守卫清单面零字面 LABS push |
| 32 | shop | HIDDEN | U12 | 他卡已收。U15 复核：HIDDEN 商店钉（rewards 边界）原样 |
| 33 | **simulation** | LABS | **U15** | **本卡**。U07 已摘洞察总览/聊天快捷动作（源注释在证）；LABS 域内 theater 互链；LoadingIndicator/_SimulationEmptyState 状态族一致；repeat=1 无门引用登记 §1。处置=维持 LABS |
| 34 | splash | CORE | U01,U06 | 他卡已收（U06 在航）。U15 复核：目录在位 |
| 35 | task | CORE | F04,U08 | 他卡已收。U15 复核：repeat P2（protocol_panel）登记 §1 |
| 36 | **theater** | LABS | **U15** | **本卡**。galaxy 预览默认隐藏（nav 契约 testWidgets 钉复跑过）；chat 预览披露摘除（U07）；_TheaterEmptyState/LoadingIndicator 一致；repeat 2 文件 P1 登记 §1。处置=维持 LABS |
| 37 | **tools** | CONTEXTUAL | I10,U10,**U15** | **本卡**。tool_registry=CORE 守卫清单面零字面 LABS push；EE-G5 ToolBodySkeleton/ToolEmptyState 状态族一致（notes/focus_stats 已骨架化）；translator_tool section 级 CPI 登记 §3-3；17/23 文件消费 DS 令牌，余为 data/model 层无 UI 面。处置=差量举证 + 登记 1 项 |
| 38 | translation | CONTEXTUAL | U07,U10 | 他卡已收。U15 复核：目录在位 |
| 39 | user | CORE | F04,U03,U06,U14 | 他卡已收（U06 在航）。U15 复核：C3 守卫清单面零字面 LABS push |
| 40 | **visual_elements** | LABS | F01,F02,F05,**U15**,S01,S03,S04 | **本卡**。U07 已摘 profile/settings 入口；**palette 44 色在 UI-TOKENS 冻结基线（域内容资产）**；模块外消费面冻结（E 组）；repeat 3 文件 P1 登记 §1。处置=维持 LABS + 消费面棘轮 |
| 41 | vocabulary | CONTEXTUAL | U07,U10 | 他卡已收。U15 复核：目录在位 |
| 42 | journey | CONTEXTUAL | I01,I07,I08,U04,U06 | 他卡已收（U06 在航）。U15 复核：目录在位（features/journey） |
| 43 | recovery | CONTEXTUAL | I04,U02 | 他卡已收（U02 在航）。U15 复核：目录在位 |
| + | learning（承载目录，非第 44 模块） | — | U10 | V4-U10 学习旅程承载（/learning/journey，goal 携参进入、缺参 ArgumentError 路由契约）；A 组白名单钉死不许幽灵化 |

在航卡（U02/U06/U13）模块面按「他卡在航」标注——本卡零触碰其文件，
不构成并线冲突（diff 仅 1 测试新文件自证）。

## §3 一致性差异处置表（acceptance②③：修复/登记分级）

**修复项：0**（无越阈值项：扫描八模块硬编码 `Color(0x` = 仅 visual_elements
域内 palette（UI-TOKENS 冻结基线在册资产）；裸 `CircularProgressIndicator`
= tools 仅 1 处 section 级；无第二主题真源；无新 LABS 入口）。

**登记项：5（登记 + 机器钉/棘轮，非口头）**：

| # | 差异 | 分级 | 处置与归属 |
|---|---|---|---|
| 1 | repeat 存量 49 文件/91 处，27 文件无门引用（§1） | 登记（清尾归 motion-policy owner + 各 face owner） | B 组集合棘轮钉死上限；P1 优先级表入册；下降须显式改基线常量 |
| 2 | home/seed_library_dashboard_card.dart 孤儿组件内含 `/seed-libraries` push（LABS 潜在入口） | 登记（文件在 home 面=U01/U07 裁决域，本卡不跨面删码） | C2 钉死零消费点不复活；删除 or 保留归 home face owner 裁决 |
| 3 | tools/translator_tool.dart:473 section 级裸 CPI（body 级 EE-G5 骨架约定不覆盖 action 在飞反馈） | 登记（替建第二加载组件将违反验收②「不新增同义组件」） | 归 tools face owner；若裁约定扩展，沿 SparkleSkeleton 家族出件 |
| 4 | HIDDEN reflection 路由注册在案（深链理论上可达，导航面零入口已钉） | 登记（深链面归 notification/深链 owner） | C1 机器钉；如需深链拦截归深链链路卡 |
| 5 | visual_element_palette（LABS 域 44 色）跨模块消费 = community 成就分享卡 1 处 | 登记（community 面=U11 APPROVE_CLOSED，不擅动） | E 组消费面冻结棘轮；扩展须卡面裁决 |

## 验收逐条自证（卡面原文 → 机器证据）

1. **「43模块每个都有explicit disposition/截图或不可达证据」** — §2 矩阵
   43+1 逐项处置；A 组 exact match 机器钉（无幽灵/无遗漏）；LABS/HIDDEN
   五模块不可达性 C 组机器钉。本卡零 UI 差量 → 截面 N/A（evidence_required
   的 screenshots_if_ui 条件面不触发，边界登记 limitations #1.5）。
2. **「不新增同义组件和主题真源」** — 本卡零产品码新增（diff 自证）；
   D 组钉八模块零主题声明（唯一真源 core/design）；E 组冻结 LABS 调色板
   溢出；translator CPI 不替建第二加载组件（§3-3 反向论证）。
3. **「原guard棘轮只降不升，无半接线屏被偷偷开放」** — UI-TOKENS 棘轮
   原样 PASS（225/275、632/727，脚本零改动）；nav 契约 6/6 复跑；
   B 组 repeat 集合棘轮新增判负；LABS/HIDDEN 状态零变更（无路由注册/
   入口开关 diff）；孤儿组件钉死不复活。

## 红线自证

- **RF-06 三冲突面零触碰**：dashboard_screen/compact_status_bar/
  task_execution_screen 零命中（diff 仅 1 测试新文件）。
- **l10n 零触碰**：本卡无文案面；L10N-REGEN-PARITY OK（10202 键）+
  i18n-coverage PASS 复跑；arb/生成物零 diff。
- **不另立第二权威**：守卫钉的是既有权威（MODULE_MATRIX/SCREEN_FAMILIES/
  UI-TOKENS/nav 契约/semantic_motion 体系），零新增规范文件。
- **不擅动他卡裁决面**：登记项 #2/#3/#5 均为他卡已收口的文件面，本卡
  以钉代改；在航卡（U02/U06/U13）文件零触碰。

## 复跑清单（全绿实录见 run_manifest.json / test_results.json）

`flutter analyze --no-pub`（No issues found!）；新套 14/14；nav 契约 6/6；
seed_library 8 + tools 6 + learning 31 + full_route 25 + rewards 边界 6；
core/design 261/261；UI-TOKENS PASS；L10N-REGEN-PARITY OK；
i18n-coverage PASS；repeat 复跑 `grep -rln "\.repeat(" mobile/lib` = 49。


## 一审勘误（receipt 762b2792）
- E-1：§2「U07 已摘」的状态账归属实为 **V3 wt356 卡 U-07（8ac6bad5）**，非 V4-U07（其实现未触这些文件）；实质断言不受影响。
- E-2：门控关键词文档写 kebab「reduce-motion」，复现谓词为驼峰 `reduceMotion`；数字真实，仅转录注记。
