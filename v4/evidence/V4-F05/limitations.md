# V4-F05 — limitations

## 范围与边界

1. **「五面」的口径 = 真实表面组件面，非整屏**：首页面 = 真实
   `TodayCockpitCard`（首页 hero 面），非 2594 行 `DashboardScreen` 整屏；
   星图面 = 真实 `TiledSectorBackground` + `GalaxyNodePreviewCard`，非 4703
   行 `GalaxyScreen` 整屏；长回答面 = 真实 `SparkleMarkdown`（聊天气泡同款
   内容渲染器），非整只 `ChatBubble`（其依赖会话 provider/网络/分享服务——
   preview 离线合同 + CH-4 守门禁止 preview 面隐性接线）。整屏装配依赖
   网络/相机/空间索引真源，属后续集成 SHA 复验或页面家族卡的范围；本卡
   「真实 Flutter 内部预览」落在其真实表面组件 + 冻结 seed，与 F02 故事页
   同一取证哲学。
2. **无真机/模拟器运行**：本机无 adb/AVD（B04 同口径）；证据为 widget-test
   真渲染泵截图（HEAVY 面的真实开销在 15 面×4 档渲染取证与串行调试），
   Ahem 测试字体块——真实文案以语义 txt 为准；触觉/音效仅保留调用时语义。
3. **截图可复现性的边界**：截图 sha256 对「同机同 Flutter 同 seed 重跑」
   稳定（Skia 确定性渲染），但 runActive 步首页面含真实骨架 shimmer——
   页面级截图（preview_page_*）在 shimmer 相位上逐跑可能差一帧；单面采集
   的 canonical 流步已避开 shimmer 步（home 取 committed），逐字节复现以
   单面 + sheet 采集为准。
4. **l10n 无新键**：preview 页与入口为中文先行的硬编码字符串——依据 F02
   故事页先例（core/design 预览面不进 arb）；入口 tile 在 flag 关时零节点，
   不进发布面，故不占 arb 词条审批路径；批准转正时随「preview→发布」决策
   一并补 arb 词条（届时同步过 N18/I18N 守卫）。
5. **ProviderScope 按流步重挂**：首页面用 `ValueKey('...-$step')` 让
   ProviderScope 在流步切换时重挂（Riverpod 覆写集合创建后不可变）——
   仅发生在隐藏 preview 页内的面卡，不触生产面；代价是一次组件重建。
6. **同一状态流的深度**：四步流覆盖 F03 的成功/高亮/中性/冲突四类呈现
   语义；`unknown`（断网对不上账）步未纳入流（其真实触发面在 F03 适配器
   测试内钉死）——preview 流步选择以「五面在 canonical 步有真实可视差」
   为准，未做成五态全排（组合爆炸 vs 取证价值的取舍，审查者可挑战）。

## 已知限制

- **星图面的扇区底色**：`SectorBackgroundPainter`（真实组件）自带扇区
  色相逻辑，不随候选色板全量跟随——quiet 档下紫色扇区云仍按组件自身
  规则渲染。这是「真实组件」的忠实呈现，不是色板失灵；页面家族卡若要
  星图全面跟随候选色板，需动 `galaxy_display_settings_provider` 的颜色
  消费链（超出本卡锁面）。
- **入口 flag 是内存静态量**：`AppFeatureFlags.enableStylePreview` 为编译
  期默认 false 的静态量（与 `enableTaskGuidanceV2` 同模式），无远程开关；
  转正/下线通过代码改动 + 审查完成，不是运行时配置。
- **持久化复原测试用 SharedPreferences mock**：`initialize()` 重读持久层
  的语义被钉住，但真实 SharedPreferences（非 mock）的磁盘行为未在本机
  验证（无设备面）。
- **长回答面无气泡容器**：`SparkleMarkdown` 承载内容渲染真实路径；气泡
  容器（圆角/头像/时间戳/操作排）属 `ChatBubble`（provider 接线），preview
  以内容渲染面为「长回答」的可视锚——卡片说明行已如实标注。

## 审查挑战点预登记（给独立审查）

- **C1（候选）**：`StylePreviewFlowFrame.of` 的流步→文案映射把 F03 冻结表
  键写死在 seed 文件（`kExperienceCopyTable['...'] ?? ''`）——若 F03 表扩键/
  改值，此处不漂移（逐字消费），但**键名**拼错时 `?? ''` 会静默空白（测试
  断言了四条文案非空，但新增流步若拼错键不会红）。挑战点：是否应改为
  assert 键存在？现取「冻结表只读消费 + 测试钉四键」，未加运行时断言。
- **C2（候选）**：首页面 ProviderScope 按流步 ValueKey 重挂——审查者可
  质疑「重挂是否恰好违反验收 2 的不重启精神」。澄清：验收 2 的 run 指
  用户会话/数据 run（探针 + 流步 + prefs 三重断言钉死），面内组件按 seed
  重装配是 preview 的取证语义（每次推进 = 确定性重渲染），与 run 存活
  断言不冲突；若审查者主张面内也不得重挂，需给 Riverpod 动态覆写的替代
  实现并同证。
- **C3（候选）**：`settlePreview` 固定 700ms 两拍泵 vs `pumpAndSettle`——
  骨架 shimmer 无限动画使 settle 永不落定（产品真实行为）；固定拍长是否
  漏掉某个 >700ms 的单次动画（成功徽章 ≤650ms、主题过渡 280ms 均覆盖）？
  若审查环境发现更长的单次动画，请给具体组件与时长，测试拍长随之调整。
- **C4（候选）**：单面语义 dump 跨四档 sha256 恒等被引为「切主题不改语义」
  的自证——但该 dump 是元素树口径（RenderParagraph 文本 + 语义注解），
  不含颜色/对比度语义；「语义恒等」的强主张仅限结构/文案层。视觉层差量
  由 PNG 承载（四档各异），两层合证才是完整口径。
- **C5（候选）**：入口走 `Navigator.push(MaterialPageRoute)` 而非命名路由——
  有意不触 `app/routes.dart`（五 Tab 合同零触碰的最小实现）；代价是深链/
  路由级测试无法直达 preview 页（只能经 flag + push）。转正时若需要命名
  路由，属 routes.dart 的授权内增量（当时需重走五 Tab 合同评审）。
