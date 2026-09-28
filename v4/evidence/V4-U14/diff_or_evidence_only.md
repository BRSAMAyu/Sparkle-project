# V4-U14 · 差量说明（diff_or_evidence_only）

任务卡：`v4/04_tasks/tasks.json` → `V4-U14`（设置、通知与所有异常表面）
分支：`agent/v4/u14`（worktree `../wtU14`，自 main@9b5e614d 开出；不 push）

## 1. 差量裁决总表（no_duplicate_rule 差量举证）

卡目标四件事逐一裁决——已存在者只举证不重写，缺口者实现：

| 卡面 | 既有事实（证据位置） | U14 裁决 |
|---|---|---|
| 主题 preview | F05 已交付 `StylePreviewEntry`（`AppFeatureFlags.enableStylePreview` 默认 false 门、发布面零差量、切档走 F01 `ThemeManager.setPixelPreviewProfile` 唯一入口），挂「我的」页开发者入口；测试钉死 `test/core/design/style_preview/` | **EVIDENCE_ONLY**（引用 F05 证据；本卡零触碰，不换发布默认主题） |
| 系统减少动态约束力 | F06 已交付 `composeDisableAnimations`（system ∨ in-app 叠加律）于 app 壳 MediaQuery 组装（`lib/app/app.dart`），唯一权威实现+测试在 `accessibility_composition_test.dart` | **EVIDENCE_ONLY**（引用 F06 证据；本卡零触碰） |
| 动效独立偏好 | F06 `AccessibilitySettings.reduceMotion`（本地持久化 + 服务端同步） | **EVIDENCE_ONLY** |
| 触觉独立偏好 | `SensoryFeedbackService.haptic_enabled`（持久化）+ F06 `hapticFeedback` 同步链 | **EVIDENCE_ONLY** |
| 提示音 vs 背景声独立 | **缺口**：单一 `sound_enabled` 同时门控提示音池与背景声（`_setSoundEnabled(false)` 连带停背景声；`playAmbient` 查 `isSoundEnabled`） | **实现**（D1，见 §2.1） |
| 通知落真实对象 / 已删对象面 | **缺口**：`/tasks/:id/execute` 路由完全忽略 `:id`，执行屏只渲染 `activeTaskProvider` 残留快照——已删深链 → 渲染错误任务或泛化空面 | **实现**（D4，见 §2.3） |
| 权限拒绝只降该能力 | 录音：voice 输入已有降级+权限引导对话框（`showAppPermissionDialog`），文本输入不受影响 | **部分已有 + 补强**（D3：永久拒绝分类上浮） |
| 声音系统拒绝播放降级 | **缺口**：播放异常静默吞掉、逐事件重试、降级状态不可见 | **实现**（D2，见 §2.2） |
| 统一异常面（404/离线/登录失效分开） | N16 `error_lexicon` 判定单源已建立；SCREEN_FAMILIES 要求的深链空对象面缺失 | **实现**（D4 配套：`ObjectUnavailableSurface`） |

## 2. 实现差量（本卡新增/修改）

### D1 · 背景声独立偏好（卡验收 1）
- `lib/core/services/sensory_feedback_service.dart`
  - 新键 `sensory_feedback.ambient_enabled`；`isAmbientEnabled()`：键未落时**继承** `sound_enabled`（向后兼容：老用户关了提示音，背景声不被升级悄悄打开），显式切换后即独立。
  - `setAmbientEnabled(false)` 停背景声（保留场景选择供重开）；`true` **不自动续播**（遵守「默认不自动播放；重开不自行续播」）。
  - `_setSoundEnabled(false)` 只停提示音池，不再连带停背景声；`playAmbient` 门控改查 `isAmbientEnabled()`。
  - 开提示音不再连带续播背景声（独立性；此前行为是 resume saved scene）。
- `lib/features/user/presentation/screens/unified_settings_screen.dart`
  - 感官反馈区新增「背景声」独立开关（key `sensory-ambient-toggle`）；背景场景/音量控件门控从 `_soundEnabled` 改为 `_ambientEnabled`（关闭时置灰——选中但不播是不诚实的中间态）。
- l10n（arb 源 + gen-l10n 再生，**纯增量、不删既有键**）：`sensoryAmbientEnabledTitle/Subtitle`；订正 `sensorySoundSubtitle` 文案（「所有音效与环境音将静默」在独立后不再属实；键保留）。

### D2 · 音频诚实降级（卡验收 2 机制面，MOTION「系统拒绝播放时降级静音并保持任务正常」）
- `SensoryFeedbackService`：非缺资产类播放失败计入连续失败，达阈值（2）置 `audioPlaybackDegraded`；降级后提示音不再逐事件重试（不连锁蜂鸣），触觉/视觉/任务流不受影响；`setSoundEnabled(true)`（用户显式动作）清除降级位=显式重试。
- 统一设置面降级提示行（key `sensory-audio-degraded-notice`）：如实呈现「系统拒绝了音频播放，提示音已静音降级；任务与提醒不受影响」，不伪造正常。

### D3 · 录音权限分类上浮（卡验收 2）
- `lib/features/chat/presentation/providers/voice_input_provider.dart`：`checkPermissions()` 记录 `isPermanentlyDenied`（系统设置层永久拒绝，去设置才可恢复），区别于本次拒绝；`reset()` 复位。既有降级事实保持：拒绝只影响语音模态，文本输入与聊天目标不堵（本卡测试钉 provider 可复位复用）。

### D4 · 任务深链闸 + 统一空对象面（卡验收 3）
- 新 `lib/features/task/presentation/screens/task_execution_deep_link_gate.dart`：
  - 快路径：active 已是目标 id → 零仓储调用透传执行屏（应用内既有路径零差量，测试钉 `getTaskCalls==0`）；
  - 本地列表缓存命中 → 设 active 进执行屏（离线/本地任务真实落点）；
  - 服务端 id → 仓储 `getTask` 确证：命中 → 落真实对象；404 类确证（lexicon `notFound`）→「已删除或不存在」面；**无法确认**（网络/超时/服务端/未分类）→「暂时无法确认」可重试面（绝不凭空宣布已删除）；判定一律走 `error_lexicon.dart` 单一 owner（N16：新域禁建私有映射）；
  - 本地-only id → 刷新本地列表后再查，仍无 → 已删除面。
- 路由接线 `lib/features/task/task_routes.dart`（非 RF-06 冲突面）：execute 路由改经闸；`missingReplacementRoute` 传 `TaskRoutes.home`。
- 新 `lib/core/design/widgets/object_unavailable_surface.dart`：`ObjectUnavailableKind{missing, offline, auth}` 三语义分开呈现（SCREEN_FAMILIES：「404/离线/登录失效与模型失败不同，不全部跳通用错误页」）；恒在回首页兜底出口；DS 令牌 + l10n；失效深链出口用 `go` 不入返回栈。
- l10n 增量：`objectUnavailableMissingTitle/Body`、`objectUnavailableOfflineTitle/Body`、`objectUnavailableGoTasks`、`objectUnavailableBackHome`。

## 3. 明确不做（边界）
- 不触碰 RF-06 三冲突面（dashboard_screen / compact_status_bar / task_execution_screen）——`git diff --name-only` 自证（见 run_manifest.commands）。
- 不动 tokens_v2/theme 通道、不改发布默认主题、不动 F05 preview flag 默认值。
- 不改既有认证/授权检查；不动 backend API 面（零 `backend/app/api/` 触碰 → 无 OpenAPI/BA-ROUTES 同步义务）。
- 不重写 F05/F06 已交付行为（见 §1 举证）。


## 一审勘误与登记（receipt 5cab258e）
- 数字订正：新测实数 **21**（9+3+2+5+2）非自述 19——实现方自列 breakdown 求和即 21，少报非夸大，以 receipt 为准。
- CH-3：limitations 引用的 manifest sha256 未随 L9 提交刷新（时点核对一致，锚失同步）——本勘误节即补注。
- CH-1（路由接线无测试钉）/CH-2（playAmbient 门拒后 _currentScene 残留，基线同构 release-only）→FIX-570 后续卡承接。
