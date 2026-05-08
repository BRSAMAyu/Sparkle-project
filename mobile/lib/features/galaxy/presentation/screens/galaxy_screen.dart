import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_build_playback_plan.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_accessibility_service.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_force_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_contribution_provider.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_display_settings_provider.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_document_upload_provider.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_draft_review_provider.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/galaxy/presentation/providers/goal_graph_overlay_provider.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_draft_review_screen.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_controls.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_document_upload_overlay.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_error_dialog.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_gesture_handler.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_mini_map.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_search_panel.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_simulation_settings_sheet.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_success_animation.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy_contribution_banner.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

final galaxyBuildPlaybackSessionProvider = StateProvider<bool>(
  (ref) => false,
);

class GalaxyPlaybackSnapshot {
  const GalaxyPlaybackSnapshot({
    required this.plan,
    required this.frozenPositions,
    required this.settledPositions,
    required this.preRevealedNodeIds,
    required this.preRevealedEdgeIds,
  });

  final GalaxyBuildPlaybackPlan plan;
  final Map<String, Offset> frozenPositions;
  final Map<String, Offset> settledPositions;
  final Set<String> preRevealedNodeIds;
  final Set<String> preRevealedEdgeIds;

  GalaxyPlaybackSnapshot copyWith({
    GalaxyBuildPlaybackPlan? plan,
    Map<String, Offset>? frozenPositions,
    Map<String, Offset>? settledPositions,
    Set<String>? preRevealedNodeIds,
    Set<String>? preRevealedEdgeIds,
  }) =>
      GalaxyPlaybackSnapshot(
        plan: plan ?? this.plan,
        frozenPositions: frozenPositions ?? this.frozenPositions,
        settledPositions: settledPositions ?? this.settledPositions,
        preRevealedNodeIds: preRevealedNodeIds ?? this.preRevealedNodeIds,
        preRevealedEdgeIds: preRevealedEdgeIds ?? this.preRevealedEdgeIds,
      );
}

enum _GalaxyEmptySpaceAction {
  uploadDocumentHere,
}

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({
    super.key,
    this.initialFocusNodeId,
    this.initialMasteryDelta,
    this.initialPackId,
  });

  final String? initialFocusNodeId;
  final double? initialMasteryDelta;
  final String? initialPackId;

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen>
    with TickerProviderStateMixin, AutomaticKeepAliveClientMixin {
  static const bool _useDarkGalaxyTheme = true;

  late final GalaxyGestureHandler _gestureHandler;
  late final Ticker _flingTicker;
  late final Ticker _physicsTicker;
  late final Ticker _ambientTicker;
  late final GalaxySpatialIndex _spatialIndex;
  late final GalaxyForceEngine _forceEngine;
  late final GalaxyAccessibilityService _accessibilityService;
  late final GalaxyLabelCache _labelCache;
  late final GalaxyBackdropPictureCache _backdropPictureCache;
  late final GalaxyParallaxStarLayerCache _parallaxStarLayerCache;
  late final TextEditingController _searchController;
  late final AnimationController _tapFeedbackController;
  late final AnimationController _cameraAnimationController;
  late final AnimationController _buildReplayController;
  late final AnimationController _layoutBlendController;
  late final AnimationController _entranceController;
  late final Animation<double> _tapFeedbackAnimation;
  late final ProviderSubscription<GalaxyDisplaySettings>
      _displaySettingsSubscription;
  late final ProviderSubscription<GalaxyState> _galaxySubscription;
  late final ProviderSubscription<int> _refreshTriggerSubscription;

  GalaxyGraphResponse? _graph;
  Map<String, Offset> _positions = const <String, Offset>{};
  Map<String, GalaxyNodeModel> _nodesById = const <String, GalaxyNodeModel>{};
  Map<String, Set<String>> _adjacency = const <String, Set<String>>{};
  Map<String, int> _nodeConnectionCounts = const <String, int>{};
  Map<String, double> _edgeStrengths = const <String, double>{};
  Map<String, Color> _darkBlendedColors = const <String, Color>{};
  Map<String, Color> _lightBlendedColors = const <String, Color>{};
  GalaxyBuildPlaybackPlan? _playbackPlan;
  GalaxyPlaybackSnapshot? _playbackSnapshot;
  Set<String> _preRevealedNodeIds = const <String>{};
  Set<String> _preRevealedEdgeIds = const <String>{};
  GalaxyCamera _camera = const GalaxyCamera(
    offset: Offset.zero,
    scale: 0.15,
    viewportSize: Size.zero,
  );
  FrictionSimulation? _flingX;
  FrictionSimulation? _flingY;
  GalaxyCamera? _cameraAnimationStart;
  GalaxyCamera? _cameraAnimationEnd;
  Curve _cameraAnimationCurve = Curves.easeInOutCubic;
  double _cameraAnimationArcScaleOutFactor = 1.0;
  Object? _loadError;
  String? _selectedNodeId;
  String? _draggingNodeId;
  String? _tapFeedbackNodeId;
  String? _pendingNavigationNodeId;
  String? _pendingPersistNodeId;
  _DraftArrivalCelebration? _draftArrivalCelebration;
  GalaxyNodeModel? _previewNode;
  Offset? _previewScreenPosition;
  Size _viewportSize = Size.zero;
  bool _isLoading = true;
  bool _didFitInitialCamera = false;
  bool _didPlayEntranceAnimation = false;
  bool _isBuildAnimating = false;
  bool _isSearchOpen = false;
  bool _isSettingsOpen = false;
  bool _performanceDegraded = false;
  double _ambientPhase = 0;
  int _sceneVersion = 0;
  String _searchQuery = '';
  List<GalaxyNodeModel> _searchResults = const <GalaxyNodeModel>[];
  Set<String> _searchMatchedNodeIds = const <String>{};
  Set<String> _spotlightNodeIds = const <String>{};
  String? _spotlightAnchorId;
  Map<String, Offset> _microDriftOffsets = const <String, Offset>{};
  bool _isGoalWorldMode = false;
  Set<String> _goalWorldNodeIds = const <String>{};
  List<GalaxyEdgeParticle> _edgeParticles = const <GalaxyEdgeParticle>[];
  List<_CelebrationEntry> _celebrations = const <_CelebrationEntry>[];
  Duration _ambientElapsed = Duration.zero;
  Duration _lastInteractionElapsed = Duration.zero;
  Duration _lastDriftShuffleElapsed = Duration.zero;
  int _consecutiveSlowFrames = 0;
  int _consecutiveFastFrames = 0;
  int _playbackElapsedMs = 0;
  double _frameBudgetMs = 16;
  double _activeReplaySpeedMultiplier = 1.0;
  bool _physicsUsesViewportCulling = true;
  Timer? _previewDismissTimer;
  Timer? _initialBuildReplayTimer;
  Timer? _pendingExternalFocusTimer;
  int _layoutOptimizationEpoch = 0;
  Map<String, Offset> _layoutBlendStartPositions = const <String, Offset>{};
  Map<String, Offset> _layoutBlendTargetPositions = const <String, Offset>{};
  bool _didApplyProviderGraph = false;
  bool? _nextProviderGraphPreserveCamera;
  String? _pendingExternalFocusNodeId;
  double? _pendingExternalMasteryDelta;
  GoRouter? _router;
  String? _lastObservedRoutePath;
  bool _isDraftReviewOpen = false;

  // Mastery milestone subscription
  StreamSubscription<MasteryMilestoneEvent>? _milestoneSubscription;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _pendingExternalFocusNodeId = widget.initialFocusNodeId;
    _pendingExternalMasteryDelta = widget.initialMasteryDelta;
    _spatialIndex = GalaxySpatialIndex();
    _forceEngine = GalaxyForceEngine();
    _accessibilityService = GalaxyAccessibilityService();
    _labelCache = GalaxyLabelCache();
    _backdropPictureCache = GalaxyBackdropPictureCache();

    _parallaxStarLayerCache = GalaxyParallaxStarLayerCache();
    _searchController = TextEditingController();
    _gestureHandler = GalaxyGestureHandler(
      screenToWorld: (screenPoint) => _camera.screenToWorld(screenPoint),
      hitTestNode: _hitTestNode,
      onCommand: _handleGestureCommand,
    );
    _displaySettingsSubscription = ref.listenManual<GalaxyDisplaySettings>(
      galaxyDisplaySettingsProvider,
      (previous, next) => _applyDisplaySettings(previous: previous, next: next),
      fireImmediately: true,
    );
    _galaxySubscription = ref.listenManual<GalaxyState>(
      galaxyProvider,
      _handleGalaxyStateChanged,
    );
    _refreshTriggerSubscription = ref.listenManual<int>(
      galaxyRefreshTriggerProvider,
      (previous, next) {
        if (previous == null || previous == next || !mounted) {
          return;
        }
        unawaited(
          _loadGraph(
            forceRefresh: true,
            preserveCamera: true,
          ),
        );
      },
    );
    // Subscribe to mastery milestone events for celebration animation
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _milestoneSubscription = ref
          .read(galaxyProvider.notifier)
          .masteryMilestones
          .listen(_handleMasteryMilestone);
    });
    _flingTicker = createTicker(_handleFlingTick);
    _physicsTicker = createTicker(_handlePhysicsTick);
    _ambientTicker = createTicker(_handleAmbientTick);
    _tapFeedbackController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 420),
    );
    _cameraAnimationController = AnimationController(vsync: this)
      ..addListener(_handleCameraAnimationTick);
    _buildReplayController = AnimationController(vsync: this)
      ..addListener(_handleBuildReplayTick)
      ..addStatusListener(_handleBuildReplayStatus);
    _layoutBlendController = AnimationController(vsync: this)
      ..addListener(_handleLayoutBlendTick)
      ..addStatusListener(_handleLayoutBlendStatus);
    _entranceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 620),
    );
    _tapFeedbackAnimation = TweenSequence<double>([
      TweenSequenceItem<double>(
        tween: Tween<double>(
          begin: 0,
          end: 1,
        ).chain(CurveTween(curve: Curves.easeOutBack)),
        weight: 55,
      ),
      TweenSequenceItem<double>(
        tween: Tween<double>(
          begin: 1,
          end: 0,
        ).chain(CurveTween(curve: Curves.easeOut)),
        weight: 45,
      ),
    ]).animate(_tapFeedbackController)
      ..addListener(() {
        if (!mounted || _tapFeedbackNodeId == null) {
          return;
        }
        setState(() {});
      });
    _tapFeedbackController.addStatusListener(_handleTapFeedbackStatus);
    SchedulerBinding.instance.addTimingsCallback(_handleFrameTimings);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      unawaited(_ambientTicker.start());
      unawaited(_loadGraph().whenComplete(_schedulePendingExternalFocus));
    });
  }

  @override
  void didUpdateWidget(covariant GalaxyScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final sameInitialFocus =
        widget.initialFocusNodeId == oldWidget.initialFocusNodeId &&
            widget.initialMasteryDelta == oldWidget.initialMasteryDelta;
    if (widget.initialFocusNodeId == null || sameInitialFocus) {
      return;
    }
    _pendingExternalFocusNodeId = widget.initialFocusNodeId;
    _pendingExternalMasteryDelta = widget.initialMasteryDelta;
    _schedulePendingExternalFocus();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _accessibilityService.initialize(context);
    final refreshRate = View.maybeOf(context)?.display.refreshRate ?? 60;
    _frameBudgetMs = 1000 / (refreshRate <= 0 ? 60 : refreshRate);
    _attachRouteRefreshListener();
  }

  @override
  void dispose() {
    _gestureHandler.dispose();
    _labelCache.clear();
    _backdropPictureCache.clear();
    _parallaxStarLayerCache.clear();
    _flingTicker.dispose();
    _physicsTicker.dispose();
    _ambientTicker.dispose();
    _searchController.dispose();
    _tapFeedbackController
      ..removeStatusListener(_handleTapFeedbackStatus)
      ..dispose();
    _cameraAnimationController
      ..removeListener(_handleCameraAnimationTick)
      ..dispose();
    _buildReplayController
      ..removeListener(_handleBuildReplayTick)
      ..removeStatusListener(_handleBuildReplayStatus)
      ..dispose();
    _layoutBlendController
      ..removeListener(_handleLayoutBlendTick)
      ..removeStatusListener(_handleLayoutBlendStatus)
      ..dispose();
    _entranceController.dispose();
    _displaySettingsSubscription.close();
    _galaxySubscription.close();
    _refreshTriggerSubscription.close();
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    unawaited(_milestoneSubscription?.cancel());
    _previewDismissTimer?.cancel();
    _initialBuildReplayTimer?.cancel();
    _pendingExternalFocusTimer?.cancel();
    SchedulerBinding.instance.removeTimingsCallback(_handleFrameTimings);
    super.dispose();
  }

  void _handleGalaxyStateChanged(GalaxyState? previous, GalaxyState next) {
    if (!mounted) {
      return;
    }

    if (next.isLoading && !_isLoading) {
      setState(() {
        _isLoading = true;
        _loadError = null;
      });
    }

    if (next.lastError != null && !next.isLoading) {
      if (previous?.lastError?.message != next.lastError!.message) {
        GalaxyErrorSnackBar.show(
          context,
          error: next.lastError!,
          onRetry: _loadGraph,
        );
      }
      setState(() {
        _isLoading = false;
        _loadError = next.lastError!.message;
      });
    }

    final graphChanged = _graph == null ||
        previous == null ||
        previous.isLoading != next.isLoading ||
        !identical(previous.nodes, next.nodes) ||
        !identical(previous.edges, next.edges) ||
        previous.userFlameIntensity != next.userFlameIntensity;
    if (!graphChanged) {
      return;
    }

    // Skip applying an empty graph during initial loading — wait for real data.
    // Without this guard, the first isLoading:true state transition sets
    // _isLoading=false and briefly shows the "empty galaxy" panel before the
    // actual graph data arrives.
    if (next.isLoading && next.nodes.isEmpty && _graph == null) {
      return;
    }

    final preserveCamera =
        _nextProviderGraphPreserveCamera ?? _didApplyProviderGraph;
    _nextProviderGraphPreserveCamera = null;
    _didApplyProviderGraph = true;
    _applyGraphData(
      GalaxyGraphResponse(
        nodes: next.nodes,
        edges: next.edges,
        userFlameIntensity: next.userFlameIntensity,
      ),
      preserveCamera: preserveCamera,
    );
  }

  void _attachRouteRefreshListener() {
    final router = GoRouter.maybeOf(context);
    if (router == null) {
      _router?.routeInformationProvider.removeListener(
        _handleRouteVisibilityChanged,
      );
      _router = null;
      _lastObservedRoutePath = null;
      return;
    }
    if (identical(_router, router)) {
      return;
    }
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    _router = router;
    _lastObservedRoutePath = router.routeInformationProvider.value.uri.path;
    router.routeInformationProvider.addListener(_handleRouteVisibilityChanged);
  }

  void _handleRouteVisibilityChanged() {
    final path = _router?.routeInformationProvider.value.uri.path;
    final previousPath = _lastObservedRoutePath;
    _lastObservedRoutePath = path;
    if (!mounted ||
        path != GalaxyRoutes.home ||
        previousPath == GalaxyRoutes.home) {
      return;
    }

    unawaited(
      _loadGraph(
        forceRefresh: true,
        preserveCamera: true,
      ),
    );
  }

  Future<void> _handlePullToRefresh() async {
    await Future.wait<void>([
      _loadGraph(
        forceRefresh: true,
        preserveCamera: true,
      ),
      ref.read(galaxyDraftReviewProvider.notifier).refresh(),
    ]);
  }

  Future<void> _loadGraph({
    bool forceRefresh = false,
    bool preserveCamera = false,
  }) async {
    _stopAllAutoMotion(commitPhysicsPosition: true);
    if (forceRefresh || _graph == null) {
      ref.invalidate(galaxyContributionProvider);
    }
    if (!preserveCamera) {
      setState(() {
        _isLoading = true;
        _loadError = null;
      });
    }

    _nextProviderGraphPreserveCamera = preserveCamera;
    await ref
        .read(galaxyProvider.notifier)
        .loadGalaxy(forceRefresh: forceRefresh);
  }

  void _schedulePendingExternalFocus() {
    if (_pendingExternalFocusNodeId == null) {
      return;
    }
    _pendingExternalFocusTimer?.cancel();
    _pendingExternalFocusTimer = Timer(
      const Duration(milliseconds: 180),
      _applyPendingExternalFocus,
    );
  }

  void _applyPendingExternalFocus() {
    final nodeId = _pendingExternalFocusNodeId;
    if (!mounted || nodeId == null || _graph == null) {
      return;
    }
    if (_viewportSize == Size.zero || !_renderPositions.containsKey(nodeId)) {
      _schedulePendingExternalFocus();
      return;
    }

    final node = _nodesById[nodeId];
    if (node == null) {
      _pendingExternalFocusNodeId = null;
      _pendingExternalMasteryDelta = null;
      return;
    }

    final masteryDelta = _pendingExternalMasteryDelta;
    _pendingExternalFocusNodeId = null;
    _pendingExternalMasteryDelta = null;

    ref
        .read(galaxyProvider.notifier)
        .setEvidenceHighlight({nodeId}, focusId: nodeId);
    _focusOnNode(nodeId, targetScale: 0.9);
    _pulseNodeWithoutNavigation(nodeId);
    _showErrorImpactMessage(node, masteryDelta);
  }

  void _pulseNodeWithoutNavigation(String nodeId) {
    setState(() {
      _tapFeedbackNodeId = nodeId;
      _pendingNavigationNodeId = null;
    });
    _tapFeedbackController
      ..stop()
      ..reset();
    unawaited(_tapFeedbackController.forward());
  }

  void _showErrorImpactMessage(GalaxyNodeModel node, double? masteryDelta) {
    final deltaText = masteryDelta == null
        ? ''
        : masteryDelta < 0
            ? context.l10n.galaxyMasteryDeltaDown(
                masteryDelta
                    .abs()
                    .toStringAsFixed(masteryDelta.abs() >= 1 ? 0 : 1),
              )
            : context.l10n.galaxyMasteryDeltaUp(
                masteryDelta.toStringAsFixed(masteryDelta.abs() >= 1 ? 0 : 1),
              );
    AppFeedback.info(
      context,
      context.l10n.galaxyNodeMasteryToast(
        node.name,
        node.masteryScore,
        deltaText,
      ),
    );
  }

  void _syncProviderSelection(String? nodeId) {
    final notifier = ref.read(galaxyProvider.notifier);
    if (nodeId == null) {
      notifier.deselectNode();
      return;
    }
    notifier.selectNode(nodeId);
  }

  void _syncProviderScale(double scale) {
    ref.read(galaxyProvider.notifier).updateScale(scale);
  }

  void _applyGraphData(
    GalaxyGraphResponse graph, {
    required bool preserveCamera,
  }) {
    final previousGraph = _graph;
    final sanitizedGraph = _sanitizeGraph(graph);
    final positions = _resolvePositions(sanitizedGraph);
    final nodesById = {
      for (final node in sanitizedGraph.nodes) node.id: node,
    };
    final adjacency = _buildAdjacency(sanitizedGraph.edges);
    final nodeConnectionCounts = {
      for (final entry in adjacency.entries) entry.key: entry.value.length,
    };
    final edgeStrengths = _buildEdgeStrengths(graph.edges);
    final darkBlendedColors = _buildBlendedColors(
      nodesById: nodesById,
      adjacency: adjacency,
      isDarkMode: true,
    );
    final lightBlendedColors = _buildBlendedColors(
      nodesById: nodesById,
      adjacency: adjacency,
      isDarkMode: false,
    );
    final playbackLaunch = _buildPlaybackLaunch(
      previousGraph: previousGraph,
      nextGraph: sanitizedGraph,
      positions: positions,
      adjacency: adjacency,
      preserveCamera: preserveCamera,
    );
    final playbackSpeedMultiplier =
        preserveCamera ? 1.0 : (playbackLaunch == null ? 1.0 : 1.45);

    _spatialIndex.build(positions, sanitizedGraph.nodes);
    _labelCache.clear();
    setState(() {
      _layoutBlendController
        ..stop()
        ..reset();
      _layoutBlendStartPositions = const <String, Offset>{};
      _layoutBlendTargetPositions = const <String, Offset>{};
      _graph = sanitizedGraph;
      _positions = positions;
      _nodesById = nodesById;
      _adjacency = adjacency;
      _nodeConnectionCounts = nodeConnectionCounts;
      _edgeStrengths = edgeStrengths;
      _darkBlendedColors = darkBlendedColors;
      _lightBlendedColors = lightBlendedColors;
      _pendingPersistNodeId = null;
      _isLoading = false;
      _didFitInitialCamera = preserveCamera;
      if (playbackLaunch != null) {
        _primePlaybackState(
          playbackLaunch,
          speedMultiplier: playbackSpeedMultiplier,
        );
      } else {
        _clearPlaybackState();
      }
      _sceneVersion++;
    });

    _scheduleLayoutOptimization(
      graph: sanitizedGraph,
      basePositions: positions,
    );

    if (!preserveCamera) {
      _startEntranceAnimationIfNeeded(playbackLaunch: playbackLaunch);
    } else {
      _refreshSearchState();
      _syncPreviewPosition();
      if (playbackLaunch != null) {
        _startPreparedPlayback(preRoll: const Duration(milliseconds: 60));
      } else {
        _startGraphSettleSimulation(impulse: 0.28);
      }
    }
    _schedulePendingExternalFocus();
  }

  Map<String, Offset> get _renderPositions =>
      _isBuildAnimating && _playbackSnapshot != null
          ? _playbackSnapshot!.frozenPositions
          : _positions;

  void _handleLayoutBlendTick() {
    if (_layoutBlendStartPositions.isEmpty ||
        _layoutBlendTargetPositions.isEmpty) {
      return;
    }
    final progress = Curves.easeInOutCubic.transform(
      _layoutBlendController.value.clamp(0.0, 1.0),
    );
    final blended = <String, Offset>{};
    for (final entry in _layoutBlendTargetPositions.entries) {
      final start = _layoutBlendStartPositions[entry.key] ?? entry.value;
      blended[entry.key] = Offset.lerp(start, entry.value, progress)!;
    }

    if (!mounted) {
      _positions = blended;
      return;
    }
    setState(() {
      _positions = blended;
      _sceneVersion++;
    });
  }

  void _handleLayoutBlendStatus(AnimationStatus status) {
    if (!mounted || status != AnimationStatus.completed) {
      return;
    }
    setState(() {
      _positions = _layoutBlendTargetPositions;
      _layoutBlendStartPositions = const <String, Offset>{};
      _layoutBlendTargetPositions = const <String, Offset>{};
      _sceneVersion++;
    });
    if (_graph != null) {
      _spatialIndex.build(_positions, _graph!.nodes);
    }
    if (!_isBuildAnimating && _graph != null) {
      _startGraphSettleSimulation(impulse: 0.12);
    }
  }

  void _startEntranceAnimationIfNeeded({
    required _PlaybackLaunch? playbackLaunch,
  }) {
    if (_viewportSize == Size.zero || _graph == null) {
      return;
    }

    final overviewCamera = _fitOverviewCamera();
    final sessionPlayedFullReplay =
        ref.read(galaxyBuildPlaybackSessionProvider);
    if (_didPlayEntranceAnimation || sessionPlayedFullReplay) {
      setState(() {
        _camera = overviewCamera;
        _didFitInitialCamera = true;
      });
      _startGraphSettleSimulation(impulse: 0.28);
      return;
    }

    final worldCenter = _computeWorldBounds().center;
    final introScale =
        (overviewCamera.scale * 0.12).clamp(overviewCamera.minScale, 0.12);
    final introCamera = overviewCamera
        .copyWith(scale: introScale)
        .centerOnWorldPoint(worldPoint: worldCenter);

    setState(() {
      _camera = introCamera;
      _didFitInitialCamera = true;
      _didPlayEntranceAnimation = true;
    });
    if (playbackLaunch != null) {
      ref.read(galaxyBuildPlaybackSessionProvider.notifier).state = true;
    }

    _entranceController
      ..stop()
      ..reset();
    _animateCameraTo(
      overviewCamera,
      duration: const Duration(milliseconds: 1400),
      curve: Curves.easeOutCubic,
    );
    _initialBuildReplayTimer?.cancel();
    _initialBuildReplayTimer = Timer(const Duration(milliseconds: 140), () {
      if (!mounted || _graph == null || playbackLaunch == null) {
        return;
      }
      _startPreparedPlayback(preRoll: const Duration(milliseconds: 30));
    });
    unawaited(_entranceController.forward());
  }

  void _refreshSearchState() {
    if (_searchQuery.trim().isEmpty) {
      return;
    }
    _updateSearchQuery(_searchQuery, updateTextField: false);
  }

  void _syncPreviewPosition() {
    final previewNode = _previewNode;
    if (previewNode == null) {
      return;
    }
    final anchor = _renderPositions[previewNode.id];
    if (anchor == null) {
      return;
    }
    _previewScreenPosition = _computePreviewPosition(
      anchor: _camera.worldToScreen(anchor),
      node: previewNode,
    );
  }

  Map<String, Offset> _resolvePositions(GalaxyGraphResponse graph) {
    final stablePositions = <String, Offset>{};
    for (final node in graph.nodes) {
      if (node.hasStablePosition) {
        stablePositions[node.id] = Offset(node.positionX!, node.positionY!);
      }
    }

    if (stablePositions.length == graph.nodes.length) {
      return stablePositions;
    }

    return GalaxyLayoutEngine.calculateInitialLayout(
      nodes: graph.nodes,
      edges: graph.edges,
      existingPositions: stablePositions.isEmpty ? null : stablePositions,
    );
  }

  Rect _computeWorldBounds() {
    final activePositions = _renderPositions;
    if (activePositions.isEmpty) {
      return Rect.fromCircle(center: Offset.zero, radius: 240);
    }

    var minX = double.infinity;
    var minY = double.infinity;
    var maxX = double.negativeInfinity;
    var maxY = double.negativeInfinity;

    for (final position in activePositions.values) {
      minX = math.min(minX, position.dx);
      minY = math.min(minY, position.dy);
      maxX = math.max(maxX, position.dx);
      maxY = math.max(maxY, position.dy);
    }

    return Rect.fromLTRB(minX, minY, maxX, maxY);
  }

  GalaxyCamera _fitOverviewCamera() => GalaxyCamera.fitRect(
        worldBounds: _computeWorldBounds(),
        viewportSize: _viewportSize,
      );

  GalaxyNodeHit? _hitTestNode(Offset worldPoint) {
    if (_isBuildAnimating ||
        _graph == null ||
        _renderPositions.isEmpty ||
        _spatialIndex.size == 0) {
      return null;
    }

    final tapRadius = math.max(20 / _camera.scale, 16.0);
    return _spatialIndex.queryNearest(worldPoint, tapRadius);
  }

  String? _hitTestPredictionOverlayNode(Offset worldPoint) {
    final overlay = ref.read(theaterOverlayProvider);
    if (overlay == null || overlay.focusNodeIds.isEmpty) {
      return null;
    }
    final tapRadius = math.max(26 / _camera.scale, 18.0);
    for (final nodeId in overlay.focusNodeIds.reversed) {
      final position = _renderPositions[nodeId];
      if (position == null) {
        continue;
      }
      if ((position - worldPoint).distance <= tapRadius) {
        return nodeId;
      }
    }
    return null;
  }

  void _openPredictionOverlay(String? targetNodeId) {
    final overlay = ref.read(theaterOverlayProvider);
    final query = <String, String>{
      if (targetNodeId != null && targetNodeId.isNotEmpty)
        'target_node_id': targetNodeId,
      if (overlay != null && overlay.topic.isNotEmpty) 'topic': overlay.topic,
    };
    final uri =
        Uri(path: '/theater', queryParameters: query.isEmpty ? null : query);
    unawaited(context.push(uri.toString()));
  }

  void _launchPredictionForPreviewNode() {
    final previewNode = _previewNode;
    if (previewNode == null) {
      return;
    }
    final query = <String, String>{
      'target_node_id': previewNode.id,
      'topic': previewNode.name,
    };
    setState(_clearPreviewState);
    unawaited(
      context.push(
        Uri(path: '/theater', queryParameters: query).toString(),
      ),
    );
  }

  void _startReviewForPreviewNode() {
    final previewNode = _previewNode;
    if (previewNode == null) {
      return;
    }
    _startReviewForNode(previewNode);
  }

  void _startReviewForNode(GalaxyNodeModel node) {
    final focusPrompt = node.reviewUrgencyReason == 'recent_errors'
        ? context.l10n
            .galaxyReviewPromptWithErrors(node.name, node.masteryScore)
        : context.l10n.galaxyReviewPromptNoErrors(node.name, node.masteryScore);
    final chatMode = node.reviewUrgencyReason == 'recent_errors'
        ? 'error_diagnosis'
        : 'study_plan';
    final query = <String, String>{
      'prompt': focusPrompt,
      'chat_mode': chatMode,
      'target_node_id': node.id,
    };
    setState(_clearPreviewState);
    unawaited(
      context.push(
        Uri(path: '/chat', queryParameters: query).toString(),
      ),
    );
  }

  void _showPreviewForNode(
    GalaxyNodeModel node, {
    required Offset anchor,
    bool scheduleDismiss = false,
  }) {
    _previewDismissTimer?.cancel();
    setState(() {
      _cancelTapFeedbackState();
      _selectedNodeId = node.id;
      _spotlightAnchorId = node.id;
      _spotlightNodeIds = _spotlightSetFor(node.id);
      _draggingNodeId = null;
      _previewNode = node;
      _previewScreenPosition = _computePreviewPosition(
        anchor: anchor,
        node: node,
      );
    });
    _syncProviderSelection(node.id);
    if (scheduleDismiss) {
      _schedulePreviewDismiss();
    }
  }

  void _handleGestureCommand(GalaxyGestureCommand command) {
    _noteInteraction();

    if (command is PanCommand) {
      _stopFling();
      _stopPhysicsSimulation(commitPendingNode: true);
      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _camera = _camera.applyPan(command.delta);
        _microDriftOffsets = const <String, Offset>{};
      });
      return;
    }

    if (command is ZoomCommand) {
      _stopFling();
      _stopPhysicsSimulation(commitPendingNode: true);
      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _camera = _camera.applyZoom(command.scaleDelta, command.focalPoint);
        _microDriftOffsets = const <String, Offset>{};
      });
      _syncProviderScale(_camera.scale);
      return;
    }

    if (command is DoubleTapCommand) {
      _handleDoubleTap(command);
      return;
    }

    if (command is TapCommand) {
      _stopBuildReplay();
      _stopPhysicsSimulation(commitPendingNode: true);
      final overlayNodeId =
          _hitTestPredictionOverlayNode(command.worldPosition);
      if (overlayNodeId != null) {
        _openPredictionOverlay(overlayNodeId);
        return;
      }
      if (command.hit == null) {
        setState(() {
          _selectedNodeId = null;
          _spotlightAnchorId = null;
          _spotlightNodeIds = const <String>{};
          _cancelTapFeedbackState();
          _clearPreviewState();
        });
        _syncProviderSelection(null);
        return;
      }

      final tappedNode = _nodesById[command.hit!.nodeId];
      if (tappedNode == null) {
        return;
      }

      if (!tappedNode.isUnlocked) {
        unawaited(_accessibilityService.lightHaptic());
        _showPreviewForNode(
          tappedNode,
          anchor: _camera.worldToScreen(command.hit!.worldPosition),
        );
        return;
      }

      _startTapFeedback(command.hit!.nodeId);
      return;
    }

    if (command is LongPressCommand) {
      _stopBuildReplay();
      _stopPhysicsSimulation(commitPendingNode: true);
      if (command.hit == null) {
        setState(() {
          _selectedNodeId = null;
          _clearPreviewState();
        });
        _syncProviderSelection(null);
        unawaited(_showEmptySpaceUploadMenu(command));
        return;
      }

      final previewNode = _nodesById[command.hit!.nodeId];
      if (previewNode == null) {
        return;
      }

      unawaited(_accessibilityService.mediumHaptic());
      _showPreviewForNode(
        previewNode,
        anchor: _camera.worldToScreen(command.hit!.worldPosition),
      );
      _schedulePreviewDismiss();
      return;
    }

    if (command is DragNodeCommand) {
      final currentPosition = _positions[command.nodeId];
      if (currentPosition == null || _graph == null) {
        return;
      }

      _stopFling();
      _stopBuildReplay();
      if (_draggingNodeId != command.nodeId) {
        _stopPhysicsSimulation(commitPendingNode: true);
        _forceEngine.anchorNode(command.nodeId, _adjacency);
      }

      final worldDelta = Offset(
        command.screenDelta.dx / _camera.scale,
        command.screenDelta.dy / _camera.scale,
      );
      final updatedPositions = Map<String, Offset>.from(_positions)
        ..[command.nodeId] = currentPosition + worldDelta;

      _spatialIndex.build(updatedPositions, _graph!.nodes);
      _startPhysicsSimulation();
      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _selectedNodeId = command.nodeId;
        _spotlightAnchorId = command.nodeId;
        _spotlightNodeIds = _spotlightSetFor(command.nodeId);
        _draggingNodeId = command.nodeId;
        _positions = updatedPositions;
        _microDriftOffsets = const <String, Offset>{};
      });
      _syncProviderSelection(command.nodeId);
      return;
    }

    if (command is FlingCommand) {
      _stopPhysicsSimulation(commitPendingNode: true);
      _startFling(command.velocity);
    }
  }

  void _handleDoubleTap(DoubleTapCommand command) {
    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    _cancelTapFeedbackState();
    _clearPreviewState();

    if (command.hit != null) {
      final nodeId = command.hit!.nodeId;
      _focusOnNode(nodeId);
      return;
    }

    if (_camera.scale >= 0.72) {
      setState(() {
        _selectedNodeId = null;
        _spotlightAnchorId = null;
        _spotlightNodeIds = const <String>{};
      });
      _syncProviderSelection(null);
      _fitOverviewAnimated();
      return;
    }

    final targetScale = 0.6.clamp(_camera.minScale, _camera.maxScale);
    final targetCamera = _camera
        .copyWith(scale: targetScale)
        .centerOnWorldPoint(worldPoint: command.worldPosition);
    _animateCameraTo(
      targetCamera,
      duration: const Duration(milliseconds: 360),
      curve: Curves.easeOutCubic,
      arcScaleOutFactor: 1.03,
    );
  }

  void _handleTapFeedbackStatus(AnimationStatus status) {
    if (status != AnimationStatus.completed || !mounted) {
      return;
    }

    final nodeId = _pendingNavigationNodeId;
    setState(() {
      _tapFeedbackNodeId = null;
      _pendingNavigationNodeId = null;
    });
    _tapFeedbackController.reset();

    if (nodeId != null) {
      unawaited(_openNodeDetailSheet(nodeId));
    }
  }

  void _startTapFeedback(String nodeId) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    setState(() {
      _clearPreviewState();
      _selectedNodeId = nodeId;
      _tapFeedbackNodeId = nodeId;
      _pendingNavigationNodeId = nodeId;
      _draggingNodeId = null;
      _spotlightAnchorId = nodeId;
      _spotlightNodeIds = _spotlightSetFor(nodeId);
    });
    _syncProviderSelection(nodeId);
    _tapFeedbackController
      ..stop()
      ..reset();
    unawaited(_tapFeedbackController.forward());
  }

  void _cancelTapFeedbackState() {
    if (_tapFeedbackNodeId == null &&
        _pendingNavigationNodeId == null &&
        !_tapFeedbackController.isAnimating) {
      return;
    }

    _tapFeedbackController
      ..stop()
      ..reset();
    _tapFeedbackNodeId = null;
    _pendingNavigationNodeId = null;
  }

  void _clearPreviewState() {
    _previewDismissTimer?.cancel();
    _previewNode = null;
    _previewScreenPosition = null;
  }

  void _schedulePreviewDismiss([
    Duration delay = const Duration(milliseconds: 14000),
  ]) {
    _previewDismissTimer?.cancel();
    _previewDismissTimer = Timer(delay, () {
      if (!mounted || _previewNode == null) {
        return;
      }
      setState(_clearPreviewState);
    });
  }

  void _noteInteraction() {
    _lastInteractionElapsed = _ambientElapsed;
    if (_microDriftOffsets.isNotEmpty && mounted) {
      setState(() {
        _microDriftOffsets = const <String, Offset>{};
      });
    }
  }

  Set<String> _spotlightSetFor(
    String nodeId, {
    bool includeNeighbors = true,
  }) =>
      includeNeighbors
          ? <String>{nodeId, ...?_adjacency[nodeId]}
          : <String>{nodeId};

  Offset _computePreviewPosition({
    required Offset anchor,
    GalaxyNodeModel? node,
  }) {
    final activeNode = node ?? _previewNode;
    final hasReviewOverlay = activeNode?.shouldPulseForReview ?? false;
    final cardWidth = hasReviewOverlay ? 252.0 : 220.0;
    final cardHeight = hasReviewOverlay ? 352.0 : 244.0;
    const gap = 16.0;
    const edgePadding = 12.0;

    var left = anchor.dx + gap;
    var top = anchor.dy + gap;

    if (_viewportSize.width - left < cardWidth) {
      left = anchor.dx - cardWidth - gap;
    }
    if (_viewportSize.height - top < cardHeight) {
      top = anchor.dy - cardHeight - gap;
    }

    left =
        left.clamp(edgePadding, _viewportSize.width - cardWidth - edgePadding);
    top =
        top.clamp(edgePadding, _viewportSize.height - cardHeight - edgePadding);
    return Offset(left, top);
  }

  void _handlePointerDown(PointerDownEvent event) {
    _noteInteraction();
    if (_tapFeedbackController.isAnimating ||
        _pendingNavigationNodeId != null) {
      setState(_cancelTapFeedbackState);
    }
    _gestureHandler.handlePointerDown(event);
  }

  void _handlePointerUp(PointerUpEvent event) {
    _noteInteraction();
    _gestureHandler.handlePointerUp(event);
    _finalizePointerSequence();
  }

  void _handlePointerCancel(PointerCancelEvent event) {
    _noteInteraction();
    _gestureHandler.handlePointerCancel(event);
    _finalizePointerSequence();
  }

  void _handlePointerSignal(PointerSignalEvent event) {
    _noteInteraction();
    if (_previewNode != null ||
        _tapFeedbackController.isAnimating ||
        _pendingNavigationNodeId != null) {
      setState(() {
        _clearPreviewState();
        _cancelTapFeedbackState();
      });
    }
    _gestureHandler.handlePointerSignal(event);
  }

  void _finalizePointerSequence() {
    final dragNodeId = _draggingNodeId;
    if (_previewNode == null && dragNodeId == null) {
      return;
    }

    setState(() {
      if (dragNodeId != null) {
        _clearPreviewState();
        _draggingNodeId = null;
        _pendingPersistNodeId = dragNodeId;
        _sceneVersion++;
      }
    });

    if (dragNodeId != null && _graph != null) {
      unawaited(_accessibilityService.selectionHaptic());
      _forceEngine.releaseAnchor();
      _startPhysicsSimulation();
    }
  }

  void _startFling(Velocity velocity) {
    _flingX = FrictionSimulation(
      0.12,
      _camera.offset.dx,
      velocity.pixelsPerSecond.dx,
    );
    _flingY = FrictionSimulation(
      0.12,
      _camera.offset.dy,
      velocity.pixelsPerSecond.dy,
    );

    if (!_flingTicker.isActive) {
      unawaited(_flingTicker.start());
    }
  }

  void _handleFlingTick(Duration elapsed) {
    final simulationX = _flingX;
    final simulationY = _flingY;
    if (simulationX == null || simulationY == null) {
      _stopFling();
      return;
    }

    final time = elapsed.inMicroseconds / Duration.microsecondsPerSecond;
    if (simulationX.isDone(time) && simulationY.isDone(time)) {
      _stopFling();
      return;
    }

    setState(() {
      _camera = _camera.copyWith(
        offset: Offset(
          simulationX.x(time),
          simulationY.x(time),
        ),
      );
    });
  }

  void _stopFling() {
    _flingX = null;
    _flingY = null;
    if (_flingTicker.isActive) {
      _flingTicker.stop();
    }
  }

  void _startPhysicsSimulation({bool useViewportCulling = true}) {
    if (_isBuildAnimating) {
      return;
    }
    _physicsUsesViewportCulling = useViewportCulling;
    if (!_physicsTicker.isActive && _forceEngine.hasActiveSimulation) {
      unawaited(_physicsTicker.start());
    }
  }

  void _handlePhysicsTick(Duration elapsed) {
    final graph = _graph;
    if (graph == null || !_forceEngine.hasActiveSimulation) {
      _stopPhysicsSimulation(commitPendingNode: true);
      return;
    }

    final result = _forceEngine.tick(
      positions: _positions,
      adjacency: _adjacency,
      edgeStrengths: _edgeStrengths,
      spatialIndex: _spatialIndex,
      viewport: _physicsUsesViewportCulling ? _camera.viewportRect : null,
    );

    _spatialIndex.build(result.positions, graph.nodes);
    if (!mounted) {
      return;
    }

    setState(() {
      _positions = result.positions;
      _sceneVersion++;
    });

    if (result.isSettled) {
      _stopPhysicsSimulation(commitPendingNode: true);
    }
  }

  void _stopPhysicsSimulation({bool commitPendingNode = false}) {
    if (_physicsTicker.isActive) {
      _physicsTicker.stop();
    }
    _physicsUsesViewportCulling = true;
    _forceEngine.clear();
    if (commitPendingNode) {
      _commitPendingNodePositionIfNeeded();
    }
  }

  void _commitPendingNodePositionIfNeeded() {
    final nodeId = _pendingPersistNodeId;
    final graph = _graph;
    if (nodeId == null || graph == null) {
      return;
    }

    final position = _positions[nodeId];
    _pendingPersistNodeId = null;
    if (position == null) {
      return;
    }

    _spatialIndex.build(_positions, graph.nodes);
    unawaited(
      ref
          .read(enhancedGalaxyRepositoryProvider)
          .updateNodePosition(nodeId, position),
    );
  }

  Future<void> _openKnowledgeDetail(String nodeId) async {
    final previousNode = _nodesById[nodeId];
    await context.pushNamed(
      'knowledgeDetail',
      pathParameters: {'id': nodeId},
    );
    if (!mounted) {
      return;
    }

    final nextNode = _nodesById[nodeId];
    if (previousNode != null && nextNode != null) {
      _triggerMasteryCelebrationIfNeeded(previousNode, nextNode);
    }
  }

  Future<void> _openNodeDetailSheet(String nodeId) async {
    final node = _nodesById[nodeId];
    if (node == null) {
      return;
    }
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    await NodeDetailSheet.show(
      context: context,
      nodeId: node.id,
      nodeLabel: node.name,
      packId: widget.initialPackId,
      onAddMaterial: _handleNodeMaterialUploadRequested,
    );
  }

  Future<void> _handleNodeMaterialUploadRequested(
    String nodeId,
    String label,
  ) async {
    await _promptForDocumentUpload(
      originScreenPosition: Offset(
        _viewportSize.width / 2,
        _viewportSize.height - 132,
      ),
      target: GalaxyDocumentUploadTarget.node(
        label: label,
        nodeId: nodeId,
        worldPosition: _renderPositions[nodeId],
      ),
    );
  }

  Future<void> _handleGalaxyCoreUploadRequested() async {
    await _promptForDocumentUpload(
      originScreenPosition: Offset(
        _viewportSize.width / 2,
        _viewportSize.height - 92,
      ),
      target: GalaxyDocumentUploadTarget.galaxyCore(
        label: context.l10n.galaxyUploadTargetGalaxyCore,
      ),
    );
  }

  Future<void> _promptForDocumentUpload({
    required Offset originScreenPosition,
    required GalaxyDocumentUploadTarget target,
  }) async {
    if (ref.read(galaxyDocumentUploadProvider.notifier).hasActiveUpload) {
      AppFeedback.info(
        context,
        context.l10n.galaxyUploadAlreadyInProgress,
      );
      return;
    }

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: supportedStudyMaterialExtensions,
    );
    final pickedFile =
        result != null && result.files.isNotEmpty ? result.files.first : null;
    final path = pickedFile?.path;
    if (path == null || !mounted) {
      return;
    }

    final started =
        await ref.read(galaxyDocumentUploadProvider.notifier).uploadDocument(
              File(path),
              target: target,
              originScreenPosition: originScreenPosition,
            );
    if (!started && mounted) {
      AppFeedback.info(
        context,
        context.l10n.galaxyUploadAlreadyInProgress,
      );
    }
  }

  Future<void> _showEmptySpaceUploadMenu(LongPressCommand command) async {
    final overlayBox =
        Overlay.of(context).context.findRenderObject() as RenderBox?;
    if (overlayBox == null) {
      return;
    }

    final selection = await showMenu<_GalaxyEmptySpaceAction>(
      context: context,
      color: const Color(0xFF0C1626),
      position: RelativeRect.fromRect(
        Rect.fromCenter(
          center: command.screenPosition,
          width: 1,
          height: 1,
        ),
        Offset.zero & overlayBox.size,
      ),
      items: [
        PopupMenuItem<_GalaxyEmptySpaceAction>(
          value: _GalaxyEmptySpaceAction.uploadDocumentHere,
          child: Row(
            children: [
              const Icon(Icons.upload_file_rounded, size: 18),
              const SizedBox(width: 10),
              Text(context.l10n.galaxyUploadDocumentHere),
            ],
          ),
        ),
      ],
    );

    if (!mounted || selection != _GalaxyEmptySpaceAction.uploadDocumentHere) {
      return;
    }

    await _promptForDocumentUpload(
      originScreenPosition: command.screenPosition,
      target: GalaxyDocumentUploadTarget.worldPosition(
        label: context.l10n.galaxyUploadTargetSelectedConstellation,
        worldPosition: command.worldPosition,
      ),
    );
  }

  Offset _resolveUploadTargetScreenPosition(
    GalaxyDocumentUploadSession session,
  ) {
    final target = session.target;
    final worldTarget = switch (target.kind) {
      GalaxyDocumentUploadTargetKind.galaxyCore => Offset.zero,
      GalaxyDocumentUploadTargetKind.worldPosition =>
        target.worldPosition ?? Offset.zero,
      GalaxyDocumentUploadTargetKind.node =>
        target.nodeId != null && _renderPositions[target.nodeId] != null
            ? _renderPositions[target.nodeId]!
            : (target.worldPosition ?? Offset.zero),
    };

    final screenPoint = _camera.worldToScreen(worldTarget);
    if (_viewportSize == Size.zero) {
      return screenPoint;
    }
    return Offset(
      screenPoint.dx.clamp(56.0, _viewportSize.width - 56.0),
      screenPoint.dy.clamp(88.0, _viewportSize.height - 132.0),
    );
  }

  void _triggerMasteryCelebrationIfNeeded(
    GalaxyNodeModel previousNode,
    GalaxyNodeModel nextNode,
  ) {
    const milestones = <int>[30, 60, 85, 100];
    final crossed = milestones
        .where(
          (threshold) =>
              previousNode.masteryScore < threshold &&
              nextNode.masteryScore >= threshold,
        )
        .toList(growable: false);
    if (crossed.isEmpty) {
      return;
    }

    final color = SectorConfig.getGlowColor(nextNode.sector);
    final entry = _CelebrationEntry(
      id: '${nextNode.id}:${DateTime.now().microsecondsSinceEpoch}',
      nodeId: nextNode.id,
      color: color,
      emphasizeNeighbors: crossed.contains(100),
    );
    final emphasis = entry.emphasizeNeighbors
        ? <String>{nextNode.id, ...?_adjacency[nextNode.id]}
        : <String>{nextNode.id};

    unawaited(
      _accessibilityService.patternHaptic(
        entry.emphasizeNeighbors ? HapticPattern.unlock : HapticPattern.success,
      ),
    );

    setState(() {
      _celebrations = [..._celebrations, entry];
      _selectedNodeId = nextNode.id;
      _spotlightAnchorId = nextNode.id;
      _spotlightNodeIds = emphasis;
    });
    _syncProviderSelection(nextNode.id);

    if (entry.emphasizeNeighbors) {
      unawaited(
        Future<void>.delayed(const Duration(milliseconds: 1200), () {
          if (!mounted) {
            return;
          }
          setState(() {
            _spotlightAnchorId = null;
            _spotlightNodeIds = const <String>{};
          });
        }),
      );
    }
  }

  void _removeCelebration(String entryId) {
    if (!mounted) {
      return;
    }
    setState(() {
      _celebrations = _celebrations
          .where((entry) => entry.id != entryId)
          .toList(growable: false);
    });
  }

  void _handleMasteryMilestone(MasteryMilestoneEvent event) {
    if (!mounted) return;
    // Find the node to get its sector color
    final node = ref
        .read(galaxyProvider)
        .nodes
        .where((n) => n.id == event.nodeId)
        .firstOrNull;
    final color = node != null
        ? SectorConfig.getGlowColor(node.sector)
        : const Color(0xFFFFD700);

    final entry = _CelebrationEntry(
      id: 'milestone:${event.nodeId}:${DateTime.now().microsecondsSinceEpoch}',
      nodeId: event.nodeId,
      color: color,
      emphasizeNeighbors: event.milestone >= 85,
    );
    setState(() {
      _celebrations = [..._celebrations, entry];
    });
  }

  void _toggleSearchPanel() {
    setState(() {
      _isSearchOpen = !_isSearchOpen;
      if (!_isSearchOpen) {
        _searchQuery = '';
        _searchResults = const <GalaxyNodeModel>[];
        _searchMatchedNodeIds = const <String>{};
        _searchController.clear();
      }
    });
  }

  void _updateSearchQuery(
    String rawQuery, {
    bool updateTextField = true,
  }) {
    final query = rawQuery.trim().toLowerCase();
    final nodes = _nodesById.values.toList(growable: false);
    if (query.isEmpty) {
      setState(() {
        _searchQuery = '';
        _searchResults = const <GalaxyNodeModel>[];
        _searchMatchedNodeIds = const <String>{};
      });
      if (updateTextField && _searchController.text.isNotEmpty) {
        _searchController.clear();
      }
      return;
    }

    final ranked = [...nodes]..sort((a, b) {
        final aScore = _searchScore(a, query);
        final bScore = _searchScore(b, query);
        if (aScore != bScore) {
          return bScore.compareTo(aScore);
        }
        final importanceCompare = b.importance.compareTo(a.importance);
        if (importanceCompare != 0) {
          return importanceCompare;
        }
        return a.name.compareTo(b.name);
      });
    final filtered =
        ranked.where((node) => _searchScore(node, query) > 0).toList();

    setState(() {
      _searchQuery = rawQuery;
      _searchResults = filtered.take(12).toList(growable: false);
      _searchMatchedNodeIds = filtered.take(24).map((node) => node.id).toSet();
    });
  }

  int _searchScore(GalaxyNodeModel node, String query) {
    final lowerName = node.name.toLowerCase();
    final sectorName = SectorConfig.getStyle(node.sector).name.toLowerCase();
    final tags = node.autoTags.map((tag) => tag.toLowerCase());
    if (lowerName == query) {
      return 100;
    }
    if (lowerName.startsWith(query)) {
      return 72 + node.importance;
    }
    if (lowerName.contains(query)) {
      return 56 + node.importance;
    }
    if (sectorName.contains(query)) {
      return 34 + node.importance;
    }
    if (tags.any((tag) => tag.contains(query))) {
      return 24 + node.importance;
    }
    return 0;
  }

  void _handleSearchNodeSelected(GalaxyNodeModel node) {
    _searchController.clear();
    setState(() {
      _isSearchOpen = false;
      _searchQuery = '';
      _searchResults = const <GalaxyNodeModel>[];
      _searchMatchedNodeIds = const <String>{};
    });
    _focusOnNode(node.id, targetScale: 0.84);
  }

  void _focusOnNode(
    String nodeId, {
    double targetScale = 0.82,
    bool highlightNeighbors = true,
  }) {
    final position = _renderPositions[nodeId];
    if (position == null) {
      return;
    }

    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    final emphasis = highlightNeighbors
        ? <String>{nodeId, ...?_adjacency[nodeId]}
        : <String>{nodeId};
    final desiredScale =
        math.max(_camera.scale, targetScale).clamp(_camera.minScale, 1.25);
    final targetCamera =
        _camera.copyWith(scale: desiredScale).centerOnWorldPoint(
              worldPoint: position,
            );

    unawaited(_accessibilityService.lightHaptic());
    setState(() {
      _selectedNodeId = nodeId;
      _spotlightAnchorId = nodeId;
      _spotlightNodeIds = emphasis;
      _clearPreviewState();
    });
    _syncProviderSelection(nodeId);
    _animateCameraTo(
      targetCamera,
      duration: const Duration(milliseconds: 520),
      curve: Curves.easeInOutCubicEmphasized,
      arcScaleOutFactor: 1.05,
    );
  }

  void _focusPreviewNode() {
    final previewNode = _previewNode;
    if (previewNode == null) {
      return;
    }
    _focusOnNode(previewNode.id);
  }

  void _inspectPreviewConnections() {
    final previewNode = _previewNode;
    if (previewNode == null) {
      return;
    }
    setState(() {
      _selectedNodeId = previewNode.id;
      _spotlightAnchorId = previewNode.id;
      _spotlightNodeIds = _spotlightSetFor(previewNode.id);
      _clearPreviewState();
    });
    _syncProviderSelection(previewNode.id);
  }

  void _handleMiniMapNavigate(Offset worldPoint) {
    _noteInteraction();
    final target = _camera.centerOnWorldPoint(worldPoint: worldPoint);
    _animateCameraTo(
      target,
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
      arcScaleOutFactor: 1.02,
    );
  }

  void _handleMiniMapDrag(Offset worldPoint) {
    _noteInteraction();
    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    setState(() {
      _camera = _camera.centerOnWorldPoint(worldPoint: worldPoint);
    });
  }

  void _handleAmbientTick(Duration elapsed) {
    _ambientElapsed = elapsed;
    final nextPhase = elapsed.inMicroseconds / Duration.microsecondsPerSecond;
    final shouldAnimateScene =
        _isBuildAnimating || _camera.scale > 0.5 || _selectedNodeId != null;
    final nextParticles = _buildEdgeParticles(nextPhase);
    final nextDriftOffsets = _buildMicroDriftOffsets(nextPhase, elapsed);

    if (!mounted) {
      _ambientPhase = nextPhase;
      return;
    }

    if (shouldAnimateScene ||
        nextParticles != _edgeParticles ||
        !_driftOffsetsEqual(nextDriftOffsets, _microDriftOffsets)) {
      setState(() {
        _ambientPhase = nextPhase;
        _edgeParticles = nextParticles;
        _microDriftOffsets = nextDriftOffsets;
      });
      return;
    }

    _ambientPhase = nextPhase;
  }

  List<GalaxyEdgeParticle> _buildEdgeParticles(double timeSeconds) =>
      const <GalaxyEdgeParticle>[];

  Map<String, Offset> _buildMicroDriftOffsets(
    double timeSeconds,
    Duration elapsed,
  ) {
    final idleFor = elapsed - _lastInteractionElapsed;
    if (_performanceDegraded ||
        idleFor < const Duration(seconds: 3) ||
        _draggingNodeId != null ||
        _previewNode != null ||
        _isSearchOpen ||
        _isBuildAnimating ||
        _nodesById.isEmpty) {
      return const <String, Offset>{};
    }

    if (elapsed - _lastDriftShuffleElapsed <
            const Duration(milliseconds: 200) &&
        _microDriftOffsets.isNotEmpty) {
      return _microDriftOffsets;
    }
    _lastDriftShuffleElapsed = elapsed;

    final sortedIds = _nodesById.keys.toList(growable: false)..sort();
    final startIndex = (elapsed.inMilliseconds ~/ 200) % sortedIds.length;
    final activeCount = math.min(8, sortedIds.length);
    final offsets = <String, Offset>{};
    for (var index = 0; index < activeCount; index++) {
      final nodeId = sortedIds[(startIndex + index * 7) % sortedIds.length];
      final seed = _nodeSeedValue(nodeId);
      offsets[nodeId] = Offset(
        math.sin(timeSeconds * 0.7 + seed) * 5,
        math.cos(timeSeconds * 0.6 + seed * 1.3) * 4,
      );
    }
    return offsets;
  }

  double _nodeSeedValue(String nodeId) =>
      ((nodeId.hashCode & 0x7fffffff) % 1000) / 100.0;

  bool _driftOffsetsEqual(
    Map<String, Offset> left,
    Map<String, Offset> right,
  ) {
    if (identical(left, right)) {
      return true;
    }
    if (left.length != right.length) {
      return false;
    }
    for (final entry in left.entries) {
      if (right[entry.key] != entry.value) {
        return false;
      }
    }
    return true;
  }

  void _handleFrameTimings(List<FrameTiming> timings) {
    var nextSlow = _consecutiveSlowFrames;
    var nextFast = _consecutiveFastFrames;
    for (final timing in timings) {
      final totalMs = timing.totalSpan.inMicroseconds / 1000;
      if (totalMs > _frameBudgetMs) {
        nextSlow += 1;
        nextFast = 0;
      } else {
        nextFast += 1;
        nextSlow = 0;
      }
    }

    final nextDegraded = nextSlow >= 5
        ? true
        : nextFast >= 30
            ? false
            : _performanceDegraded;

    _consecutiveSlowFrames = nextSlow;
    _consecutiveFastFrames = nextFast;

    if (nextDegraded == _performanceDegraded || !mounted) {
      return;
    }

    setState(() {
      _performanceDegraded = nextDegraded;
      if (nextDegraded) {
        _microDriftOffsets = const <String, Offset>{};
        _edgeParticles = const <GalaxyEdgeParticle>[];
      }
    });
  }

  void _handleCameraAnimationTick() {
    final start = _cameraAnimationStart;
    final end = _cameraAnimationEnd;
    if (start == null || end == null || !mounted) {
      return;
    }

    final t = _cameraAnimationCurve.transform(
      _cameraAnimationController.value.clamp(0.0, 1.0),
    );
    final arcFactor = _cameraAnimationArcScaleOutFactor;
    final scale = arcFactor <= 1.0
        ? lerpDouble(start.scale, end.scale, t)!
        : _arcInterpolatedScale(
            start.scale,
            end.scale,
            t,
            arcFactor: arcFactor,
          );
    setState(() {
      _camera = GalaxyCamera(
        offset: Offset.lerp(start.offset, end.offset, t)!,
        scale: scale,
        viewportSize: end.viewportSize,
        minScale: end.minScale,
        maxScale: end.maxScale,
      );
    });
    _syncProviderScale(scale);
  }

  void _animateCameraTo(
    GalaxyCamera target, {
    Duration duration = const Duration(milliseconds: 400),
    Curve curve = Curves.easeInOutCubic,
    double arcScaleOutFactor = 1.0,
  }) {
    _cameraAnimationStart = _camera;
    _cameraAnimationEnd = target;
    _cameraAnimationCurve = curve;
    _cameraAnimationArcScaleOutFactor = arcScaleOutFactor;
    _cameraAnimationController
      ..duration = duration
      ..stop()
      ..reset();
    unawaited(_cameraAnimationController.forward());
  }

  double _arcInterpolatedScale(
    double startScale,
    double endScale,
    double t, {
    required double arcFactor,
  }) {
    const pivot = 0.6;
    final peakScale =
        math.max(startScale, endScale).clamp(0.0, _camera.maxScale) * arcFactor;
    if (t <= pivot) {
      return lerpDouble(
        startScale,
        peakScale.clamp(startScale, _camera.maxScale),
        Curves.easeOutCubic.transform((t / pivot).clamp(0.0, 1.0)),
      )!;
    }
    return lerpDouble(
      peakScale.clamp(endScale, _camera.maxScale),
      endScale,
      Curves.easeInOutCubic.transform(
        ((t - pivot) / (1 - pivot)).clamp(0.0, 1.0),
      ),
    )!;
  }

  void _primePlaybackState(
    _PlaybackLaunch launch, {
    double speedMultiplier = 1.0,
  }) {
    _playbackPlan = launch.plan;
    _preRevealedNodeIds = launch.preRevealedNodeIds;
    _preRevealedEdgeIds = launch.preRevealedEdgeIds;
    _playbackSnapshot = GalaxyPlaybackSnapshot(
      plan: launch.plan,
      frozenPositions: Map<String, Offset>.unmodifiable(launch.frozenPositions),
      settledPositions:
          Map<String, Offset>.unmodifiable(launch.frozenPositions),
      preRevealedNodeIds: launch.preRevealedNodeIds,
      preRevealedEdgeIds: launch.preRevealedEdgeIds,
    );
    _playbackElapsedMs = 0;
    _selectedNodeId = null;
    _spotlightAnchorId = null;
    _spotlightNodeIds = const <String>{};
    _draggingNodeId = null;
    _isBuildAnimating = true;
    _activeReplaySpeedMultiplier = speedMultiplier;
    _syncProviderSelection(null);
    _buildReplayController
      ..duration = Duration(milliseconds: _currentBuildReplayDurationMs())
      ..stop()
      ..reset();
  }

  void _clearPlaybackState({bool resetElapsed = true}) {
    _playbackPlan = null;
    _playbackSnapshot = null;
    _preRevealedNodeIds = const <String>{};
    _preRevealedEdgeIds = const <String>{};
    if (resetElapsed) {
      _playbackElapsedMs = 0;
    }
    _isBuildAnimating = false;
    _activeReplaySpeedMultiplier = 1.0;
  }

  void _scheduleLayoutOptimization({
    required GalaxyGraphResponse graph,
    required Map<String, Offset> basePositions,
  }) {
    final epoch = ++_layoutOptimizationEpoch;
    final settings = ref.read(galaxyDisplaySettingsProvider);
    unawaited(() async {
      final result = await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
        nodes: graph.nodes,
        edges: graph.edges,
        initialPositions: basePositions,
        sectorAffinity: settings.sectorAffinity,
      );
      if (!mounted || epoch != _layoutOptimizationEpoch || _graph != graph) {
        return;
      }

      final optimizedPositions = result.positions;
      if (_isBuildAnimating) {
        final snapshot = _playbackSnapshot;
        if (snapshot == null) {
          return;
        }
        setState(() {
          _positions = optimizedPositions;
          _playbackSnapshot = snapshot.copyWith(
            settledPositions: optimizedPositions,
          );
          _sceneVersion++;
        });
        return;
      }

      _beginLayoutBlend(optimizedPositions);
    }());
  }

  void _beginLayoutBlend(Map<String, Offset> targetPositions) {
    if (targetPositions.isEmpty) {
      return;
    }
    _layoutBlendStartPositions = Map<String, Offset>.from(_positions);
    _layoutBlendTargetPositions = Map<String, Offset>.from(targetPositions);
    _layoutBlendController
      ..duration = const Duration(milliseconds: 260)
      ..stop()
      ..reset();
    unawaited(_layoutBlendController.forward());
  }

  void _handleBuildReplayTick() {
    if (!mounted) {
      return;
    }

    final playbackPlan = _playbackPlan;
    final progress = _buildReplayController.value.clamp(0.0, 1.0);
    final nextElapsedMs = playbackPlan == null
        ? 0
        : (playbackPlan.totalDurationMs * progress).round();
    setState(() {
      _playbackElapsedMs = nextElapsedMs;
      _ambientPhase =
          _ambientElapsed.inMicroseconds / Duration.microsecondsPerSecond;
    });
  }

  void _handleBuildReplayStatus(AnimationStatus status) {
    if (!mounted || status != AnimationStatus.completed) {
      return;
    }

    final settledPositions = _playbackSnapshot?.settledPositions;
    setState(() {
      _playbackElapsedMs = _playbackPlan?.totalDurationMs ?? 0;
      _clearPlaybackState(resetElapsed: false);
      _spotlightAnchorId = null;
      _spotlightNodeIds = const <String>{};
    });
    if (settledPositions != null) {
      _beginLayoutBlend(settledPositions);
    } else {
      _startGraphSettleSimulation(impulse: 0.22);
    }
  }

  void _toggleBuildReplay() {
    if (_isBuildAnimating) {
      _stopBuildReplay();
      return;
    }
    _startBuildReplay();
  }

  void _startBuildReplay({bool preserveCurrentCamera = false}) {
    final graph = _graph;
    if (graph == null || _viewportSize == Size.zero) {
      return;
    }

    final playbackPlan = GalaxyBuildPlaybackPlan.full(
      nodes: graph.nodes,
      edges: graph.edges,
      positions: _positions,
      adjacency: _adjacency,
    );
    if (playbackPlan.isEmpty) {
      return;
    }
    _launchPlayback(
      _PlaybackLaunch(
        plan: playbackPlan,
        frozenPositions: Map<String, Offset>.from(_positions),
        preRevealedNodeIds: const <String>{},
        preRevealedEdgeIds: const <String>{},
      ),
      preserveCurrentCamera: preserveCurrentCamera,
    );
  }

  void _stopBuildReplay() {
    _initialBuildReplayTimer?.cancel();
    if (!_isBuildAnimating && !_buildReplayController.isAnimating) {
      return;
    }

    _buildReplayController
      ..stop()
      ..reset();
    if (!mounted) {
      return;
    }
    setState(() {
      _clearPlaybackState();
      _spotlightAnchorId = null;
      _spotlightNodeIds = const <String>{};
    });
  }

  int _currentBuildReplayDurationMs() {
    final playbackPlan = _playbackPlan;
    if (playbackPlan == null || playbackPlan.isEmpty) {
      return 7200;
    }
    final replaySpeed = ref.read(galaxyDisplaySettingsProvider).replaySpeed;
    final effectiveReplaySpeed = (replaySpeed * _activeReplaySpeedMultiplier)
        .clamp(kGalaxyReplaySpeedMin, kGalaxyReplaySpeedMax);
    return (playbackPlan.totalDurationMs / effectiveReplaySpeed)
        .round()
        .clamp(1, 40000);
  }

  _PlaybackLaunch? _buildPlaybackLaunch({
    required GalaxyGraphResponse? previousGraph,
    required GalaxyGraphResponse nextGraph,
    required Map<String, Offset> positions,
    required Map<String, Set<String>> adjacency,
    required bool preserveCamera,
  }) {
    if (!preserveCamera) {
      final sessionPlayedFullReplay =
          ref.read(galaxyBuildPlaybackSessionProvider);
      if (sessionPlayedFullReplay) {
        return null;
      }
      final fullPlan = GalaxyBuildPlaybackPlan.full(
        nodes: nextGraph.nodes,
        edges: nextGraph.edges,
        positions: positions,
        adjacency: adjacency,
      );
      if (fullPlan.isEmpty) {
        return null;
      }
      return _PlaybackLaunch(
        plan: fullPlan,
        frozenPositions: Map<String, Offset>.from(positions),
        preRevealedNodeIds: const <String>{},
        preRevealedEdgeIds: const <String>{},
      );
    }

    final animatedNodeIds = _collectIncrementalAnimatedNodeIds(
      previousGraph: previousGraph,
      nextGraph: nextGraph,
    );
    if (animatedNodeIds.isEmpty) {
      return null;
    }

    final allNodeIds = nextGraph.nodes.map((node) => node.id).toSet();
    final preRevealedNodeIds = allNodeIds.difference(animatedNodeIds);
    final preRevealedEdgeIds = nextGraph.edges
        .where(
          (edge) =>
              !animatedNodeIds.contains(edge.sourceId) &&
              !animatedNodeIds.contains(edge.targetId),
        )
        .map((edge) => edge.id)
        .toSet();
    final incrementalPlan = GalaxyBuildPlaybackPlan.incremental(
      nodes: nextGraph.nodes,
      edges: nextGraph.edges,
      positions: positions,
      adjacency: adjacency,
      animatedNodeIds: animatedNodeIds,
      preRevealedNodeIds: preRevealedNodeIds,
    );
    if (incrementalPlan.isEmpty) {
      return null;
    }
    return _PlaybackLaunch(
      plan: incrementalPlan,
      frozenPositions: Map<String, Offset>.from(positions),
      preRevealedNodeIds: preRevealedNodeIds,
      preRevealedEdgeIds: preRevealedEdgeIds,
    );
  }

  Set<String> _collectIncrementalAnimatedNodeIds({
    required GalaxyGraphResponse? previousGraph,
    required GalaxyGraphResponse nextGraph,
  }) {
    if (previousGraph == null) {
      return const <String>{};
    }

    final previousNodesById = {
      for (final node in previousGraph.nodes) node.id: node,
    };
    final animatedNodeIds = <String>{};
    for (final nextNode in nextGraph.nodes) {
      final previousNode = previousNodesById[nextNode.id];
      if (previousNode == null) {
        animatedNodeIds.add(nextNode.id);
        continue;
      }
      if (!previousNode.isUnlocked && nextNode.isUnlocked) {
        animatedNodeIds.add(nextNode.id);
      }
    }
    return animatedNodeIds;
  }

  void _preparePlayback(
    _PlaybackLaunch launch, {
    double speedMultiplier = 1.0,
  }) {
    setState(() {
      _primePlaybackState(
        launch,
        speedMultiplier: speedMultiplier,
      );
      _sceneVersion++;
    });
  }

  void _startPreparedPlayback({
    Duration preRoll = const Duration(milliseconds: 100),
  }) {
    if (!_isBuildAnimating || _playbackPlan == null) {
      return;
    }
    _buildReplayController
      ..duration = Duration(milliseconds: _currentBuildReplayDurationMs())
      ..stop()
      ..reset();
    _initialBuildReplayTimer?.cancel();
    _initialBuildReplayTimer = Timer(preRoll, () {
      if (!mounted || !_isBuildAnimating || _playbackPlan == null) {
        return;
      }
      unawaited(_buildReplayController.forward());
    });
  }

  void _launchPlayback(
    _PlaybackLaunch launch, {
    required bool preserveCurrentCamera,
  }) {
    if (_graph == null || _viewportSize == Size.zero) {
      return;
    }

    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    _clearPreviewState();
    _cancelTapFeedbackState();
    final overviewCamera = _fitOverviewCamera();

    setState(() {
      _camera = preserveCurrentCamera ? _camera : overviewCamera;
    });
    _preparePlayback(launch);
    _startPreparedPlayback();
  }

  GalaxyGraphResponse _sanitizeGraph(GalaxyGraphResponse graph) {
    final validNodes =
        graph.nodes.where(_isRenderableNode).toList(growable: false);
    final validNodeIds = validNodes.map((node) => node.id).toSet();
    final validEdges = graph.edges
        .where(
          (edge) =>
              validNodeIds.contains(edge.sourceId) &&
              validNodeIds.contains(edge.targetId),
        )
        .toList(growable: false);
    return GalaxyGraphResponse(
      nodes: validNodes,
      edges: validEdges,
      userFlameIntensity: graph.userFlameIntensity,
    );
  }

  bool _isRenderableNode(GalaxyNodeModel node) {
    final name = node.name.trim();
    if (name.isEmpty || name.toLowerCase() == 'null' || name.contains('�')) {
      return false;
    }
    final hasReadableGlyph = RegExp(
      r'[A-Za-z0-9\u4E00-\u9FFF]',
    ).hasMatch(name);
    if (!hasReadableGlyph) {
      return false;
    }
    return !RegExp(r'^[?？·•\-_=\s]+$').hasMatch(name);
  }

  void _applyDisplaySettings({
    required GalaxyDisplaySettings? previous,
    required GalaxyDisplaySettings next,
  }) {
    _forceEngine.updateParameters(
      springK: next.linkForce,
      repulsionK: next.repelForce,
      centerGravity: next.centerForce,
      springRestLength: next.linkDistance,
    );

    final replaySpeedChanged =
        previous != null && previous.replaySpeed != next.replaySpeed;
    if (replaySpeedChanged && _isBuildAnimating) {
      final progress = _buildReplayController.value.clamp(0.0, 1.0);
      _buildReplayController
        ..stop()
        ..duration = Duration(milliseconds: _currentBuildReplayDurationMs());
      unawaited(_buildReplayController.forward(from: progress));
    }

    final forcesChanged = previous != null &&
        (previous.centerForce != next.centerForce ||
            previous.repelForce != next.repelForce ||
            previous.linkForce != next.linkForce ||
            previous.linkDistance != next.linkDistance);
    if (forcesChanged) {
      _previewPhysicsSettingsChange();
    }
  }

  void _previewPhysicsSettingsChange() {
    final graph = _graph;
    if (graph == null || _positions.isEmpty || _viewportSize == Size.zero) {
      return;
    }

    _forceEngine.activateNodes(
      _positions.keys,
      positions: _positions,
      impulse: 0.78,
    );
    _startPhysicsSimulation(useViewportCulling: false);
  }

  void _startGraphSettleSimulation({double impulse = 0.4}) {
    final graph = _graph;
    if (graph == null || _positions.isEmpty) {
      return;
    }

    _forceEngine.activateNodes(
      _positions.keys,
      positions: _positions,
      impulse: impulse,
    );
    _startPhysicsSimulation(useViewportCulling: false);
  }

  void _resetSimulationSettings() {
    ref.read(galaxyDisplaySettingsProvider.notifier).resetToDefaults();
  }

  Future<void> _openSimulationSettings() async {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    setState(() {
      _isSettingsOpen = true;
    });
    await showSensoryModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) {
          final settings = ref.read(galaxyDisplaySettingsProvider);
          final notifier = ref.read(galaxyDisplaySettingsProvider.notifier);
          return GalaxySimulationSettingsSheet(
            isDarkMode: isDarkMode,
            settings: settings,
            onTextFadeThresholdChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(textFadeThreshold: value),
              );
              setSheetState(() {});
            },
            onNodeSizeScaleChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(nodeSizeScale: value),
              );
              setSheetState(() {});
            },
            onLinkThicknessScaleChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(linkThicknessScale: value),
              );
              setSheetState(() {});
            },
            onCenterForceChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(centerForce: value),
              );
              setSheetState(() {});
            },
            onRepelForceChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(repelForce: value),
              );
              setSheetState(() {});
            },
            onLinkForceChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(linkForce: value),
              );
              setSheetState(() {});
            },
            onLinkDistanceChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(linkDistance: value),
              );
              setSheetState(() {});
            },
            onReplaySpeedChanged: (value) {
              notifier.updateWith(
                (current) => current.copyWith(replaySpeed: value),
              );
              setSheetState(() {});
            },
            onReset: () {
              _resetSimulationSettings();
              setSheetState(() {});
            },
          );
        },
      ),
    );
    if (!mounted) {
      return;
    }
    setState(() {
      _isSettingsOpen = false;
    });
  }

  void _stopAllAutoMotion({required bool commitPhysicsPosition}) {
    _stopFling();
    _stopBuildReplay();
    _stopPhysicsSimulation(commitPendingNode: commitPhysicsPosition);
  }

  void _updateViewportSize(Size nextSize) {
    if (_viewportSize == nextSize || nextSize == Size.zero) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _viewportSize == nextSize || nextSize == Size.zero) {
        return;
      }

      final previousSize = _viewportSize;
      final resizedCamera = previousSize == Size.zero
          ? _camera.copyWith(viewportSize: nextSize)
          : _camera.withViewportSize(nextSize);
      final shouldFit = !_didFitInitialCamera && _graph != null;

      setState(() {
        _viewportSize = nextSize;
        _camera = shouldFit ? _fitOverviewCamera() : resizedCamera;
        if (shouldFit) {
          _didFitInitialCamera = true;
        }
        if (_previewNode != null && _previewScreenPosition != null) {
          final nodeId = _previewNode!.id;
          final anchor = _renderPositions[nodeId];
          if (anchor != null) {
            _previewScreenPosition = _computePreviewPosition(
              anchor: _camera.worldToScreen(anchor),
              node: _previewNode,
            );
          }
        }
      });
      _schedulePendingExternalFocus();
    });
  }

  void _zoomAroundCenter(double factor) {
    if (_viewportSize == Size.zero) {
      return;
    }
    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    final target = _camera.applyZoom(
      factor,
      Offset(_viewportSize.width / 2, _viewportSize.height / 2),
    );
    _animateCameraTo(
      target,
      duration: const Duration(milliseconds: 220),
    );
  }

  void _fitOverviewAnimated() {
    _stopFling();
    _stopPhysicsSimulation(commitPendingNode: true);
    _animateCameraTo(_fitOverviewCamera());
  }

  Map<String, Set<String>> _buildAdjacency(List<GalaxyEdgeModel> edges) {
    final adjacency = <String, Set<String>>{};
    for (final edge in edges) {
      adjacency.putIfAbsent(edge.sourceId, () => <String>{}).add(edge.targetId);
      adjacency.putIfAbsent(edge.targetId, () => <String>{}).add(edge.sourceId);
    }
    return adjacency;
  }

  Map<String, double> _buildEdgeStrengths(List<GalaxyEdgeModel> edges) {
    final strengths = <String, double>{};
    for (final edge in edges) {
      final key =
          GalaxyForceEngine.edgeStrengthKey(edge.sourceId, edge.targetId);
      final value = (0.75 + edge.strength * 0.65).clamp(0.5, 1.4);
      final current = strengths[key];
      if (current == null || value > current) {
        strengths[key] = value;
      }
    }
    return strengths;
  }

  Map<String, Color> _buildBlendedColors({
    required Map<String, GalaxyNodeModel> nodesById,
    required Map<String, Set<String>> adjacency,
    required bool isDarkMode,
  }) =>
      {
        for (final node in nodesById.values)
          node.id: SectorConfig.computeBlendedColor(
            node: node,
            neighbors: (adjacency[node.id] ?? const <String>{})
                .map((neighborId) => nodesById[neighborId])
                .whereType<GalaxyNodeModel>(),
            isDarkMode: isDarkMode,
          ),
      };

  SectorEnum? _currentSector() {
    if (_viewportSize == Size.zero || _camera.scale < 0.5) {
      return null;
    }

    final worldCenter = _camera.screenToWorld(
      Offset(_viewportSize.width / 2, _viewportSize.height / 2),
    );
    if (worldCenter.distance < 140) {
      return null;
    }

    return SectorConfig.getSectorForPosition(worldCenter);
  }

  _OverviewStatsData _buildOverviewStats(GalaxyGraphResponse graph) {
    final totalNodes = graph.nodes.length;
    final unlocked = graph.nodes.where((node) => node.isUnlocked).length;
    final masteryAverage = totalNodes == 0
        ? 0
        : (graph.nodes
                    .map((node) => node.masteryScore)
                    .fold<int>(0, (sum, value) => sum + value) /
                totalNodes)
            .round();

    return _OverviewStatsData(
      totalNodes: totalNodes,
      unlockedNodes: unlocked,
      masteryAverage: masteryAverage,
    );
  }

  Future<void> _openDraftReview({String? batchId}) async {
    if (_isDraftReviewOpen) {
      return;
    }
    final draftState = ref.read(galaxyDraftReviewProvider);
    final batch = draftState.batchById(batchId) ?? draftState.promptBatch;
    if (batch == null) {
      await ref.read(galaxyDraftReviewProvider.notifier).refresh();
      return;
    }

    _isDraftReviewOpen = true;
    final result = await context.push<GalaxyDraftReviewResult>(
      GalaxyRoutes.draftReview,
      extra: GalaxyDraftReviewRouteArgs(batchId: batch.id),
    );
    _isDraftReviewOpen = false;

    if (!mounted || result == null) {
      return;
    }
    _playDraftArrivalCelebration(result);
  }

  void _playDraftArrivalCelebration(GalaxyDraftReviewResult result) {
    if (result.acceptedCount <= 0) {
      AppFeedback.info(
        context,
        context.l10n.galaxyDraftCompletionNothingAdded,
      );
      return;
    }

    final acceptedLabels = result.reviewedNodes
        .where((node) => node.decision != GalaxyDraftDecision.reject)
        .map((node) => node.finalName)
        .take(5)
        .toList(growable: false);
    final summary = context.l10n.galaxyDraftCompletionSummary(
      result.acceptedCount,
      result.totalDraftCount,
    );

    setState(() {
      _draftArrivalCelebration = _DraftArrivalCelebration(
        id: DateTime.now().microsecondsSinceEpoch.toString(),
        labels: acceptedLabels,
        summary: summary,
      );
    });
    AppFeedback.success(context, summary);
  }

  void _dismissDraftArrivalCelebration() {
    if (!mounted) {
      return;
    }
    setState(() {
      _draftArrivalCelebration = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    const isDarkMode = _useDarkGalaxyTheme;
    const backgroundColor = isDarkMode ? Color(0xFF060A12) : Color(0xFFF5F6F8);
    final displaySettings = ref.watch(galaxyDisplaySettingsProvider);
    final graph = _graph;
    final currentSector = _currentSector();
    final blendedColors = isDarkMode ? _darkBlendedColors : _lightBlendedColors;
    final overviewStats = graph == null ? null : _buildOverviewStats(graph);
    final showMasteryEmptyBanner = overviewStats != null &&
        overviewStats.totalNodes > 0 &&
        overviewStats.masteryAverage == 0;
    final contributionStats = ref.watch(galaxyContributionProvider);
    final draftReviewState = ref.watch(galaxyDraftReviewProvider);
    final draftPromptBatch = draftReviewState.promptBatch;
    final showDraftPendingIndicator =
        draftPromptBatch == null && draftReviewState.pendingBatchCount > 0;
    final theaterOverlay = ref.watch(theaterOverlayProvider);
    final examSprintActive =
        ref.watch(examSprintDashboardProvider).valueOrNull != null;
    final uploadState = ref.watch(galaxyDocumentUploadProvider);
    final uploadSession = uploadState.session;
    final activeGoalId = ref.watch(activeGoalHeaderProvider);
    final goalOverlayData = activeGoalId != null
        ? ref.watch(goalGraphOverlayProvider(activeGoalId)).valueOrNull
        : null;
    if (goalOverlayData != null && goalOverlayData.nodes.isNotEmpty) {
      _goalWorldNodeIds = goalOverlayData.nodes.map((n) => n.id).toSet();
    } else {
      _goalWorldNodeIds = const <String>{};
      if (_isGoalWorldMode) _isGoalWorldMode = false;
    }

    final baseTheme = Theme.of(context);
    final galaxyTheme = baseTheme.copyWith(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: baseTheme.colorScheme.copyWith(
        brightness: Brightness.dark,
        surface: const Color(0xFF101929),
        onSurface: DS.neutral0,
      ),
    );

    return Semantics(
      container: true,
      label: context.l10n.galaxy,
      child: Theme(
        data: galaxyTheme,
        child: Scaffold(
          backgroundColor: backgroundColor,
          appBar: theaterOverlay == null
              ? null
              : AppBar(
                  backgroundColor: backgroundColor.withValues(alpha: 0.9),
                  surfaceTintColor: Colors.transparent,
                  elevation: 0,
                  titleSpacing: 16,
                  title: Align(
                    alignment: Alignment.centerLeft,
                    child: ActionChip(
                      avatar: const Icon(
                        Icons.auto_graph_rounded,
                        size: 18,
                      ),
                      label: Text(context.l10n.galaxySimMode),
                      onPressed: () => _openPredictionOverlay(null),
                    ),
                  ),
                ),
          body: SparkleRefreshIndicator(
            onRefresh: _handlePullToRefresh,
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverFillRemaining(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      _updateViewportSize(
                        Size(constraints.maxWidth, constraints.maxHeight),
                      );

                      if (_isLoading) {
                        return _StatusPanel(
                          backgroundColor: backgroundColor,
                          foregroundColor: DS.neutral0,
                          title: context.l10n.galaxyLoadingTitle,
                          message: context.l10n.galaxyLoadingMessage,
                          highlights: <String>[
                            context.l10n.searchNodes,
                            context.l10n.galaxySimMode,
                            context.l10n.galaxyOverviewNodes,
                          ],
                          showLoader: true,
                        );
                      }

                      if (_loadError != null) {
                        return _StatusPanel(
                          backgroundColor: backgroundColor,
                          foregroundColor:
                              isDarkMode ? DS.neutral0 : DS.neutral900,
                          title: context.l10n.galaxyLoadFailedTitle,
                          message: '$_loadError',
                          actionLabel: context.l10n.retry,
                          onAction: _loadGraph,
                        );
                      }

                      if (graph == null || graph.nodes.isEmpty) {
                        return _StatusPanel(
                          backgroundColor: backgroundColor,
                          foregroundColor:
                              isDarkMode ? DS.neutral0 : DS.neutral900,
                          title: context.l10n.galaxyEmptyTitle,
                          message: context.l10n.galaxyEmptyFirst,
                          highlights: <String>[
                            context.l10n.galaxyEmptyHighlights1,
                            context.l10n.galaxyEmptyHighlights2,
                            context.l10n.galaxyEmptyHighlights3,
                          ],
                          actionLabel: context.l10n.galaxyEmptyActionLabel,
                          onAction: () async {
                            await context.push(TaskRoutes.taskCreate);
                          },
                        );
                      }

                      return AnimatedSwitcher(
                        duration: const Duration(milliseconds: 300),
                        switchInCurve: Curves.easeOut,
                        switchOutCurve: Curves.easeIn,
                        child: AnimatedBuilder(
                          animation: _entranceController,
                          builder: (context, child) {
                            final progress = _entranceController.value;
                            return ImageFiltered(
                              imageFilter: ImageFilter.blur(
                                sigmaX: (12 * (1 - progress)).clamp(0, 50),
                                sigmaY: (12 * (1 - progress)).clamp(0, 50),
                              ),
                              child: Opacity(
                                opacity: progress,
                                child: Transform.scale(
                                  scale: 0.9 +
                                      0.1 *
                                          Curves.easeOutCubic
                                              .transform(progress),
                                  child: child,
                                ),
                              ),
                            );
                          },
                          child: Stack(
                            key: const ValueKey<bool>(isDarkMode),
                            children: [
                              Listener(
                              behavior: HitTestBehavior.opaque,
                              onPointerDown: _handlePointerDown,
                              onPointerMove: _gestureHandler.handlePointerMove,
                              onPointerUp: _handlePointerUp,
                              onPointerCancel: _handlePointerCancel,
                              onPointerSignal: _handlePointerSignal,
                              child: RepaintBoundary(
                                child: CustomPaint(
                                  painter: StarMapPainter(
                                    camera: _camera,
                                    nodesById: _nodesById,
                                    edges: graph.edges,
                                    positions: _renderPositions,
                                    spatialIndex: _spatialIndex,
                                    labelCache: _labelCache,
                                    backdropPictureCache: _backdropPictureCache,
                                    parallaxStarLayerCache:
                                        _parallaxStarLayerCache,
                                    sceneVersion: _sceneVersion,
                                    selectedNodeId: _selectedNodeId,
                                    previewNodeId: _previewNode?.id,
                                    draggingNodeId: _draggingNodeId,
                                    tapFeedbackNodeId: _tapFeedbackNodeId,
                                    tapFeedbackProgress:
                                        _tapFeedbackAnimation.value,
                                    tapFeedbackPhase:
                                        _tapFeedbackController.value,
                                    isDarkMode: isDarkMode,
                                    worldBounds: _computeWorldBounds(),
                                    blendedColors: blendedColors,
                                    displaySettings: displaySettings,
                                    playbackPlan: _playbackPlan,
                                    playbackElapsedMs: _playbackElapsedMs,
                                    preRevealedNodeIds: _preRevealedNodeIds,
                                    preRevealedEdgeIds: _preRevealedEdgeIds,
                                    nodeConnectionCounts: _nodeConnectionCounts,
                                    ambientPhase: _ambientPhase,
                                    isBuildAnimating: _isBuildAnimating,
                                    spotlightNodeIds: _isGoalWorldMode
                                        ? _goalWorldNodeIds
                                        : _spotlightNodeIds,
                                    spotlightAnchorId: _isGoalWorldMode
                                        ? null
                                        : _spotlightAnchorId,
                                    searchMatchedNodeIds: _searchMatchedNodeIds,
                                    driftOffsets: _microDriftOffsets,
                                    edgeParticles: _edgeParticles,
                                    celebrationNodeIds: _celebrations
                                        .map((entry) => entry.nodeId)
                                        .toSet(),
                                    performanceDegraded: _performanceDegraded,
                                    predictionOverlay: theaterOverlay,
                                    examSprintActive: examSprintActive,
                                  ),
                                  child: const SizedBox.expand(),
                                ),
                              ),
                            ),
                            ..._celebrations.map((entry) {
                              final worldPosition =
                                  _renderPositions[entry.nodeId];
                              if (worldPosition == null) {
                                return const SizedBox.shrink();
                              }
                              final neighborIds =
                                  _adjacency[entry.nodeId] ?? const <String>{};
                              final neighborScreenPositions = <Offset>[];
                              for (final nid in neighborIds) {
                                final nPos = _renderPositions[nid];
                                if (nPos != null) {
                                  neighborScreenPositions
                                      .add(_camera.worldToScreen(nPos));
                                }
                              }
                              return Positioned.fill(
                                child: IgnorePointer(
                                  child: StarSuccessAnimation(
                                    key: ValueKey(entry.id),
                                    position:
                                        _camera.worldToScreen(worldPosition),
                                    color: entry.color,
                                    neighborPositions: neighborScreenPositions,
                                    emphasizeNeighbors:
                                        entry.emphasizeNeighbors,
                                    onComplete: () =>
                                        _removeCelebration(entry.id),
                                  ),
                                ),
                              );
                            }),
                            if (_draftArrivalCelebration != null)
                              Positioned.fill(
                                child: SparkleGalaxyArrivalOverlay(
                                  key: ValueKey(_draftArrivalCelebration!.id),
                                  labels: _draftArrivalCelebration!.labels,
                                  summary: _draftArrivalCelebration!.summary,
                                  onComplete: _dismissDraftArrivalCelebration,
                                ),
                              ),
                            if (uploadSession != null)
                              GalaxyDocumentUploadOverlay(
                                session: uploadSession,
                                targetScreenPosition:
                                    _resolveUploadTargetScreenPosition(
                                  uploadSession,
                                ),
                                onRetry: () => ref
                                    .read(galaxyDocumentUploadProvider.notifier)
                                    .retryLastUpload(),
                                onDismiss: () => ref
                                    .read(galaxyDocumentUploadProvider.notifier)
                                    .clearSession(),
                              ),
                            if (_previewNode != null &&
                                _previewScreenPosition != null)
                              Positioned(
                                left: _previewScreenPosition!.dx,
                                top: _previewScreenPosition!.dy,
                                child: AnimatedScale(
                                  scale: 1,
                                  duration: const Duration(milliseconds: 180),
                                  curve: Curves.easeOutBack,
                                  child: AnimatedOpacity(
                                    opacity: 1,
                                    duration: const Duration(milliseconds: 160),
                                    child: GalaxyNodePreviewCard(
                                      node: _previewNode!,
                                      onFocus: _focusPreviewNode,
                                      onInspectConnections:
                                          _inspectPreviewConnections,
                                      onViewDetails: () => unawaited(
                                        _openKnowledgeDetail(_previewNode!.id),
                                      ),
                                      onStartReview: _startReviewForPreviewNode,
                                      onLaunchPrediction:
                                          _launchPredictionForPreviewNode,
                                    ),
                                  ),
                                ),
                              ),
                            SafeArea(
                              child: Stack(
                                children: [
                                  Positioned(
                                    top: 12,
                                    left: 16,
                                    child: AnimatedSwitcher(
                                      duration:
                                          const Duration(milliseconds: 150),
                                      child: currentSector == null
                                          ? const SizedBox.shrink()
                                          : GalaxySectorIndicator(
                                              key: ValueKey(currentSector.name),
                                              label: SectorConfig.getStyle(
                                                currentSector,
                                              ).name,
                                              color: SectorConfig.getColor(
                                                currentSector,
                                              ),
                                              isDarkMode: isDarkMode,
                                            ),
                                    ),
                                  ),
                                  if (overviewStats != null &&
                                      _camera.scale < 0.32)
                                    Positioned(
                                      top: 14,
                                      right: 16,
                                      child: _GalaxyOverviewStats(
                                        stats: overviewStats,
                                        isDarkMode: isDarkMode,
                                      ),
                                    ),
                                  Positioned(
                                    top: 112,
                                    right: 16,
                                    left:
                                        constraints.maxWidth < 560 ? 16 : null,
                                    child: GoalWorldGraphMiniPanel(
                                      isGoalWorldMode: _isGoalWorldMode,
                                      onViewModeToggle: () {
                                        setState(() {
                                          _isGoalWorldMode = !_isGoalWorldMode;
                                          if (!_isGoalWorldMode) {
                                            _spotlightNodeIds =
                                                const <String>{};
                                            _spotlightAnchorId = null;
                                          }
                                        });
                                      },
                                    ),
                                  ),
                                  Positioned(
                                    top: 56,
                                    left: 16,
                                    right: 16,
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        contributionStats.when(
                                          data: (stats) =>
                                              GalaxyContributionBanner(
                                            isDarkMode: isDarkMode,
                                            stats: stats,
                                          ),
                                          loading: () =>
                                              const GalaxyContributionBanner
                                                  .loading(
                                            isDarkMode: isDarkMode,
                                          ),
                                          error: (_, __) =>
                                              const SizedBox.shrink(),
                                        ),
                                        if (showMasteryEmptyBanner) ...[
                                          const SizedBox(height: 12),
                                          _GalaxyMasteryEmptyBanner(
                                            onAction: () => context.push(
                                              TaskRoutes.taskCreate,
                                            ),
                                          ),
                                        ],
                                        if (draftPromptBatch != null) ...[
                                          const SizedBox(height: 12),
                                          _GalaxyDraftPromptCard(
                                            batch: draftPromptBatch,
                                            onReview: () => _openDraftReview(
                                              batchId: draftPromptBatch.id,
                                            ),
                                            onDismiss: () => ref
                                                .read(
                                                  galaxyDraftReviewProvider
                                                      .notifier,
                                                )
                                                .dismissPrompt(
                                                  draftPromptBatch.id,
                                                ),
                                          ),
                                        ],
                                        if (showDraftPendingIndicator) ...[
                                          const SizedBox(height: 12),
                                          Align(
                                            alignment: Alignment.centerRight,
                                            child: _GalaxyDraftPendingIndicator(
                                              batchCount: draftReviewState
                                                  .pendingBatchCount,
                                              draftCount: draftReviewState
                                                  .pendingDraftCount,
                                              onTap: _openDraftReview,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                  Positioned(
                                    left: 0,
                                    right: 0,
                                    bottom: 18,
                                    child: Center(
                                      child: FloatingActionButton.extended(
                                        heroTag: 'galaxy_add_study_material',
                                        onPressed: uploadSession != null &&
                                                !uploadSession.isTerminal
                                            ? null
                                            : _handleGalaxyCoreUploadRequested,
                                        icon:
                                            const Icon(Icons.menu_book_rounded),
                                        label: Text(
                                          context.l10n.galaxyUploadFabLabel,
                                        ),
                                      ),
                                    ),
                                  ),
                                  Positioned(
                                    left: 16,
                                    bottom: 16,
                                    child: AnimatedOpacity(
                                      opacity: _camera.scale >= 0.3 ? 1 : 0,
                                      duration:
                                          const Duration(milliseconds: 180),
                                      child: IgnorePointer(
                                        ignoring: _camera.scale < 0.3,
                                        child: GalaxyMiniMap(
                                          camera: _camera,
                                          positions: _renderPositions,
                                          nodesById: _nodesById,
                                          blendedColors: blendedColors,
                                          worldBounds: _computeWorldBounds(),
                                          isDarkMode: isDarkMode,
                                          sceneVersion: _sceneVersion,
                                          onNavigate: _handleMiniMapNavigate,
                                          onViewportDragged: _handleMiniMapDrag,
                                        ),
                                      ),
                                    ),
                                  ),
                                  Positioned(
                                    right: 16,
                                    bottom: 16,
                                    child: GalaxyControls(
                                      onZoomIn: () => _zoomAroundCenter(1.5),
                                      onFitToOverview: _fitOverviewAnimated,
                                      onZoomOut: () =>
                                          _zoomAroundCenter(1 / 1.5),
                                      onReplay: _toggleBuildReplay,
                                      onSearch: _toggleSearchPanel,
                                      onSettings: _openSimulationSettings,
                                      isDarkMode: isDarkMode,
                                      isReplaying: _isBuildAnimating,
                                      isSearchOpen: _isSearchOpen,
                                      isSettingsOpen: _isSettingsOpen,
                                    ),
                                  ),
                                  Positioned(
                                    top: 58,
                                    right: 16,
                                    child: AnimatedSlide(
                                      offset: _isSearchOpen
                                          ? Offset.zero
                                          : const Offset(0, -0.08),
                                      duration:
                                          const Duration(milliseconds: 220),
                                      curve: Curves.easeOutCubic,
                                      child: AnimatedOpacity(
                                        opacity: _isSearchOpen ? 1 : 0,
                                        duration:
                                            const Duration(milliseconds: 180),
                                        child: IgnorePointer(
                                          ignoring: !_isSearchOpen,
                                          child: GalaxySearchPanel(
                                            controller: _searchController,
                                            query: _searchQuery,
                                            results: _searchResults,
                                            isDarkMode: isDarkMode,
                                            onQueryChanged: _updateSearchQuery,
                                            onClose: _toggleSearchPanel,
                                            onNodeSelected:
                                                _handleSearchNodeSelected,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DraftArrivalCelebration {
  const _DraftArrivalCelebration({
    required this.id,
    required this.labels,
    required this.summary,
  });

  final String id;
  final List<String> labels;
  final String summary;
}

class _GalaxyDraftPromptCard extends StatelessWidget {
  const _GalaxyDraftPromptCard({
    required this.batch,
    required this.onReview,
    required this.onDismiss,
  });

  final GalaxyDraftBatch batch;
  final VoidCallback onReview;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onReview,
        borderRadius: BorderRadius.circular(24),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: const LinearGradient(
              colors: <Color>[
                Color(0xE6223658),
                Color(0xE6142038),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: DS.neutral0.withValues(alpha: 0.1),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.galaxyShadow.withValues(alpha: 0.16),
                blurRadius: 24,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: DS.neutral0.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(
                        Icons.auto_awesome_rounded,
                        color: DS.neutral0,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.l10n.galaxyDraftReviewPromptTitle(
                              batch.drafts.length,
                              batch.documentName,
                            ),
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: DS.neutral0,
                              fontWeight: FontWeight.w800,
                              height: 1.2,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            context.l10n.galaxyDraftReviewPromptBody,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: DS.neutral0.withValues(alpha: 0.72),
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: onDismiss,
                      icon: Icon(
                        Icons.close_rounded,
                        color: DS.neutral0.withValues(alpha: 0.8),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: DS.neutral0,
                          side: BorderSide(
                            color: DS.neutral0.withValues(alpha: 0.18),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: onDismiss,
                        child: Text(context.l10n.galaxyDraftReviewLater),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: DS.neutral0,
                          foregroundColor: const Color(0xFF182238),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: onReview,
                        icon: const Icon(Icons.swipe_rounded, size: 18),
                        label: Text(context.l10n.galaxyDraftReviewNow),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _GalaxyDraftPendingIndicator extends StatelessWidget {
  const _GalaxyDraftPendingIndicator({
    required this.batchCount,
    required this.draftCount,
    required this.onTap,
  });

  final int batchCount;
  final int draftCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(999),
          child: Ink(
            decoration: BoxDecoration(
              color: const Color(0xD9101A2C),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: DS.neutral0.withValues(alpha: 0.1),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: DS.warning,
                      boxShadow: [
                        BoxShadow(
                          color: DS.warning.withValues(alpha: 0.5),
                          blurRadius: 10,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    context.l10n.galaxyDraftPendingIndicator(
                      batchCount,
                      draftCount,
                    ),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.neutral0,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({
    required this.backgroundColor,
    required this.foregroundColor,
    required this.title,
    this.highlights = const <String>[],
    this.showLoader = false,
    this.message,
    this.actionLabel,
    this.onAction,
  });

  final Color backgroundColor;
  final Color foregroundColor;
  final String title;
  final List<String> highlights;
  final bool showLoader;
  final String? message;
  final String? actionLabel;
  final Future<void> Function()? onAction;

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return ColoredBox(
      color: backgroundColor,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: (isDarkMode ? DS.neutral0 : DS.neutral900)
                    .withValues(alpha: isDarkMode ? 0.04 : 0.03),
                borderRadius: BorderRadius.circular(28),
                border: Border.all(
                  color: (isDarkMode ? DS.neutral0 : DS.neutral900)
                      .withValues(alpha: 0.08),
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 28,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TweenAnimationBuilder<double>(
                      tween: Tween<double>(begin: 0.2, end: 1),
                      duration: const Duration(milliseconds: 1200),
                      curve: Curves.easeInOut,
                      builder: (context, value, _) => SizedBox(
                        width: 76,
                        height: 76,
                        child: CustomPaint(
                          painter: _StatusOrbPainter(
                            progress: value,
                            isDarkMode: isDarkMode,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      title,
                      style: TextStyle(
                        color: foregroundColor,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.2,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    if (message != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        message!,
                        style: TextStyle(
                          color: foregroundColor.withValues(alpha: 0.72),
                          fontSize: 14,
                          height: 1.5,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                    if (highlights.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 8,
                        runSpacing: 8,
                        children: highlights
                            .map(
                              (item) => Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 6,
                                ),
                                decoration: BoxDecoration(
                                  color:
                                      foregroundColor.withValues(alpha: 0.08),
                                  borderRadius: BorderRadius.circular(999),
                                  border: Border.all(
                                    color: foregroundColor.withValues(
                                      alpha: 0.12,
                                    ),
                                  ),
                                ),
                                child: Text(
                                  item,
                                  style: TextStyle(
                                    color:
                                        foregroundColor.withValues(alpha: 0.72),
                                    fontSize: 12,
                                    fontWeight: DS.fontWeightSemibold,
                                  ),
                                ),
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                    if (showLoader) ...[
                      const SizedBox(height: 18),
                      const _StatusLoader(),
                    ],
                    if (actionLabel != null && onAction != null) ...[
                      const SizedBox(height: 18),
                      FilledButton(
                        onPressed: () => unawaited(onAction!()),
                        child: Text(actionLabel!),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GalaxyOverviewStats extends StatelessWidget {
  const _GalaxyOverviewStats({
    required this.stats,
    required this.isDarkMode,
  });

  final _OverviewStatsData stats;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: (isDarkMode ? const Color(0xCC101929) : DS.neutral0)
              .withValues(alpha: 0.88),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: (isDarkMode ? DS.neutral0 : DS.neutral900)
                .withValues(alpha: 0.08),
          ),
          boxShadow: [
            BoxShadow(
              color:
                  DS.galaxyShadow.withValues(alpha: isDarkMode ? 0.18 : 0.08),
              blurRadius: 20,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _OverviewMetric(
                label: context.l10n.galaxyOverviewNodes,
                value: stats.totalNodes.toDouble(),
                suffix: '',
                emptyLabel: context.l10n.galaxyNotStarted,
                isEmpty: stats.totalNodes == 0,
                isDarkMode: isDarkMode,
              ),
              const SizedBox(width: 14),
              _OverviewMetric(
                label: context.l10n.galaxyOverviewUnlocked,
                value: stats.unlockRatio * 100,
                suffix: '%',
                emptyLabel: context.l10n.galaxyNotLit,
                isEmpty: stats.unlockedNodes == 0,
                isDarkMode: isDarkMode,
              ),
              const SizedBox(width: 14),
              _OverviewMetric(
                label: context.l10n.galaxyOverviewMastery,
                value: stats.masteryAverage.toDouble(),
                suffix: '%',
                emptyLabel: context.l10n.galaxyNotStarted,
                isEmpty: stats.masteryAverage == 0,
                isDarkMode: isDarkMode,
              ),
            ],
          ),
        ),
      );
}

class _OverviewMetric extends StatelessWidget {
  const _OverviewMetric({
    required this.label,
    required this.value,
    required this.suffix,
    required this.emptyLabel,
    required this.isEmpty,
    required this.isDarkMode,
  });

  final String label;
  final double value;
  final String suffix;
  final String emptyLabel;
  final bool isEmpty;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) {
    final foreground = isDarkMode ? DS.neutral0 : const Color(0xFF101828);
    final secondary = isDarkMode
        ? DS.neutral0.withValues(alpha: 0.62)
        : DS.galaxyShadow.withValues(alpha: 0.54);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: secondary,
            fontSize: 11,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: 2),
        if (isEmpty)
          Text(
            emptyLabel,
            style: TextStyle(
              color: foreground,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          )
        else
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0, end: value),
            duration: const Duration(milliseconds: 720),
            curve: Curves.easeOutCubic,
            builder: (context, animatedValue, _) => Text(
              '${animatedValue.round()}$suffix',
              style: TextStyle(
                color: foreground,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
      ],
    );
  }
}

class _GalaxyMasteryEmptyBanner extends StatelessWidget {
  const _GalaxyMasteryEmptyBanner({required this.onAction});

  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xE6101929),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.neutral0.withValues(alpha: 0.08)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: DS.neutral0.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.auto_awesome_outlined,
                  color: DS.neutral0,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.galaxyNoMasteryTitle,
                      style: TextStyle(
                        color: DS.neutral0,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      context.l10n.galaxyNoMasterySubtitle,
                      style: TextStyle(
                        color: DS.neutral0.withValues(alpha: 0.72),
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton(
                onPressed: onAction,
                child: Text(context.l10n.galaxyGoStudy),
              ),
            ],
          ),
        ),
      );
}

class _StatusLoader extends StatelessWidget {
  const _StatusLoader();

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0, end: 1),
        duration: const Duration(milliseconds: 1000),
        curve: Curves.easeInOut,
        builder: (context, value, _) => Row(
          mainAxisSize: MainAxisSize.min,
          children: List<Widget>.generate(3, (index) {
            final phase = (value + index * 0.18) % 1.0;
            final opacity = 0.25 + math.sin(phase * math.pi) * 0.55;
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Theme.of(context)
                      .colorScheme
                      .primary
                      .withValues(alpha: opacity.clamp(0.15, 0.9)),
                ),
              ),
            );
          }),
        ),
      );
}

class _StatusOrbPainter extends CustomPainter {
  const _StatusOrbPainter({
    required this.progress,
    required this.isDarkMode,
  });

  final double progress;
  final bool isDarkMode;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final baseColor =
        isDarkMode ? const Color(0xFF7CA9FF) : const Color(0xFF3A67DA);
    canvas
      ..drawCircle(
        center,
        22 + progress * 6,
        Paint()
          ..color = baseColor.withValues(alpha: 0.12)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
      )
      ..drawCircle(
        center,
        16,
        Paint()
          ..shader = RadialGradient(
            colors: [
              DS.neutral0.withValues(alpha: 0.92),
              baseColor,
              baseColor.withValues(alpha: 0.18),
            ],
          ).createShader(Rect.fromCircle(center: center, radius: 16)),
      );
  }

  @override
  bool shouldRepaint(covariant _StatusOrbPainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.isDarkMode != isDarkMode;
}

class _OverviewStatsData {
  const _OverviewStatsData({
    required this.totalNodes,
    required this.unlockedNodes,
    required this.masteryAverage,
  });

  final int totalNodes;
  final int unlockedNodes;
  final int masteryAverage;

  double get unlockRatio => totalNodes == 0 ? 0 : unlockedNodes / totalNodes;
}

class _PlaybackLaunch {
  const _PlaybackLaunch({
    required this.plan,
    required this.frozenPositions,
    required this.preRevealedNodeIds,
    required this.preRevealedEdgeIds,
  });

  final GalaxyBuildPlaybackPlan plan;
  final Map<String, Offset> frozenPositions;
  final Set<String> preRevealedNodeIds;
  final Set<String> preRevealedEdgeIds;
}

class _CelebrationEntry {
  const _CelebrationEntry({
    required this.id,
    required this.nodeId,
    required this.color,
    required this.emphasizeNeighbors,
  });

  final String id;
  final String nodeId;
  final Color color;
  final bool emphasizeNeighbors;
}
