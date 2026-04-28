import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/home/home_routes.dart';

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
      shareHashtag: queryParameters['share_hashtag']?.trim().isNotEmpty == true
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
      shareHashtag: raw['share_hashtag']?.toString().trim().isNotEmpty == true
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
        'knowledge_explorer_50' => S.current.achievementMilestoneUnitNodes,
        'sprint_veteran' => S.current.achievementMilestoneUnitSprints,
        _ => S.current.achievementMilestoneUnitDays,
      };

  String get headline => switch (milestoneId) {
        'knowledge_explorer_50' => S.current.achievementMilestoneHeadlineNodes,
        'sprint_veteran' => S.current.achievementMilestoneHeadlineSprints,
        _ => S.current.achievementMilestoneHeadlineDefault,
      };

  String get subheadline => switch (milestoneId) {
        'knowledge_explorer_50' => S.current.achievementMilestoneSubheadlineNodes,
        'sprint_veteran' => S.current.achievementMilestoneSubheadlineSprints,
        _ => S.current.achievementMilestoneSubheadlineDefault,
      };

  String get badgeLabel => switch (milestoneId) {
        'knowledge_explorer_50' => 'Galaxy Explorer',
        'sprint_veteran' => 'Sprint Veteran',
        _ => 'Core Sparkle User',
      };

  static int _defaultCelebrationValue(String milestoneId) =>
      switch (milestoneId) {
        'knowledge_explorer_50' => 50,
        'sprint_veteran' => 2,
        _ => 30,
      };

  static String _defaultShareHashtag(String milestoneId) =>
      milestoneId == '30_day_learner' ? S.current.achievementMilestoneHashtag30Day : S.current.achievementMilestoneHashtagDefault;
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
          AppFeedback.success(context, context.l10n.achievementMilestoneShareOpened);
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
            play: true,
            intensity: SparkleCelebrationIntensity.large,
            child: SafeArea(
              child: Stack(
                children: [
                  const Positioned.fill(child: _MilestoneBackdrop()),
                  Positioned(
                    top: DS.spacing8,
                    left: DS.spacing8,
                    child: SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      icon: const Icon(Icons.close_rounded),
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
                                      ? const SizedBox(
                                          width: 18,
                                          height: 18,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Icon(Icons.ios_share_rounded),
                                  label: Text(_isSharing ? context.l10n.achievementMilestoneShareInProgress : context.l10n.achievementMilestoneShareNow),
                                ),
                                OutlinedButton.icon(
                                  onPressed: _continueLearning,
                                  icon: const Icon(Icons.check_circle_outline),
                                  label: Text(context.l10n.achievementMilestoneContinueLearning),
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
              const Color(0xFF13213C),
              const Color(0xFF2F4F7A),
              const Color(0xFFF6C453).withValues(alpha: 0.22),
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
                color: const Color(0xFFF6C453).withValues(alpha: 0.24),
              ),
            ),
            Positioned(
              bottom: -40,
              left: -20,
              child: _GlowOrb(
                size: 180,
                color: const Color(0xFF7DD3FC).withValues(alpha: 0.18),
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
          fontWeight: FontWeight.w800,
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
            const Color(0xFF10203B).withValues(alpha: 0.96),
            const Color(0xFF172B4D).withValues(alpha: 0.96),
            const Color(0xFF2E4A75).withValues(alpha: 0.94),
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
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              payload.badgeLabel,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: const Color(0xFFFFE29A),
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
                        color: const Color(0xFFFFE29A),
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
              borderRadius: BorderRadius.circular(20),
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
  Widget build(BuildContext context) => Container(
        width: 150,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(20),
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
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
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
