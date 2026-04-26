import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

/// Aurora status awareness bar with three-layer design:
/// 1. Collapsed: one-line summary (e.g. "Aurora · 已校准")
/// 2. Light expansion: correctable judgment card
/// 3. Deep expansion: four modeling facet cards
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
      return _buildLoadingBar();
    }
    if (!snapshot.auroraActive) {
      return _buildInactiveBar();
    }
    return _buildActiveBar(snapshot);
  }

  // ── Layer 0: Loading ──────────────────────────────────────────

  Widget _buildLoadingBar() => _BarContainer(
        onTap: () {},
        child: Row(
          children: [
            _StatusTonePill(
              label: context.l10n.auroraLoading,
              color: DS.info,
            ),
            const SizedBox(width: DS.spacing8),
            const Expanded(child: _ShimmerRow()),
          ],
        ),
      );

  // ── Layer 0: Inactive ─────────────────────────────────────────

  Widget _buildInactiveBar() => _BarContainer(
        onTap: () {},
        child: Row(
          children: [
            Icon(
              Icons.auto_awesome_outlined,
              size: 16,
              color: DS.textSecondary.withValues(alpha: 0.7),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                context.l10n.auroraStatusInactive,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                ),
              ),
            ),
          ],
        ),
      );

  // ── Layer 1-3: Active Aurora ──────────────────────────────────

  Widget _buildActiveBar(AuroraControlSurfaceSnapshot snapshot) {
    final tone = _toneColor(snapshot.overallStatus);
    final collapsedLabel = _collapsedLabel(snapshot);

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
          // ── Layer 1: Collapsed one-liner ──
          Row(
            children: [
              _StatusTonePill(label: 'Aurora', color: tone),
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
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: 11,
                ),
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

          // ── Layer 2: Light expansion (correctable judgment) ──
          SizeTransition(
            sizeFactor: _expandAnimation,
            axisAlignment: -1,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: DS.spacing10),
                _buildLightExpansion(snapshot),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLightExpansion(AuroraControlSurfaceSnapshot snapshot) {
    final tone = _toneColor(snapshot.overallStatus);
    final primaryFacet = _mostActionableFacet(snapshot.facets);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary judgment
        Text(
          snapshot.summary,
          style: TextStyle(
            color: DS.textPrimary,
            fontSize: DS.fontSizeXs,
            height: 1.4,
          ),
        ),
        const SizedBox(height: DS.spacing8),

        // Evidence from primary facet
        if (primaryFacet != null) ...[
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing4,
            children: [
              Text(
                context.l10n.auroraEvidence,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                ),
              ),
              ...primaryFacet.signals.take(2).map(
                    (s) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing6,
                        vertical: DS.spacing2,
                      ),
                      decoration: BoxDecoration(
                        color: tone.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        s,
                        style: TextStyle(
                          color: tone,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
        ],

        // Action buttons
        Row(
          children: [
            _ActionButton(
              label: context.l10n.auroraActionConfirm,
              onTap: () => _setExpansion(_AuroraExpansion.collapsed),
              isPrimary: true,
            ),
            const SizedBox(width: DS.spacing8),
            _ActionButton(
              label: context.l10n.auroraActionDisagree,
              onTap: () => _setExpansion(_AuroraExpansion.deep),
              isPrimary: false,
            ),
            const SizedBox(width: DS.spacing8),
            _ActionButton(
              label: context.l10n.auroraActionRecalibrate,
              onTap: () => _setExpansion(_AuroraExpansion.collapsed),
              isPrimary: false,
            ),
          ],
        ),
      ],
    );
  }

  // ── Helpers ───────────────────────────────────────────────────

  String _collapsedLabel(AuroraControlSurfaceSnapshot snapshot) {
    final l10n = context.l10n;
    return switch (snapshot.overallStatus) {
      'ready' => l10n.auroraStatusReady,
      'recalibrating' => l10n.auroraStatusRecalibrating,
      'partial' => l10n.auroraStatusPartial,
      _ => l10n.auroraStatusMissing,
    };
  }

  AuroraFacetSnapshot? _mostActionableFacet(List<AuroraFacetSnapshot> facets) {
    // Prefer recalibrating facets, then partial, then first non-missing
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

  Color _toneColor(String status) {
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
}

// ── Expansion state ─────────────────────────────────────────────

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
          margin: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing4,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
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
            border: Border.all(
              color: DS.borderSubtle,
              width: 0.8,
            ),
          ),
          child: child,
        ),
      );
}

class _StatusTonePill extends StatelessWidget {
  const _StatusTonePill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.onTap,
    required this.isPrimary,
  });

  final String label;
  final VoidCallback onTap;
  final bool isPrimary;

  @override
  Widget build(BuildContext context) {
    if (isPrimary) {
      return GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing4,
          ),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.3),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: DS.brandPrimary,
              fontSize: 11,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ),
      );
    }
    return GestureDetector(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: DS.spacing4,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: DS.textSecondary,
            fontSize: 11,
            fontWeight: DS.fontWeightMedium,
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
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
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
