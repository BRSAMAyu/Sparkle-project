# V4-G04 · R1 独立审查（review_r1）

- 审查员：V4-G04 R1（独立未参与会话；实现系三程接力，R1 与三程均无会话连续性）
- 日期：2026-09-29 ｜ 分支 agent/v4/g04 ｜ 被审树：1d699d83（实现）+ 306b6503（证据）
- 方法：全部亲验不信自报——diff 逐行亲读 + 亲跑 4 批测试 + 独立 Python 对比度复算 + 证据重生成哈希对账 + 双棘轮 base/head 对账。R1 全程零产品码触碰，审查 commit 后树净（唯一新增 = 本文件）。

## 裁决：PASS_WITH_CHALLENGES

八靶全过；新增挑战 R1-C1/C2（LOW）+ R1-C3~C5（INFO），自报 CH-1~CH-6 逐条核销均支持实现侧。

## 逐靶裁决

### T1 S8/S9 修复质量 — PASS（最重靶）
- S8（runAsync）：亲读 g04_family_four_style_test.dart L706-726——toImage/toByteData/写盘全部包入 `tester.runAsync`，且仅在 `G04_EVIDENCE_DIR` 置位分支进入（L706），常规跑不触达——「F1 全量先于修复仍全绿」的时序挑战（CH-6）由代码结构直接成立。
- 判例实查（git log 亲证，非引用转述）：F05 style_preview_evidence_test.dart commit 7918a683 在册，其 L91 `runAsync` + L58/L65 RenderParagraph/RenderSemanticsAnnotations 口径与 S8/S9 修复同款；G05 g05_family_four_style_test.dart commit 5f3b2c0e 在册，L275 同款 runAsync。
- S9 非空转实证：在库 4 份语义 txt 各 8515B、md5 逐字节相同、内容真实（节点名/领域/掌握度/解锁态/操作标签在树，非空表恒等）。R1 亲跑重生成（批次 3，G04_EVIDENCE_DIR 置位）→ 新 4 份语义 txt 与 4 张 PNG 与在库 raw/ 逐字节同哈希（PNG 97fc2f8b/b63e7bb1/5d4e9f42/1fc66a92，语义 0a10d36d）——S8/S9 修复后路径由 R1 独立复现。
- [R1-C3 INFO] G04 dump 较 F05 少 rect/value/isButton 字段——跨档恒等钉的必要省略（几何随档变会破坏恒等断言），但测试注释「字段等价」表述过强，应作「字段覆盖语义钉所需子集」。

### T2 对比度钉真实性 — PASS
- 独立 Python 复算（色值全部从 theme_manager.dart/pixel_preview_theme.dart/galaxy_canvas_palette.dart 代码实取，WCAG 2.x 公式独立实现）：
  - G4-1 classic pill 修复墨：success 14.30 / warning 14.31（≥4.5）
  - G4-5 画布九色：masteryLow 4.83 / masteryMid 9.14 / masteryHigh 12.97 / masteryFull 13.04 / predictionGold 13.38 / riskHigh 7.55 / riskMedium 12.55 / riskLow 10.79 / errorPulse 5.66（≥3.0）
  - G4-8 草稿白墨族：1.0/0.72/0.58 三档 = 19.89/10.34/6.89（≥4.5）
  - G4-6 标签墨：warm 17.77 / cool 16.79（≥4.5）；G4-10 dusk 修复墨 17261C 8.46（≥3.0）
- 修前判负探针全红（防自证绿灯）：E-1 CB 档 1.92:1 <4.5 红、E-2 hero 白字 1.24:1 红（与自报 1.24 精确一致）、E-3 五 pastel 1.45–2.39 全 <3.0 红、G4-10 dusk 白墨 1.87 <3.0 红。判别力在证。
- [R1-C4 INFO] E-1 自报 2.09:1 vs R1 亲算 1.92:1——方向一致均判负，探针有效；数值口径差异不追。

### T3 golden 确定性 — PASS
- 8 张 golden 常态容差比对亲跑绿（批次 1，+23 含 G04 套 21）。
- raw/ 4 PNG 与 golden 基线 4 张 SHA256 逐字节同哈希亲验（跨会话确定性自证成立）。
- 更强证据：R1 亲跑重生成 4 PNG + 4 语义树，8/8 与在库证据逐字节同哈希。

### T4 孤儿进程收割合法性 — PASS（附 R1-C1 LOW）
- 按「不信任该证据」指令，R1 未采信 +3408 孤儿跑，改以亲跑 4 批覆盖全部受影响面：批次 1 G04 套+goldens +23 绿；批次 2 galaxy/error_book/learning/knowledge 家族 +251 ~1 绿；批次 3 core/design 335（见下）；批次 4 g03 家族+共享 widget +155 绿；analyze 零亲跑。SHA 对账：批次 1 开跑时 HEAD=306b6503 实录，产品码树=1d699d83。
- F1 全量整批（27 分钟）R1 未复跑——降级为挑战 R1-C1，见下。
- R1 自查披露：批次 3 与批次 4 曾并发执行（R1 调度失误），批次 3 出现 10 处失败（ink_sparkle.frag 资产竞因等环境 flake，与 G04 文件零交集）；串行单独重跑该 10 文件 +101 全绿 exit 0——确证为审查侧并发污染而非回归。批次 3 其余 325 绿 + 重试 101 绿 = core/design 全绿结论成立。

### T5 双棘轮 — PASS
- repeat：HEAD 48 文件/90 调用点 == base 27a47d2f 48/90（git grep 双端亲跑），零漂移。
- ui-tokens：R1 亲跑 PASS color=123/275 fontSize=632/727；baseline JSON base→head 零 diff（棘轮基线未动，只降性质成立）。
- [R1-C5 INFO] 审查简报侧「123/225」系笔误；证据内部（receipt/test_results）一致记 123/275，与 R1 实测一致。

### T6 纯呈现层红线 — PASS
- 17 个产品文件（16 改 + palette 新增）diff 逐行亲读：全部为颜色字面量→GalaxyCanvasPalette 同值换名（R1 逐常量核对 20+ 组值逐位相等）或登记过的有意修复（hero 亮度自适应墨、glyph 语义槽化+0.38 加深、onPrimary 槽 ×2、48dp 触达、vignette 墨钉死、node_preview colorScheme.surface 化、回退图标墨 DS.neutral0、语义小字墨收敛 ×3 族）。回调/路由/状态/交互零变更。
- PathMetrics toList 物化：Flutter PathMetrics 确为一次性可迭代，物化为行为保持修复，绘制输出不变。
- RF-06 三高危（dashboard_screen/compact_status_bar/task_execution_screen）+ shop|/s04|v3-output|routes/|backend/|proto/：git diff --name-only grep 零命中亲证。
- [R1-C2 LOW] vignette 墨钉死（DS.neutral900→F4F1EB）：classic 档逐位不变属实；dusk 档原值实为 F5F0E3（duskInk），钉死引入 ≤0.4% 通道级微差——painter 注释「classic/dusk 输出不变」对 dusk 非逐位精确。属登记过的有意修复且新输出已被 golden 钉住，不阻断；建议后续把该注释改为「classic 逐位不变、dusk 亚感知微差」。

### T7 邻族完整性（CI54 教训） — PASS
- g03（memory/aurora/cognitive，NOT_STARTED 卡）既有测试 +251 归批次 2/4、+155 批次 4 亲跑全绿。
- 共享面：error_card_galaxy_echo / h5_cross_system_chains / compact_error_card_a7_tap 亲跑绿；引用被改组件的全部测试目录（galaxy widget/unit/integration/performance、error_book、learning、knowledge）在批次 2 全绿。无 G05 式旧钉冲突。
- CH-3 核销：error_card_mastery_band_test diff 亲读——1:1 替换（band 文字墨 == masteryBandColor → == DS.textPrimary），断言数不减、负向断言与进度条 owner 钉保留、G4-1 四档公式钉新增。属「改呈现契约须同步钉」，非删断言取绿。

### T8 CH-1~CH-6 复核 + 证据五件套 — PASS
- 五件套 + artifacts_sha256 + raw/ 8 文件齐；artifacts_sha256 与现树全部对账（8 PNG/txt + 5 文档逐哈希亲验）。
- CH-1（三程完整性）：时间线无法事后全验，但产出完整性由 R1 全套亲跑独立背书；commit 单点拆分（1d699d83 实现 + 306b6503 证据）属实。核销。
- CH-2（palette 落位）：pixel_preview_theme 同位先例亲证（同目录）；守卫对 features 新字面量零容忍亲证；落位非规避（该文件全量值被 G4-5/G4-6/G4-7 机检覆盖）。核销。
- CH-3：见 T7。核销。CH-4（reduce-motion 证据层级）：E± 三重探针 + 位置零位移，widget 级与登记口径一致；已由批次 1 亲跑绿。核销。CH-5（48dp 密度）：C 组四档 ≥48 机检亲跑绿，50+tight48 解释与 diff 实况吻合。核销。CH-6：见 T1——落盘分支常规跑不可达由代码结构亲证。核销。
- [R1-C5b INFO] receipt 称「CH-1~CH-6 预登记于 limitations.md §4」，limitations §4 实为 CH-1~5、CH-6 在 receipt challenges 数组——登记齐但位置表述不精确。

## 新增挑战汇总（供 leader 处置）

| # | 级别 | 内容 | 处置建议 |
|---|---|---|---|
| R1-C1 | LOW | F1 全量 +3408 为第二程孤儿跑收割的第二手证据，R1 未整批复跑（27 min）；R1 以 4 批亲跑（23/251/335/155）+ analyze 0 全绿覆盖全部受影响面作替代终证 | 接受替代终证闭账；若需字面全量，挂 CI 自然轮 |
| R1-C2 | LOW | vignette 钉死对 dusk 非逐位不变（F5F0E3→F4F1EB，≤0.4% 通道），注释「classic/dusk 输出不变」过强 | 注释口径修正，随手修或挂后续 |
| R1-C3 | INFO | S9 dump 较 F05 少 rect/value/isButton（恒等钉必要省略），「字段等价」表述过强 | 随手改注释 |
| R1-C4 | INFO | E-1 自报 2.09:1 vs 亲算 1.92:1（均判负，探针有效） | 无需处置 |
| R1-C5 | INFO | CH-6 登记位置 + 简报侧 ui-tokens 笔误（证据内部一致 123/275） | 无需处置 |

## 最重风险

R1-C1：全量单批证据为第二手（孤儿收割），未由独立会话整批复现——已以受影响面 4 批亲跑全绿实质覆盖，残余风险为 mobile 域其他未触及模块存在与 G04 无关的既有失败未被发现（与 G04 diff 无因果）。次重为 R1-C2 的 dusk 亚感知色差已被 golden 钉死，无漂移风险。

## 审查侧资源声明

全程 --concurrency=1 单进程纪律（批次 3/4 并发为 R1 调度失误，已披露并以串行重跑矫正）；df 开跑 34Gi（>15G 红线未触）；零 mutation（树在审查 commit 前恒净）；未 push；未动产品码。
