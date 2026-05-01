import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/context_decision_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_calibration_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_status_layer_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/contextual_correction_bar.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Aurora status awareness bar — 6-state model.
///
/// States: sensing | calibrated | risk_found | needs_confirm |
///         calibration_available | cooling_down
///
/// Layer 1: Collapsed one-liner (always visible)
/// Layer 2: Light expansion (correctable judgment)
/// Layer 3: Deep expansion (four facet cards + wake controls)
class StatusAwarenessBar extends ConsumerStatefulWidget {
  const StatusAwarenessBar({
    this.conversationId,
    this.hasActiveRun = false,
    super.key,
  });

  final String? conversationId;
  final bool hasActiveRun;

  @override
  ConsumerState<StatusAwarenessBar> createState() => _StatusAwarenessBarState();
}

class _StatusAwarenessBarState extends ConsumerState<StatusAwarenessBar>
    with SingleTickerProviderStateMixin {
  _AuroraExpansion _expansion = _AuroraExpansion.collapsed;
  String? _selectedCorrectionSemantic;
  late final AnimationController _controller;
  late final Animation<double> _expandAnimation;
  late final AuroraStatusNotifier _statusNotifier;
  Object? _auroraBgmToken;
  String? _lastSyncedAuroraStatus;

  static const Duration _animDuration = Duration(milliseconds: 300);

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: _animDuration,
    );
    _expandAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOutCubic,
    );
    _statusNotifier = ref.read(auroraStatusProvider.notifier);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _statusNotifier.startPeriodicRefresh(
        conversationId: widget.conversationId,
      );
    });
  }

  @override
  void didUpdateWidget(covariant StatusAwarenessBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldConversation = oldWidget.conversationId?.trim();
    final nextConversation = widget.conversationId?.trim();
    if (oldConversation != nextConversation) {
      _statusNotifier.startPeriodicRefresh(
        conversationId: widget.conversationId,
      );
    } else if (oldWidget.hasActiveRun != widget.hasActiveRun) {
      unawaited(
        _statusNotifier.refresh(
          conversationId: widget.conversationId,
        ),
      );
    }
  }

  @override
  void dispose() {
    _statusNotifier.stopPeriodicRefresh();
    unawaited(BgmService.clearAuroraStatus(_auroraBgmToken));
    _controller.dispose();
    super.dispose();
  }

  void _setExpansion(_AuroraExpansion next) {
    setState(() => _expansion = next);
    if (next == _AuroraExpansion.collapsed) {
      unawaited(_controller.reverse());
    } else {
      unawaited(_controller.forward());
    }
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = ref.watch(auroraStatusProvider);

    if (snapshot == null) {
      return _buildLoading();
    }
    if (!snapshot.auroraActive) {
      _syncAuroraSensoryState(null);
      return _buildInactive();
    }
    _syncAuroraSensoryState(snapshot);
    return _buildActive(snapshot);
  }

  // ── Loading / Inactive ────────────────────────────────────────

  Widget _buildLoading() => _BarContainer(
        accentColor: DS.info,
        semanticLabel: context.l10n.auroraLoading,
        onTap: () {},
        child: Row(
          children: [
            _StatusPill(label: 'Aurora', color: DS.info),
            const SizedBox(width: DS.spacing8),
            const Expanded(child: _ShimmerRow()),
          ],
        ),
      );

  Widget _buildInactive() => _BarContainer(
        accentColor: DS.textSecondary,
        semanticLabel: context.l10n.auroraStatusInactive,
        onTap: () {},
        child: Row(
          children: [
            Icon(Icons.auto_awesome_outlined,
                size: 16, color: DS.textSecondary.withValues(alpha: 0.7)),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                context.l10n.auroraStatusInactive,
                style:
                    TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeXs),
              ),
            ),
          ],
        ),
      );

  // ── Active: 6-state bar ───────────────────────────────────────

  Widget _buildActive(AuroraControlSurfaceSnapshot snapshot) {
    final tone = _bandColor(snapshot.overallStatus);
    final collapsedLabel = _bandShortLabel(snapshot);
    final contextLabel = ref.watch(lastContextDecisionProvider);
    final timeContext = snapshot.timeContext;
    final taskHealth = snapshot.taskHealth;

    return _BarContainer(
      accentColor: tone,
      semanticLabel: collapsedLabel,
      onTap: () {
        if (_expansion == _AuroraExpansion.collapsed) {
          _setExpansion(_AuroraExpansion.light);
        } else {
          _setExpansion(_AuroraExpansion.collapsed);
        }
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Layer 1: Collapsed
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () {
              if (_expansion == _AuroraExpansion.collapsed) {
                _setExpansion(_AuroraExpansion.light);
              } else {
                _setExpansion(_AuroraExpansion.collapsed);
              }
            },
            child: Semantics(
              button: true,
              label: collapsedLabel,
              onTap: () {
                if (_expansion == _AuroraExpansion.collapsed) {
                  _setExpansion(_AuroraExpansion.light);
                } else {
                  _setExpansion(_AuroraExpansion.collapsed);
                }
              },
              child: SparkleStaggerItem(
                key: ValueKey('aurora-status-${snapshot.overallStatus}'),
                index: 0,
                offset: 0.018,
                beginScale: 0.992,
                motionToken: SparkleMotionToken.micro,
                child: Row(
                  children: [
                    _StatusPill(label: 'Aurora', color: tone),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: AnimatedSwitcher(
                        duration: _animDuration,
                        switchInCurve: Curves.easeOutCubic,
                        switchOutCurve: Curves.easeInCubic,
                        child: Text(
                          collapsedLabel,
                          key: ValueKey<String>(collapsedLabel),
                          style: TextStyle(
                            color: DS.textPrimary,
                            fontSize: DS.fontSizeXs,
                            fontWeight: DS.fontWeightMedium,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    const SizedBox(width: DS.spacing6),
                    Text(
                      '${snapshot.readyCount}/${snapshot.totalCount}',
                      style: TextStyle(color: DS.textSecondary, fontSize: 11),
                    ),
                    const SizedBox(width: DS.spacing4),
                    Icon(
                      _expansion != _AuroraExpansion.collapsed
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                      size: 16,
                      color: DS.textSecondary,
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (contextLabel != null)
            Padding(
              padding:
                  const EdgeInsets.only(top: DS.spacing4, left: DS.spacing20),
              child: Text(
                contextLabel,
                style: TextStyle(color: DS.textSecondary, fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          if (snapshot.lastCorrectionEffect.visible)
            Padding(
              padding:
                  const EdgeInsets.only(top: DS.spacing6, left: DS.spacing20),
              child: _CorrectionEffectPill(
                label: context.l10n.auroraCorrectionApplied,
              ),
            ),
          if (timeContext.visible && timeContext.label.isNotEmpty)
            Padding(
              padding:
                  const EdgeInsets.only(top: DS.spacing6, left: DS.spacing20),
              child: _TimeContextPill(
                label: timeContext.label,
                subtitle: timeContext.subtitle,
                color: _timeContextColor(timeContext),
                onTap: timeContext.hasConflict
                    ? () => _triggerCalibration(snapshot)
                    : () => _setExpansion(_AuroraExpansion.light),
              ),
            ),
          if (taskHealth.visible && taskHealth.label.isNotEmpty)
            Padding(
              padding:
                  const EdgeInsets.only(top: DS.spacing6, left: DS.spacing20),
              child: _TaskHealthPill(
                health: taskHealth,
                color: _taskHealthColor(taskHealth),
                onTap: taskHealth.needsAttention
                    ? () => _triggerTaskStuckCoreSession(snapshot)
                    : () => _setExpansion(_AuroraExpansion.light),
              ),
            ),

          // Layer 2/3: Expandable
          if (_expansion != _AuroraExpansion.collapsed)
            SizeTransition(
              sizeFactor: _expandAnimation,
              axisAlignment: -1,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: DS.spacing10),
                  _buildExpansionContent(snapshot, tone),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildExpansionContent(
      AuroraControlSurfaceSnapshot snapshot, Color tone) {
    if (_expansion == _AuroraExpansion.deep) {
      final maxHeight =
          (MediaQuery.sizeOf(context).height * 0.62).clamp(280.0, 420.0);
      return ConstrainedBox(
        constraints: BoxConstraints(maxHeight: maxHeight),
        child: SingleChildScrollView(
          child: _buildDeepExpansion(snapshot),
        ),
      );
    }
    return _buildLightExpansion(snapshot, tone);
  }

  // ── Layer 2: Light expansion ──────────────────────────────────

  Widget _buildLightExpansion(
      AuroraControlSurfaceSnapshot snapshot, Color tone) {
    final primaryFacet = _mostActionableFacet(snapshot.facets);
    final wake = snapshot.wakeEligibility;
    final l10n = context.l10n;
    final topGroup = snapshot.topPredictedGroup;
    final evidence = _statusEvidence(snapshot);
    final selectedCorrection = _selectedCorrectionSemantic;
    final showPredictedOptions = topGroup != null &&
        topGroup.options.isNotEmpty &&
        (snapshot.overallStatus == 'needs_confirm' ||
            snapshot.overallStatus == 'risk_found' ||
            snapshot.overallStatus == 'cooling_down');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary
        Text(
          _lightJudgmentText(snapshot, evidence),
          style: TextStyle(
              color: DS.textPrimary, fontSize: DS.fontSizeXs, height: 1.4),
        ),

        // Evidence
        if (primaryFacet != null || evidence.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing4,
            children: [
              Text(l10n.auroraEvidence,
                  style: TextStyle(
                      color: DS.textSecondary, fontSize: DS.fontSizeXs)),
              ...evidence.take(3).map((s) => Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing6, vertical: DS.spacing2),
                    decoration: BoxDecoration(
                      color: tone.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(s, style: TextStyle(color: tone, fontSize: 11)),
                  )),
            ],
          ),
        ],

        // ── Predicted reply options (Aurora modeling chips) ──────────
        if (showPredictedOptions) ...[
          const SizedBox(height: DS.spacing12),
          if (topGroup.question.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Text(
                topGroup.question,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: [
              ...topGroup.primaryOptions.take(4).map((option) =>
                  _PredictedOptionChip(
                    option: option,
                    bandStatus: snapshot.overallStatus,
                    groupId: topGroup.groupId,
                    conversationId: widget.conversationId,
                    onTap: () {
                      final payload = AuroraCorrectionPayload.chip(
                        surface: AuroraCorrectionSurface.statusBand,
                        semanticValue: option.semanticValue,
                        label: auroraCorrectionPresentationFor(
                          context,
                          option,
                        ).label,
                        isDisconfirming: option.isDisconfirming,
                        bandStatus: snapshot.overallStatus,
                        telemetryId: option.telemetryId,
                        groupId: topGroup.groupId,
                        conversationId: widget.conversationId ?? '',
                      );
                      // Record telemetry
                      final telemetry =
                          AuroraTelemetryService(ref.read(apiClientProvider));
                      unawaited(telemetry.recordChipSelected(
                        option: option,
                        groupId: payload.groupId,
                        bandStatus: payload.bandStatus,
                        conversationId: payload.conversationId,
                      ));
                      // Collapse bar after selection
                      _setExpansion(_AuroraExpansion.collapsed);
                      unawaited(SensoryFeedbackService.emitAuroraEvent(
                        AuroraSensoryEvent.correctionCompleted,
                      ));
                      ref
                          .read(auroraStatusProvider.notifier)
                          .markCorrectionEffective(
                            semanticValue: option.semanticValue,
                          );
                      // Refresh status
                      unawaited(ref.read(auroraStatusProvider.notifier).refresh(
                            conversationId: widget.conversationId,
                          ));
                    },
                  )),
              // Freeform correction chip
              if (topGroup.freeformOption != null)
                _PredictedOptionChip(
                  option: topGroup.freeformOption!,
                  bandStatus: snapshot.overallStatus,
                  groupId: topGroup.groupId,
                  conversationId: widget.conversationId,
                  onTap: () {
                    // Freeform opens the Core Session for deeper interaction
                    _triggerCoreSession(snapshot);
                  },
                ),
            ],
          ),
        ] else ...[
          const SizedBox(height: DS.spacing12),
          Text(
            l10n.auroraLayerCorrectionQuestion,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: _fallbackCorrectionOptions(l10n)
                .map(
                  (option) => _StatusCorrectionChip(
                    option: option,
                    selected: selectedCorrection == option.semanticValue,
                    onTap: () => _recordStatusCorrection(snapshot, option),
                  ),
                )
                .toList(),
          ),
        ],

        if (selectedCorrection != null) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            l10n.auroraCorrectionRecorded,
            style: TextStyle(
              color: DS.success,
              fontSize: 11,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ],

        const SizedBox(height: DS.spacing10),

        // Context-sensitive action buttons
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing6,
          children: _buildActions(snapshot, wake, l10n),
        ),
      ],
    );
  }

  List<Widget> _buildActions(AuroraControlSurfaceSnapshot snapshot,
      AuroraWakeEligibility wake, AppLocalizations l10n) {
    final actions = <Widget>[];

    if (snapshot.timeContext.hasConflict) {
      actions.add(_ActionChip(
        label: l10n.chatStatusQuickCalibrate,
        onTap: () => _triggerCalibration(snapshot),
        isPrimary: true,
      ));
    }

    switch (snapshot.overallStatus) {
      case 'risk_found':
        if (wake.canUserWake) {
          // Primary: enter Core Session for deep recalibration
          actions.add(_ActionChip(
            label: l10n.auroraActionDeepConversation,
            onTap: () => _triggerCoreSession(snapshot),
            isPrimary: true,
          ));
        }
        actions.add(_ActionChip(
          label: l10n.auroraActionViewDetails,
          onTap: () => _setExpansion(_AuroraExpansion.deep),
        ));
      case 'needs_confirm':
        if (wake.canUserWake) {
          actions.add(_ActionChip(
            label: l10n.auroraActionDeepConversation,
            onTap: () => _triggerCoreSession(snapshot),
            isPrimary: true,
          ));
        }
        actions.add(_ActionChip(
          label: l10n.auroraActionViewDetails,
          onTap: () => _setExpansion(_AuroraExpansion.deep),
        ));
      case 'calibration_available':
        if (wake.canUserWake) {
          // Full L3 session — most impactful action
          actions.add(_ActionChip(
            label: l10n.auroraWakeAvailable(wake.userQuotaRemaining),
            onTap: () => _triggerCoreSession(snapshot),
            isPrimary: true,
          ));
        }
        // Fallback: light calibration panel
        actions.add(_ActionChip(
          label: context.l10n.chatStatusQuickCalibrate,
          onTap: () => _triggerCalibration(snapshot),
        ));
      case 'cooling_down':
        actions.add(_ActionChip(
          label: l10n.auroraWakeCooling(wake.cooldownRemainingMin),
        ));
        actions.add(_ActionChip(
          label: l10n.auroraWakeQuickFallback,
          onTap: () => _triggerCalibration(snapshot),
        ));
      default:
        actions.add(_ActionChip(
          label: l10n.auroraActionViewDetails,
          onTap: () => _setExpansion(_AuroraExpansion.deep),
        ));
    }

    return actions;
  }

  // ── Layer 3: Deep expansion ───────────────────────────────────

  Widget _buildDeepExpansion(AuroraControlSurfaceSnapshot snapshot) {
    final l10n = context.l10n;
    final tone = _bandColor(snapshot.overallStatus);
    final selfConfidence = snapshot.selfEvaluation.confidence ??
        _facetByKey(snapshot.facets, 'self_model')?.confidence;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AuroraStatusLayerCard(
          title: l10n.auroraLayerCurrentStatus,
          icon: Icons.monitor_heart_outlined,
          accentColor: tone,
          summary: snapshot.summary,
          bullets: _statusEvidence(snapshot),
          expandLabel: l10n.auroraLayerExpand,
          collapseLabel: l10n.auroraLayerCollapse,
        ),
        const SizedBox(height: DS.spacing10),
        AuroraStatusLayerCard(
          title: l10n.auroraLayerMemoryReferences,
          icon: Icons.history_edu_outlined,
          accentColor: DS.info,
          summary: _memoryReferenceSummary(snapshot, l10n),
          bullets: _memoryReferences(snapshot),
          expandLabel: l10n.auroraLayerExpand,
          collapseLabel: l10n.auroraLayerCollapse,
        ),
        const SizedBox(height: DS.spacing10),
        AuroraStatusLayerCard(
          title: l10n.auroraLayerNextSuggestion,
          icon: Icons.route_outlined,
          accentColor: DS.success,
          summary: _nextSuggestion(snapshot, l10n),
          bullets: _nextSuggestionBullets(snapshot),
          expandLabel: l10n.auroraLayerExpand,
          collapseLabel: l10n.auroraLayerCollapse,
        ),
        const SizedBox(height: DS.spacing10),
        AuroraStatusLayerCard(
          title: l10n.auroraLayerSelfEvaluation,
          icon: Icons.psychology_alt_outlined,
          accentColor: DS.brandPrimary,
          summary: _selfEvaluationSummary(snapshot, l10n),
          confidenceLabel: selfConfidence == null
              ? null
              : l10n.auroraConfidenceLabel((selfConfidence * 100).round()),
          bullets: _selfEvaluationBullets(snapshot),
          expandLabel: l10n.auroraLayerExpand,
          collapseLabel: l10n.auroraLayerCollapse,
        ),
        const SizedBox(height: DS.spacing10),
        _ActionChip(
          label: l10n.auroraActionWakeDeepConversation,
          onTap: () => _triggerCoreSession(snapshot),
          isPrimary: true,
        ),
      ],
    );
  }

  // ── Calibration triggers ──────────────────────────────────────

  /// Light calibration — bottom sheet with observation/judgment/options.
  void _triggerCalibration(AuroraControlSurfaceSnapshot snapshot) {
    final primaryFacet = _mostActionableFacet(snapshot.facets);
    unawaited(showAuroraCalibration(
      context: context,
      observation: primaryFacet?.summary ?? snapshot.summary,
      judgment: snapshot.summary,
      confirmQuestion: context.l10n.auroraCalibrationConfirm,
      confirmOptions: [
        context.l10n.chatMinutes30,
        context.l10n.chatMinutes45,
        context.l10n.chatMinutes60
      ],
      onConfirm: (option) {
        unawaited(SensoryFeedbackService.emitAuroraEvent(
          AuroraSensoryEvent.correctionCompleted,
        ));
        unawaited(ref.read(auroraStatusProvider.notifier).refresh(
              conversationId: widget.conversationId,
            ));
      },
    ));
  }

  /// L3 Core Session — full multi-message interactive modeling session.
  void _triggerCoreSession(AuroraControlSurfaceSnapshot snapshot) {
    final wake = snapshot.wakeEligibility;
    _setExpansion(_AuroraExpansion.collapsed);
    unawaited(SensoryFeedbackService.emitAuroraEvent(
      AuroraSensoryEvent.coreSessionOpen,
    ));
    unawaited(showAuroraCoreSession(
      context: context,
      bandStatus: snapshot.overallStatus,
      wakeReasons: wake.wakeReasons,
      entryReason: AuroraCoreSessionEntryReason.fromSnapshot(
        snapshot: snapshot,
        triggerSource: 'status_bar',
        agendaPreview: const ['确认状态带里的判断', '决定下一步是否调整计划'],
      ),
      conversationId: widget.conversationId,
      scope: wake.suggestedScope.isNotEmpty ? wake.suggestedScope : null,
      sessionType: 'user_initiated',
    ).then((_) {
      // After session exits, refresh the status bar
      unawaited(ref.read(auroraStatusProvider.notifier).refresh(
            conversationId: widget.conversationId,
          ));
    }));
  }

  void _triggerTaskStuckCoreSession(AuroraControlSurfaceSnapshot snapshot) {
    final health = snapshot.taskHealth;
    _setExpansion(_AuroraExpansion.collapsed);
    unawaited(SensoryFeedbackService.emitAuroraEvent(
      AuroraSensoryEvent.coreSessionOpen,
    ));
    unawaited(showAuroraCoreSession(
      context: context,
      bandStatus: 'calibration_available',
      wakeReasons: const ['task_stuck_pattern'],
      entryReason: AuroraCoreSessionEntryReason(
        triggerSource: 'task_health_status_bar',
        observedSignals: [
          health.label,
          if (health.subtitle.trim().isNotEmpty) health.subtitle,
        ],
        suggestedAgendaPreview: const [
          '确认任务卡点的主要原因',
          '把下一张任务卡调小一点',
        ],
        whyNow: context.l10n.auroraTaskStuckWhyNow,
        estimatedMinutes: 2,
      ),
      conversationId: widget.conversationId,
      scope: health.label,
      sessionType: 'task_stuck_light',
    ).then((_) {
      unawaited(ref.read(auroraStatusProvider.notifier).refresh(
            conversationId: widget.conversationId,
          ));
    }));
  }

  void _syncAuroraSensoryState(AuroraControlSurfaceSnapshot? snapshot) {
    final nextStatus = snapshot?.overallStatus;
    if (_lastSyncedAuroraStatus == nextStatus) {
      return;
    }
    final previousStatus = _lastSyncedAuroraStatus;
    _lastSyncedAuroraStatus = nextStatus;
    unawaited(_applyAuroraSensoryState(nextStatus, previousStatus));
  }

  Future<void> _applyAuroraSensoryState(
    String? nextStatus,
    String? previousStatus,
  ) async {
    try {
      final enabled = await SensoryFeedbackService.isAuroraLinkageEnabled();
      _auroraBgmToken = await BgmService.applyAuroraStatus(
        status: nextStatus,
        token: _auroraBgmToken,
        sceneTrack: BgmTrack.chat,
        enabled: enabled,
      );
      if (enabled && previousStatus != null && nextStatus != null) {
        await SensoryFeedbackService.emitAuroraEvent(
          AuroraSensoryEvent.statusChanged,
          enableSound: nextStatus == 'calibration_available',
        );
      }
    } catch (_) {
      // Sensory linkage is deliberately best effort.
    }
  }

  // ── Helpers ───────────────────────────────────────────────────

  String _bandShortLabel(AuroraControlSurfaceSnapshot snapshot) {
    final l10n = context.l10n;
    return switch (snapshot.overallStatus) {
      'sensing' => l10n.auroraBandShortSensing,
      'calibrated' => l10n.auroraBandShortCalibrated,
      'risk_found' => l10n.auroraBandShortRiskFound,
      'needs_confirm' => l10n.auroraBandShortNeedsConfirm,
      'calibration_available' => l10n.auroraBandShortCalibrationAvailable,
      'cooling_down' => l10n.auroraBandShortCoolingDown,
      _ => l10n.auroraBandShortSensing,
    };
  }

  String _lightJudgmentText(
    AuroraControlSurfaceSnapshot snapshot,
    List<String> evidence,
  ) {
    final label = _bandShortLabel(snapshot);
    final firstEvidence = evidence.isEmpty ? '' : evidence.first;
    if (firstEvidence.isEmpty) {
      return '${context.l10n.auroraLayerJudgmentPrefix}$label。';
    }
    return '${context.l10n.auroraLayerJudgmentPrefix}$label（$firstEvidence）。';
  }

  Color _bandColor(String status) {
    switch (status) {
      case 'calibrated':
        return DS.success;
      case 'risk_found':
        return DS.warning;
      case 'needs_confirm':
        return DS.info;
      case 'calibration_available':
        return DS.brandPrimary;
      case 'cooling_down':
        return DS.textSecondary;
      default:
        return DS.textSecondary;
    }
  }

  Color _timeContextColor(AuroraTimeContext context) {
    switch (context.severity) {
      case 'warning':
        return DS.warning;
      case 'info':
        return DS.info;
      default:
        return DS.textSecondary;
    }
  }

  Color _taskHealthColor(AuroraTaskHealth health) {
    switch (health.severity) {
      case 'warning':
        return DS.warning;
      case 'success':
        return DS.success;
      case 'info':
        return DS.info;
      default:
        return DS.textSecondary;
    }
  }

  AuroraFacetSnapshot? _mostActionableFacet(List<AuroraFacetSnapshot> facets) {
    for (final f in facets) {
      if (f.isRecalibrating) return f;
    }
    for (final f in facets) {
      if (f.status == 'partial') return f;
    }
    for (final f in facets) {
      if (f.isActive) return f;
    }
    return facets.isNotEmpty ? facets.first : null;
  }

  AuroraFacetSnapshot? _facetByKey(
    List<AuroraFacetSnapshot> facets,
    String key,
  ) =>
      facets.where((facet) => facet.key == key).firstOrNull;

  List<String> _statusEvidence(AuroraControlSurfaceSnapshot snapshot) {
    final seen = <String>{};
    final evidence = <String>[];
    void add(String value) {
      final normalized = value.trim();
      if (normalized.isEmpty || !seen.add(normalized)) {
        return;
      }
      evidence.add(normalized);
    }

    for (final item in snapshot.statusEvidenceChain) {
      add(item);
    }
    if (snapshot.timeContext.visible && snapshot.timeContext.label.isNotEmpty) {
      add(snapshot.timeContext.subtitle.trim().isEmpty
          ? snapshot.timeContext.label
          : '${snapshot.timeContext.label} · ${snapshot.timeContext.subtitle}');
    }
    if (snapshot.taskHealth.visible && snapshot.taskHealth.label.isNotEmpty) {
      add(snapshot.taskHealth.subtitle.trim().isEmpty
          ? snapshot.taskHealth.label
          : '${snapshot.taskHealth.label} · ${snapshot.taskHealth.subtitle}');
    }
    for (final facet in snapshot.facets) {
      for (final signal in facet.signals) {
        add(signal);
      }
      if (evidence.length >= 5) {
        break;
      }
    }
    return evidence.take(5).toList();
  }

  List<String> _memoryReferences(AuroraControlSurfaceSnapshot snapshot) {
    if (snapshot.memoryReferences.isNotEmpty) {
      return snapshot.memoryReferences;
    }
    final fallback = <String>[];
    final userFacet = _facetByKey(snapshot.facets, 'user_model');
    final goalFacet = _facetByKey(snapshot.facets, 'goal_model');
    if (userFacet != null && userFacet.summary.trim().isNotEmpty) {
      fallback.add(userFacet.summary);
    }
    if (goalFacet != null && goalFacet.summary.trim().isNotEmpty) {
      fallback.add(goalFacet.summary);
    }
    return fallback;
  }

  String _memoryReferenceSummary(
    AuroraControlSurfaceSnapshot snapshot,
    AppLocalizations l10n,
  ) {
    final references = _memoryReferences(snapshot);
    if (references.isEmpty) {
      return l10n.auroraLayerMemoryFallback;
    }
    return references.first;
  }

  String _nextSuggestion(
    AuroraControlSurfaceSnapshot snapshot,
    AppLocalizations l10n,
  ) {
    final backendSuggestion = snapshot.nextStepSuggestion.trim();
    if (backendSuggestion.isNotEmpty) {
      return backendSuggestion;
    }
    if (snapshot.timeContext.hasConflict) {
      return l10n.auroraLayerNextSuggestionTimeConflict;
    }
    final topOption = snapshot.topPredictedGroup?.primaryOptions.firstOrNull;
    if (topOption != null && topOption.label.trim().isNotEmpty) {
      return topOption.label;
    }
    return l10n.auroraLayerNextSuggestionFallback;
  }

  List<String> _nextSuggestionBullets(AuroraControlSurfaceSnapshot snapshot) {
    final options = snapshot.topPredictedGroup?.primaryOptions
            .map((option) => option.label.trim())
            .where((label) => label.isNotEmpty)
            .take(3)
            .toList() ??
        const <String>[];
    if (options.isNotEmpty) {
      return options;
    }
    return snapshot.wakeEligibility.wakeReasons.take(3).toList();
  }

  String _selfEvaluationSummary(
    AuroraControlSurfaceSnapshot snapshot,
    AppLocalizations l10n,
  ) {
    if (snapshot.selfEvaluation.why.trim().isNotEmpty) {
      return snapshot.selfEvaluation.why.trim();
    }
    final selfFacet = _facetByKey(snapshot.facets, 'self_model');
    if (selfFacet != null && selfFacet.summary.trim().isNotEmpty) {
      return selfFacet.summary;
    }
    return l10n.auroraLayerSelfEvalFallback;
  }

  List<String> _selfEvaluationBullets(AuroraControlSurfaceSnapshot snapshot) {
    final bullets = <String>[];
    final risk = snapshot.selfEvaluation.risk.trim();
    if (risk.isNotEmpty) {
      bullets.add(risk);
    }
    final selfFacet = _facetByKey(snapshot.facets, 'self_model');
    if (selfFacet != null) {
      bullets.addAll(selfFacet.signals);
    }
    return bullets;
  }

  List<_StatusCorrectionOption> _fallbackCorrectionOptions(
    AppLocalizations l10n,
  ) =>
      [
        _StatusCorrectionOption(
          label: l10n.auroraCorrectionTimeNotEnough,
          semanticValue: 'time_not_enough',
        ),
        _StatusCorrectionOption(
          label: l10n.auroraCorrectionTooHard,
          semanticValue: 'content_too_hard',
        ),
        _StatusCorrectionOption(
          label: l10n.auroraCorrectionLowEnergy,
          semanticValue: 'low_energy',
        ),
        _StatusCorrectionOption(
          label: l10n.auroraCorrectionNoneOfThese,
          semanticValue: 'none_of_these',
          isDisconfirming: true,
        ),
      ];

  void _recordStatusCorrection(
    AuroraControlSurfaceSnapshot snapshot,
    _StatusCorrectionOption option,
  ) {
    setState(() => _selectedCorrectionSemantic = option.semanticValue);
    unawaited(SensoryFeedbackService.emitAuroraEvent(
      AuroraSensoryEvent.correctionCompleted,
    ));
    final payload = AuroraCorrectionPayload.chip(
      surface: AuroraCorrectionSurface.statusBand,
      semanticValue: option.semanticValue,
      label: option.label,
      isDisconfirming: option.isDisconfirming,
      bandStatus: snapshot.overallStatus,
      groupId: 'status_awareness_bar_fallback',
      conversationId: widget.conversationId ?? '',
    );
    final telemetry = AuroraTelemetryService(ref.read(apiClientProvider));
    unawaited(telemetry.recordStatusBandCorrection(
      label: payload.label,
      semanticValue: payload.semanticValue,
      isDisconfirming: payload.isDisconfirming,
      bandStatus: payload.bandStatus,
      telemetryId: payload.telemetryId,
      groupId: payload.groupId,
      conversationId: payload.conversationId,
    ));
    ref.read(auroraStatusProvider.notifier).markCorrectionEffective(
          semanticValue: option.semanticValue,
        );
    unawaited(ref.read(auroraStatusProvider.notifier).refresh(
          conversationId: widget.conversationId,
        ));
  }
}

// ── Enums ───────────────────────────────────────────────────────

enum _AuroraExpansion { collapsed, light, deep }

// ── Shared widgets ──────────────────────────────────────────────

class _BarContainer extends StatelessWidget {
  const _BarContainer({
    required this.accentColor,
    required this.semanticLabel,
    required this.onTap,
    required this.child,
  });

  final Color accentColor;
  final String semanticLabel;
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        explicitChildNodes: true,
        label: semanticLabel,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOutCubic,
          margin: const EdgeInsets.symmetric(
              horizontal: DS.spacing16, vertical: DS.spacing4),
          padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12, vertical: DS.spacing10),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                accentColor.withValues(alpha: 0.10),
                DS.surfaceSecondary.withValues(alpha: 0.96),
                DS.surfacePrimary.withValues(alpha: 0.88),
              ],
            ),
            borderRadius: BorderRadius.circular(DS.radius12),
            border: Border.all(
              color: accentColor.withValues(alpha: 0.18),
              width: 0.8,
            ),
          ),
          child: child,
        ),
      );
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8, vertical: DS.spacing4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
              color: color,
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightSemibold),
        ),
      );
}

class _TimeContextPill extends StatelessWidget {
  const _TimeContextPill({
    required this.label,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  final String label;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final semantic = subtitle.trim().isEmpty ? label : '$label. $subtitle';
    return Semantics(
      container: true,
      button: true,
      label: semantic,
      onTap: onTap,
      child: ExcludeSemantics(
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 28),
            padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8, vertical: DS.spacing4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(999),
              border:
                  Border.all(color: color.withValues(alpha: 0.22), width: 0.8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.event_busy_outlined, size: 13, color: color),
                const SizedBox(width: DS.spacing4),
                Flexible(
                  child: Text(
                    subtitle.trim().isEmpty ? label : '$label · $subtitle',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: color,
                      fontSize: 11,
                      fontWeight: DS.fontWeightMedium,
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
}

class _TaskHealthPill extends StatelessWidget {
  const _TaskHealthPill({
    required this.health,
    required this.color,
    required this.onTap,
  });

  final AuroraTaskHealth health;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final subtitle =
        health.subtitle.trim().isNotEmpty ? health.subtitle : health.trendLabel;
    final semantic =
        subtitle.trim().isEmpty ? health.label : '${health.label}. $subtitle';
    return Semantics(
      container: true,
      button: true,
      label: semantic,
      onTap: onTap,
      child: ExcludeSemantics(
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 28),
            padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8, vertical: DS.spacing4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(999),
              border:
                  Border.all(color: color.withValues(alpha: 0.22), width: 0.8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.assignment_late_outlined, size: 13, color: color),
                const SizedBox(width: DS.spacing4),
                Flexible(
                  child: Text(
                    subtitle.trim().isEmpty
                        ? health.label
                        : '${health.label} · $subtitle',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: color,
                      fontSize: 11,
                      fontWeight: DS.fontWeightMedium,
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
}

class _CorrectionEffectPill extends StatelessWidget {
  const _CorrectionEffectPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Semantics(
        label: label,
        child: ExcludeSemantics(
          child: Container(
            constraints: const BoxConstraints(minHeight: 28),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing4,
            ),
            decoration: BoxDecoration(
              color: DS.semanticSuccess.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: DS.semanticSuccess.withValues(alpha: 0.22),
                width: 0.8,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.check_circle_outline_rounded,
                  size: 13,
                  color: DS.semanticSuccess,
                ),
                const SizedBox(width: DS.spacing4),
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.semanticSuccess,
                      fontSize: 11,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _ActionChip extends StatelessWidget {
  const _ActionChip({
    required this.label,
    this.onTap,
    this.isPrimary = false,
  });
  final String label;
  final VoidCallback? onTap;
  final bool isPrimary;

  @override
  Widget build(BuildContext context) {
    if (onTap == null) {
      return Container(
        padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10, vertical: DS.spacing6),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label,
            style: TextStyle(color: DS.textSecondary, fontSize: 11)),
      );
    }
    final foreground = isPrimary ? DS.brandPrimary : DS.textSecondary;
    return Listener(
      key: ValueKey<String>('aurora-status-action-$label'),
      behavior: HitTestBehavior.opaque,
      onPointerUp: (_) => onTap?.call(),
      child: Semantics(
        button: true,
        label: label,
        onTap: onTap,
        child: ExcludeSemantics(
          child: Container(
            constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
            padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10, vertical: DS.spacing6),
            decoration: BoxDecoration(
              color: isPrimary
                  ? DS.brandPrimary.withValues(alpha: 0.1)
                  : DS.surfaceSecondary.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(999),
              border: isPrimary
                  ? Border.all(color: DS.brandPrimary.withValues(alpha: 0.25))
                  : null,
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: TextStyle(
                color: foreground,
                fontSize: 11,
                fontWeight:
                    isPrimary ? DS.fontWeightMedium : DS.fontWeightRegular,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusCorrectionOption {
  const _StatusCorrectionOption({
    required this.label,
    required this.semanticValue,
    this.isDisconfirming = false,
  });

  final String label;
  final String semanticValue;
  final bool isDisconfirming;
}

class _StatusCorrectionChip extends StatelessWidget {
  const _StatusCorrectionChip({
    required this.option,
    required this.selected,
    required this.onTap,
  });

  final _StatusCorrectionOption option;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? DS.success : DS.info;
    return Listener(
      key: ValueKey<String>(
        'aurora-status-correction-${option.semanticValue}',
      ),
      behavior: HitTestBehavior.opaque,
      onPointerUp: (_) => onTap(),
      child: Semantics(
        button: true,
        selected: selected,
        label: option.label,
        onTap: onTap,
        child: ExcludeSemantics(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
            padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10, vertical: DS.spacing6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: selected ? 0.14 : 0.08),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: color.withValues(alpha: 0.28)),
            ),
            alignment: Alignment.center,
            child: Text(
              option.label,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight:
                    selected ? DS.fontWeightSemibold : DS.fontWeightMedium,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Predicted option chip ───────────────────────────────────────

class _PredictedOptionChip extends StatelessWidget {
  const _PredictedOptionChip({
    required this.option,
    required this.bandStatus,
    required this.groupId,
    required this.conversationId,
    required this.onTap,
  });

  final AuroraPredictedReplyOption option;
  final String bandStatus;
  final String groupId;
  final String? conversationId;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isSpecial = option.isDisconfirming || option.isFreeform;
    final color = isSpecial ? DS.textSecondary : DS.info;
    final presentation = auroraCorrectionPresentationFor(context, option);
    return Listener(
      behavior: HitTestBehavior.opaque,
      onPointerUp: (_) => onTap(),
      child: Semantics(
        button: true,
        label: presentation.label,
        onTap: onTap,
        child: ExcludeSemantics(
          child: Container(
            constraints: const BoxConstraints(minHeight: 32, minWidth: 44),
            padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10, vertical: DS.spacing6),
            decoration: BoxDecoration(
              color: isSpecial
                  ? Colors.transparent
                  : color.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color:
                    isSpecial ? DS.borderSubtle : color.withValues(alpha: 0.25),
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              presentation.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isSpecial ? DS.textSecondary : color,
                fontSize: 11,
                fontWeight:
                    isSpecial ? DS.fontWeightRegular : DS.fontWeightMedium,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ShimmerRow extends StatelessWidget {
  const _ShimmerRow();

  @override
  Widget build(BuildContext context) => Row(
        children: List.generate(
          4,
          (_) => const Padding(
            padding: EdgeInsets.only(right: DS.spacing6),
            child: _ShimmerDot(),
          ),
        ),
      );
}

class _ShimmerDot extends StatefulWidget {
  const _ShimmerDot();

  @override
  State<_ShimmerDot> createState() => _ShimmerDotState();
}

class _ShimmerDotState extends State<_ShimmerDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1200));
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          final opacity = 0.25 + 0.25 * (_controller.value * 2 - 1).abs();
          return Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: DS.textSecondary.withValues(alpha: opacity),
            ),
          );
        },
      );
}
