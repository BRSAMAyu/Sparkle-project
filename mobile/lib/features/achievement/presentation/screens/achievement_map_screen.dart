import 'dart:async';

import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/animation_lifecycle_mixin.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_milestone_badge.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

class AchievementMapScreen extends ConsumerStatefulWidget {
  const AchievementMapScreen({super.key});

  @override
  ConsumerState<AchievementMapScreen> createState() =>
      _AchievementMapScreenState();
}

class _AchievementMapScreenState extends ConsumerState<AchievementMapScreen> {
  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final state = ref.watch(achievementMapProvider);
    final achievementState = ref.watch(achievementProvider);
    final progressById = <String, double>{
      for (final entry in achievementState.achievements)
        entry.achievement.id:
            (entry.progressPercentage / 100).clamp(0.0, 1.0).toDouble(),
    };

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: Text(
          l10n.achievementMapTitle,
          style: TextStyle(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: DS.textPrimary),
          onPressed: () => context.pop(),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          // Focus button - navigate to nearest unlocked achievement
          IconButton(
            icon: Icon(Icons.my_location, color: DS.textPrimary),
            tooltip: l10n.achievementMapFocusTooltip,
            onPressed: state.isLoading || state.nodes.isEmpty
                ? null
                : () => _showFocusTooltip(context, state.nodes),
          ),
        ],
      ),
      child: state.isLoading
          ? Center(
              child: CircularProgressIndicator(color: DS.brandPrimary),
            )
          : state.error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        l10n.loadingFailed,
                        style: TextStyle(color: DS.textSecondary),
                      ),
                      const SizedBox(height: DS.spacing8),
                      SparkleButton.outline(
                        label: l10n.retry,
                        onPressed: () =>
                            ref.read(achievementMapProvider.notifier).refresh(),
                      ),
                    ],
                  ),
                )
              : _CosmicConstellationCanvas(
                  nodes: state.nodes,
                  connections: state.connections,
                  progressById: progressById,
                  onNodeTap: (node) => _showNodePreview(context, node),
                ),
    );
  }

  /// Find and navigate to the nearest unlocked achievement
  void _showFocusTooltip(BuildContext context, List<AchievementMapNode> nodes) {
    final targetNode = nodes.firstWhere(
      (n) => n.isRecommendedTarget,
      orElse: () => nodes.firstWhere(
        (n) => !n.isUnlocked && !n.isHidden,
        orElse: () => nodes.first,
      ),
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.l10n.achievementMapFocusHint(targetNode.name)),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _showNodePreview(BuildContext context, AchievementMapNode node) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: Colors.transparent,
        isScrollControlled: true,
        builder: (context) => _AchievementNodeBottomSheet(node: node),
      ),
    );
  }
}

class _AchievementNodeBottomSheet extends StatelessWidget {
  const _AchievementNodeBottomSheet({required this.node});

  final AchievementMapNode node;

  @override
  Widget build(BuildContext context) {
    final color = RarityColorProvider.getColor(node.rarity);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Container(
          padding: const EdgeInsets.all(DS.spacing20),
          decoration: BoxDecoration(
            color: DS.deepSpaceStart.withValues(alpha: 0.96),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: color.withValues(alpha: 0.28)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      node.name,
                      style: TextStyle(
                        fontSize: DS.fontSizeLg,
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                      ),
                    ),
                  ),
                  if (node.isRecommendedTarget)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing10,
                        vertical: DS.spacing6,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.18),
                        borderRadius: DS.borderRadius12,
                      ),
                      child: Text(
                        '下一枚高价值目标',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          fontWeight: DS.fontWeightSemibold,
                          color: color,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: DS.spacing10),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _MetaChip(label: node.laneLabel, color: color),
                  _MetaChip(
                      label: _displayStateLabel(node.displayState),
                      color: Colors.white70),
                  _MetaChip(
                      label: '${node.progressPercentage}%', color: DS.info),
                ],
              ),
              if (node.unlockHint != null) ...[
                const SizedBox(height: DS.spacing16),
                Text(
                  node.unlockHint!,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
              ],
              if (node.rewardPreview.isNotEmpty) ...[
                const SizedBox(height: DS.spacing16),
                Text(
                  '解锁后你会获得',
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                ...node.rewardPreview.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.auto_awesome, size: 14, color: color),
                        const SizedBox(width: DS.spacing6),
                        Expanded(
                          child: Text(
                            item,
                            style: TextStyle(
                              fontSize: DS.fontSizeXs,
                              color: DS.textSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing18),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.outline(
                      label: '关闭',
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton.primary(
                      label: '查看详情',
                      onPressed: () {
                        Navigator.of(context).pop();
                        context.push('/achievements/${node.id}');
                      },
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _displayStateLabel(String state) {
    switch (state) {
      case 'unlocked':
        return '已解锁';
      case 'ready_to_pursue':
        return '可冲刺';
      case 'close_to_unlock':
        return '接近解锁';
      case 'hidden_unrevealed':
        return '隐藏中';
      default:
        return '前置阻塞';
    }
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: DS.borderRadius12,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          color: color,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Cosmic constellation canvas - the main animated map
// ---------------------------------------------------------------------------

class _CosmicConstellationCanvas extends StatefulWidget {
  const _CosmicConstellationCanvas({
    required this.nodes,
    required this.connections,
    required this.progressById,
    required this.onNodeTap,
  });

  final List<AchievementMapNode> nodes;
  final List<Map<String, dynamic>> connections;
  final Map<String, double> progressById;
  final ValueChanged<AchievementMapNode> onNodeTap;

  @override
  State<_CosmicConstellationCanvas> createState() =>
      _CosmicConstellationCanvasState();
}

class _CosmicConstellationCanvasState extends State<_CosmicConstellationCanvas>
    with TickerProviderStateMixin, AnimationLifecycleMixin {
  late final AnimationController _twinkleController;
  late final AnimationController _pulseController;
  late final AnimationController _nodeEntranceController;

  /// Controller for InteractiveViewer
  final TransformationController _transformationController =
      TransformationController();

  /// Cached star positions generated once with a seeded random.
  late List<_Star> _stars;
  int _starCount = 0;
  bool _reduceMotion = false;
  bool _orbitalParticlesEnabled = false;
  int _registeredParticleCount = 0;
  bool _hasInitializedViewport = false;

  @override
  void initState() {
    super.initState();

    // Slow twinkle cycle for the star field (8 seconds).
    _twinkleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    // Pulse cycle for connection glow dots and node rings (3 seconds).
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    // Entrance animation for nodes (staggered).
    final totalDuration =
        Duration(milliseconds: 600 + widget.nodes.length * 40);
    _nodeEntranceController = AnimationController(
      vsync: this,
      duration: totalDuration,
    )..forward();

    registerController(
      _twinkleController,
      onResume: () => _twinkleController.repeat(),
    );
    registerController(
      _pulseController,
      onResume: () => _pulseController.repeat(),
    );

    _stars = [];
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _updateMotionPreference(context.reduceMotion);
    _updateOrbitalParticleRegistration(force: true);
    _updateStarField();
    _initializeViewportCenter();
  }

  /// Initialize viewport to center the content
  void _initializeViewportCenter() {
    if (_hasInitializedViewport || widget.nodes.isEmpty) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      final screenSize = MediaQuery.of(context).size;
      final appBarHeight = kToolbarHeight;

      // Calculate canvas bounds
      var minX = double.infinity;
      var maxX = double.negativeInfinity;
      var minY = double.infinity;
      var maxY = double.negativeInfinity;
      const padding = 100.0;

      for (final node in widget.nodes) {
        final x = (node.position['x'] ?? 0) + padding;
        final y = (node.position['y'] ?? 0) + padding;
        minX = math.min(minX, x);
        maxX = math.max(maxX, x);
        minY = math.min(minY, y);
        maxY = math.max(maxY, y);
      }

      final contentWidth = maxX - minX + padding * 2;
      final contentHeight = maxY - minY + padding * 2;

      // Calculate scale to fit content on screen with some padding
      final availableHeight = screenSize.height - appBarHeight - 100;
      final scaleX = screenSize.width / contentWidth;
      final scaleY = availableHeight / contentHeight;
      final scale = math.min(scaleX, math.min(scaleY, 1.0));

      // Calculate translation to center content
      final scaledContentWidth = contentWidth * scale;
      final scaledContentHeight = contentHeight * scale;
      final offsetX = (screenSize.width - scaledContentWidth) / 2 -
          minX * scale +
          padding * scale;
      final offsetY = appBarHeight +
          (availableHeight - scaledContentHeight) / 2 -
          minY * scale +
          padding * scale;

      _transformationController.value = Matrix4.identity()
        ..translateByDouble(offsetX, offsetY, 0, 1)
        ..scaleByDouble(scale, scale, 1, 1);

      _hasInitializedViewport = true;
    });
  }

  @override
  void didUpdateWidget(covariant _CosmicConstellationCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.nodes.length != widget.nodes.length) {
      _nodeEntranceController.duration =
          Duration(milliseconds: 600 + widget.nodes.length * 40);
      _hasInitializedViewport = false;
      _initializeViewportCenter();
    }
    _updateOrbitalParticleRegistration(force: true);
  }

  void _zoomBy(double factor) {
    final current = _transformationController.value.clone();
    final nextScale = (current.getMaxScaleOnAxis() * factor).clamp(0.4, 3.0);
    final dx = current.storage[12];
    final dy = current.storage[13];
    _transformationController.value = Matrix4.identity()
      ..translateByDouble(dx, dy, 0, 1)
      ..scaleByDouble(nextScale, nextScale, 1, 1);
  }

  void _resetViewport() {
    _hasInitializedViewport = false;
    _initializeViewportCenter();
  }

  List<Map<String, String>> _laneLegend() {
    final seen = <String>{};
    final lanes = <Map<String, String>>[];
    for (final node in widget.nodes) {
      final key = '${node.lane}|${node.laneLabel}';
      if (!seen.add(key)) continue;
      lanes.add({'lane': node.lane, 'label': node.laneLabel});
    }
    return lanes;
  }

  Color _laneColor(String lane) {
    switch (lane) {
      case 'streak_lane':
        return const Color(0xFFFF8A3D);
      case 'sprint_lane':
        return const Color(0xFF2FB6FF);
      case 'knowledge_lane':
        return const Color(0xFF78E08F);
      case 'social_lane':
        return const Color(0xFFE8A1FF);
      default:
        return const Color(0xFFFFD166);
    }
  }

  void _updateMotionPreference(bool reduceMotion) {
    if (_reduceMotion == reduceMotion) return;
    _reduceMotion = reduceMotion;
    if (_reduceMotion) {
      _twinkleController.stop();
      _pulseController.stop();
      _nodeEntranceController.stop();
      _releaseOrbitalParticles();
    } else {
      if (!_twinkleController.isAnimating) {
        _twinkleController.repeat();
      }
      if (!_pulseController.isAnimating) {
        _pulseController.repeat();
      }
      if (_nodeEntranceController.value == 0.0) {
        _nodeEntranceController.forward();
      }
      _updateOrbitalParticleRegistration(force: true);
    }
  }

  void _updateStarField() {
    final count = _getAdaptiveStarCount();
    if (count == _starCount) return;
    _starCount = count;

    final rng = math.Random(42);
    _stars = List.generate(count, (_) {
      return _Star(
        x: rng.nextDouble(),
        y: rng.nextDouble(),
        radius: 0.5 + rng.nextDouble() * 1.5,
        baseOpacity: 0.2 + rng.nextDouble() * 0.6,
        phase: rng.nextDouble() * math.pi * 2,
      );
    });
  }

  int _getAdaptiveStarCount() {
    final dpr = MediaQuery.of(context).devicePixelRatio;
    if (dpr < 2.0) return 30;
    if (dpr < 3.0) return 45;
    return 60;
  }

  int _calculateOrbitalParticleCount() {
    var total = 0;
    for (final node in widget.nodes) {
      if (!node.isUnlocked) continue;
      total += _orbitalParticlesForRarity(node.rarity);
    }
    return total;
  }

  void _updateOrbitalParticleRegistration({bool force = false}) {
    final desiredCount = _reduceMotion ? 0 : _calculateOrbitalParticleCount();

    if (!force && desiredCount == _registeredParticleCount) return;
    _releaseOrbitalParticles();

    if (desiredCount > 0 &&
        GlobalParticleCounter.tryAddParticles(desiredCount)) {
      _registeredParticleCount = desiredCount;
      _orbitalParticlesEnabled = true;
    }
  }

  void _releaseOrbitalParticles() {
    if (_registeredParticleCount > 0) {
      GlobalParticleCounter.releaseParticles(_registeredParticleCount);
      _registeredParticleCount = 0;
    }
    _orbitalParticlesEnabled = false;
  }

  @override
  void dispose() {
    _releaseOrbitalParticles();
    _twinkleController.dispose();
    _pulseController.dispose();
    _nodeEntranceController.dispose();
    _transformationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.nodes.isEmpty) {
      return Center(
        child: Text(
          context.l10n.achievementMapEmpty,
          style: TextStyle(color: DS.textSecondary),
        ),
      );
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final reduceMotion = _reduceMotion;
    final starStartColor = isDark ? DS.deepSpaceStart : DS.surfacePrimary;
    final starEndColor = isDark ? DS.deepSpaceEnd : DS.surfaceSecondary;
    final starColor = isDark ? Colors.white : DS.neutral600;

    // Compute positions & canvas size.
    final positions = <String, Offset>{};
    final nodeMap = <String, AchievementMapNode>{};
    var maxX = 0.0;
    var maxY = 0.0;
    const padding = 100.0;

    for (final node in widget.nodes) {
      final x = (node.position['x'] ?? 0) + padding;
      final y = (node.position['y'] ?? 0) + padding;
      maxX = math.max(maxX, x);
      maxY = math.max(maxY, y);
      positions[node.id] = Offset(x, y);
      nodeMap[node.id] = node;
    }

    final canvasWidth = maxX + padding;
    final canvasHeight = maxY + padding;

    final lanes = _laneLegend();

    return Stack(
      children: [
        InteractiveViewer(
          transformationController: _transformationController,
          minScale: 0.35,
          maxScale: 3.5,
          panEnabled: true,
          scaleEnabled: true,
          constrained: false,
          interactionEndFrictionCoefficient: 0.001,
          boundaryMargin: const EdgeInsets.all(DS.spacing32),
          child: SizedBox(
            width: canvasWidth,
            height: canvasHeight,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // Layer 0 - Deep space background + star field.
                Positioned.fill(
                  child: reduceMotion
                      ? CustomPaint(
                          painter: _StarFieldPainter(
                            stars: _stars,
                            animValue: 0.0,
                            startColor: starStartColor,
                            endColor: starEndColor,
                            starColor: starColor,
                            reduceMotion: true,
                          ),
                        )
                      : AnimatedBuilder(
                          animation: _twinkleController,
                          builder: (context, _) => CustomPaint(
                            painter: _StarFieldPainter(
                              stars: _stars,
                              animValue: _twinkleController.value,
                              startColor: starStartColor,
                              endColor: starEndColor,
                              starColor: starColor,
                              reduceMotion: false,
                            ),
                          ),
                        ),
                ),

                // Layer 1 - Connection lines (gradient + glow + pulse dots).
                Positioned.fill(
                  child: reduceMotion
                      ? CustomPaint(
                          painter: _ConstellationLinesPainter(
                            connections: widget.connections,
                            positions: positions,
                            nodeMap: nodeMap,
                            progressById: widget.progressById,
                            pulseValue: 0.0,
                            showPulseDots: false,
                          ),
                        )
                      : AnimatedBuilder(
                          animation: _pulseController,
                          builder: (context, _) => CustomPaint(
                            painter: _ConstellationLinesPainter(
                              connections: widget.connections,
                              positions: positions,
                              nodeMap: nodeMap,
                              progressById: widget.progressById,
                              pulseValue: _pulseController.value,
                              showPulseDots: true,
                            ),
                          ),
                        ),
                ),

                // Layer 2 - Floating orbital particles around unlocked nodes.
                if (_orbitalParticlesEnabled)
                  Positioned.fill(
                    child: AnimatedBuilder(
                      animation: _pulseController,
                      builder: (context, _) => CustomPaint(
                        painter: _OrbitalParticlesPainter(
                          nodes: widget.nodes,
                          positions: positions,
                          animValue: _pulseController.value,
                          isDark: isDark,
                        ),
                      ),
                    ),
                  ),

                // Layer 3 - Node widgets.
                ...List.generate(widget.nodes.length, (index) {
                  final node = widget.nodes[index];
                  final offset = positions[node.id] ?? Offset.zero;
                  final progress = widget.progressById[node.id] ??
                      (node.isUnlocked ? 1.0 : 0.0);

                  // Staggered entrance timing.
                  final delayMs = index * 40;
                  final totalMs =
                      _nodeEntranceController.duration!.inMilliseconds;
                  final start = delayMs / totalMs;
                  final end = math.min((delayMs + 600) / totalMs, 1.0);

                  final entranceAnim = CurvedAnimation(
                    parent: _nodeEntranceController,
                    curve: Interval(start, end, curve: Curves.elasticOut),
                  );

                  final nodeWidget = _CosmicNodeWidget(
                    node: node,
                    progress: progress,
                    reduceMotion: reduceMotion,
                    pulseController: _pulseController,
                    onTap: widget.onNodeTap,
                  );

                  return Positioned(
                    left: offset.dx - 44,
                    top: offset.dy - 44,
                    child: reduceMotion
                        ? nodeWidget
                        : ScaleTransition(
                            scale: entranceAnim,
                            child: nodeWidget,
                          ),
                  );
                }),
              ],
            ),
          ),
        ),
        Positioned(
          top: DS.spacing24,
          left: DS.spacing16,
          right: 88,
          child: IgnorePointer(
            ignoring: false,
            child: Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.deepSpaceStart.withValues(alpha: 0.82),
                borderRadius: DS.borderRadius16,
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x22000000),
                    blurRadius: 24,
                    offset: Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '征服路径图',
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    '双指缩放或用右侧控件查看不同赛道，推荐目标会被重点高亮。',
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      height: 1.45,
                      color: DS.textSecondary,
                    ),
                  ),
                  if (lanes.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing10),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: lanes
                          .take(4)
                          .map(
                            (lane) => Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing10,
                                vertical: DS.spacing6,
                              ),
                              decoration: BoxDecoration(
                                color: _laneColor(lane['lane']!)
                                    .withValues(alpha: 0.16),
                                borderRadius: DS.borderRadius12,
                              ),
                              child: Text(
                                lane['label']!,
                                style: TextStyle(
                                  fontSize: DS.fontSizeXs,
                                  fontWeight: DS.fontWeightMedium,
                                  color: _laneColor(lane['lane']!),
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
        Positioned(
          right: DS.spacing16,
          bottom: DS.spacing32,
          child: Column(
            children: [
              _MapControlButton(
                icon: Icons.add,
                tooltip: '放大',
                onTap: () => _zoomBy(1.2),
              ),
              const SizedBox(height: DS.spacing10),
              _MapControlButton(
                icon: Icons.remove,
                tooltip: '缩小',
                onTap: () => _zoomBy(0.84),
              ),
              const SizedBox(height: DS.spacing10),
              _MapControlButton(
                icon: Icons.center_focus_strong,
                tooltip: '重置视角',
                onTap: _resetViewport,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MapControlButton extends StatelessWidget {
  const _MapControlButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: DS.deepSpaceStart.withValues(alpha: 0.86),
        borderRadius: DS.borderRadius16,
        child: InkWell(
          borderRadius: DS.borderRadius16,
          onTap: onTap,
          child: Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              borderRadius: DS.borderRadius16,
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Icon(icon, color: DS.textPrimary, size: 22),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Star data model
// ---------------------------------------------------------------------------

class _Star {
  const _Star({
    required this.x,
    required this.y,
    required this.radius,
    required this.baseOpacity,
    required this.phase,
  });

  final double x;
  final double y;
  final double radius;
  final double baseOpacity;
  final double phase;
}

// ---------------------------------------------------------------------------
// Star field painter - deep space gradient + twinkling stars
// ---------------------------------------------------------------------------

class _StarFieldPainter extends CustomPainter {
  _StarFieldPainter({
    required this.stars,
    required this.animValue,
    required this.startColor,
    required this.endColor,
    required this.starColor,
    required this.reduceMotion,
  });

  final List<_Star> stars;
  final double animValue;
  final Color startColor;
  final Color endColor;
  final Color starColor;
  final bool reduceMotion;

  @override
  void paint(Canvas canvas, Size size) {
    // Deep space gradient background.
    final bgRect = Rect.fromLTWH(0, 0, size.width, size.height);
    final bgPaint = Paint()
      ..shader = ui.Gradient.linear(
        Offset.zero,
        Offset(size.width, size.height),
        [startColor, endColor],
      );
    canvas.drawRect(bgRect, bgPaint);

    // Twinkling stars.
    final starPaint = Paint()..style = PaintingStyle.fill;
    for (final star in stars) {
      final twinkle = reduceMotion
          ? 1.0
          : math.sin(animValue * math.pi * 2 + star.phase) * 0.3 + 0.7;
      final opacity = (star.baseOpacity * twinkle).clamp(0.0, 1.0);
      starPaint.color = starColor.withValues(alpha: opacity);
      canvas.drawCircle(
        Offset(star.x * size.width, star.y * size.height),
        star.radius,
        starPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _StarFieldPainter old) =>
      old.animValue != animValue ||
      old.startColor != startColor ||
      old.endColor != endColor ||
      old.starColor != starColor ||
      old.reduceMotion != reduceMotion;
}

// ---------------------------------------------------------------------------
// Constellation lines painter - gradient, glow, dashed locked, pulse dots
// ---------------------------------------------------------------------------

class _ConstellationLinesPainter extends CustomPainter {
  _ConstellationLinesPainter({
    required this.connections,
    required this.positions,
    required this.nodeMap,
    required this.progressById,
    required this.pulseValue,
    required this.showPulseDots,
  });

  final List<Map<String, dynamic>> connections;
  final Map<String, Offset> positions;
  final Map<String, AchievementMapNode> nodeMap;
  final Map<String, double> progressById;
  final double pulseValue;
  final bool showPulseDots;

  @override
  void paint(Canvas canvas, Size size) {
    for (final connection in connections) {
      final fromId = connection['from'] as String?;
      final toId = connection['to'] as String?;
      if (fromId == null || toId == null) continue;

      final from = positions[fromId];
      final to = positions[toId];
      if (from == null || to == null) continue;

      final fromNode = nodeMap[fromId];
      final toNode = nodeMap[toId];
      if (fromNode == null || toNode == null) continue;

      final bothUnlocked = fromNode.isUnlocked && toNode.isUnlocked;
      final fromProgress =
          progressById[fromId] ?? (fromNode.isUnlocked ? 1.0 : 0.0);
      final toProgress = progressById[toId] ?? (toNode.isUnlocked ? 1.0 : 0.0);
      final isCompleted = fromProgress >= 1.0 && toProgress >= 1.0;
      final fromColor = RarityColorProvider.getColor(fromNode.rarity);
      final toColor = RarityColorProvider.getColor(toNode.rarity);

      if (bothUnlocked) {
        _drawUnlockedLine(canvas, from, to, fromColor, toColor, isCompleted);
        if (showPulseDots) {
          _drawPulseDot(canvas, from, to, fromColor, toColor);
        }
      } else {
        _drawLockedDashedLine(canvas, from, to);
      }
    }
  }

  void _drawUnlockedLine(
    Canvas canvas,
    Offset from,
    Offset to,
    Color fromColor,
    Color toColor,
    bool isCompleted,
  ) {
    // Glow layer.
    final glowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = isCompleted ? 5.0 : 4.0
      ..maskFilter = MaskFilter.blur(
        BlurStyle.normal,
        isCompleted ? 4 : 3,
      )
      ..shader = ui.Gradient.linear(
        from,
        to,
        [
          fromColor.withValues(alpha: isCompleted ? 0.45 : 0.3),
          toColor.withValues(alpha: isCompleted ? 0.45 : 0.3),
        ],
      );
    canvas.drawLine(from, to, glowPaint);

    // Sharp line.
    final linePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = isCompleted ? 2.2 : 1.5
      ..shader = ui.Gradient.linear(
        from,
        to,
        [
          fromColor.withValues(alpha: isCompleted ? 0.95 : 0.8),
          toColor.withValues(alpha: isCompleted ? 0.95 : 0.8),
        ],
      );
    canvas.drawLine(from, to, linePaint);
  }

  void _drawPulseDot(
    Canvas canvas,
    Offset from,
    Offset to,
    Color fromColor,
    Color toColor,
  ) {
    final t = pulseValue;
    final dotPos = Offset.lerp(from, to, t)!;
    final dotColor = Color.lerp(fromColor, toColor, t)!;

    // Outer glow.
    final glowPaint = Paint()
      ..color = dotColor.withValues(alpha: 0.4)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawCircle(dotPos, 4.0, glowPaint);

    // Core dot.
    final corePaint = Paint()..color = dotColor.withValues(alpha: 0.9);
    canvas.drawCircle(dotPos, 2.0, corePaint);
  }

  void _drawLockedDashedLine(Canvas canvas, Offset from, Offset to) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    final dx = to.dx - from.dx;
    final dy = to.dy - from.dy;
    final length = math.sqrt(dx * dx + dy * dy);
    if (length == 0) return;

    const dashLen = 6.0;
    const gapLen = 4.0;
    final ux = dx / length;
    final uy = dy / length;

    var d = 0.0;
    while (d < length) {
      final segEnd = math.min(d + dashLen, length);
      canvas.drawLine(
        Offset(from.dx + ux * d, from.dy + uy * d),
        Offset(from.dx + ux * segEnd, from.dy + uy * segEnd),
        paint,
      );
      d += dashLen + gapLen;
    }
  }

  @override
  bool shouldRepaint(covariant _ConstellationLinesPainter old) =>
      old.pulseValue != pulseValue ||
      old.connections != connections ||
      old.positions != positions ||
      old.progressById != progressById ||
      old.showPulseDots != showPulseDots;
}

// ---------------------------------------------------------------------------
// Orbital particles painter - tiny dots orbiting unlocked nodes
// ---------------------------------------------------------------------------

int _orbitalParticlesForRarity(AchievementRarity rarity) {
  switch (rarity) {
    case AchievementRarity.legendary:
      return 4;
    case AchievementRarity.epic:
      return 2;
    case AchievementRarity.rare:
    case AchievementRarity.common:
      return 2;
  }
}

class _OrbitalParticlesPainter extends CustomPainter {
  _OrbitalParticlesPainter({
    required this.nodes,
    required this.positions,
    required this.animValue,
    required this.isDark,
  });

  final List<AchievementMapNode> nodes;
  final Map<String, Offset> positions;
  final double animValue;
  final bool isDark;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;

    for (final node in nodes) {
      if (!node.isUnlocked) continue;

      final center = positions[node.id];
      if (center == null) continue;

      final color = _getAdaptiveColor(
        RarityColorProvider.getColor(node.rarity),
        isDark,
      );
      // 2-4 particles per unlocked node based on rarity.
      final particleCount = _orbitalParticlesForRarity(node.rarity);

      for (var i = 0; i < particleCount; i++) {
        final orbitRadius = 30.0 + i * 6.0;
        final speed = 1.0 + i * 0.3;
        final phase = (i * math.pi * 2 / particleCount);
        final angle = animValue * math.pi * 2 * speed + phase;

        final px = center.dx + math.cos(angle) * orbitRadius;
        final py = center.dy + math.sin(angle) * orbitRadius;

        // Outer glow.
        paint.color = color.withValues(alpha: 0.25);
        paint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
        canvas.drawCircle(Offset(px, py), 2.5, paint);

        // Core.
        paint.color = color.withValues(alpha: 0.7);
        paint.maskFilter = null;
        canvas.drawCircle(Offset(px, py), 1.2, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _OrbitalParticlesPainter old) =>
      old.animValue != animValue || old.isDark != isDark;

  Color _getAdaptiveColor(Color baseColor, bool isDark) {
    if (isDark) return baseColor;
    return HSLColor.fromColor(baseColor).withLightness(0.3).toColor();
  }
}

// ---------------------------------------------------------------------------
// Cosmic node widget - circular, glowing, with entrance animation
// ---------------------------------------------------------------------------

class _CosmicNodeWidget extends StatelessWidget {
  const _CosmicNodeWidget({
    required this.node,
    required this.pulseController,
    required this.progress,
    required this.reduceMotion,
    required this.onTap,
  });

  final AchievementMapNode node;
  final AnimationController pulseController;
  final double progress;
  final bool reduceMotion;
  final ValueChanged<AchievementMapNode> onTap;

  IconData _iconForCategory(String category) {
    switch (category.toLowerCase()) {
      case 'streak':
        return Icons.local_fire_department_rounded;
      case 'mastery':
        return Icons.psychology_rounded;
      case 'milestone':
        return Icons.flag_rounded;
      case 'social':
        return Icons.people_rounded;
      case 'task_complete':
        return Icons.task_alt_rounded;
      case 'hidden':
        return Icons.visibility_off_rounded;
      case 'study_time':
        return Icons.schedule_rounded;
      case 'sprint':
        return Icons.speed_rounded;
      case 'contract':
        return Icons.handshake_rounded;
      case 'node_explore':
        return Icons.explore_rounded;
      default:
        return Icons.star_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = RarityColorProvider.getColor(node.rarity);
    const nodeSize = 52.0;
    final isNearCompletion =
        progress >= 0.75 || node.displayState == 'close_to_unlock';
    final isRecommended = node.isRecommendedTarget;

    return GestureDetector(
      onTap: () => onTap(node),
      child: SizedBox(
        width: 88,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Glow ring + node circle.
            SizedBox(
              width: 68,
              height: 68,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Animated outer glow ring (unlocked only).
                  if (node.isUnlocked || isRecommended)
                    reduceMotion
                        ? Container(
                            width: 66,
                            height: 66,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: color.withValues(
                                  alpha: isRecommended
                                      ? 0.75
                                      : (isNearCompletion ? 0.5 : 0.3),
                                ),
                                width: isRecommended
                                    ? 3.0
                                    : (isNearCompletion ? 2.6 : 2.0),
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: color.withValues(
                                    alpha: isRecommended
                                        ? 0.38
                                        : (isNearCompletion ? 0.3 : 0.18),
                                  ),
                                  blurRadius: isRecommended
                                      ? 20
                                      : (isNearCompletion ? 16 : 12),
                                  spreadRadius: isRecommended
                                      ? 4
                                      : (isNearCompletion ? 3 : 2),
                                ),
                              ],
                            ),
                          )
                        : AnimatedBuilder(
                            animation: pulseController,
                            builder: (context, _) {
                              final pulseOpacity = (isRecommended
                                      ? 0.55
                                      : (isNearCompletion ? 0.4 : 0.3)) +
                                  (isRecommended
                                          ? 0.3
                                          : (isNearCompletion ? 0.25 : 0.2)) *
                                      math.sin(
                                        pulseController.value * math.pi * 2,
                                      );
                              return Container(
                                width: 66,
                                height: 66,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color:
                                        color.withValues(alpha: pulseOpacity),
                                    width: isRecommended
                                        ? 3.0
                                        : (isNearCompletion ? 2.6 : 2.0),
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: color.withValues(
                                        alpha: pulseOpacity * 0.5,
                                      ),
                                      blurRadius: isRecommended
                                          ? 20
                                          : (isNearCompletion ? 16 : 12),
                                      spreadRadius: isRecommended
                                          ? 4
                                          : (isNearCompletion ? 3 : 2),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),

                  // Core circle.
                  Container(
                    width: nodeSize,
                    height: nodeSize,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: node.isUnlocked
                          ? LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                color.withValues(alpha: 0.35),
                                color.withValues(alpha: 0.15),
                              ],
                            )
                          : null,
                      color: node.isUnlocked
                          ? null
                          : DS.surfaceSecondary.withValues(alpha: 0.6),
                      border: Border.all(
                        color: node.isUnlocked
                            ? color.withValues(alpha: 0.7)
                            : Colors.white.withValues(alpha: 0.1),
                        width: 1.5,
                      ),
                    ),
                    child: node.isUnlocked
                        ? Icon(
                            _iconForCategory(node.category),
                            color: color,
                            size: DS.iconSizeSm,
                          )
                        : Stack(
                            alignment: Alignment.center,
                            children: [
                              Icon(
                                _iconForCategory(node.category),
                                color: DS.textTertiary.withValues(alpha: 0.4),
                                size: DS.iconSizeSm,
                              ),
                              Icon(
                                Icons.lock_outline,
                                color: Colors.white.withValues(alpha: 0.35),
                                size: 16,
                              ),
                            ],
                          ),
                  ),

                  if (isRecommended)
                    Positioned(
                      bottom: -2,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.92),
                          borderRadius: DS.borderRadius8,
                        ),
                        child: Text(
                          'NEXT',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: DS.fontWeightBold,
                            color: DS.neutral0,
                            letterSpacing: 0.6,
                          ),
                        ),
                      ),
                    ),

                  // Milestone overlay badge.
                  Positioned(
                    top: -4,
                    right: -4,
                    child: AchievementMilestoneBadge(
                      progress: progress,
                      rarity: node.rarity,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: DS.spacing4),

            // Name label with dark background chip.
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing6,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: isRecommended
                    ? color.withValues(alpha: 0.26)
                    : DS.deepSpaceStart.withValues(alpha: 0.75),
                borderRadius: DS.borderRadius8,
                border: isRecommended
                    ? Border.all(color: color.withValues(alpha: 0.45))
                    : null,
              ),
              child: Text(
                node.name,
                maxLines: 2,
                textAlign: TextAlign.center,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightMedium,
                  color: node.isUnlocked ? DS.textPrimary : DS.textTertiary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
