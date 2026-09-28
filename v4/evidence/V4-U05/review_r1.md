# V4-U05 一审 receipt（独立审查）

- 审查会话：wtU05R1（未参与实现）；实现 commit `69238e23`，基线 `20f1d99f`，审查时工作树干净、HEAD=实现 commit。
- 审查日期：2026-09-29。方法：全 diff 逐行读 + 独立复跑 + 双突变独立重放 + merge-tree 合并演练 + 守卫亲跑。
- **裁决：PASS_WITH_CHALLENGES**（可合并；挑战 R1-C1/R1-C2 随合并登记，不阻断；建议项 R1-S1/R1-S2 立接续卡/后续测试）。

## 0. 独立复跑记录（亲跑，非转抄）

| 面 | 命令 | 结果 |
|---|---|---|
| 新测 26（视觉档17+读屏3+抽屉6） | `flutter test test/features/galaxy/unit/capability_channel_visual_test.dart test/features/galaxy/unit/galaxy_a11y_channel_suffix_test.dart test/features/galaxy/widget/node_detail_capability_section_test.dart` | +26 All passed |
| 证据采集测 3 | `flutter test test/features/galaxy/widget/u05_evidence_test.dart` | +3 All passed |
| galaxy 回归 | `flutter test test/features/galaxy/ test/widget/galaxy_node_preview_card_test.dart test/widget/error_card_galaxy_echo_test.dart test/widget/h5_cross_system_chains_test.dart` | **+192 ~1（既有 skip）** 与自述精确一致 |
| KEYNAV/CTA 差量举证面 | `flutter test test/features/galaxy/widget/galaxy_screen_keynav_test.dart test/features/galaxy/widget/galaxy_rail_cta_clearance_test.dart` | +6 All passed |
| analyze | `flutter analyze --no-pub lib test` | No issues found! |
| 全量守卫 | `bash scripts/run_all_rule_guards.sh` | all rule guards passed (88 rules) |
| 四棘轮 | 四个 `scripts/guards/check_*_ratchet.py` | 全 PASS（UI-TOKENS color=225/275, fontSize=634/727 等，与自述一致） |

29 计数分解核对：capability_channel_visual 17 = 13 个静态声明 + for 循环 4 通道展开（`capability_channel_visual_test.dart:92-112`）；3+6+3 与文件逐一数出一致。**29 属实**。

## 1. D04 通道红线（最重靶）——过

- **verified 唯一性**：唯一判定点 `capability_channel.dart:49`（`allowsMasteredBrightness => this == verified`）；`resolveGalaxyStarVisualStyle` 非verified 一律 `_capped`（fill≤0.82、glow=0、pulse/halo=false，`:230-241`、`:260-284`）。painter 三处掌握档特效调用点全部改走 `capability.claimsVerification` 门：光晕分支 `star_map_painter.dart:1594-1597`、光斑 `:1726-1730`、呼吸脉冲 `:2329-2333`——与纯函数层构成双保险。
- **M1 独立重放**：`if (!verified) {` → `if (false) {`（practiced 放行掌握档）→ `capability_channel_visual_test` **7 失败**（+10 -7 亲跑），还原后文件 sha256 恒等 `ab92ae25…`（与 run_manifest 登记一致）。自述记 6，实跑 7（保守方向），见 R1-C2。
- **M2 独立重放**：按自述字面（`_openNodeDetailSheet` 不传 `graphEventSources`）→ **node_detail_capability_section_test 仍 6/6 全绿**——该测试直构 `NodeDetailSheet`，不经过 galaxy_screen，**自述的 M2 捕获声明不可复现**。改在 sheet 内 `_historyBody` 掐断 `graphEventSources:` 透传 → verified 溯源行正例红（+0 -1 亲跑；自述记 2 失败）。详见 R1-C1/R1-C2。
- **unknown fail-closed**：`fromWire` default→unknown（`:62-63`）、缺 `user_status`→默认 unknown（`:87-91`）、线值漂移 `mastered_v2`→unknown 且版本字段独立照实透传（测试 `:206-219` 钉）。99 分无通道数据不进掌握档（`capability_channel_visual_test.dart:258-278`）。
- **non_human/trace_only 零特效零进度假象**：四态逐一钉（`:97-112` 循环）+ 环标记虚线互异（`:116-145`）+ 抽屉「不计入能力掌握」文案钉（`node_detail_capability_section_test.dart:164-165`）。
- **零数据写入**：`capability`/`graphEventSources` 均不在 `galaxy_model.g.dart` 的 `_$GalaxyNodeModelToJson`（亲查生成文件，字段清单止于 `position_y`）；fromJson 纯读不改装 `mastery_score`。CH-2 的「变化面仅视觉+读屏」成立。

## 2. 验收三条——过（①带 R1-C1 测试覆盖缺口）

- **① 节点点开来源与投影 version 一致**：同源为真——`galaxy_screen.dart:2016-2019` 把同一 `GalaxyNodeModel` 的 `capability`+`graphEventSources` 传入 sheet；`_CapabilityEvidenceSection` 只渲染该快照，加载期即呈现不等 /history（`node_detail_sheet.dart:191-195` 区段），来源行/通道/版本三者同对象。**但该 screen→sheet 接线没有任何测试钉**（M2 字面重放全绿即为证），结构性保证当前只靠代码事实——见 R1-C1。
- **② 缩放按钮不遮挡主 CTA + 键盘可选节点**：本卡 diff 零触碰 `GalaxyControls`/焦点管理（全 diff 核对）；`galaxy_screen_keynav_test` 用真实 `LogicalKeyboardKey.arrowDown/tab/shift+tab` 事件遍历（非断言空转），`galaxy_rail_cta_clearance_test` 在套件中随跑全绿。差量举证合规（no_duplicate_rule）。
- **③ 不开特效全信息可读 + 无数据不造进度**：形状分层在 style 层钉死（ringMark 四态互异 + 封顶档 glow=0 时标记仍在，`capability_channel_visual_test.dart:147-159`）；painter `_drawCapabilityRingMark`（`star_map_painter.dart:2488-2531`）按 mark 绘制、与特效无关；掌握度 0「尚未学习」诚实面不被破坏；`投影版本 v\d` 全树 findsNothing 反例钉（抽屉测 `:137`）。

## 3. CH-1~CH-6 逐项裁决

- **CH-1（色温升温是否构成已掌握亮度强解读）— 裁决：否，现口径维持**。依据：后端 D04 doctrine 明文「亮度仍按存量分数渲染=参与足迹」（`backend/app/schemas/galaxy.py:617-646`，`_calculate_status` 封顶的是**标签**，`_calculate_brightness` 不封顶）；移动端封顶（fill 0.82/ring 0.38）比后端更紧；掌握档专属语言（0.94/0.72/光晕/脉冲/双环）verified 独占；通道身份由环标记形状承载，无特效可读（验收③成立不依赖色温）。若舰队后续收紧，改点确在 `_nodeStyle` 一处（`star_map_painter.dart:2294-2317` 委托点）。
- **CH-2（fail-closed 存量星变暗行为变化面）— 裁决：接受，无需应用内过渡文案**。变化面核实仅视觉档+读屏后缀+抽屉新增，零写入零删除零分数改动（§1 末条）；降级方向是「少声称」非「少信息」，抽屉通道标签即解释本身。建议合并登记进集成 release notes 即可。
- **CH-3（抽屉快照冻结 staleness）— 裁决：冻结符合验收①语义**。「点开看到的是点开时刻的一致投影」：冻结保证 (来源, 版本) 对内部恒一致；若改监听活 provider 反而可能引入「新版本+旧行」混合窗口。重开 sheet 即取新快照。staleness 提示列为可选接续项，非本卡义务。
- **CH-4（J-08 verified 图标不改）— 裁决：本卡不改正确**。V3 已 DONE 面不重置（AGENTS 硬规则+卡 no_duplicate_rule），卡验收不含该面；实现已如实登记 limitation #4。**注意残余张力真实存在**：practiced 节点带 outcome 行时，成功绿 `verified_outlined` 行紧邻「练习过 · 未独立检验」同屏（`node_detail_sheet.dart:141-150` + `:1302-1335`）——建议立接续卡换中性溯源图标（R1-S1）。
- **CH-5（ensureVisible 适配是否断言弱化）— 裁决：非弱化**。diff 仅插入 `ensureVisible`+pumpAndSettle 两行（`h5_cross_system_chains_test.dart:101-104`）；点按目标、`chat_mode`、`initial_context` 全键断言逐字保留（`:107-116` 亲读）；chain B/D 独立未动，套件全绿。
- **CH-6（Ahem 截图证据充分性）— 裁决：按 F04 先例充分**。亲验两份语义 dump 含声称原文+坐标：practiced「练习过 · 未独立检验」`u05_sheet_practiced_semantics.txt:21`、「不代表已掌握」`:24`、「投影版本 v7」`:30`；verified「独立检验通过」「独立测验 · 第 3 章单元测验」`u05_sheet_verified_semantics.txt:21,27`。画布无像素截图由 17 纯函数钉+painter nodesById 集成断言补偿（limitation #1 如实）。残余：环标记绘制几何（半径/透明度）无 golden 钉，纯呈现层，可接受。

## 4. 合并落差（vs main）

- 审查时 `origin/main`=`b1cec7c2`（含 ba6381fa F06 及其后 CI42）；merge-base=本卡基线 `20f1d99f`。
- `git merge-tree --write-tree HEAD origin/main`：**唯一冲突 = `v4/04_tasks/tasks.json`**（整 tasks 数组区冲突，双方各改自己卡位状态——舰队状态文件惯例，集成时按双方卡位并集机械解，非代码冲突）。
- 重叠文件全部 auto-merge：`galaxy_accessibility_service.dart`（F06 加 connectedNames 尾参+连接子句；U05 加通道后缀——**合并树亲验**：播报顺序 mastery→通道后缀→学习次数→重要性→连接子句，语义组合成立）；`galaxy_screen.dart`（F06 连接名注入 :1383 与 U05 能力传参 :2077 不同区域）；`app_zh/en.arb`+生成 dart ×3（双方各追加键，合并后按 arb 为源 `flutter gen-l10n` 再生即净）。
- 无行级代码冲突风险；集成后必须复跑 integration_reverify（review_receipt.json 已列）。

## 5. 其他核对

- **gRPC 降级诚实性**：实核 `proto/galaxy_service.proto:99-130`——`GalaxyNodeUserStatus` 存在（GRAPH-GRPC-SHAPE 补过）但**不含 `mastery_evidence`/`projection_version`**，gRPC 路径节点必然走 unknown+版本未知，与限制 #3 行为结论一致。措辞勘误：#3 写「不带 user_status」不准（带，但缺子块），净行为相同，随 R1-C2 一并订正。
- **l10n**：zh/en 键集差为空（双 0），新增 30 键+2 占位符 meta 双语齐备，`@galaxyCapabilityProjectionVersion{version:int}`/`@galaxyCapabilitySourceFallback{code:String}` 类型化；测试对 zh 原文字符串逐字断言通过=生成链一致。「+44 键」计数为 diff 行数口径（每文件 +44 行），非键数，无漂移。
- **拖拽态口径观察（R1-O1，不改判）**：`_capped` 拖拽分支把 ring 抬到 0.46>0.38（`capability_channel.dart:270-274`）——与既有全档拖拽可见性语义一致（旧代码拖拽同样抬 0.46），且恒低于 mastered 拖拽 0.72、glow/pulse 恒零；「ring≤0.38」应理解为静态态口径，建议 docstring 加「（静态）」二字。
- 五 Tab/RF-06 三文件/classic/`core/design`/backend/proto：全 diff 核对零触碰，与 diff_or_evidence_only §4 一致。

## 6. 挑战与建议（不阻断合并）

- **R1-C1（测试覆盖缺口）**：screen→sheet 同源接线（`galaxy_screen.dart:2016-2019`）零测试钉——按自述 M2 字面突变 `_openNodeDetailSheet` 后 29 新测全绿（亲放）。当前代码对，验收①运行时成立；但未来重构可无声断链。处置：集成时或接续卡补一条「真实 GalaxyScreen 泵→开节点→抽屉溯源行断言」测试；短期最低限度先修 M2 记录（下条）。
- **R1-C2（突变记录失实，须订正）**：test_results.json 的 M1 记 6 失败（实跑 7）、M2 记「`_openNodeDetailSheet` 不传 graphEventSources 被 node_detail_capability_section_test 2 失败捕获」（不可复现；可复现的是 sheet 内 `_historyBody` 掐断→1 失败）。证据纪律要求记录与可复现事实一致：合并时随 state 订正该两条（纯证据文档订正，不动实现）。限制 #3 的「不带 user_status」措辞同批订正为「user_status 无 mastery_evidence/projection_version 子块」。
- **R1-S1（建议接续卡）**：`_OutcomeEvidenceRow` 中性图标替换（CH-4）；抽屉 staleness 提示（CH-3，可选）；R1-C1 接线钉测试。
- **R1-O1**：`_capped` 拖拽 ring 0.46 与「ring≤0.38」静态口径 docstring 澄清。
- **R1-O3**：manifest「+44 键」口径注明为 diff 行数。

## 7. 裁决

**PASS_WITH_CHALLENGES**：三条验收全部独立复核成立；D04 通道红线（verified 唯一掌握档、fail-closed、无数据不造进度）代码+测试+M1 重放三重证实；数字与守卫全部亲跑属实；合并面清晰（仅 tasks.json 状态文件冲突）。不阻断项=R1-C1/R1-C2（合并登记+证据订正）/R1-S1（接续卡）。审查过程临时突变全部还原，工作树干净（HEAD=69238e23，临时文件仅 /tmp）。
