# V4-S02 · 差量裁决（diff or evidence-only）

**分支**：`agent/v4/s02`（自 main@dce840da 开出，不 push）
**性质**：实现差量（非 evidence-only）——本卡验收 1/2 的机制面仓库未满足，按卡实现最小增量。

## 一句话设计

音频焦点状态机（`AudioFocusController`，策略权威、零播放路径）+ 提示音独立音量 + 运行时合法资产门（消费 S04 账本判定面），由既有唯一播放执行面（`SensoryFeedbackService` 提示音池/环境床、`TtsService`、`AudioRecordingService`）消费裁决——不造第二播放权威。

## 实现差量（新增 2 文件）

### `mobile/lib/core/services/audio_focus_controller.dart`（新）
- 状态机与 MOTION §音频焦点状态逐一对应：`IDLE→USER_PLAYING→DUCKED_BY_TTS / PAUSED_BY_RECORDING / PAUSED_BY_CALL / STOPPED_BY_USER`。
- 策略输出：`promptsSuppressed`（录音/通话 → 提示音全抑制）、`ambientFactor`（TTS duck ×0.25；暂停/停止 ×0）、`ambientPausedTemporarily`（瞬时抢占可恢复语义）。
- 恢复语义按平台惯例：录音/通话结束恢复到抢占前会话态（Android 瞬时焦点失而复得 / iOS AVAudioSession interruption-shouldResume 惯例的调用级实现）；**耳机拔出 → STOPPED_BY_USER，任何抢占结束都不自续**（不转扬声器大声续播）；多抢占并存时最后一个结束才裁决。
- **重开不自续**：会话态是进程内的，不持久化——冷启动恒 IDLE，只有用户显式点播（选场景/开始专注）才进入 USER_PLAYING（与 U14「开启开关不自动续播」语义对齐并下探一层）。
- 录音/通话期间的点播请求被拒（返回 false）——录音不回录背景床。
- 监听面异常不反噬（呈现策略异常不伤任务流）。

### `mobile/lib/core/services/audio_asset_gate.dart`（新）
- `kLicensedAudioAssets`：账本 APPROVED∩ship 音频集（28 UI 提示音 + 5 环境床）的**消费镜像**（与 F03 文案表镜像 backend 表同一模式）。
- `audio_asset_gate_s02_test.dart` 读 `mobile/assets/asset_ledger.json` **原文**逐键双向对账（门缺键=误伤合法资产红；门有私货=自造权威红；数量不等红）——单一权威仍是账本，本门只是运行时消费面。
- 反例钉：PROPOSED 的 curated BGM（10 条商用录音许可未证实，S04 已隔离于发布面）运行时同样必被拒；未知路径缺省拒绝。
- 「不合法资产不进 bundle」的打包面拦截是 S04 守卫 L003/L004（本卡跑通 88 守卫实证 `proposed 全部隔离于发布面`），本门是播放路径的对偶纵深：**未证实许可就不播出**。

## 实现差量（修改 4 文件）

### `mobile/lib/core/services/sensory_feedback_service.dart`
- **提示音独立音量**（S02 新键 `sensory_feedback.sfx_volume`，默认 1.0）：与 U14 的环境音量键（`ambient_volume`）构成「环境/提示音两独立音量」；每事件规格音量 × 用户音量合成于 `_playSound` 单点；互不连带（键级隔离钉）。
- **默认关闭（卡验收1）**：`sound_enabled` 缺省 true→false；`ambient_enabled` 键未落缺省 false（U14 的继承机制替换为更强的绝对缺省——U14 保护意图「老用户不被升级悄悄打开」不减反增）。
- **焦点消费**：`emit()` 增 `!promptsSuppressed`（录音不回录提示音）；`init()` 订阅焦点裁决 → 环境床 duck/暂停/恢复/停止单点执行（`_applyAudioFocusDecision`）；`playAmbient` 增合法资产门 + 显式点播会话登记（抢占期点播被拒）；`resumeAmbient` 在 STOPPED_BY_USER 拒绝自续；`setAmbientVolume` 输出 = 用户音量 × 焦点系数（duck 期间调音量不越权放大）。
- **dispose** 解绑焦点监听（测试冷启动等价）。

### `mobile/lib/core/services/tts_service.dart`
- speak/完成/取消/出错/stop/dispose 接入焦点：`beginTts()/endTts()`（USER_PLAYING→DUCKED_BY_TTS→复原），TTS 抢占期间环境床压低不消除（「TTS可duck/暂停环境床」）；无播放会话时 TTS 不造会话。

### `mobile/lib/features/chat/data/services/audio_recording_service.dart`
- 麦克风真实开流成功 → `beginRecording()`（PAUSED_BY_RECORDING，全输出抑制）；清理/停止 → `endRecording()`（幂等）。三处录音入口（聊天语音按钮/统一 omni bar/voice provider）共享本单点接线。

### `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`
- 新增提示音音量滑杆（`sensory-sfx-volume`）：随提示音开关置灰（关了提示音还能调音量是不诚实的中间态）；调整只写 sfx 轴，不触碰环境音量。

### l10n
- `app_zh.arb`/`app_en.arb` 纯增量 1 键 `sensorySfxVolumeTitle`（提示音音量）+ `flutter gen-l10n` 再生 ×3 生成文件；未手改生成物。

## Evidence-only 引证面（不重写）

- **BGM 运行时许可过滤**：`BgmService` 的 `releaseApproved` 过滤（bgm_service.dart:2594）已由 S04 落地，本卡差量举证引用之（L006 守卫 + bgm_catalog releaseApproved=false 全 10 条 curated），不在 BGM 上叠第二道门。
- **「重开不自续」的启动面**：现有启动路径本无 ambient 自动播放钩子（U14 已断言 setAmbientScene 无 autoplay 副作用）；本卡加钉的是焦点会话语义（进程内不持久化）+ 服务面「重开零自动播放」调用级断言，未改启动代码。
- **触觉/视觉通道**：F03 适配器与触觉偏好面零触碰；验收 2 的抑制只作用于声音输出（触觉与任务流恒不受影响，测试钉）。

## 边界自证

- RF-06 三冲突面（dashboard_screen / compact_status_bar / task_execution_screen）、`app/routes.dart`、tokens_v2/theme 通道：零触碰。
- 音量/偏好持久键全部仍归 SensoryFeedbackService 单源（新键 `sfx_volume` 也在其中）；无第二权威。
- 未新增任何 pubspec 依赖/平台通道（复用既有 audioplayers/flutter_tts/record；vendored third_party_plugins 无音频插件可复用，故零新平台面）。
- 生成文件：`lib/gen/` l10n 经 `flutter gen-l10n` 再生（arb 源纪律）；未触碰 `*/gen/` 其余生成物与 SQLC/Alembic 面。
- 全仓守卫 88 rules PASS（含 V4S04-ASSETS：ledger=49 approved=38 proposed=11 隔离如常）。
