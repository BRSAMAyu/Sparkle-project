# V4-G04 · limitations

## 1. NOT_RUN / 边界面（如实登记，不冒充）

1. **长尾屏未逐泵 × 四风格**：家族逐面泵制面 = 星图画布身份、资料库屏、上传浮层、
   缩放控件、种子库空态 + 修复载体屏（知识详情/错题三屏/学习旅程）；galaxy 长尾
   （search_panel/error_dialog/graphrag 等）与 documents/error_book/learning 次级
   屏未逐屏四风格泵制。风险边界实证：家族七模块 `Color(0x…)` 字面量全部收敛进
   两个名单 owner（`GalaxyCanvasPalette` + `SectorConfig`，后者为既有领域色板
   owner），长尾无私有字面量源、同令牌管线；兜底 = Q05 三端重卡审查
   （no_duplicate_rule 分工）。
2. **vocabulary 模块无呈现面**：`lib/features/vocabulary/` 仅 data/repository/
   provider，无任何 `*_screen.dart`（find 实证 = 0）——卡面 modules 含
   vocabulary，本卡按模块现状登记为「无四风格呈现面可走查」，非缺陷豁免。
   若后续 vocabulary 出屏，其面走查归该屏的实现卡。
3. **真机四风格目检/截图矩阵** → NOT_RUN（本卡无真机/模拟器触达）；已交付面 =
   flutter test 确定性泵制（F05 判例面）+ B04 容差 golden + raw/ 下成对
   PNG+语义树证据；逐态实机矩阵归 Q05。
4. **锁租约 NOT_RUN + 双会话冲突已发生**：sparkle-coordination-v2 私有远端未
   配置于本机（G01/S01 同口径）；本卡执行期内前任会话实际存活并在同一
   worktree 并发产出（diff_or_evidence_only §断点续跑专节），第二程以
   「等待静默 ≥10 分钟 → 顺序接管」消除互写窗口，但**租约缺位下的双实现者
   风险是流程事实**——第三程接管时第二程已配额中断（后台回归由第三程收割，
   见 §3.3），三程产出以最终 commit 树状态与全套回归绿为准。
5. **G04_EVIDENCE_DIR 成对证据为 widget 级宿主截图**（720×1280 逻辑 2x PNG +
   渲染层语义树 txt，F05/G05 判例口径），非真机截图；卡片 normal 档，HEAVY 截图
   矩阵归 Q05。**第三程补登**：该成对证据在第二任会话仅声明未落成——证据落盘
   路径存在两处遗留缺陷（裸 await toImage 超时 / 语义 dump 恒空表，见
   diff_or_evidence_only §第三程续跑 S8/S9），本程修复后 raw/ 8 文件（4 PNG +
   4 语义树）方为真实落盘；此前的声明-落地差如实登记为断点续跑过程事实。
6. **golden 基线量 = 2 面 × 4 风格**：错题/学习/知识等修复载体以公式钉 +
   契约钉 + 语义钉覆盖，未各出 golden（G01 同口径：基线量按「家族关键屏」
   最小充分原则，扩 golden 属基线资产膨胀须独立签理由）。
7. **全量治理守卫未整批重跑**：本卡回归口径 = mobile 测试域 + 三棘轮
   （repeat/ui-tokens/reduce-motion）；`run_all_rule_guards.sh` 全量基线未在本
   卡重跑（非本卡面）。

## 2. 已知取舍（实现面）

1. **palette 落位 core/design/tokens_v2 而非 features/**：ui-tokens 棘轮对
   features 新增字面量文件零容忍且 baseline never-raise，收敛式新色板在
   features/ 下无法合法落棘轮（FAIL 实证在 run_manifest 命令 11）；移入设计层
   = `pixel_preview_theme` 判例（色值定义归 design 目录）。文件仍是「画布身份
   色定义源」而非 DS 语义槽——**提升为全仓令牌槽仍属 Q08 类发布面决策**
   （预登记挑战 CH-2）。
2. **掌握度契约钉更新（S5）**：error_card 档位文字墨由 masteryBandColor 改
   textPrimary 是有意修复（全强度语义色小字在像素档不齐 4.5:1；档位语义由
   文案承载、色相保留进度条/tint），旧契约钉（文字==band 色）随之更新——
   这是「改呈现契约须同步钉」而非「放松既有门」；进度条 owner 钉原样保留。
3. **预览卡暗档底微差**：`0xE6151D30` → `colorScheme.surface`（星图强制暗
   子树内 = chromePanel 0xFF101929 同族色阶），非逐位等值但在代码注释叙证
   为「同族深空海军、dusk 外挂随暮色表面」——视觉合同变化已由 golden 钉住。
4. **dusk 库面 golden 重签（S7）**：图标墨修复改变 ~0.2% 像素，旧基线在
   0.5% 容差带内仍会绿——但已知故意变更不应靠容差吸收，故重签并登记理由；
   重签后常态比对通过。
5. **E-1 探针改判 CB 档**：classic 默认档 warning 已是重校准深墨（4.90:1
   通过），旧公式判负前提不成立；探针改用色觉辅助档（E69F00 高饱和橙同一
   公式 2.09:1 失败）——「逐色测试」判例（ACCESSIBILITY_ASSETS：高对比/
   色觉辅助维持既有配置并逐色测试）。

## 3. 移交与协作边界

1. **Q05 分工**：本卡交付后 G04 家族返绿，Q05 三端重卡审查可据
   evidence/V4-G04/ 走查；两卡不重复出同面截图矩阵。
2. **FIX-581（golden 比较器跨机容差）不归本卡**：本卡 golden 在基线机
   自比通过；CI 跨机问题按该卡口径处理。
3. **存活会话收尾风险移交——已了结（第三程核实）**：第二任会话在写完证据文档后
   配额中断，未再写入；其 18:49:53 发起的后台全量回归由第三程会话等待收尾后
   收割（+3408 全绿），未观测到接管后的任何并发写入。合并前建议协调者仍按
   流程确认无遗留会话持有本 worktree。

## 4. 审查挑战预登记（CH-1 ~ CH-5，供独立审查 R1 直取）

- **CH-1 双会话续跑的完整性**：接管前存活会话产出与接管后本会话产出无同点
  互写——反方证据 = 时间线（18:01–18:22 存活写入全部在 18:32 接管决策前；
  接管后本会话改动均有 Edit 工具记录）+ 最终全量回归绿；挑战者可核对
  commit 拆分（实现 commit 单点）与 /tmp 快照。
- **CH-2 palette 落位是否规避棘轮**：移入 core/design 是否=「换目录躲守卫」
  ——反方证据 = DESIGN_SYSTEM「迁移令牌只触 design 目录」+ pixel_preview_
  theme 同位先例 + 守卫立法本意是 features 业务呈现层不新增裸值，色值定义
  源归设计层正是其设计意图；正方 = baseline never-raise 规则同样不可违，
  两约束下唯一合法解即迁移。
- **CH-3 S5 契约钉更新是否「删断言取绿」**：反方证据 = 钉从「文字==band 色」
  改为「文字==textPrimary + 进度条==band 色」，断言数量不减、owner 钉保留、
  G4-1 四档公式钉同口径新增；正方可主张旧契约即 N12 验收原文——移交 =
  EB-G5 语义 owner 复核。
- **CH-4 E± 证据层级**：上传浮层 reduce-motion 以位置零位移 + 在场 + 零异常
  三重探针（非 S01 RGBA 字节级）——G01 CH-6 同构，SparkleConfetti 面 widget
  级 RGBA 判例已在库。
- **CH-5 触达 48dp 的密度收窄解释**：Container 50dp+tight 48 约束 vs 主题
  视觉密度再收 2dp 的实测口径（46）——机检钉在 C 组四档全过；挑战者可复算
  IconButton 视觉密度公式。
