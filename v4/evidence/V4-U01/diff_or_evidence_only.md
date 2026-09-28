# V4-U01 · diff_or_evidence_only

执行：wtU01（分支 `agent/v4/u01`，自 main@`e50107fe` 开出）· 2026-09-29 · mobile 单域增量，零 HEAVY、零模型调用、零 backend/gateway/proto/迁移触碰。**RF-06 三个组员冲突面（dashboard_screen / compact_status_bar / task_execution_screen）零 diff**；接续卡走 TodayCockpitCard 同款模式（新组件 + cockpit 卡内组合，ui-home 锁本卡独占）；五 Tab 路由合同零触碰；classic（preview off）零新增差量——像素通道零改动，style preview 面仅追加离线合同 override（preview 本体非产品面）。

## 设计（一句话）

首页接续 = cockpit 卡内新挂 `EpisodeResumeStrip`（读面 = I01 `episode_resume_view.v1` + I06 回执读面双真源组合、fail-closed）：fresh 视图时「上次/下一步」如实可见、主 CTA 标签收敛为「继续这一步」（**同一任务同一条既有跳转链路，只改标签不改目标**）；stale 视图只渲染不确定性说明、不接续（B05 §9 反例钉死）；无回执/无任务/视图降级 → 零渲染（零假历史）。

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **验收①「360 宽首屏有主 CTA，不靠滚动找下一步」基线已部分满足**：J-03 TodayCockpitCard 即首屏唯一主行动卡（V3 已落，不重建）。本卡差量 = 接续证据进首屏（「上次到哪+下一步」此前无处呈现）+ 新增整屏 360×800 装载回归钉（`360×800 整屏装载` 用例，主 CTA rect.bottom ≤ 800 断言）。
- **I01 视图如实消费**：读模型字段/词表/过期判定与 `backend/app/core/episode_resume_view.py` 逐字对齐（`kEpisodeResumeViewSchemaVersion` / `kResumeDegradeReasons` / TruthClass 五值 / `episodeResumeStaleReason` = `resume_view_stale_reason` 客户端可判定子集）。
- **不造第二权威**：零新表、零新端点、零本地持久化（视图退出即弃）；接续依据 ref 严格取 I06 读面 `selection_role == 'resume_view'` 的回执（拿 chat_context 等其他角色冒充接续依据 = 归因错置，不做——provider 反例测试钉死）。

## 交付物（语义命名）

| 文件 | 性质 | 说明 |
|---|---|---|
| `mobile/lib/features/home/data/episode_resume_models.dart` | 新增 | `episode_resume_view.v1` 移动端消费投影（fail-closed 解析 + 字段级降级 + 过期判定子集） |
| `mobile/lib/features/home/presentation/providers/episode_resume_provider.dart` | 新增 | 接续状态派生（回执读面 × today 选择流 × I01 端点；五门未过即 hidden） |
| `mobile/lib/features/home/presentation/widgets/episode_resume_strip.dart` | 新增 | 接续证据条（ready/stale/缺席三态如实渲染；纯文本零可点目标） |
| `mobile/lib/features/home/presentation/widgets/today_cockpit_card.dart` | 修改 | 卡内挂载 strip + 主 CTA 标签收敛（`continueStepFor` 同任务绑定 + 新鲜才收敛；stalled 态不收敛） |
| `mobile/lib/core/network/api_endpoints.dart` | 修改 | `episodeResumeTask(taskId)` 常量（I01 唯一 REST 入口） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + gen | 修改 | 5 词条（eyebrow/上次/下一步/stale 说明/继续 CTA），`flutter gen-l10n` 重生成 |
| `mobile/lib/core/design/style_preview/style_preview_faces.dart` | 修改 | preview 离线合同补钉（回执读面 off + growth 空态，零网络——F05 同一合同） |
| `mobile/test/features/home/dashboard_test_harness.dart` | 修改 | 回执读面钉 modeGated 确定性默认（存量基线 = 接续条如实缺席；用例经 extraOverrides 覆盖） |
| `mobile/test/widget/a11y_u08_state_semantics_test.dart` | 修改 | 同款零网络桩（断言强度不变，run 条语义用例原样） |
| 4 个测试文件 | 新增 | models 6 测 / provider 9 测 / 集成 7 测 / 证据 2 测 = 24 测（每验收面一正一反） |

## 与验收逐条对照（全部可失败）

1. **「360宽首屏有主CTA，不靠滚动找下一步」**
   - 正：`360×800 整屏装载` 用例（整屏 DashboardScreen，接续条在场）断言主 CTA rect.bottom ≤ 800 且 ensureVisible 后仍在视口；证据截图 `u01_resume_ready_360x800.png` 主 CTA 于首屏 y≈410。
   - 反：`反：stale 视图 → …主 CTA 照旧「先做这个/Start Here」`——stale 视图不得改写主行动（改写即红）。
2. **「新用户零假历史；回归有真last_step/可调整」**
   - 正：`正：新鲜视图 → 上次/下一步如实可见`（视图原文渲染，`Last time: 读完第三章前两节`）；「可调整」路径 = 既有 ghost 次级入口（/tasks 换任务）原样保留，接续不强制。
   - 反 ×3：回执 off（modeGated）→ 条缺席 + 零占位文案；无 nextAction 任务 → 零请求零渲染（provider 层）；视图降级 view=null → 缺席（不渲染半真视图）。
3. **「退出/重进不强制自动播放或重播成就」**
   - 正：`正：卸载重挂（等价退出重进）`——零导航、零 Dialog/SnackBar、内容纯静态复现、transientCallbackCount == 0（无 auto-play 遗留帧）。
   - 反（结构性）：接续条为纯静态文本（无 tap/无 timer/无动画状态机），代码面不存在自动播放路径；provider 全门均被动读面。

## 红线自证（diff 逐面）

- `git diff main -- mobile/lib/features/home/presentation/screens/dashboard_screen.dart mobile/lib/core/design/widgets/compact_status_bar*`（及 task_execution_screen）为空——三冲突面零触碰。
- 五 Tab：`mobile/lib/app/routes.dart` 零 diff；底部导航组件零 diff。
- classic 零差量：design_system.dart / theme_manager.dart / tokens_v2 零 diff；像素通道零 diff。
- 生成物：`mobile/lib/gen`（gitignored，实体复制，永不提交）零触碰；l10n 生成物经 `flutter gen-l10n` 官方通道再生成（arb 为源）。

## F03 反向面 / D01 曝光面处置

- 接续条为只读呈现面，零操作零成功面孔；「继续」走既有 `_startTask` 链路（activeTaskProvider → execute 路由），无新通道、无假成功。
- **D01 mark_seen 不接线的裁决**：D01 曝光记账唯一入口 `mark_seen` 要求 `receipt_ref` 必指 D-05 权威 exposed 回执（I2 双门）；首页接续条非 intervention record、无权威回执可指——造 ref 即违 I2（假曝光记录）。F03 消费面已就绪（`resume_available` kind 在 experience_event.v1 封闭词表），待 WS 帧下发面（contract-owner 单独合并）后自动生效。已登记 limitations + 审查挑战。
