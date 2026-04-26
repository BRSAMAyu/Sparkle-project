import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

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
  bool _expanded = false;
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

  void _toggle() {
    setState(() {
      _expanded = !_expanded;
      if (_expanded) {
        unawaited(_controller.forward());
      } else {
        unawaited(_controller.reverse());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = ref.watch(auroraStatusProvider);

    return AnimatedBuilder(
      animation: _expandAnimation,
      builder: (context, _) {
        if (snapshot == null) {
          return _buildLoadingBar();
        }
        if (!snapshot.auroraActive) {
          return _buildInactiveBar();
        }
        return _buildBar(snapshot);
      },
    );
  }

  Widget _buildLoadingBar() => _BarContainer(
        onTap: () {},
        child: Row(
          children: [
            _StatusTonePill(
              label: 'Aurora 感知加载中',
              color: DS.info,
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Row(
                children: List.generate(
                  4,
                  (_) => const Padding(
                    padding: EdgeInsets.only(right: DS.spacing6),
                    child: _ShimmerDot(),
                  ),
                ),
              ),
            ),
          ],
        ),
      );

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
                'Aurora 还没有形成可用的认知读数',
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                ),
              ),
            ),
          ],
        ),
      );

  Widget _buildBar(AuroraControlSurfaceSnapshot snapshot) {
    final tone = _toneColor(snapshot.overallStatus);
    final label = _overallLabel(snapshot);
    final facets = snapshot.facets;

    final collapsedRow = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _StatusTonePill(label: label, color: tone),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    '${snapshot.readyCount}/${snapshot.totalCount}',
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                snapshot.summary,
                maxLines: _expanded ? 3 : 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: DS.fontSizeXs,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: facets
                    .map(
                      (facet) => _FacetChip(
                        facet: facet,
                      ),
                    )
                    .toList(),
              ),
            ],
          ),
        ),
        const SizedBox(width: DS.spacing8),
        Icon(
          _expanded
              ? Icons.keyboard_arrow_up_rounded
              : Icons.keyboard_arrow_down_rounded,
          size: 18,
          color: DS.textSecondary,
        ),
      ],
    );

    return _BarContainer(
      onTap: _toggle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          collapsedRow,
          SizeTransition(
            sizeFactor: _expandAnimation,
            axisAlignment: -1,
            child: Padding(
              padding: const EdgeInsets.only(top: DS.spacing10),
              child: Column(
                children: facets
                    .map(
                      (facet) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing8),
                        child: _FacetCard(facet: facet),
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
        ],
      ),
    );
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

  String _overallLabel(AuroraControlSurfaceSnapshot snapshot) {
    switch (snapshot.overallStatus) {
      case 'ready':
        return 'Aurora 感知已收束';
      case 'recalibrating':
        return 'Aurora 正在自校准';
      case 'partial':
        return 'Aurora 正在补全建模';
      default:
        return 'Aurora 感知待建立';
    }
  }
}

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

class _FacetChip extends StatelessWidget {
  const _FacetChip({
    required this.facet,
  });

  final AuroraFacetSnapshot facet;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(facet.status);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            facet.label,
            style: TextStyle(
              color: color,
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _FacetCard extends StatelessWidget {
  const _FacetCard({
    required this.facet,
  });

  final AuroraFacetSnapshot facet;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(facet.status);
    final confidenceText = facet.confidence == null
        ? null
        : '把握度 ${(facet.confidence! * 100).round()}%';
    final freshnessText = facet.freshnessSeconds == null
        ? null
        : '新鲜度 ${_freshnessLabel(facet.freshnessSeconds!)}';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: DS.surfacePrimary.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(
          color: color.withValues(alpha: 0.28),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  facet.label,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              Text(
                _statusLabel(facet.status),
                style: TextStyle(
                  color: color,
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            facet.summary,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeXs,
              height: 1.35,
            ),
          ),
          if (confidenceText != null || freshnessText != null) ...[
            const SizedBox(height: DS.spacing6),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing4,
              children: [
                if (confidenceText != null)
                  Text(
                    confidenceText,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                if (freshnessText != null)
                  Text(
                    freshnessText,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
              ],
            ),
          ],
          if (facet.signals.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: facet.signals
                  .map(
                    (signal) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      decoration: BoxDecoration(
                        color: DS.surfaceSecondary,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        signal,
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
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

Color _statusColor(String status) {
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

String _statusLabel(String status) {
  switch (status) {
    case 'ready':
      return '已连通';
    case 'recalibrating':
      return '重校准中';
    case 'partial':
      return '补全中';
    default:
      return '未形成';
  }
}

String _freshnessLabel(int seconds) {
  if (seconds < 60) {
    return '${seconds}s';
  }
  if (seconds < 3600) {
    return '${(seconds / 60).round()}m';
  }
  return '${(seconds / 3600).round()}h';
}
