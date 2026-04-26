import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/context_decision_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_calibration_panel.dart';

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
  late final AnimationController _controller;
  late final Animation<double> _expandAnimation;

  static const Duration _animDuration = Duration(milliseconds: 250);

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
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(auroraStatusProvider.notifier).startPeriodicRefresh(
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
      ref.read(auroraStatusProvider.notifier).startPeriodicRefresh(
            conversationId: widget.conversationId,
          );
    } else if (oldWidget.hasActiveRun != widget.hasActiveRun) {
      unawaited(
        ref.read(auroraStatusProvider.notifier).refresh(
              conversationId: widget.conversationId,
            ),
      );
    }
  }

  @override
  void dispose() {
    ref.read(auroraStatusProvider.notifier).stopPeriodicRefresh();
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
      return _buildInactive();
    }
    return _buildActive(snapshot);
  }

  // ── Loading / Inactive ────────────────────────────────────────

  Widget _buildLoading() => _BarContainer(
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
        onTap: () {},
        child: Row(
          children: [
            Icon(Icons.auto_awesome_outlined, size: 16, color: DS.textSecondary.withValues(alpha: 0.7)),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                context.l10n.auroraStatusInactive,
                style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeXs),
              ),
            ),
          ],
        ),
      );

  // ── Active: 6-state bar ───────────────────────────────────────

  Widget _buildActive(AuroraControlSurfaceSnapshot snapshot) {
    final tone = _bandColor(snapshot.overallStatus);
    final collapsedLabel = _bandLabel(snapshot);
    final contextLabel = ref.watch(lastContextDecisionProvider);

    return _BarContainer(
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
          Row(
            children: [
              _StatusPill(label: 'Aurora', color: tone),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  collapsedLabel,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightMedium,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
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
          if (contextLabel != null)
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing4, left: DS.spacing20),
              child: Text(
                contextLabel,
                style: TextStyle(color: DS.textSecondary, fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),

          // Layer 2/3: Expandable
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

  Widget _buildExpansionContent(AuroraControlSurfaceSnapshot snapshot, Color tone) {
    if (_expansion == _AuroraExpansion.deep) {
      return _buildDeepExpansion(snapshot);
    }
    return _buildLightExpansion(snapshot, tone);
  }

  // ── Layer 2: Light expansion ──────────────────────────────────

  Widget _buildLightExpansion(AuroraControlSurfaceSnapshot snapshot, Color tone) {
    final primaryFacet = _mostActionableFacet(snapshot.facets);
    final wake = snapshot.wakeEligibility;
    final l10n = context.l10n;
    final topGroup = snapshot.topPredictedGroup;
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
          snapshot.summary,
          style: TextStyle(color: DS.textPrimary, fontSize: DS.fontSizeXs, height: 1.4),
        ),

        // Evidence
        if (primaryFacet != null) ...[
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing4,
            children: [
              Text(l10n.auroraEvidence, style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeXs)),
              ...primaryFacet.signals.take(2).map((s) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: DS.spacing6, vertical: DS.spacing2),
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
          if (topGroup!.question.isNotEmpty)
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
              ...topGroup.primaryOptions.take(4).map((option) => _PredictedOptionChip(
                    option: option,
                    bandStatus: snapshot.overallStatus,
                    groupId: topGroup.groupId,
                    conversationId: widget.conversationId,
                    onTap: () {
                      // Record telemetry
                      final telemetry = AuroraTelemetryService(ref.read(apiClientProvider));
                      unawaited(telemetry.recordChipSelected(
                        option: option,
                        groupId: topGroup.groupId,
                        bandStatus: snapshot.overallStatus,
                        conversationId: widget.conversationId,
                      ));
                      // Collapse bar after selection
                      _setExpansion(_AuroraExpansion.collapsed);
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

  List<Widget> _buildActions(AuroraControlSurfaceSnapshot snapshot, AuroraWakeEligibility wake, dynamic l10n) {
    final actions = <Widget>[];

    switch (snapshot.overallStatus) {
      case 'risk_found':
        if (wake.canUserWake) {
          // Primary: enter Core Session for deep recalibration
          actions.add(_ActionChip(
            label: l10n.auroraActionRecalibrate,
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
            label: l10n.auroraActionRecalibrate,
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
          label: '快速校准',
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
    final facetLabels = {
      'user_model': l10n.auroraFacetAboutYou,
      'goal_model': l10n.auroraFacetAboutGoal,
      'scene_model': l10n.auroraFacetAboutNow,
      'self_model': l10n.auroraFacetAboutJudgment,
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: snapshot.facets.map((facet) {
        final color = _facetColor(facet.status);
        return Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing10),
          child: _FacetCard(
            label: facetLabels[facet.key] ?? facet.label,
            status: _facetStatusLabel(facet.status, l10n),
            statusColor: color,
            summary: facet.summary,
            confidence: facet.confidence,
            signals: facet.signals,
          ),
        );
      }).toList(),
    );
  }

  // ── Calibration triggers ──────────────────────────────────────

  /// Light calibration — bottom sheet with observation/judgment/options.
  void _triggerCalibration(AuroraControlSurfaceSnapshot snapshot) {
    final primaryFacet = _mostActionableFacet(snapshot.facets);
    showAuroraCalibration(
      context: context,
      observation: primaryFacet?.summary ?? snapshot.summary,
      judgment: snapshot.summary,
      confirmQuestion: context.l10n.auroraCalibrationConfirm,
      confirmOptions: const ['30 分钟', '45 分钟', '60 分钟'],
      onConfirm: (option) {
        unawaited(ref.read(auroraStatusProvider.notifier).refresh(
              conversationId: widget.conversationId,
            ));
      },
    );
  }

  /// L3 Core Session — full multi-message interactive modeling session.
  void _triggerCoreSession(AuroraControlSurfaceSnapshot snapshot) {
    final wake = snapshot.wakeEligibility;
    _setExpansion(_AuroraExpansion.collapsed);
    unawaited(showAuroraCoreSession(
      context: context,
      ref: ref,
      bandStatus: snapshot.overallStatus,
      wakeReasons: wake.wakeReasons,
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

  // ── Helpers ───────────────────────────────────────────────────

  String _bandLabel(AuroraControlSurfaceSnapshot snapshot) {
    final l10n = context.l10n;
    return switch (snapshot.overallStatus) {
      'sensing' => l10n.auroraBandSensing,
      'calibrated' => l10n.auroraBandCalibrated,
      'risk_found' => l10n.auroraBandRiskFound,
      'needs_confirm' => l10n.auroraBandNeedsConfirm,
      'calibration_available' => l10n.auroraBandCalibrationAvailable,
      'cooling_down' => l10n.auroraBandCoolingDown,
      _ => l10n.auroraBandSensing,
    };
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

  Color _facetColor(String status) {
    switch (status) {
      case 'ready':
        return DS.success;
      case 'recalibrating':
        return DS.warning;
      case 'partial':
        return DS.info;
      default:
        return DS.textSecondary;
    }
  }

  String _facetStatusLabel(String status, dynamic l10n) {
    return switch (status) {
      'ready' => l10n.auroraFacetReady,
      'recalibrating' => l10n.auroraFacetRecalibrating,
      'partial' => l10n.auroraFacetPartial,
      _ => l10n.auroraFacetMissing,
    };
  }
}

// ── Enums ───────────────────────────────────────────────────────

enum _AuroraExpansion { collapsed, light, deep }

// ── Shared widgets ──────────────────────────────────────────────

class _BarContainer extends StatelessWidget {
  const _BarContainer({required this.onTap, required this.child});
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: DS.spacing16, vertical: DS.spacing4),
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing10),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                DS.surfaceSecondary.withValues(alpha: 0.96),
                DS.surfacePrimary.withValues(alpha: 0.88),
              ],
            ),
            borderRadius: BorderRadius.circular(DS.radius12),
            border: Border.all(color: DS.borderSubtle, width: 0.8),
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
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(color: color, fontSize: DS.fontSizeXs, fontWeight: DS.fontWeightSemibold),
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
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing10, vertical: DS.spacing6),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label, style: TextStyle(color: DS.textSecondary, fontSize: 11)),
      );
    }
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing10, vertical: DS.spacing6),
        decoration: BoxDecoration(
          color: isPrimary ? DS.brandPrimary.withValues(alpha: 0.1) : DS.surfaceSecondary.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(999),
          border: isPrimary ? Border.all(color: DS.brandPrimary.withValues(alpha: 0.25)) : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isPrimary ? DS.brandPrimary : DS.textSecondary,
            fontSize: 11,
            fontWeight: isPrimary ? DS.fontWeightMedium : DS.fontWeightRegular,
          ),
        ),
      ),
    );
  }
}

class _FacetCard extends StatelessWidget {
  const _FacetCard({
    required this.label,
    required this.status,
    required this.statusColor,
    required this.summary,
    required this.confidence,
    required this.signals,
  });

  final String label;
  final String status;
  final Color statusColor;
  final String summary;
  final double? confidence;
  final List<String> signals;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing10),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: statusColor.withValues(alpha: 0.28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(label,
                      style: TextStyle(
                          color: DS.textPrimary, fontSize: DS.fontSizeSm, fontWeight: DS.fontWeightSemibold)),
                ),
                Text(status, style: TextStyle(color: statusColor, fontSize: DS.fontSizeXs, fontWeight: DS.fontWeightSemibold)),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Text(summary, style: TextStyle(color: DS.textPrimary, fontSize: DS.fontSizeXs, height: 1.35)),
            if (signals.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: signals
                    .map((s) => Container(
                          padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
                          decoration: BoxDecoration(
                            color: DS.surfaceSecondary,
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(s, style: TextStyle(color: DS.textSecondary, fontSize: 11)),
                        ))
                    .toList(),
              ),
            ],
          ],
        ),
      );
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
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing10, vertical: DS.spacing6),
        decoration: BoxDecoration(
          color: isSpecial ? Colors.transparent : color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: isSpecial ? DS.borderSubtle : color.withValues(alpha: 0.25),
          ),
        ),
        child: Text(
          option.label,
          style: TextStyle(
            color: isSpecial ? DS.textSecondary : color,
            fontSize: 11,
            fontWeight: isSpecial ? DS.fontWeightRegular : DS.fontWeightMedium,
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

class _ShimmerDotState extends State<_ShimmerDot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200));
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
