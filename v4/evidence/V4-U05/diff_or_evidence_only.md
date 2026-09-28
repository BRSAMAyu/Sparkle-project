# V4-U05｜星图轨迹与证据详情视觉 · diff_or_evidence_only

执行：wtU05（分支 `agent/v4/u05`，自 main@`20f1d99f` 开出）· 2026-09-29 · 纯 mobile 增量，零 backend/proto/迁移/生成文件改动，无模型调用。

## 1. 一句话设计

**移动端消费 D04 数据面，把「能力证据」与「活动足迹」在星图轨迹与证据详情两面分开**：新增封闭四值通道词表（`capability_channel.dart`，消费后端 `capability.channel.v1`，fail-closed 未知线值=unknown 绝不升级为已检验）→ `GalaxyNodeModel` 解析 `user_status.mastery_evidence.capability_channel` + `projection_version` → 画笔视觉档唯一判定点 `resolveGalaxyStarVisualStyle`：**verified（独立检验）是唯一允许掌握档亮度/光晕/呼吸脉冲/双环标记的通道；practiced（练习过）与 non_human/trace_only/unknown 一律封顶 SHINING 档（fill ≤0.82、ring ≤0.38、零光晕零脉冲）**，环标记形状分层（双环=verified／单环=practiced／虚线=痕迹面）不依赖特效也可读；节点详情 sheet 新增「能力证据与来源」抽屉（通道用户语言+溯源行+投影版本，与节点轨迹同一图快照——「点开来源与投影 version 一致」由同源结构性保证）；读屏播报加通道如实后缀（高分练习存量不再被播报成已掌握）。

## 2. 可失败验收逐条（卡面原文 → 实现/证据；每面一正一反）

### 验收① 节点点开来源与投影 version 一致 — PASS

- **同源结构性保证**：`galaxy_screen._openNodeDetailSheet` 把 `node.capability` + `node.graphEventSources`（同一 `GalaxyGraphResponse` 快照）传入 sheet；`_CapabilityEvidenceSection` 只渲染这份快照，绝不与异步 `/history` 混渲——来源行、通道、版本三者同投影。
- **正例**：`node_detail_capability_section_test`（verified 节点：`独立检验通过` + `投影版本 v7` + 溯源行「独立测验/学习成果记录」如实映射）；`u05_evidence_test`（verified 抽屉截图+语义 dump，语义 txt 含「投影版本 v7」原文）。
- **反例**：同测（practiced 节点：`练习过 · 未独立检验` + `不代表已掌握` 文案，`独立检验通过` findsNothing；无版本数据 → `投影版本未知`，全树无编造的「投影版本 vN」）。

### 验收② 缩放按钮不遮挡主 CTA，键盘可选节点 — PASS（差量举证，不重写）

- 既有资产已满足：`galaxy_rail_cta_clearance_test`（V3-FIX-60 相机 rail 与主 CTA 避让锁）+ `galaxy_screen_keynav_test`（GALAXY-KEYNAV 方向键/Tab 图序遍历、Enter 激活、Esc 分层、焦点环同步）——本卡零触碰 `GalaxyControls`/焦点管理，全套随本卡增量复跑全绿（galaxy 套件 192 通过，见 test_results.json）。
- 本卡增量面同样键盘可达：来源抽屉为纯静态文本（无交互元素即无焦点陷阱），sheet 既有 CTA 焦点路径不变（`node_detail_sheet_test` 既有断言全绿）；200% 字体面由 `node_detail_capability_section_test`（200% 字泵无异常+关键文案可见）与既有 `context_receipt_panel` 同型纪律覆盖。

### 验收③ 不开特效仍理解全部信息，无数据不造进度 — PASS

- **形状承载通道身份（不依赖特效）**：verified=双环／practiced=单细环／痕迹面=虚线环（与 F02 `PixelStateOutline.dashed` 同语义）；封顶档 `glowAlpha=0` 时标记仍在——`capability_channel_visual_test`「反例：封顶档零特效时形状标记仍在」钉死。掌握档庆祝语言（≥85 光晕/呼吸脉冲/大光斑）只有 verified 通道触发（painter 三处调用点全部改走 `capability.claimsVerification` 门）。
- **PRACTICED 星绝不渲染为已掌握亮度（反例钉）**：`resolveGalaxyStarVisualStyle(mastery: 92, channel: practiced)` → fill=0.82 封顶、ring=0.38、glow=0、无脉冲无光晕；四态逐一钉（practiced/non_human/trace_only/unknown 各测）；verified 92 同分正例对照可达 0.94 掌握档。
- **无数据不造进度**：缺 `user_status`（gateway gRPC proto 形状/旧缓存）→ unknown + 无投影版本 + 视觉按未检验渲染（99 分存量也不进掌握档）；掌握度 ≤0 保持既有「尚未学习」诚实面；sheet 来源空 →「暂无来源记录」、词表外 source_type →「来源 · {原始码}」（不猜语义）、缺 source_type 行结构性剔除。

## 3. 交付物（真实路径）

| 文件 | 性质 | 内容 |
|---|---|---|
| `mobile/lib/features/galaxy/domain/capability_channel.dart` | 新（291 行） | 封闭四值词表 + `GalaxyCapabilityChannel.fromWire`（fail-closed）+ `GalaxyNodeCapabilityEvidence.fromJson`（快照解析）+ `resolveGalaxyStarVisualStyle`（视觉档唯一判定点，纯函数） |
| `mobile/lib/shared/entities/galaxy_model.dart` | 改 +11 | `GalaxyNodeModel.capability` 字段（fromJson/copyWith/构造） |
| `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart` | 改 | `_nodeStyle` 委托视觉档判定；脉冲/glow/光斑三处调用点接 `claimsVerification` 门；`_drawCapabilityRingMark`（双环/单环/虚线，lod≥l1） |
| `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` | 改 +282 | `_CapabilityEvidenceSection`（通道徽章+用户语言文案+溯源行+投影版本）+ `_CapabilitySourceRow`（封闭 source_type 词表映射+原始码回退）；`show`/widget 新参透传 |
| `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` | 改 +4 | `_openNodeDetailSheet` 传 `capability` + `graphEventSources`（同快照同源） |
| `mobile/lib/features/galaxy/data/services/galaxy_accessibility_service.dart` | 改 +22 | `getNodeSemanticLabel` 通道如实后缀（`_channelSemanticSuffix`） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + 生成 dart ×3 | 改 +44 键 | 能力面/溯源行/投影版本/读屏后缀双语词表 |
| `mobile/test/...`（4 新 + 1 改） | 测试 | 见 test_results.json |

## 4. 验收对照之外的边界守护

- **五 Tab 零触碰**：diff 无 `app/routes.dart`/`shell_navigation.dart`。
- **RF-06 冲突面零触碰**：冲突清单三文件（dashboard_screen/compact_status_bar/task_execution_screen，F04 证据登记口径）不在 diff；galaxy_screen 不在任何组员在改清单。
- **classic 零差量**：`core/design/` 零 diff（无像素主题/令牌/组件新增）；来源抽屉用标准 DS 组件（`DS.surfacePanel`/`borderSubtle`/语义色槽），无 pixel 装饰面引入。
- **backend 只消费不新造**：零 backend diff；消费面 = D04 已合并的图响应字段（`capability_channel`/`projection_version`/`graph_event_sources`），无新读面 API。
- **不碰 .env/proto/迁移/生成文件**：`mobile/lib/gen`、`backend/app/gen` 为 gitignored 实体复制（自主检出复制，未入库、未手改）。
- **`tool/openclaw_connection_smoke.dart` 既有 analyze 报错**：main 同样存在（开卡前既有），本卡零触碰。

## 5. 突变注入（可失败性实证；一审 R1-C2 订正版）

- **M1 通道门旁路**（`resolveGalaxyStarVisualStyle` 中 `!verified` 分支改恒 false，即练习星放行掌握档）：`capability_channel_visual_test.dart` **7 失败**（practiced 92 封顶钉 + 四态逐一钉 + 无数据 99 分钉；实现自述误记 6，一审独立重放 +10 -7 亲跑 7）——还原后 sha256 恒等（ab92ae25…）全绿。
- **M2 同源断链**（可复现形式 = sheet 内 `_historyBody` 掐断 `graphEventSources:` 透传）：`node_detail_capability_section_test` verified 正例溯源行 **1 失败**——还原后全绿。（订正：实现自述的「`_openNodeDetailSheet` 不传 `graphEventSources` 被该测 2 失败捕获」不可复现——该测直构 sheet 不经过 galaxy_screen，字面突变后仍 6/6 全绿；screen→sheet 接线缺口由 R1-C1 整改补钉。）
- **M3 screen→sheet 同源接线旁路**（R1-C1 整改自验，2026-09-28：`_openNodeDetailSheet` 传 `capability: null` + `graphEventSources: const []`）：`galaxy_screen_sheet_wiring_test` **1 失败**（抽屉退化为 unknown 面，「独立检验通过」断言红）——还原后 galaxy_screen.dart sha256 恒等（0cc8b42b…），新测全绿。此突变类在补钉前无任何测试可捕获（即 R1-C1 缺口本体）。
