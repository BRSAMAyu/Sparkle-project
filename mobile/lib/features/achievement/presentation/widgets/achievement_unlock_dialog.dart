import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart'
    as chat;
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

enum _AchievementUnlockActionState {
  idle,
  closing,
  sharing,
  navigating,
}

/// 成就解锁弹窗
///
/// 显示成就解锁动画，根据稀有度显示不同视觉效果
class AchievementUnlockDialog extends StatefulWidget {
  const AchievementUnlockDialog({
    required this.event,
    super.key,
    this.onShare,
    this.onViewRewards,
    this.onClose,
    this.comboCount,
    this.milestoneInfo,
  });

  /// 接受AchievementUnlockEvent (来自achievement_model.dart)
  final AchievementUnlockEvent event;
  final VoidCallback? onShare;
  final VoidCallback? onViewRewards;
  final VoidCallback? onClose;

  /// 成就连击数量 (P1功能)
  final int? comboCount;

  /// 里程碑信息 (P1功能)
  final MilestoneInfo? milestoneInfo;

  /// 从WebSocket事件创建弹窗
  static Future<void> showFromWsEvent(
    BuildContext context,
    chat.AchievementUnlockEvent wsEvent, {
    VoidCallback? onShare,
    VoidCallback? onViewRewards,
    bool barrierDismissible = true,
    int? comboCount,
    MilestoneInfo? milestoneInfo,
  }) {
    final event = wsEvent.toUnlockModel();
    return show(
      context,
      AchievementUnlockEvent(
        achievementId: event.achievementId,
        name: event.name,
        rarity: event.rarity,
        unlockedAt: event.unlockedAt,
        isFirst: event.isFirst,
        visualEffect: event.visualEffect,
        visualEffectType: event.visualEffectType,
        rewards: event.rewards,
        rewardPreview: event.rewardPreview,
        surfacePreview: event.surfacePreview,
        gloryLines: event.gloryLines,
        contextSnapshot: event.contextSnapshot,
        contextStory: event.contextStory,
      ),
      onShare: onShare,
      onViewRewards: onViewRewards,
      barrierDismissible: barrierDismissible,
      comboCount: comboCount,
      milestoneInfo: milestoneInfo,
    );
  }

  @override
  State<AchievementUnlockDialog> createState() =>
      _AchievementUnlockDialogState();

  /// 显示成就解锁弹窗
  static Future<void> show(
    BuildContext context,
    AchievementUnlockEvent event, {
    VoidCallback? onShare,
    VoidCallback? onViewRewards,
    bool barrierDismissible = true,
    int? comboCount,
    MilestoneInfo? milestoneInfo,
  }) =>
      showSensoryGeneralDialog(
        context: context,
        barrierDismissible: barrierDismissible,
        barrierLabel: context.l10n.achievementUnlockBarrierLabel,
        barrierColor: DS.textPrimary.withValues(alpha: 0.7),
        transitionDuration: const Duration(milliseconds: 600),
        pageBuilder: (context, animation, secondaryAnimation) =>
            AchievementUnlockDialog(
          event: event,
          onShare: onShare,
          onViewRewards: onViewRewards,
          comboCount: comboCount,
          milestoneInfo: milestoneInfo,
        ),
        transitionBuilder: (context, animation, secondaryAnimation, child) =>
            _AchievementUnlockTransition(
          animation: animation,
          rarity: event.rarity,
          child: child,
        ),
      );
}

class _AchievementUnlockDialogState extends State<AchievementUnlockDialog>
    with TickerProviderStateMixin {
  static const _actionCooldown = Duration(milliseconds: 180);

  late AnimationController _scaleController;
  late AnimationController _rotateController;
  late AnimationController _particleController;
  late AnimationController _glowController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotateAnimation;
  late Animation<double> _glowAnimation;
  bool _showLegendaryAura = false;
  _AchievementUnlockActionState _actionState =
      _AchievementUnlockActionState.idle;

  @override
  void initState() {
    super.initState();
    _initAnimations();
  }

  void _initAnimations() {
    // 缩放动画
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(
        parent: _scaleController,
        curve: Curves.elasticOut,
      ),
    );
    unawaited(_scaleController.forward());

    // 旋转动画
    _rotateController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    );
    _rotateAnimation = Tween<double>(begin: 0, end: 2 * math.pi).animate(
      _rotateController,
    );

    // 粒子动画
    _particleController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    // 光晕动画
    _glowController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(
        parent: _glowController,
        curve: Curves.easeInOut,
      ),
    );

    // 根据稀有度启动不同动画
    _startRarityAnimations();
  }

  void _startRarityAnimations() {
    unawaited(BgmService.boostTemporarily());
    switch (widget.event.rarity) {
      case AchievementRarity.common:
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementCommon),
        );
      case AchievementRarity.rare:
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementRare),
        );
        unawaited(_glowController.repeat(reverse: true));
      case AchievementRarity.epic:
        unawaited(
          SensoryFeedbackService.emitSeries(
            const [
              SensoryFeedbackEvent.achievementEpic,
              SensoryFeedbackEvent.achievementRare,
              SensoryFeedbackEvent.achievementEpic,
            ],
            gap: const Duration(milliseconds: 150),
          ),
        );
        unawaited(_glowController.repeat(reverse: true));
        unawaited(_particleController.repeat());
      case AchievementRarity.legendary:
        unawaited(
          SensoryFeedbackService.emitSeries(
            const [
              SensoryFeedbackEvent.achievementLegendary,
              SensoryFeedbackEvent.achievementEpic,
              SensoryFeedbackEvent.achievementRare,
              SensoryFeedbackEvent.achievementEpic,
              SensoryFeedbackEvent.achievementLegendary,
            ],
            gap: const Duration(milliseconds: 120),
          ),
        );
        _showLegendaryAura = true;
        unawaited(
          Future<void>.delayed(const Duration(seconds: 3), () {
            if (!mounted) return;
            setState(() {
              _showLegendaryAura = false;
            });
          }),
        );
        unawaited(_rotateController.repeat());
        unawaited(_particleController.repeat());
        unawaited(_glowController.repeat(reverse: true));
    }
  }

  @override
  void dispose() {
    _scaleController.dispose();
    _rotateController.dispose();
    _particleController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rarity = widget.event.rarity;

    return BgmScope(
      track: BgmTrack.celebration,
      priority: BgmPriority.stage,
      child: Dialog(
        backgroundColor: DS.overlay30.withValues(alpha: 0),
        elevation: 0,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // 背景特效
            if (rarity != AchievementRarity.common) _buildBackgroundEffects(),
            if (_showLegendaryAura) _buildLegendaryAura(),

            // 连击横幅 (P1功能 - 成就连击反馈)
            if (widget.comboCount != null && widget.comboCount! > 1)
              _buildComboBanner(),

            // 主内容
            _buildContent(),

            // 粒子效果
            if (rarity == AchievementRarity.rare ||
                rarity == AchievementRarity.epic ||
                rarity == AchievementRarity.legendary)
              _buildParticleOverlay(),
            if (rarity != AchievementRarity.common)
              Positioned.fill(
                child: IgnorePointer(
                  child: SparkleConfetti(
                    play: true,
                    enableSensory: false,
                    alignment: Alignment.center,
                    intensity: rarity == AchievementRarity.rare
                        ? SparkleCelebrationIntensity.medium
                        : SparkleCelebrationIntensity.large,
                    particleCount: _confettiParticleCount(rarity),
                    colors: _confettiColors(rarity),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _dismissUnlockDialog() async {
    final navigator = Navigator.of(context, rootNavigator: true);
    if (navigator.canPop()) {
      navigator.pop();
    }
    await Future<void>.delayed(_actionCooldown);
  }

  Future<void> _runDialogAction(
    _AchievementUnlockActionState nextState,
    VoidCallback? callback,
  ) async {
    if (_actionState != _AchievementUnlockActionState.idle) {
      return;
    }
    setState(() => _actionState = nextState);
    try {
      await _dismissUnlockDialog();
      callback?.call();
    } finally {
      if (mounted) {
        setState(() => _actionState = _AchievementUnlockActionState.idle);
      }
    }
  }

  void _handleClose() {
    unawaited(
      _runDialogAction(_AchievementUnlockActionState.closing, widget.onClose),
    );
  }

  void _handleShare() {
    unawaited(
      _runDialogAction(_AchievementUnlockActionState.sharing, widget.onShare),
    );
  }

  void _handleViewRewards() {
    unawaited(
      _runDialogAction(
        _AchievementUnlockActionState.navigating,
        widget.onViewRewards,
      ),
    );
  }

  int _confettiParticleCount(AchievementRarity rarity) => switch (rarity) {
        AchievementRarity.common => 0,
        AchievementRarity.rare => 25,
        AchievementRarity.epic => 60,
        AchievementRarity.legendary => 120,
      };

  List<Color> _confettiColors(AchievementRarity rarity) => switch (rarity) {
        AchievementRarity.common => [DS.neutral400],
        AchievementRarity.rare => [DS.rarityRare, DS.info, DS.warning],
        AchievementRarity.epic => [DS.rarityEpic, DS.warning, DS.info],
        AchievementRarity.legendary => [
            const Color(0xFFFFE082),
            const Color(0xFFFFC107),
            const Color(0xFFFFF8E1),
            DS.warning,
          ],
      };

  Widget _buildContent() {
    final rarity = widget.event.rarity;
    final colors = _getRarityColors();

    return LayoutBuilder(
      builder: (context, constraints) {
        final dialogWidth = math.min(constraints.maxWidth - 24, 320.0);
        final compact = dialogWidth < 300;

        return ConstrainedBox(
          constraints: BoxConstraints(maxWidth: dialogWidth),
          child: SingleChildScrollView(
            child: Container(
              width: dialogWidth,
              padding: EdgeInsets.all(compact ? DS.spacing20 : DS.spacing24),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    colors.primary.withValues(alpha: 0.95),
                    colors.secondary.withValues(alpha: 0.9),
                  ],
                ),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: colors.border,
                  width: 2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: colors.glow,
                    blurRadius: 32,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 稀有度徽章
                  RarityBadge(rarity: rarity, showLabel: !compact),
                  const SizedBox(height: DS.spacing16),

                  // 成就图标
                  _buildIconContainer(),
                  const SizedBox(height: DS.spacing16),

                  // 成就名称
                  Text(
                    widget.event.name,
                    textAlign: TextAlign.center,
                    maxLines: compact ? 3 : 4,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: compact ? DS.fontSizeLg : DS.fontSizeXl,
                      fontWeight: DS.fontWeightBold,
                      color: colors.text,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),

                  // 解锁文本
                  Text(
                    _getUnlockText(),
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      color: colors.text.withValues(alpha: 0.8),
                    ),
                  ),

                  // 解锁时间
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
                    child: Text(
                      _formatTime(widget.event.unlockedAt),
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: colors.text.withValues(alpha: 0.6),
                      ),
                    ),
                  ),

                  // 首次解锁标记
                  if (widget.event.isFirst)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing12,
                        vertical: DS.spacing6,
                      ),
                      decoration: BoxDecoration(
                        color: DS.warning.withValues(alpha: 0.3),
                        borderRadius: DS.borderRadius12,
                        border: Border.all(
                          color: DS.warning,
                        ),
                      ),
                      child: Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        spacing: DS.spacing4,
                        children: [
                          Icon(
                            Icons.star,
                            size: DS.iconSizeSm,
                            color: DS.warning,
                          ),
                          Text(
                            context.l10n.achievementUnlockFirstUnlocker,
                            style: TextStyle(
                              fontSize: DS.fontSizeXs,
                              fontWeight: DS.fontWeightBold,
                              color: DS.warning,
                            ),
                          ),
                        ],
                      ),
                    ),

                  // 里程碑信息 (P1功能 - 进度里程碑庆祝)
                  if (widget.milestoneInfo != null)
                    _buildMilestoneSection(widget.milestoneInfo!),

                  if (widget.event.contextStory?.trim().isNotEmpty ??
                      false) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildEvidenceSection(widget.event.contextStory!.trim()),
                  ],

                  if (widget.event.rewardPreview.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildRewardPreviewSection(),
                  ],

                  if (widget.event.gloryLines.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildGloryLinesSection(),
                  ],

                  if (widget.event.surfacePreview.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildSurfacePreviewSection(),
                  ],

                  // 视觉元素奖励预览
                  if (_hasVisualElementRewards())
                    _VisualElementPreviewSection(
                      rewards: widget.event.rewards!,
                      glowAnimation: _glowAnimation,
                    ),

                  const SizedBox(height: DS.spacing20),

                  // 操作按钮
                  if (compact)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (widget.onViewRewards != null) ...[
                          _buildActionButton(
                            icon: Icons.workspace_premium_outlined,
                            label: context.l10n.achievementUnlockViewRewards,
                            isPrimary: true,
                            onPressed: _handleViewRewards,
                          ),
                          const SizedBox(height: DS.spacing12),
                        ],
                        _buildActionButton(
                          icon: Icons.close,
                          label: context.l10n.achievementUnlockClose,
                          isPrimary: false,
                          onPressed: _handleClose,
                        ),
                        const SizedBox(height: DS.spacing12),
                        _buildActionButton(
                          icon: Icons.share,
                          label: context.l10n.achievementUnlockShare,
                          isPrimary: true,
                          onPressed: _handleShare,
                        ),
                      ],
                    )
                  else
                    Row(
                      children: [
                        if (widget.onViewRewards != null) ...[
                          Expanded(
                            child: _buildActionButton(
                              icon: Icons.workspace_premium_outlined,
                              label: context.l10n.achievementUnlockViewRewards,
                              isPrimary: true,
                              onPressed: _handleViewRewards,
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                        ],
                        Expanded(
                          child: _buildActionButton(
                            icon: Icons.close,
                            label: context.l10n.achievementUnlockClose,
                            isPrimary: false,
                            onPressed: _handleClose,
                          ),
                        ),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: _buildActionButton(
                            icon: Icons.share,
                            label: context.l10n.achievementUnlockShare,
                            isPrimary: true,
                            onPressed: _handleShare,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildIconContainer() {
    final rarity = widget.event.rarity;
    final colors = _getRarityColors();

    return AnimatedBuilder(
      animation: _scaleAnimation,
      builder: (context, child) => Transform.scale(
        scale: _scaleAnimation.value,
        child: AnimatedBuilder(
          animation: _rotateAnimation,
          builder: (context, child) {
            final shouldRotate = rarity == AchievementRarity.legendary;
            return Transform.rotate(
              angle: shouldRotate ? _rotateAnimation.value * 0.1 : 0,
              child: Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      colors.primary,
                      colors.secondary,
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: colors.glow,
                      blurRadius: 24,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: AnimatedBuilder(
                  animation: _glowAnimation,
                  builder: (context, child) => Container(
                    margin: EdgeInsets.all(DS.xs * _glowAnimation.value),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: colors.background,
                    ),
                    child: Icon(
                      _getIconForRarity(),
                      size: 50,
                      color: colors.icon,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildBackgroundEffects() {
    final rarity = widget.event.rarity;

    switch (rarity) {
      case AchievementRarity.rare:
        return _buildGlowingRings();
      case AchievementRarity.epic:
        return _buildPulsingWaves();
      case AchievementRarity.legendary:
        return _buildRainbowExplosion();
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildGlowingRings() => AnimatedBuilder(
        animation: _glowAnimation,
        builder: (context, child) => Container(
          width: 360,
          height: 360,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: DS.warning.withValues(alpha: 0.3 * _glowAnimation.value),
              width: 2,
            ),
          ),
        ),
      );

  Widget _buildPulsingWaves() => AnimatedBuilder(
        animation: _particleController,
        builder: (context, child) => Container(
          width: 400,
          height: 400,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: DS.taskReflection.withValues(
                alpha: 0.2 * (1 - _particleController.value),
              ),
              width: 3,
            ),
          ),
        ),
      );

  Widget _buildRainbowExplosion() => AnimatedBuilder(
        animation: _particleController,
        builder: (context, child) {
          final progress = _particleController.value;
          return CustomPaint(
            size: const Size(400, 400),
            painter: _RainbowExplosionPainter(progress),
          );
        },
      );

  Widget _buildParticleOverlay() => Positioned.fill(
        child: CustomPaint(
          painter: _ParticlePainter(
            rarity: widget.event.rarity,
            animation: _particleController,
          ),
        ),
      );

  Widget _buildLegendaryAura() => Positioned.fill(
        child: IgnorePointer(
          child: AnimatedBuilder(
            animation: _glowController,
            builder: (context, child) => DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(32),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFFFD54F)
                        .withValues(alpha: 0.18 * _glowAnimation.value),
                    blurRadius: 36,
                    spreadRadius: 10,
                  ),
                ],
              ),
            ),
          ),
        ),
      );

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required bool isPrimary,
    required VoidCallback onPressed,
  }) {
    final colors = _getRarityColors();

    final isBusy = _actionState != _AchievementUnlockActionState.idle;

    return GestureDetector(
      onTap: isBusy ? null : onPressed,
      child: Container(
        padding: const EdgeInsets.symmetric(
          vertical: DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: isPrimary
              ? colors.primary.withValues(alpha: isBusy ? 0.48 : 0.8)
              : null,
          border: Border.all(
            color: colors.border.withValues(alpha: isBusy ? 0.6 : 1),
            width: 1.5,
          ),
          borderRadius: DS.borderRadius12,
        ),
        child: Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: DS.spacing6,
          runSpacing: DS.spacing4,
          children: [
            Icon(
              icon,
              size: DS.iconSizeSm,
              color: colors.text,
            ),
            Text(
              isBusy &&
                      ((label == context.l10n.achievementUnlockClose &&
                              _actionState ==
                                  _AchievementUnlockActionState.closing) ||
                          (label == context.l10n.achievementUnlockShare &&
                              _actionState ==
                                  _AchievementUnlockActionState.sharing) ||
                          (label == context.l10n.achievementUnlockViewRewards &&
                              _actionState ==
                                  _AchievementUnlockActionState.navigating))
                  ? context.l10n.achievementUnlockProcessing
                  : label,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightMedium,
                color: colors.text.withValues(alpha: isBusy ? 0.82 : 1),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRewardPreviewSection() {
    final colors = _getRarityColors();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.background.withValues(alpha: 0.72),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: colors.border.withValues(alpha: 0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.achievementUnlockGloryHarvest,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightBold,
              color: colors.text,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          ...widget.event.rewardPreview.map(
            (line) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.check_circle, size: 14, color: colors.border),
                  const SizedBox(width: DS.spacing6),
                  Expanded(
                    child: Text(
                      line,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: colors.text.withValues(alpha: 0.88),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEvidenceSection(String evidence) {
    final colors = _getRarityColors();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.background.withValues(alpha: 0.72),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: colors.border.withValues(alpha: 0.42)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.auto_awesome_rounded,
            size: 16,
            color: colors.border,
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              evidence,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: colors.text.withValues(alpha: 0.88),
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGloryLinesSection() {
    final colors = _getRarityColors();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.primary.withValues(alpha: 0.18),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: colors.border.withValues(alpha: 0.35)),
      ),
      child: Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: widget.event.gloryLines
            .map(
              (line) => Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing6,
                ),
                decoration: BoxDecoration(
                  color: colors.background.withValues(alpha: 0.8),
                  borderRadius: DS.borderRadius12,
                ),
                child: Text(
                  line,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightMedium,
                    color: colors.text,
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _buildSurfacePreviewSection() {
    final colors = _getRarityColors();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.achievementUnlockIdentityChange,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightBold,
            color: colors.text,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: widget.event.surfacePreview
              .map(
                (surface) => Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing6,
                  ),
                  decoration: BoxDecoration(
                    color: colors.background.withValues(alpha: 0.82),
                    borderRadius: DS.borderRadius12,
                    border:
                        Border.all(color: colors.border.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    surface,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: colors.text,
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ],
    );
  }

  _RarityColors _getRarityColors() {
    switch (widget.event.rarity) {
      case AchievementRarity.common:
        return _RarityColors(
          primary: DS.neutral200,
          secondary: DS.neutral300,
          border: DS.neutral400,
          glow: DS.neutral400.withValues(alpha: 0.3),
          text: DS.neutral800,
          background: DS.neutral0,
          icon: DS.neutral600,
        );
      case AchievementRarity.rare:
        return _RarityColors(
          primary: DS.rarityRare,
          secondary: DS.warning,
          border: DS.rarityRare,
          glow: DS.rarityRare.withValues(alpha: 0.5),
          text: DS.rarityRareText,
          background: DS.neutral0.withValues(alpha: 0.9),
          icon: DS.rarityRareText,
        );
      case AchievementRarity.epic:
        return _RarityColors(
          primary: DS.rarityEpic,
          secondary: DS.brandSecondary,
          border: DS.rarityEpic,
          glow: DS.rarityEpic.withValues(alpha: 0.6),
          text: DS.onBrandPrimary,
          background: DS.neutral0.withValues(alpha: 0.95),
          icon: DS.onBrandPrimary,
        );
      case AchievementRarity.legendary:
        return _RarityColors(
          primary: DS.rarityLegendary,
          secondary: DS.info,
          border: DS.rarityRare,
          glow: DS.rarityRare.withValues(alpha: 0.7),
          text: DS.onBrandPrimary,
          background: DS.neutral0.withValues(alpha: 0.95),
          icon: DS.onBrandPrimary,
        );
    }
  }

  IconData _getIconForRarity() {
    switch (widget.event.rarity) {
      case AchievementRarity.common:
        return Icons.military_tech;
      case AchievementRarity.rare:
        return Icons.stars;
      case AchievementRarity.epic:
        return Icons.auto_awesome;
      case AchievementRarity.legendary:
        return Icons.diamond;
    }
  }

  String _getUnlockText() {
    switch (widget.event.rarity) {
      case AchievementRarity.common:
        return context.l10n.achievementUnlockTitleCommon;
      case AchievementRarity.rare:
        return context.l10n.achievementUnlockTitleRare;
      case AchievementRarity.epic:
        return context.l10n.achievementUnlockTitleEpic;
      case AchievementRarity.legendary:
        return context.l10n.achievementUnlockTitleLegendary;
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inSeconds < 60) {
      return context.l10n.achievementUnlockTimeJustNow;
    } else if (diff.inMinutes < 60) {
      return context.l10n.achievementUnlockTimeMinutesAgo(diff.inMinutes);
    } else if (diff.inHours < 24) {
      return context.l10n.achievementUnlockTimeHoursAgo(diff.inHours);
    } else {
      return context.l10n.achievementUnlockTimeDate(
        time.month,
        time.day,
        time.hour.toString().padLeft(2, '0'),
        time.minute.toString().padLeft(2, '0'),
      );
    }
  }

  /// P1功能: 成就连击横幅
  Widget _buildComboBanner() {
    final comboCount = widget.comboCount!;

    return Positioned(
      top: -20,
      child: AnimatedBuilder(
        animation: _scaleAnimation,
        builder: (context, child) => Transform.scale(
          scale: _scaleAnimation.value.clamp(0.8, 1.2),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 280),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing20,
              vertical: DS.spacing10,
            ),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  DS.rarityLegendary,
                  DS.rarityRare,
                ],
              ),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: DS.rarityLegendary.withValues(alpha: 0.5),
                  blurRadius: 10,
                ),
              ],
            ),
            child: Wrap(
              alignment: WrapAlignment.center,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: DS.spacing8,
              runSpacing: DS.spacing4,
              children: [
                Icon(
                  Icons.local_fire_department,
                  color: DS.onBrandPrimary,
                  size: 24,
                ),
                Text(
                  context.l10n.achievementUnlockCombo(comboCount),
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightBold,
                    color: DS.onBrandPrimary,
                  ),
                ),
                Text(
                  _getComboText(comboCount),
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.onBrandPrimary.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// P1功能: 里程碑信息区域
  Widget _buildMilestoneSection(MilestoneInfo milestone) {
    final colors = _getRarityColors();

    return Container(
      margin: const EdgeInsets.only(top: DS.spacing12),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: colors.primary.withValues(alpha: 0.2),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: colors.primary.withValues(alpha: 0.5),
        ),
      ),
      child: Column(
        children: [
          Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: DS.spacing4,
            runSpacing: DS.spacing4,
            children: [
              Icon(
                Icons.flag,
                size: DS.iconSizeSm,
                color: colors.primary,
              ),
              Text(
                context.l10n.achievementUnlockMilestoneReached,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                  color: colors.text,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            milestone.description,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: colors.text.withValues(alpha: 0.8),
            ),
          ),
          if (milestone.reward != null) ...[
            const SizedBox(height: DS.spacing8),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: DS.warning.withValues(alpha: 0.3),
                borderRadius: DS.borderRadius8,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.card_giftcard,
                    size: 14,
                    color: DS.warning,
                  ),
                  const SizedBox(width: DS.spacing4),
                  Text(
                    milestone.reward!,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightBold,
                      color: DS.warning,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _getComboText(int count) {
    if (count >= 10) return context.l10n.achievementUnlockComboGodlike;
    if (count >= 5) return context.l10n.achievementUnlockComboAmazing;
    if (count >= 3) return context.l10n.achievementUnlockComboKeepGoing;
    return context.l10n.achievementUnlockComboNice;
  }

  bool _hasVisualElementRewards() {
    final rewards = widget.event.rewards;
    if (rewards == null || rewards.isEmpty) return false;
    return rewards.any((reward) => reward['type'] == 'visual_element');
  }
}

class _VisualElementPreviewSection extends StatelessWidget {
  const _VisualElementPreviewSection({
    required this.rewards,
    required this.glowAnimation,
  });

  final List<Map<String, dynamic>> rewards;
  final Animation<double> glowAnimation;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final visualRewards =
        rewards.where((reward) => reward['type'] == 'visual_element').toList();
    if (visualRewards.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.achievementRewardVisualElement,
          style: TextStyle(
            color: DS.textPrimary,
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: visualRewards.take(3).map((reward) {
            final name = reward['name'] ??
                reward['display'] ??
                reward['title'] ??
                l10n.achievementRewardVisualElement;
            return AnimatedBuilder(
              animation: glowAnimation,
              builder: (context, child) => Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing6,
                ),
                decoration: BoxDecoration(
                  color: DS.surfaceHigh.withValues(alpha: 0.9),
                  borderRadius: DS.borderRadius12,
                  border: Border.all(
                    color:
                        DS.warning.withValues(alpha: 0.4 * glowAnimation.value),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.auto_awesome,
                      size: 14,
                      color: DS.warning,
                    ),
                    const SizedBox(width: DS.spacing4),
                    Flexible(
                      child: Text(
                        name.toString(),
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}

/// 成就解锁转场动画
class _AchievementUnlockTransition extends StatelessWidget {
  const _AchievementUnlockTransition({
    required this.animation,
    required this.rarity,
    required this.child,
  });

  final Animation<double> animation;
  final AchievementRarity rarity;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    // 根据稀有度使用不同的动画曲线
    final curve = _getCurveForRarity();
    final curvedAnimation = CurvedAnimation(
      parent: animation,
      curve: curve,
    );

    // 根据稀有度添加额外的动画效果
    switch (rarity) {
      case AchievementRarity.common:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: curvedAnimation,
            child: child,
          ),
        );
      case AchievementRarity.rare:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.5, end: 1.0).animate(
              CurvedAnimation(
                parent: animation,
                curve: Curves.elasticOut,
              ),
            ),
            child: child,
          ),
        );
      case AchievementRarity.epic:
        return FadeTransition(
          opacity: curvedAnimation,
          child: RotationTransition(
            turns: Tween<double>(begin: -0.05, end: 0).animate(
              CurvedAnimation(
                parent: animation,
                curve: Curves.elasticOut,
              ),
            ),
            child: ScaleTransition(
              scale: Tween<double>(begin: 0.3, end: 1.0).animate(
                CurvedAnimation(
                  parent: animation,
                  curve: Curves.elasticOut,
                ),
              ),
              child: child,
            ),
          ),
        );
      case AchievementRarity.legendary:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.1, end: 1.0).animate(
              CurvedAnimation(
                parent: animation,
                curve: Curves.elasticOut,
              ),
            ),
            child: child,
          ),
        );
    }
  }

  Curve _getCurveForRarity() {
    switch (rarity) {
      case AchievementRarity.common:
        return Curves.easeOut;
      case AchievementRarity.rare:
        return Curves.easeOutBack;
      case AchievementRarity.epic:
        return Curves.elasticOut;
      case AchievementRarity.legendary:
        return Curves.elasticOut;
    }
  }
}

/// 稀有度颜色配置
class _RarityColors {
  _RarityColors({
    required this.primary,
    required this.secondary,
    required this.border,
    required this.glow,
    required this.text,
    required this.background,
    required this.icon,
  });

  final Color primary;
  final Color secondary;
  final Color border;
  final Color glow;
  final Color text;
  final Color background;
  final Color icon;
}

/// 粒子绘制器
class _ParticlePainter extends CustomPainter {
  _ParticlePainter({
    required this.rarity,
    required this.animation,
  });

  final AchievementRarity rarity;
  final Animation<double> animation;

  @override
  void paint(Canvas canvas, Size size) {
    if (rarity == AchievementRarity.common) return;

    final center = Offset(size.width / 2, size.height / 2);
    final progress = animation.value;
    final random = math.Random(42); // 固定种子保证一致性

    final particleCount = rarity == AchievementRarity.legendary ? 50 : 20;
    final baseColor = _getParticleBaseColor();

    for (var i = 0; i < particleCount; i++) {
      final angle = (i / particleCount) * 2 * math.pi + progress * 0.5;
      final distance = 50 + progress * 150;
      final x = center.dx + math.cos(angle) * distance;
      final y = center.dy + math.sin(angle) * distance;

      final particleSize = rarity == AchievementRarity.legendary
          ? (4 + random.nextDouble() * 4) * (1 - progress * 0.5)
          : 3.0;

      final paint = Paint()
        ..color = baseColor.withValues(
          alpha: (0.6 * (1 - progress * 0.8)),
        )
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), particleSize, paint);
    }
  }

  Color _getParticleBaseColor() {
    switch (rarity) {
      case AchievementRarity.rare:
        return DS.rarityRare;
      case AchievementRarity.epic:
        return DS.rarityEpic;
      case AchievementRarity.legendary:
        return DS.rarityRare;
      default:
        return DS.neutral400;
    }
  }

  @override
  bool shouldRepaint(_ParticlePainter oldDelegate) =>
      oldDelegate.animation.value != animation.value;
}

/// 彩虹爆炸绘制器
class _RainbowExplosionPainter extends CustomPainter {
  _RainbowExplosionPainter(this.progress);

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final colors = [
      DS.rarityLegendary,
      DS.rarityRare,
      DS.success,
      DS.info,
    ];

    for (var i = 0; i < colors.length; i++) {
      final radius = 80 + progress * 120 + i * 30;
      final paint = Paint()
        ..color =
            colors[i].withValues(alpha: (0.3 - progress * 0.25).clamp(0.0, 0.3))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(_RainbowExplosionPainter oldDelegate) =>
      oldDelegate.progress != progress;
}

/// P1功能: 里程碑信息类
class MilestoneInfo {
  MilestoneInfo({
    required this.milestoneType,
    required this.description,
    this.reward,
    this.progressPercentage,
  });

  factory MilestoneInfo.fromProgress(double oldProgress, double newProgress) {
    final oldMilestone = (oldProgress * 100).toInt() ~/ 25;
    final newMilestone = (newProgress * 100).toInt() ~/ 25;

    if (newMilestone > oldMilestone && newMilestone <= 4) {
      final percentage = newMilestone * 25;
      return MilestoneInfo(
        milestoneType: '$percentage%',
        description: S.achievementUnlockMilestoneProgress(percentage),
        reward: _getMilestoneReward(percentage),
        progressPercentage: newProgress,
      );
    }
    throw ArgumentError('No milestone crossed');
  }

  final String milestoneType; // '25%', '50%', '75%', '100%'
  final String description;
  final String? reward;
  final double? progressPercentage;

  static String? _getMilestoneReward(int percentage) {
    switch (percentage) {
      case 25:
        return S.achievementUnlockPhotonReward10;
      case 50:
        return S.achievementUnlockPhotonReward25;
      case 75:
        return S.achievementUnlockPhotonReward50;
      case 100:
        return S.achievementUnlockPhotonReward100;
      default:
        return null;
    }
  }
}
