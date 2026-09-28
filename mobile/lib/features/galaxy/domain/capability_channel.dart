/// V4-U05 · 星图能力通道移动端词表与视觉分层（纯函数、零 IO）。
///
/// 设计真源（不另立第二真相）：
/// - **后端词表唯一权威** = D04 `backend/app/services/galaxy/capability_channel.py`
///   （`capability.channel.v1` 封闭四值：verified/practiced/non_human/trace_only）。
///   本文件只做**消费面**：把 `user_status.mastery_evidence.capability_channel`
///   线值解析成封闭词表，任何未知线值 fail-closed 归 [GalaxyCapabilityChannel.unknown]
///   ——绝不把「数据没说」升级成「已检验」。
/// - **视觉语义** = SCREEN_FAMILIES 星图家族「星图是一张可探索的证据路径……
///   不开特效仍理解全部信息，无数据不造进度」+ D04「练习过≠检验通过；
///   spark 纯时长=活动痕迹；亮度保留存量分数=参与足迹」。
///
/// 视觉分层合同（形状区分，不依赖特效/发光也能读）：
///
/// | 通道          | 环标记           | 亮度上限         | 脉冲/光晕（特效面） |
/// |---------------|------------------|------------------|---------------------|
/// | verified      | 双环             | 按分数可达掌握档 | 允许（唯一）        |
/// | practiced     | 单细环           | 封顶 SHINING 档  | 永不                |
/// | non_human     | 虚线环           | 封顶 SHINING 档  | 永不                |
/// | trace_only    | 虚线环           | 封顶 SHINING 档  | 永不                |
/// | unknown(无数据)| 虚线环          | 封顶 SHINING 档  | 永不                |
///
/// 「PRACTICED 星绝不渲染为已掌握亮度」由此处 `allowsMasteredBrightness`
/// 唯一判定：只有 `verified` 为 true（含 legacy 高分存量——参与足迹亮度封顶
/// 在 SHINING 档，与后端 D04 标签封顶同口径）。
library;

/// 星图能力通道（消费 D04 后端封闭四值 + 客户端 fail-closed unknown）。
enum GalaxyCapabilityChannel {
  /// 独立检验通过（唯一允许掌握档视觉/能力声称）。
  verified,

  /// 练习过（真实人类参与，未独立检验；参与足迹可见，不声称掌握）。
  practiced,

  /// Agent 产物（不计人类能力；只留溯源）。
  nonHuman,

  /// 仅活动痕迹（纯时长 / demo / 估计；只留痕迹）。
  traceOnly,

  /// 数据面未提供或线值不可识别（fail-closed：不声称任何能力）。
  unknown,

  ;

  /// 该通道是否允许「已掌握」档视觉（光晕/脉冲/掌握档亮度）。
  /// 唯一真通道 = verified；反例钉（PRACTICED 高分存量绝不进该分支）。
  bool get allowsMasteredBrightness => this == GalaxyCapabilityChannel.verified;

  /// 后端 D04 线值 → 词表（未知线值 fail-closed unknown，不抛异常）。
  static GalaxyCapabilityChannel fromWire(Object? raw) {
    switch (raw?.toString()) {
      case 'verified':
        return GalaxyCapabilityChannel.verified;
      case 'practiced':
        return GalaxyCapabilityChannel.practiced;
      case 'non_human':
        return GalaxyCapabilityChannel.nonHuman;
      case 'trace_only':
        return GalaxyCapabilityChannel.traceOnly;
      default:
        return GalaxyCapabilityChannel.unknown;
    }
  }
}

/// 节点级能力证据投影（从图响应 `user_status` 快照解析；只读呈现面）。
///
/// 与节点轨迹同源：同一份 `GalaxyGraphResponse` 快照解析出的通道、
/// `projection_version` 与溯源行，来源抽屉呈现的就是这份快照——
/// 「节点点开来源与投影 version 一致」由同快照结构性保证。
class GalaxyNodeCapabilityEvidence {
  const GalaxyNodeCapabilityEvidence({
    this.channel = GalaxyCapabilityChannel.unknown,
    this.hasChannelData = false,
    this.projectionVersion,
    this.evidenceCount,
    this.isLegacyEstimate,
  });

  /// 从图响应节点 JSON 解析（`user_status.mastery_evidence` + `projection_version`）。
  ///
  /// 缺 `user_status` / 缺 `mastery_evidence`（旧缓存、gateway gRPC proto 形状）→
  /// `hasChannelData=false` + unknown：fail-closed，视觉按「未检验」渲染，
  /// 不伪造检验状态。
  factory GalaxyNodeCapabilityEvidence.fromJson(Map<String, dynamic> nodeJson) {
    final userStatus = nodeJson['user_status'];
    if (userStatus is! Map<String, dynamic>) {
      return const GalaxyNodeCapabilityEvidence();
    }
    final masteryEvidence = userStatus['mastery_evidence'];
    final evidenceMap = masteryEvidence is Map<String, dynamic>
        ? masteryEvidence
        : const <String, dynamic>{};
    final channelRaw = evidenceMap['capability_channel'];
    final rawEvidenceCount = evidenceMap['evidence_count'];
    return GalaxyNodeCapabilityEvidence(
      channel: GalaxyCapabilityChannel.fromWire(channelRaw),
      hasChannelData: channelRaw != null,
      projectionVersion: (userStatus['projection_version'] as num?)?.toInt(),
      evidenceCount: rawEvidenceCount is num ? rawEvidenceCount.toInt() : null,
      isLegacyEstimate: evidenceMap['is_legacy_estimate'] as bool?,
    );
  }

  /// 通道（未提供数据时 = unknown）。
  final GalaxyCapabilityChannel channel;

  /// 数据面是否真实提供了通道字段（false = 无数据，诚实降级）。
  final bool hasChannelData;

  /// 投影版本（D04：user_node_status.revision 透传；撤回重算 +1 新 version）。
  /// null = 数据面未提供（诚实显示「未知」，不编造版本号）。
  final int? projectionVersion;

  /// 真实证据计数（D02/D04 evidence_count；null = 未提供）。
  final int? evidenceCount;

  /// 掌握度是否为 legacy 时间估算（null = 未提供）。
  final bool? isLegacyEstimate;

  /// 节点是否声称「已独立检验」（唯一允许掌握视觉/能力措辞的通道）。
  bool get claimsVerification => channel.allowsMasteredBrightness;
}

/// 星图节点环标记（形状区分维；不开特效也能读）。
enum GalaxyStarRingMark {
  /// 无标记（锁定节点沿用既有虚线问号语言）。
  none,

  /// 单细环 = 练习过/未检验档（参与足迹）。
  single,

  /// 双环 = 独立检验通过（唯一掌握档标记）。
  double,

  /// 虚线环 = 仅痕迹/Agent 产物/通道未知（边界不确定性可视化，
  /// 与 F02 PixelStateOutline.dashed 同语义）。
  dashed,
}

/// 星图节点视觉档（`StarMapPainter._nodeStyle` 的纯函数消费面）。
class GalaxyStarVisualStyle {
  const GalaxyStarVisualStyle({
    required this.fillAlpha,
    required this.masteryRingAlpha,
    required this.glowAlpha,
    required this.coreAlpha,
    required this.ringMark,
    required this.allowMasteredPulse,
    required this.allowMasteredHalo,
  });

  final double fillAlpha;
  final double masteryRingAlpha;
  final double glowAlpha;
  final double coreAlpha;
  final GalaxyStarRingMark ringMark;
  final bool allowMasteredPulse;
  final bool allowMasteredHalo;
}

/// SHINING 档上限（未检验节点亮度封顶——与后端 D04 `_calculate_status`
/// 的 80+ 封顶 SHINING 同口径：参与足迹可见，绝不进掌握档）。
const double kGalaxyUnverifiedFillAlphaCap = 0.82;
const double kGalaxyUnverifiedRingAlphaCap = 0.38;
const double kGalaxyUnverifiedCoreAlphaCap = 0.28;

/// 星图节点视觉档解析（纯函数；painter 与测试共用唯一判定点）。
///
/// - 未解锁：锁定档（低透明度 + 无环标记；虚线问号语言由 painter 既有分支画）。
/// - verified：按分数走既有四档（含掌握档 0.94/0.72/光晕），环标记 = 双环。
/// - 其余一切通道（含 unknown）：亮度封顶 SHINING 档（fill ≤0.82、
///   ring ≤0.38、无光晕、无脉冲），环标记按通道分层（单环/虚线环）。
GalaxyStarVisualStyle resolveGalaxyStarVisualStyle({
  required bool isUnlocked,
  required num masteryScore,
  required GalaxyCapabilityChannel channel,
  bool isDragging = false,
}) {
  if (!isUnlocked) {
    return const GalaxyStarVisualStyle(
      fillAlpha: 0.22,
      masteryRingAlpha: 0,
      glowAlpha: 0,
      coreAlpha: 0.12,
      ringMark: GalaxyStarRingMark.none,
      allowMasteredPulse: false,
      allowMasteredHalo: false,
    );
  }

  final verified = channel.allowsMasteredBrightness;
  final ringMark = switch (channel) {
    GalaxyCapabilityChannel.verified => GalaxyStarRingMark.double,
    GalaxyCapabilityChannel.practiced => GalaxyStarRingMark.single,
    GalaxyCapabilityChannel.nonHuman ||
    GalaxyCapabilityChannel.traceOnly ||
    GalaxyCapabilityChannel.unknown =>
      GalaxyStarRingMark.dashed,
  };

  final score = masteryScore.toDouble();
  double fillAlpha;
  double masteryRingAlpha = 0;
  double glowAlpha = 0;
  var coreAlpha = 0.18;
  var verifiedMasteredTier = false;

  if (score < 30) {
    fillAlpha = 0.32;
    masteryRingAlpha = 0;
  } else if (score < 60) {
    fillAlpha = 0.58;
    masteryRingAlpha = 0;
    coreAlpha = 0.24;
  } else if (score < 85) {
    fillAlpha = 0.82;
    masteryRingAlpha = 0.38;
    coreAlpha = 0.28;
  } else {
    fillAlpha = 0.94;
    masteryRingAlpha = 0.72;
    glowAlpha = 0.18;
    coreAlpha = 0.34;
    verifiedMasteredTier = true;
  }

  if (!verified) {
    // 反例钉落点：legacy/练习高分存量封顶 SHINING 档，绝不进掌握档
    // （fill ≤0.82、ring ≤0.38、无光晕、无脉冲——与后端 D04 标签封顶同口径）。
    return _capped(
      fillAlpha: verifiedMasteredTier ? kGalaxyUnverifiedFillAlphaCap : fillAlpha,
      ringAlpha:
          verifiedMasteredTier ? kGalaxyUnverifiedRingAlphaCap : masteryRingAlpha,
      coreAlpha: verifiedMasteredTier ? kGalaxyUnverifiedCoreAlphaCap : coreAlpha,
      ringMark: ringMark,
      isDragging: isDragging,
    );
  }

  if (isDragging) {
    fillAlpha = 0.88;
    masteryRingAlpha = masteryRingAlpha < 0.46 ? 0.46 : masteryRingAlpha;
    glowAlpha = glowAlpha < 0.14 ? 0.14 : glowAlpha;
    coreAlpha = coreAlpha < 0.28 ? 0.28 : coreAlpha;
  }
  return GalaxyStarVisualStyle(
    fillAlpha: fillAlpha,
    masteryRingAlpha: masteryRingAlpha,
    glowAlpha: glowAlpha,
    coreAlpha: coreAlpha,
    ringMark: ringMark,
    allowMasteredPulse: true,
    allowMasteredHalo: true,
  );
}

GalaxyStarVisualStyle _capped({
  required double fillAlpha,
  required double ringAlpha,
  required double coreAlpha,
  required GalaxyStarRingMark ringMark,
  required bool isDragging,
}) {
  var cappedFill = fillAlpha;
  var cappedRing = ringAlpha;
  var cappedCore = coreAlpha;
  if (isDragging) {
    cappedFill = 0.88.clamp(0.0, kGalaxyUnverifiedFillAlphaCap);
    cappedRing = cappedRing < 0.46 ? 0.46 : cappedRing;
    cappedCore = cappedCore < 0.28 ? 0.28 : cappedCore;
  }
  return GalaxyStarVisualStyle(
    fillAlpha: cappedFill,
    masteryRingAlpha: cappedRing,
    glowAlpha: 0,
    coreAlpha: cappedCore,
    ringMark: ringMark,
    allowMasteredPulse: false,
    allowMasteredHalo: false,
  );
}
