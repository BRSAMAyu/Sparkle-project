# V4-G04 — diff_or_evidence_only

## 结论一句话

星图/学习/错题/资料家族（galaxy/documents/error_book/learning/knowledge/seed_library/vocabulary）按「F05 判例确定性面走查 → 就地修 → 四风格对比度逐对机检 + 语义钉 + 8 张 golden」完成四风格商业化打磨：星图画布身份色阶收敛进单一名源 `GalaxyCanvasPalette`（原 11 文件 40+ 处匿名 `Color(0x…)`，值逐位保留）；走查实修 14 处风格面缺陷（hero 白字白底 1.1:1、文件类型 glyph pastel 浅档 1.7–3.1:1、全强度语义色小字、恒暗画布 DS 漂移墨、44→48dp 触达目标、PathMetrics 一次性迭代崩溃等）；续跑收口补修 3 处（双插画 on-accent 图标墨 dusk 2.2/1.9:1 <3:1 → `colorScheme.onPrimary` 校准槽、掌握度契约钉随新呈现契约更新、palette 落位 core/design/tokens_v2 使 ui-tokens 棘轮合法 PASS）；守卫测试 G04 套 21 测（对比度矩阵 10 + 修前判负探针 3 + 48dp 触达 + 星图面语义钉 + reduce-motion E± + 资料库 200% + 种子库空态 + G4-10/F 组回退钉）+ golden 2 测 8 张（dusk 库面因图标墨修复重签，理由已登记）；家族回归 galaxy 191 / error_book+learning+knowledge+seed_library 68 / core/design 335 分批 `--concurrency=1` 全绿 + 全量单批见 test_results.json；analyze 零 issue；repeat 棘轮 48 文件/90 调用点零漂移、ui-tokens 棘轮 color=123/275 大幅只降（基线时 225）、fontSize=632/727 持平；RF-06 三高危文件零触碰。

## 断点续跑与双会话冲突处置（如实登记）

前任 agent 中途中断，遗留 dirty 工作树（16 个产品文件 + 2 个未跟踪文件 + 1 个临时探针文件），**全部继承零丢弃**。续跑会话启动监视后发现**前任会话实际仍存活**并在同一 worktree 继续产出（18:01–18:22 实时编辑：PathMetrics 物化修复、_ControlButton 50dp+tight 约束、node_preview 卡 colorScheme.surface 化、E-1 探针改判 CB 色觉辅助档、D 组领域名改「宇宙」、G4-4 标签墨改 textPrimary、g04_four_style golden 套新建）。为避免双实现者互写（卡面 `required_locks: ui-polish-g04` 即防此），本会话按最低风险路径**等待写入静默（≥10 分钟零变化）后顺序接管**，不重写存活会话已完成部分，只做审计 + 缺口补完：

| # | 续跑收口补完（本会话） | 依据 |
|---|---|---|
| S1 | document_library 双插画（_MiniGalaxyIllustration/_LargeGalaxyIllustration）on-accent 图标墨 `Colors.white` → `Theme.of(context).colorScheme.onPrimary` ×2 | dusk 亮 accent 渐变上白图标 2.21/1.90:1 <3:1（图形档，WCAG 公式实测）；G01 A8/A9 同判例；dusk 档 onPrimary=accentInk 0xFF17261C 复算 6.1–8.2:1 |
| S2 | G4-10 公式钉：四档 on-accent 墨 × 渐变四止点 ≥3:1 + dusk 白墨修前判负探针 | F06 判例（最终计算颜色）+ G05「公式钉 + widget 钉」双层模式 |
| S3 | F 组 widget 回退钉：真实泵制读 resolved `Icon.color` 四档 == 校准槽 | 产品码回退 Colors.white 会在此失败（G05 Errata C1 同款收口） |
| S4 | `GalaxyCanvasPalette` 落位 features/** → `core/design/tokens_v2/`（+10 处 import 按序迁移、node_preview 残留 unused import 清除） | `check_ui_design_tokens_ratchet` 对 features 新增字面量文件零容忍且 baseline「never raise」；色值定义归设计层 = `pixel_preview_theme` 同判例；不迁则棘轮 FAIL，迁后 PASS color=123/275（较基线 225 只降） |
| S5 | `error_card_mastery_band_test` 契约钉随新呈现契约更新（band 文字墨 textPrimary；进度条仍钉 masteryBandColor） | G04 有意修复（全强度语义色小字像素档不齐 4.5:1，G4-1 同口径）使旧契约失败；更新理由在文件头注明 |
| S6 | E-1 探针注释勘误（8B4500 为 highContrast 档值，classic 默认档实为 7D5C26） | 注释准确性，断言不受影响 |
| S7 | g04_four_style golden 基线重签（8 张） | S1 图标墨修复改变 dusk 库面像素（~0.2%，旧基线靠 0.5% 容差带吸收不诚实）；重签理由按 EVALUATION_PROTOCOL 登记 |

## 第三程续跑（证据收口会话，2026-09-29 晚；两任前任配额中断后第三任接管）

第二任会话写完上文时再次配额中断：实现与证据文档在盘、**未 commit**，其 18:49:53 发起的全量回归以后台进程存活。第三程会话接管时核实：该孤儿跑正是 receipt 引用的「全量单批」证据，遂**不杀不弃**，只读审计等其收尾（+3408 ~23 All tests passed! FULL_EXIT=0，约 27 分钟）后收割为 F1 台账。接管期补完两项**前任遗留证据路径缺陷**（均在测试文件证据落盘分支，常规跑不触达故 F1 全量仍全绿）：

| # | 第三程收口补完 | 依据与实证 |
|---|---|---|
| S8 | D 组证据落盘裸 `await boundary.toImage` 包入 `tester.runAsync` 真异步窗口 | 置 `G04_EVIDENCE_DIR` 首跑 D 组 10 分钟超时（两连跑复现）：引擎回调在 fake-async 测试区永不完成；F05 `_capture` / G05 同款 runAsync 判例。修复后 2 秒全绿 |
| S9 | 语义树 dump 由 `widget is Semantics` widget 直查改 F05 渲染层口径（RenderParagraph 文本 + RenderSemanticsAnnotations 标签） | 前版泵内恒空表 → raw/ 语义 txt 0 字节、跨档恒等钉**空转**；改后 4 档各 8515 字节同构真实树（节点名/领域/掌握度/解锁态逐项在树），D 组语义钉由空转转实锚 |

第三程终证台账（全数字为本机可复跑真实退出码，详见 test_results.json）：全量单批 +3408 ~23 全绿（F1）→ S8/S9 修复后 G04 套 +21 全绿且 raw/ 8 文件真实落盘（F2）→ core/design 终态 +335 全绿（F3）→ analyze No issues found（F4）→ repeat 棘轮 48/90 零漂移、ui-tokens 棘轮 PASS color=123/275 fontSize=632/727。实现以 1d699d83 单点 commit（28 files +1724/-98），证据随后独立 commit。

## 走查缺陷清单（继承修复 + 续跑收口；四风格 × 逐面）

### A. 继承已修（前任 + 存活会话，呈现层风格面）

| # | 面 | 缺陷（走查实证） | 修复 |
|---|---|---|---|
| A1 | 资料库 hero 卡 | 白字钉死：classic 浅/paperDay/quiet 下 deepSpaceStart 渐变亮止经浅彩派生，白字仅 ~1.2:1 | 墨随画布亮度取对侧（深档白字逐位保留，浅档 textPrimary/textSecondary 四档 ≥4.5:1，G4-3 钉） |
| A2 | 资料库 hero 指标玻璃面 | 浅档白玻璃+白字 1.1:1 | 玻璃基料与墨同随亮度（浅档墨玻璃） |
| A3 | 资料库文件类型 glyph | 五枚 pastel 字面量（pdf/docx/pptx/md/image）浅档 1.7–3.1:1 全面不足 | 收敛语义槽（error/info/warning/success/reflection，G01 纸屑六槽判例），浅档同色相加深 0.38，图标 ≥3:1、标签墨 textPrimary ≥4.5:1（G4-4 钉）；深档全强度逐位保持 |
| A4 | 资料库状态徽章 | 全强度 warning/success/error 做 labelMedium 浅档 1.9–3.6:1 | 状态语义由 label 文案唯一承载，文字墨 textPrimary，色相保留 tint/描边（G05 pill 判例） |
| A5 | 错题本（detail/review/card） | 掌握度档位/你的答案/正确答案/统计值全强度语义色做小字 | 文字墨收敛 textPrimary，档位语义由文案承载、色相保留 tint/图标/进度条（S5 契约钉同步） |
| A6 | 学习旅程 | parse 状态 chip 全强度色小字不齐、OCR 手输提示 warning 小字 1.9–2.2:1、降级横幅 error 小字 3.6:1 | chip 底留状态 tint、文字墨统一 textPrimary；提示/横幅正文墨 textSecondary/textPrimary |
| A7 | 知识详情 | 收藏星标恒取深档领域 pastel，浅面 2.2:1 | 领域色按环境亮度取档（primaryColorFor/glowColorFor，深档逐位保持） |
| A8 | 星图恒暗画布 | 11 文件 40+ 匿名 `Color(0x…)` 散落；暗角墨钉 `DS.neutral900` 随 profile 漂移（浅色档漏深墨进恒暗画布） | 收敛单一名源 `GalaxyCanvasPalette`（值逐位保留），暗角墨钉死画布身份值 |
| A9 | 星图缩放控件 | 触达目标 44dp（Container 装饰边框吞 2dp 实测仅 46 可点） | 容器 50dp（48 可点区+2×1 描边内缩）+ IconButton tight 48×48 约束，四档机检 ≥48（C 组钉） |
| A10 | 上传浮层 trail painter | `PathMetrics` 一次性可迭代被 isEmpty 消费后再 `.first`，测试引擎必现 "Bad state: No element" | 物化一次再判空，绘制输出逐位不变（E± 钉随附） |
| A11 | 节点预览卡/草稿审查/迷你图/设置 sheet/贡献横幅/监测徽章/上传链路 | 各自匿名深空色阶 | 收敛进 palette（panel/glass/gradient/cyan/perf 各组，值逐位）；预览卡暗档底改随 colorScheme.surface（星图强制暗子树内=chromePanel 同族，dusk 外挂随暮色表面，代码注释叙证） |
| A12 | 回退图标墨（草稿审查屏） | `DS.textPrimary` 随 profile 变，浅色档把深墨图标漏进恒暗暗底 | 恒暗族白墨走 `DS.neutral0` 与兄弟元素同源 |

### B. 登记不修（📋 0 处产品缺陷残留）/ 范围外

- 家族内容面 `Colors.*` 残余仅 4 处：hero 墨双分支的深档白字（A1 判例的合法侧）×2 + 续跑收口后双插画 onPrimary 化（S1）——不再有未登记白墨叠 accent 面。
- vocabulary 模块仅有 data/repository/provider，无任何 presentation 屏（`find lib/features/vocabulary -name "*_screen.dart"` = 0）——无四风格呈现面可走查，属模块现状而非本卡缺陷（limitations §1）。

## 验收逐条自证（卡面原文 → 机器证据）

1. **「家族内零风格专属缺陷：任一风格下无对比度失败/文本截断/令牌外颜色/布局破碎」** —
   - 对比度：G04 套 A 组 10 测（正文对四档 ≥4.5:1、pill/chip 修复墨、hero 亮度自适应、glyph 图标 ≥3:1 且标签 ≥4.5:1、**星图 canvas 专项 G4-5/G4-6/G4-7/G4-8**：掌握度节点四档+领域七色+预测/风险/庆祝/错误脉冲 vs 恒暗画布 ≥3:1、标签墨 ≥4.5:1、chrome 控件/迷你图/上传链 ≥3:1、草稿审查白墨族 ≥4.5:1、classic 深档第二锚）+ G4-10 on-accent 墨 + B 组 3 个修前判负探针（E-1 CB 档 warning 2.09:1、E-2 hero 白字 1.24:1、E-3 pastel glyph <3:1——探针全部真实失败，判别力在证）。
   - 令牌外颜色：家族七模块 `grep 'Color(0x'` = 仅 palette/sector_config 两个名单源 owner（galaxy 77 处全在其内）；ui-tokens 棘轮 PASS color=123/275（基线冻结时 225，**只降**）fontSize=632/727（持平）。
   - 文本截断/布局破碎：F 组资料库 200% 文本 × 四档零异常零溢出泵制；D 组星图面四档零异常 + 语义结构跨档恒等；8 张 golden 常态容差比对全过。
2. **「四风格各有确定性 golden+语义钉且 CI 可失败」** — golden：`test/goldens/g04_four_style/` 星图面+资料库屏 × classic/paperDay/dusk/quiet = 8 张，B04 容差比较器（0.5% 带界、无 skip 门、常态比对路径；跨机漂移 ~0.18% 带内、真实回归 ≥0.6% 硬失败，FIX-581 另卡不归本卡）；语义钉：D 组节点名「特征值与对角化」+ 领域名「宇宙」四档在场且语义树跨档恒等、G 组种子库空态「还没有创建种子库」+ 主操作四档逐字一致、F 组 hero 标题四档在场。基线重签 1 次（S7，理由已登记）。
3. **「既有功能测试全绿+analyze 零+repeat 棘轮只降不升」** — analyze `flutter analyze` = **No issues found!**（含修复存活会话遗留 unused_import 与本会话 3 处 directives_ordering）；回归：galaxy 191 / error_book+learning+knowledge+seed_library 68 / core/design 335 分批 `--concurrency=1` 全绿，全量单批结果见 test_results.json；repeat 棘轮 48 文件/90 调用点（base 27a47d2f 同值，零新增）；reduce-motion：E 组上传浮层等价钉（低动态首帧静止终态 + 600ms 零位移 + E- 常规通道在场控制组）+ 无新增 `.repeat(` 动画面 + 既有 motion_reduce_motion_test 全绿。

## 走查分母与覆盖面（scope_and_denominator）

- **逐面 × 四风格泵制面**：星图画布身份（palette 全组机检 + D 组真实组件面 + 2 面 golden）、资料库屏（hero/glyph/状态徽章/插画/200%，F 组 + golden）、上传浮层（E± reduce-motion）、缩放控件（C 组 48dp 四档）、种子库空态（G 组）、知识详情/错题三屏/学习旅程（走查缺陷修复载体 + A 组公式钉全档复算 + 既有功能测试回归）。
- **未逐泵长尾**：galaxy 长尾（search_panel/error_dialog/graphrag 等同令牌管线且 palette 收敛后无私有字面量，`grep 'Color(0x'` 实证）、documents 长尾组件、error_book/learning 次级屏——风险边界与 G01 判例同构（家族字面量归两名单 owner + Q05 三端重卡审查兜底），登记 limitations §1。
- **vocabulary**：无呈现面（现状盘点，非缺陷）。

## 红线自证

- **纯呈现层**：全部 diff 为颜色/墨色/tint/触达尺寸/一次迭代物化；无路由/状态/交互/契约变更。PathMetrics toList 为绘制输出逐位不变的测试引擎崩溃修复（A10）。`_useDarkGalaxyTheme` 恒暗产品身份、发布默认主题（classic）零差量原则全程保持——classic 浅/深档输出除有意的对比度修复点外逐位不变。
- **禁触面**：`git diff --name-only | grep -iE 'shop|/s04|v3-output|routes/|backend/|proto/'` = 零命中；S04/Shop HIDDEN 零触碰；不 push；未动主仓与其他 worktree。
- **资源红线**：全程 `flutter test --concurrency=1`；每轮前 df ≥34Gi 可用（未触 15G 红线）、swap 自查；golden 产物入库即基线资产（非运行时垃圾）；无 v3-output 产物提交。
- **锁**：`ui-polish-g04` 租约 NOT_RUN（sparkle-coordination-v2 私有远端未配置于本机，G01/S01 同口径）；冲突面以 diff 自证。**双会话冲突事实与顺序接管处置见文首专节**——此为本卡特有的过程风险登记，接管前后工作树状态均有快照（/tmp/g04_inherited_final_snapshot.diff 留档于执行机）。

## 工具链与环境事实

Flutter 3.41.3 stable / darwin 25.6.0 arm64；worktree wtG04 直连主仓分支 `agent/v4/g04`（base=27a47d2f，头无新提交、全部未提交改动起跑）；`mobile/lib/gen` gitignored 实体目录在位；跑测全程 df 35→34Gi 可用、swap 无耗尽。
