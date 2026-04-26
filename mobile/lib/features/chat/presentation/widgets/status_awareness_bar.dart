import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

/// Status Awareness Bar (状态感知条).
///
/// A collapsible bar that shows the user's 4+1 Aurora modeling domain
/// coverage.  In its default (collapsed) state it renders a thin strip of
/// indicator dots.  Tapping expands it to reveal per-domain status rows.
class StatusAwarenessBar extends ConsumerStatefulWidget {
  const StatusAwarenessBar({super.key});

  @override
  ConsumerState<StatusAwarenessBar> createState() =>
      _StatusAwarenessBarState();
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
    // Kick off initial fetch
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(auroraStatusProvider.notifier).refresh();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() {
      _expanded = !_expanded;
      if (_expanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(auroraStatusProvider);

    return AnimatedBuilder(
      animation: _expandAnimation,
      builder: (context, _) {
        if (status == null) {
          return _buildLoadingBar();
        }
        if (!status.auroraActive) {
          return _buildInactiveBar();
        }
        return _buildBar(status);
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Loading shimmer
  // ---------------------------------------------------------------------------
  Widget _buildLoadingBar() {
    return _BarContainer(
      onTap: () {},
      child: Row(
        children: [
          Text(
            'Aurora',
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
          const SizedBox(width: DS.sm),
          ...List.generate(
            5,
            (_) => Padding(
              padding: const EdgeInsets.only(right: DS.spacing4),
              child: _ShimmerDot(),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Inactive (Aurora has never run for this user)
  // ---------------------------------------------------------------------------
  Widget _buildInactiveBar() {
    return _BarContainer(
      onTap: () {},
      child: Row(
        children: [
          Icon(
            Icons.auto_awesome_outlined,
            size: 14,
            color: DS.textSecondary.withValues(alpha: 0.6),
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            'Aurora \u672a\u6fc0\u6d3b', // "Aurora 未激活"
            style: TextStyle(
              color: DS.textSecondary.withValues(alpha: 0.7),
              fontSize: DS.fontSizeXs,
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Main bar
  // ---------------------------------------------------------------------------
  Widget _buildBar(AuroraModelingStatus status) {
    final domains = status.domains;
    final coveredCount = domains.where((d) => d.isCovered).length;
    final totalCount = domains.length;

    // Collapsed content: indicator dots
    final collapsedRow = Row(
      children: [
        _StatusDot(isActive: status.modelingComplete),
        const SizedBox(width: DS.spacing4),
        Text(
          '$coveredCount/$totalCount',
          style: TextStyle(
            color: DS.textSecondary,
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
        const SizedBox(width: DS.sm),
        ...domains.map((d) => Padding(
              padding: const EdgeInsets.only(right: DS.spacing4),
              child: _StatusDot(isActive: d.isCovered),
            )),
        const Spacer(),
        Icon(
          _expanded
              ? Icons.keyboard_arrow_up_rounded
              : Icons.keyboard_arrow_down_rounded,
          size: 16,
          color: DS.textSecondary,
        ),
      ],
    );

    // Expanded content: domain rows
    final expandedRows = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        collapsedRow,
        SizeTransition(
          sizeFactor: _expandAnimation,
          axisAlignment: -1.0,
          child: Padding(
            padding: const EdgeInsets.only(top: DS.sm),
            child: Column(
              children: domains
                  .map((d) => _DomainRow(
                        label: d.label,
                        isCovered: d.isCovered,
                        hasTension: d.hasTension,
                      ))
                  .toList(),
            ),
          ),
        ),
      ],
    );

    return _BarContainer(
      onTap: _toggle,
      child: expandedRows,
    );
  }
}

// =============================================================================
// Helper widgets
// =============================================================================

class _BarContainer extends StatelessWidget {
  const _BarContainer({required this.onTap, required this.child});

  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        margin: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(
            color: DS.borderSubtle,
            width: 0.6,
          ),
        ),
        child: child,
      ),
    );
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.isActive});

  final bool isActive;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: isActive ? DS.success : DS.surfaceTertiary,
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: DS.success.withValues(alpha: 0.4),
                  blurRadius: 4,
                  spreadRadius: 0.5,
                ),
              ]
            : null,
      ),
    );
  }
}

class _ShimmerDot extends StatefulWidget {
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
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
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
}

class _DomainRow extends StatelessWidget {
  const _DomainRow({
    required this.label,
    required this.isCovered,
    required this.hasTension,
  });

  final String label;
  final bool isCovered;
  final bool hasTension;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        children: [
          Icon(
            isCovered ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
            size: 14,
            color: isCovered ? DS.success : DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: isCovered ? DS.textPrimary : DS.textSecondary,
                fontSize: DS.fontSizeXs,
                fontWeight:
                    isCovered ? DS.fontWeightMedium : DS.fontWeightRegular,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing6,
              vertical: 1,
            ),
            decoration: BoxDecoration(
              color: isCovered
                  ? DS.success.withValues(alpha: 0.12)
                  : DS.surfaceTertiary.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(DS.radius6),
            ),
            child: Text(
              isCovered ? '\u5df2\u5b8c\u6210' : '\u5f85\u4e86\u89e3', // "已完成" / "待了解"
              style: TextStyle(
                color: isCovered ? DS.success : DS.textSecondary,
                fontSize: 10,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ),
          if (hasTension) ...[
            const SizedBox(width: DS.spacing4),
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: DS.warning.withValues(alpha: 0.8),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
