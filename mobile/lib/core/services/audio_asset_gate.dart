/// V4-S02 · 音频合法资产门（消费 V4-S04 许可账本判定面，不造第二权威）。
///
/// 合同（卡规格 + `v4/02_design/MOTION_AUDIO_HAPTICS.md` §声音设计）：
/// 「音频资产需原作者/授权、来源、是否可商用/修改/分发、归属与哈希；
/// 未证实许可就不打包上线。」——「不进 bundle」由 S04 守卫
/// （scripts/guards/check_asset_release_surface.py L003/L004）在打包面强制；
/// 本门是**运行时消费面**：即使异常打包，音频播放路径也拒绝无许可资产，
/// 静默降级（账本 fallback=silent），任务流恒不受影响。
///
/// 权威与消费关系（不造第二权威）：
/// - 唯一权威仍是 `mobile/assets/asset_ledger.json`（status=APPROVED 且
///   ship_in_product=true 才可播）；
/// - 本文件内的 [kLicensedAudioAssets] 是账本 APPROVED∩ship 音频集的**消费
///   镜像**（与 F03 文案表镜像 backend 表同一模式），由
///   `audio_asset_gate_s02_test.dart` 逐键对账（读账本原文比对 + 反例钉：
///   PROPOSED 资产必被拒）——单边漂移即红。
library;

/// 账本 APPROVED ∩ ship_in_product 的音频资产集（键 = 账本 asset_id，
/// 与 SensoryFeedbackService/AmbientScene 的播放路径同命名空间）。
///
/// 当前 = 28 个 UI 提示音 + 5 个环境床（全部 internal_original，S04 账本
/// 逐条六要素齐全）。PROPOSED 的 curated BGM（10 条商用录音许可未证实）
/// **不在**本集——它们同样被 bgm_catalog 的 releaseApproved=false 过滤
/// （BgmService 运行时面）与本门双重拦截。
const Set<String> kLicensedAudioAssets = <String>{
  // ── UI 提示音（assets/audio/ui/）───────────────────────────────────────
  'audio/ui/achievement_common.ogg',
  'audio/ui/achievement_epic.ogg',
  'audio/ui/achievement_legendary.ogg',
  'audio/ui/achievement_rare.ogg',
  'audio/ui/ai_start.ogg',
  'audio/ui/card_flip.ogg',
  'audio/ui/checkin.ogg',
  'audio/ui/complete.ogg',
  'audio/ui/confirm.ogg',
  'audio/ui/dialog_open.ogg',
  'audio/ui/drag_drop.ogg',
  'audio/ui/drag_start.ogg',
  'audio/ui/error.ogg',
  'audio/ui/focus_complete.ogg',
  'audio/ui/message_send.ogg',
  'audio/ui/nav.ogg',
  'audio/ui/off.ogg',
  'audio/ui/on.ogg',
  'audio/ui/select.ogg',
  'audio/ui/sheet_open.ogg',
  'audio/ui/star_unlock.ogg',
  'audio/ui/streak.ogg',
  'audio/ui/success.ogg',
  'audio/ui/tap.ogg',
  'audio/ui/toggle.ogg',
  'audio/ui/warning.ogg',
  'audio/ui/button1.ogg',
  'audio/ui/button2.ogg',
  // ── 环境床（assets/audio/ambient/）─────────────────────────────────────
  'audio/ambient/cafe.ogg',
  'audio/ambient/ocean_waves.ogg',
  'audio/ambient/piano.ogg',
  'audio/ambient/rain.ogg',
  'audio/ambient/white_noise.ogg',
};

/// 音频合法资产门：播放前的最后一道许可裁决（运行时消费面）。
abstract final class AudioAssetGate {
  /// 该音频资产是否已获许可（账本 APPROVED ∩ ship_in_product）。
  ///
  /// 未知路径一律 false（缺省拒绝——「未证实许可就不打包上线」的播放面
  /// 对偶：未证实许可就不播出）。
  static bool isLicensed(String assetPath) =>
      kLicensedAudioAssets.contains(assetPath);

  /// 已许可资产的路径原样返回；未许可返回 null（调用方静默跳过，
  /// 账本 fallback=silent 语义）。
  static String? licensedPathOrNull(String assetPath) =>
      isLicensed(assetPath) ? assetPath : null;
}
