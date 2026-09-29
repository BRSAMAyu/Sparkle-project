import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/home/home_routes.dart';

// 庆祝时刻固定美术底（V4-G06 登记的 dl-spec 豁免，同 rarity identity 惯例）：
// 里程碑庆祝是“深夜星空 + 金”的一次性时刻面，与档位无关的固定美术方向。
// 自包含对比度已机检钉死（test/goldens/v4_g06 四档审计：白/暖金对深蓝族
// 5.3–16:1），关闭按钮 + reduce-motion 数字直出 + 低刺激彩带抑制（U-02）
// 保证庆祝可关语义四档成立。改成随档派生属发布面美术决策，登记 Q08 待裁，
// 不在本卡顺手改。
// [coldColorLiteral 登记] 六枚冷相硬编码在该维度 ratchet 基线内（本文件
// 基线 6，只降不升；替换为随档令牌需先裁美术方向，见上）。
const _celebrationNavy = Color(0xFF13213C);
const _celebrationMidBlue = Color(0xFF2F4F7A);
const _celebrationGold = Color(0xFFF6C453);
const _celebrationLightBlue = Color(0xFF7DD3FC);
const _celebrationDarkNavy = Color(0xFF10203B);
const _celebrationDeepBlue = Color(0xFF172B4D);
const _celebrationSteelBlue = Color(0xFF2E4A75);
const _celebrationWarmGold = Color(0xFFFFE29A);

class MilestoneCelebrationPayload {
  const MilestoneCelebrationPayload({
    required this.milestoneId,
    required this.celebrationValue,
    required this.studyDays,
    required this.masteredNodes,
    required this.completedSprints,
    required this.errorCount,
    this.shareHashtag = '',
  });

  factory MilestoneCelebrationPayload.fromQueryParameters(
    String milestoneId,
    Map<String, String> queryParameters,
  ) {
    int parseInt(String key, int fallback) =>
        int.tryParse(queryParameters[key] ?? '') ?? fallback;

    return MilestoneCelebrationPayload(
      milestoneId: milestoneId,
      celebrationValue: parseInt(
        'celebration_value',
        _defaultCelebrationValue(milestoneId),
      ),
      studyDays: parseInt('study_days', 0),
      masteredNodes: parseInt('mastered_nodes', 0),
      completedSprints: parseInt('completed_sprints', 0),
      errorCount: parseInt('error_count', 0),
      shareHashtag: queryParameters['share_hashtag']?.trim().isNotEmpty ?? false
          ? queryParameters['share_hashtag']!.trim()
          : _defaultShareHashtag(milestoneId),
    );
  }

  factory MilestoneCelebrationPayload.fromMap(Map<String, dynamic> raw) {
    int parseInt(String key, int fallback) {
      final value = raw[key];
      if (value is int) return value;
      if (value is num) return value.toInt();
      return int.tryParse(value?.toString() ?? '') ?? fallback;
    }

    final milestoneId = raw['milestone_id']?.toString() ??
        raw['milestoneId']?.toString() ??
        raw['achievement_id']?.toString() ??
        '30_day_learner';
    return MilestoneCelebrationPayload(
      milestoneId: milestoneId,
      celebrationValue:
          parseInt('celebration_value', _defaultCelebrationValue(milestoneId)),
      studyDays: parseInt('study_days', 0),
      masteredNodes: parseInt('mastered_nodes', 0),
      completedSprints: parseInt('completed_sprints', 0),
      errorCount: parseInt('error_count', 0),
      shareHashtag: raw['share_hashtag']?.toString().trim().isNotEmpty ?? false
          ? raw['share_hashtag'].toString().trim()
          : _defaultShareHashtag(milestoneId),
    );
  }

  final String milestoneId;
  final int celebrationValue;
  final int studyDays;
  final int masteredNodes;
  final int completedSprints;
  final int errorCount;
  final String shareHashtag;

  String get unitLabel => switch (milestoneId) {
        'knowledge_explorer_50' => S.achievementMilestoneUnitNodes,
        'sprint_veteran' => S.achievementMilestoneUnitSprints,
        _ => S.achievementMilestoneUnitDays,
      };

  String get headline => switch (milestoneId) {
        'knowledge_explorer_50' => S.achievementMilestoneHeadlineNodes,
        'sprint_veteran' => S.achievementMilestoneHeadlineSprints,
        _ => S.achievementMilestoneHeadlineDefault,
      };

  String get subheadline => switch (milestoneId) {
        'knowledge_explorer_50' => S.achievementMilestoneSubheadlineNodes,
        'sprint_veteran' => S.achievementMilestoneSubheadlineSprints,
        _ => S.achievementMilestoneSubheadlineDefault,
      };

  String get badgeLabel => switch (milestoneId) {
        'knowledge_explorer_50' => S.achievementMilestoneBadgeGalaxy,
        'sprint_veteran' => S.achievementMilestoneBadgeSprint,
        _ => S.achievementMilestoneBadgeCore,
      };

  static int _defaultCelebrationValue(String milestoneId) =>
      switch (milestoneId) {
        'knowledge_explorer_50' => 50,
        'sprint_veteran' => 2,
        _ => 30,
      };

  static String _defaultShareHashtag(String milestoneId) =>
      milestoneId == '30_day_learner'
          ? S.achievementMilestoneHashtag30Day
          : S.achievementMilestoneHashtagDefault;
}

class MilestoneCelebrationScreen extends ConsumerStatefulWidget {
  const MilestoneCelebrationScreen({
    required this.payload,
    this.shareImageBuilder,
    this.shareLauncher,
    super.key,
  });

  final MilestoneCelebrationPayload payload;

  @visibleForTesting
  final Future<File?> Function()? shareImageBuilder;

  @visibleForTesting
  final Future<void> Function(File imageFile, String shareText)? shareLauncher;

  @override
  ConsumerState<MilestoneCelebrationScreen> createState() =>
      _MilestoneCelebrationScreenState();
}

class _MilestoneCelebrationScreenState
    extends ConsumerState<MilestoneCelebrationScreen>
    with SingleTickerProviderStateMixin {
  final GlobalKey _shareBoundaryKey = GlobalKey();
  late final AnimationController _numberController;
  bool _isSharing = false;

  @override
  void initState() {
    super.initState();
    _numberController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );
    unawaited(_numberController.forward());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (context.reduceMotion && !_numberController.isCompleted) {
      _numberController.value = 1.0;
    }
  }

  @override
  void dispose() {
    _numberController.dispose();
    super.dispose();
  }

  Future<void> _share() async {
    if (_isSharing) return;
    setState(() => _isSharing = true);
    try {
      final imageFile =
          await (widget.shareImageBuilder?.call() ?? _captureShareImage());
      if (!mounted || imageFile == null) return;

      final shareText = _buildShareText(widget.payload);
      final launcher = widget.shareLauncher;
      if (launcher != null) {
        await launcher(imageFile, shareText);
      } else {
        final result = await ref
            .read(universalShareServiceProvider)
            .shareToSystem(imageFile: imageFile, text: shareText);
        if (!mounted) return;
        if (result.isSuccess) {
          AppFeedback.success(
              context, context.l10n.achievementMilestoneShareOpened,);
        } else if (result.error != null) {
          AppFeedback.error(context, result.error!);
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }

  Future<File?> _captureShareImage() async {
    await WidgetsBinding.instance.endOfFrame;
    final boundary = _shareBoundaryKey.currentContext?.findRenderObject()
        as RenderRepaintBoundary?;
    if (boundary == null) return null;

    final image = await boundary.toImage(pixelRatio: 3);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    if (byteData == null) return null;

    final tempDir = await getTemporaryDirectory();
    final file = File(
      '${tempDir.path}/sparkle_milestone_${widget.payload.milestoneId}_${DateTime.now().millisecondsSinceEpoch}.png',
    );
    await file.writeAsBytes(byteData.buffer.asUint8List(), flush: true);
    return file;
  }

  String _buildShareText(MilestoneCelebrationPayload payload) =>
      context.l10n.achievementMilestoneShareText(
        payload.shareHashtag,
        payload.headline,
        '${payload.studyDays}',
        '${payload.masteredNodes}',
        '${payload.completedSprints}',
        '${payload.errorCount}',
      );

  void _dismissToAchievements() {
    RouteResilience.popOrGo(
      context,
      fallbackRoute: AchievementRoutes.basePath,
    );
  }

  void _continueLearning() {
    RouteResilience.popOrGo(context, fallbackRoute: HomeRoutes.home);
  }

  @override
  Widget build(BuildContext context) => RouteResilienceScope(
        fallbackRoute: AchievementRoutes.basePath,
        child: Scaffold(
          backgroundColor: DS.surfacePrimary,
          body: SparkleConfetti(
            // V4-G06 reduce-motion 等价：系统减动效时庆祝彩带不发射
            // （低刺激档已由 U-02 在 SparkleConfetti 内部抑制）；庆祝
            // 内容（数字、徽章、可关语义）不受影响。
            play: !context.reduceMotion,
            intensity: SparkleCelebrationIntensity.large,
            child: SafeArea(
              child: Stack(
                children: [
                  const Positioned.fill(child: _MilestoneBackdrop()),
                  Positioned(
                    top: DS.spacing8,
                    left: DS.spacing8,
                    // 甲式（A11Y-BATCH5）：semanticLabel 承载按钮名。
                    child: SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      icon: const Icon(Icons.close_rounded),
                      semanticLabel: context.l10n.close,
                      onPressed: _dismissToAchievements,
                    ),
                  ),
                  Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(
                        DS.spacing20,
                        DS.spacing56,
                        DS.spacing20,
                        DS.spacing24,
                      ),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 760),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            RepaintBoundary(
                              key: _shareBoundaryKey,
                              child: _MilestoneHeroCard(
                                payload: widget.payload,
                                numberController: _numberController,
                              ),
                            ),
                            const SizedBox(height: DS.spacing20),
                            Wrap(
                              alignment: WrapAlignment.center,
                              spacing: DS.spacing12,
                              runSpacing: DS.spacing12,
                              children: [
                                FilledButton.icon(
                                  key: const ValueKey('milestone-share'),
                                  onPressed: _isSharing ? null : _share,
                                  icon: _isSharing
                                      ? LoadingIndicator.circular(size: 18)
                                      : const Icon(Icons.ios_share_rounded),
                                  label: Text(_isSharing
                                      ? context.l10n
                                          .achievementMilestoneShareInProgress
                                      : context
                                          .l10n.achievementMilestoneShareNow,),
                                ),
                                OutlinedButton.icon(
                                  onPressed: _continueLearning,
                                  icon: const Icon(Icons.check_circle_outline),
                                  label: Text(context.l10n
                                      .achievementMilestoneContinueLearning,),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _MilestoneBackdrop extends StatelessWidget {
  const _MilestoneBackdrop();

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfacePrimary,
              _celebrationNavy,
              _celebrationMidBlue,
              _celebrationGold.withValues(alpha: 0.22),
            ],
          ),
        ),
        child: Stack(
          children: [
            Positioned(
              top: -60,
              right: -30,
              child: _GlowOrb(
                size: 220,
                color: _celebrationGold.withValues(alpha: 0.24),
              ),
            ),
            Positioned(
              bottom: -40,
              left: -20,
              child: _GlowOrb(
                size: 180,
                color: _celebrationLightBlue.withValues(alpha: 0.18),
              ),
            ),
          ],
        ),
      );
}

class _MilestoneHeroCard extends StatelessWidget {
  const _MilestoneHeroCard({
    required this.payload,
    required this.numberController,
  });

  final MilestoneCelebrationPayload payload;
  final Animation<double> numberController;

  @override
  Widget build(BuildContext context) {
    final titleStyle = Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
          height: 1.08,
        );
    final bodyStyle = Theme.of(context).textTheme.bodyLarge?.copyWith(
          color: Colors.white.withValues(alpha: 0.82),
          height: 1.45,
        );

    return Container(
      padding: const EdgeInsets.all(DS.spacing24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _celebrationDarkNavy.withValues(alpha: 0.96),
            _celebrationDeepBlue.withValues(alpha: 0.96),
            _celebrationSteelBlue.withValues(alpha: 0.94),
          ],
        ),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.24),
            blurRadius: 32,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing8,
            ),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.10),
              borderRadius: DS.borderRadiusFull,
            ),
            child: Text(
              payload.badgeLabel,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: _celebrationWarmGold,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.4,
                  ),
            ),
          ),
          const SizedBox(height: DS.spacing20),
          Text(payload.headline, style: titleStyle),
          const SizedBox(height: DS.spacing12),
          Text(payload.subheadline, style: bodyStyle),
          const SizedBox(height: DS.spacing24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              AnimatedBuilder(
                animation: numberController,
                builder: (context, child) {
                  final value =
                      (payload.celebrationValue * numberController.value)
                          .round();
                  return Text(
                    '$value',
                    key: const ValueKey('milestone-big-number'),
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          height: 0.92,
                        ),
                  );
                },
              ),
              const SizedBox(width: DS.spacing12),
              Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing12),
                child: Text(
                  payload.unitLabel,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: _celebrationWarmGold,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing24),
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              _StatChip(
                key: const ValueKey('milestone-stat-study-days'),
                label: context.l10n.achievementMilestoneStatStudyDays,
                value: '${payload.studyDays}',
              ),
              _StatChip(
                key: const ValueKey('milestone-stat-mastered-nodes'),
                label: context.l10n.achievementMilestoneStatMasteredNodes,
                value: '${payload.masteredNodes}',
              ),
              _StatChip(
                key: const ValueKey('milestone-stat-completed-sprints'),
                label: context.l10n.achievementMilestoneStatCompletedSprints,
                value: '${payload.completedSprints}',
              ),
              _StatChip(
                key: const ValueKey('milestone-stat-error-count'),
                label: context.l10n.achievementMilestoneStatErrorCount,
                value: '${payload.errorCount}',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: DS.borderRadius20,
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Text(
              context.l10n.achievementMilestoneCoreUserMessage,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.84),
                    height: 1.5,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.value,
    super.key,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        // V4-G06 200% 文本：固定 150 宽在 2.0 缩放下截断标签——改下限
        // 约束，卡片随文本放大增高（DESIGN_SYSTEM 布局条款：200% 时
        // 允许更高卡片，不截断主内容）。
        constraints: const BoxConstraints(minWidth: 150, maxWidth: 320),
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            borderRadius: DS.borderRadius20,
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: Colors.white.withValues(alpha: 0.70),
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
        ),
      );
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({
    required this.size,
    required this.color,
  });

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                color,
                color.withValues(alpha: 0.02),
              ],
            ),
          ),
        ),
      );
}
