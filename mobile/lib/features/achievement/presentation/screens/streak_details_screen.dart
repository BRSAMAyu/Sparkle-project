import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

class StreakDetailsScreen extends ConsumerStatefulWidget {
  const StreakDetailsScreen({super.key});

  @override
  ConsumerState<StreakDetailsScreen> createState() =>
      _StreakDetailsScreenState();
}

class _StreakDetailsScreenState extends ConsumerState<StreakDetailsScreen> {
  static const int _historyDays = 90;
  int? _lastCelebratedRecord;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final stats = ref.read(streakStatsProvider);
    final bestRecord = stats.longestStreak > 0
        ? stats.longestStreak
        : math.max(stats.maxStreak, stats.currentStreak);
    if (stats.currentStreak > 0 &&
        stats.currentStreak >= bestRecord &&
        _lastCelebratedRecord != stats.currentStreak) {
      _lastCelebratedRecord = stats.currentStreak;
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.streak));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final streakStats = ref.watch(streakStatsProvider);
    final historyState = ref.watch(streakHistoryProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(l10n.streakDetails),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _AnimatedSection(
                    delay: Duration(),
                    child: StreakIndicator(
                      style: StreakIndicatorStyle.full,
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  _StreakInsightBanner(
                    stats: streakStats,
                    totalCheckins: historyState.days
                        .where((d) => d.status == StreakDayStatus.active)
                        .length,
                  ),
                  const SizedBox(height: DS.spacing16),
                  _AnimatedSection(
                    delay: const Duration(milliseconds: 100),
                    child: _buildStatsGrid(streakStats, historyState, l10n),
                  ),
                  const SizedBox(height: DS.spacing24),
                  _AnimatedSection(
                    delay: const Duration(milliseconds: 200),
                    child: _buildCalendarCard(historyState, l10n),
                  ),
                  const SizedBox(height: DS.spacing16),
                  _AnimatedSection(
                    delay: const Duration(milliseconds: 300),
                    child: _buildRiskHint(streakStats, l10n),
                  ),
                  const SizedBox(height: DS.spacing16),
                  _AnimatedSection(
                    delay: const Duration(milliseconds: 400),
                    child: _buildShopCallToAction(context, l10n),
                  ),
                  const SizedBox(height: DS.spacing24),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsGrid(
    StreakStats stats,
    StreakHistoryState historyState,
    AppLocalizations l10n,
  ) {
    final bestRecord = stats.longestStreak > 0
        ? stats.longestStreak
        : math.max(stats.maxStreak, stats.currentStreak);
    final freezeUsed = historyState.days
        .where((day) => day.usedFreeze)
        .length;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 380;
        final crossAxisCount = isCompact ? 2 : 3;
        final tileWidth =
            (constraints.maxWidth - (crossAxisCount - 1) * DS.spacing12) /
                crossAxisCount;

        final tiles = [
          _StatTile(
            index: 0,
            title: l10n.streakCurrentLabel,
            value: l10n.streakDays(stats.currentStreak),
            icon: Icons.local_fire_department_rounded,
            color: DS.getStreakColor(stats.currentStreak),
          ),
          _StatTile(
            index: 1,
            title: l10n.streakBestRecord,
            value: l10n.streakDays(bestRecord),
            icon: Icons.emoji_events_outlined,
            color: DS.rarityLegendary,
          ),
          _StatTile(
            index: 2,
            title: l10n.streakTotalCheckin,
            value: '${stats.totalCheckinDays}',
            icon: Icons.calendar_today_outlined,
            color: DS.brandPrimary,
          ),
          _StatTile(
            index: 3,
            title: l10n.streakFreezeCharges,
            value: '${stats.freezeCharges}/${stats.maxFreezeCharges}',
            icon: Icons.ac_unit,
            color: DS.semanticWarning,
          ),
          _StatTile(
            index: 4,
            title: l10n.streakFreezeUsed,
            value: '$freezeUsed',
            icon: Icons.ac_unit,
            color: DS.brandSecondary,
          ),
        ];

        return Wrap(
          spacing: DS.spacing12,
          runSpacing: DS.spacing12,
          children: tiles
              .map(
                (tile) => SizedBox(
                  width: tileWidth,
                  child: tile,
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget _buildCalendarCard(
    StreakHistoryState state,
    AppLocalizations l10n,
  ) {
    if (state.isLoading) {
      return _buildCalendarShell(
        l10n,
        const SparkleListSkeleton(),
      );
    }

    if (state.error != null) {
      return _buildCalendarShell(
        l10n,
        Column(
          children: [
            Text(
              l10n.loadingFailed(state.error!),
              style: TextStyle(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            SparkleButton.outline(
              label: l10n.retry,
              onPressed: () => ref
                  .read(streakHistoryProvider.notifier)
                  .loadHistory(),
            ),
          ],
        ),
      );
    }

    if (state.days.isEmpty) {
      return _buildCalendarShell(
        l10n,
        Center(
          child: Text(
            l10n.streakHistoryEmpty,
            style: TextStyle(color: DS.textSecondary),
          ),
        ),
      );
    }

    return _buildCalendarShell(
      l10n,
      Column(
        children: [
          _buildCalendarLegend(l10n),
          const SizedBox(height: DS.spacing12),
          _buildCalendarGrid(state.days, l10n),
        ],
      ),
    );
  }

  Widget _buildCalendarShell(AppLocalizations l10n, Widget child) => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.streakCalendarTitle,
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            l10n.streakCalendarRange(_historyDays),
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          child,
        ],
      ),
    );

  Widget _buildCalendarLegend(AppLocalizations l10n) => Wrap(
      spacing: DS.spacing12,
      runSpacing: DS.spacing8,
      children: [
        _LegendItem(
          color: DS.semanticSuccess,
          label: l10n.streakStatusActive,
        ),
        _LegendItem(
          color: DS.semanticWarning,
          label: l10n.streakStatusFrozen,
        ),
        _LegendItem(
          color: DS.neutral300,
          label: l10n.streakStatusMissed,
        ),
      ],
    );

  Widget _buildCalendarGrid(
    List<StreakDayRecord> days,
    AppLocalizations l10n,
  ) {
    final localizations = MaterialLocalizations.of(context);
    final firstDayIndex = localizations.firstDayOfWeekIndex;
    final weekdayLabels = List.generate(
      7,
      (index) => localizations.narrowWeekdays[(firstDayIndex + index) % 7],
    );

    final startDay = days.first.day;
    final leadingEmpty = _leadingEmptyCells(startDay, firstDayIndex);
    final totalCells = leadingEmpty + days.length;
    final rows = (totalCells / 7).ceil();
    final cellCount = rows * 7;

    final cellItems = List<StreakDayRecord?>.filled(cellCount, null);
    for (var i = 0; i < days.length; i++) {
      cellItems[leadingEmpty + i] = days[i];
    }

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: weekdayLabels
              .map(
                (label) => Expanded(
                  child: Center(
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textTertiary,
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: DS.spacing8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            mainAxisSpacing: DS.spacing6,
            crossAxisSpacing: DS.spacing6,
          ),
          itemCount: cellCount,
          itemBuilder: (context, index) {
            final record = cellItems[index];
            return _CalendarCell(record: record, index: index);
          },
        ),
      ],
    );
  }

  int _leadingEmptyCells(DateTime day, int firstDayIndex) {
    final weekdayIndex = day.weekday % 7; // Sunday = 0
    var diff = weekdayIndex - firstDayIndex;
    if (diff < 0) diff += 7;
    return diff;
  }

  Widget _buildRiskHint(StreakStats stats, AppLocalizations l10n) {
    if (stats.freezeCharges > 1) {
      return const SizedBox.shrink();
    }

    final isCritical = stats.freezeCharges == 0;
    final background = isCritical
        ? DS.semanticError.withValues(alpha: 0.1)
        : DS.semanticWarning.withValues(alpha: 0.1);
    final border = isCritical ? DS.semanticError : DS.semanticWarning;
    final text = isCritical
        ? l10n.streakRiskNoFreeze
        : l10n.streakRiskLowFreeze;

    return _RiskHintCard(
      isCritical: isCritical,
      background: background,
      borderColor: border,
      text: text,
    );
  }

  Widget _buildShopCallToAction(BuildContext context, AppLocalizations l10n) => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.streakShopTitle,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  l10n.streakShopSubtitle,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: DS.spacing12),
          SparkleButton.primary(
            label: l10n.streakShopAction,
            onPressed: () => context.push('/shop'),
          ),
        ],
      ),
    );
}

// ---------------------------------------------------------------------------
// _AnimatedSection: Fade-in wrapper with stagger delay for major sections
// ---------------------------------------------------------------------------

class _AnimatedSection extends StatefulWidget {
  const _AnimatedSection({
    required this.delay,
    required this.child,
  });

  final Duration delay;
  final Widget child;

  @override
  State<_AnimatedSection> createState() => _AnimatedSectionState();
}

class _AnimatedSectionState extends State<_AnimatedSection> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    Future.delayed(widget.delay, () {
      if (mounted) setState(() => _visible = true);
    });
  }

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: _visible ? 1 : 0),
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeOutCubic,
      builder: (context, value, child) => Opacity(
        opacity: value,
        child: Transform.translate(
          offset: Offset(0, 12 * (1 - value)),
          child: child,
        ),
      ),
      child: widget.child,
    );
}

// ---------------------------------------------------------------------------
// _StatTile: Entrance animation (fade + scale, staggered by index)
// ---------------------------------------------------------------------------

class _StatTile extends StatefulWidget {
  const _StatTile({
    required this.index,
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  final int index;
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  @override
  State<_StatTile> createState() => _StatTileState();
}

class _StatTileState extends State<_StatTile>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
    _scaleAnimation = Tween<double>(begin: 0.9, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutCubic,
      ),
    );

    Future.delayed(Duration(milliseconds: widget.index * 60), () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// Parse the leading integer from a stat value string.
  /// Returns null if the value does not start with a digit.
  int? _parseLeadingInt(String value) {
    final match = RegExp(r'^\d+').firstMatch(value);
    if (match == null) return null;
    return int.tryParse(match.group(0)!);
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
      opacity: _fadeAnimation,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: DS.surfacePrimary,
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(widget.icon, color: widget.color, size: DS.iconSizeSm),
              const SizedBox(height: DS.spacing8),
              Text(
                widget.title,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              _AnimatedStatValue(
                value: widget.value,
                targetNumber: _parseLeadingInt(widget.value),
              ),
            ],
          ),
        ),
      ),
    );
}

// ---------------------------------------------------------------------------
// _AnimatedStatValue: Count-up animation for numeric stat values
// ---------------------------------------------------------------------------

class _AnimatedStatValue extends StatelessWidget {
  const _AnimatedStatValue({
    required this.value,
    required this.targetNumber,
  });

  final String value;
  final int? targetNumber;

  @override
  Widget build(BuildContext context) {
    if (targetNumber == null || targetNumber == 0) {
      return Text(
        value,
        style: TextStyle(
          fontSize: DS.fontSizeBase,
          fontWeight: DS.fontWeightSemibold,
          color: DS.textPrimary,
        ),
      );
    }

    // Determine the suffix after the leading number (e.g. "/5" or " days").
    final leadingStr = targetNumber.toString();
    final suffix = value.substring(leadingStr.length);

    return TweenAnimationBuilder<int>(
      tween: IntTween(begin: 0, end: targetNumber!),
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOutCubic,
      builder: (context, animValue, _) => Text(
        '$animValue$suffix',
        style: TextStyle(
          fontSize: DS.fontSizeBase,
          fontWeight: DS.fontWeightSemibold,
          color: DS.textPrimary,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _LegendItem
// ---------------------------------------------------------------------------

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: DS.borderRadiusFull,
          ),
        ),
        const SizedBox(width: DS.spacing6),
        Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.textSecondary,
          ),
        ),
      ],
    );
}

// ---------------------------------------------------------------------------
// _CalendarCell: Stagger entrance + enhanced visuals
// ---------------------------------------------------------------------------

class _CalendarCell extends StatefulWidget {
  const _CalendarCell({required this.record, required this.index});

  final StreakDayRecord? record;
  final int index;

  @override
  State<_CalendarCell> createState() => _CalendarCellState();
}

class _CalendarCellState extends State<_CalendarCell>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<double> _scaleAnimation;

  // Pulsing border animation for today's cell
  AnimationController? _pulseController;
  Animation<double>? _pulseAnimation;

  bool get _isToday {
    if (widget.record == null) return false;
    final day = widget.record!.day;
    final today = DateTime.now();
    return day.year == today.year &&
        day.month == today.month &&
        day.day == today.day;
  }

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutCubic,
      ),
    );

    // Stagger delay: index * 15ms, capped at 1500ms
    final delay = Duration(
      milliseconds: math.min(widget.index * 15, 1500),
    );
    Future.delayed(delay, () {
      if (mounted) _controller.forward();
    });

    // Pulsing glow for today's cell
    if (_isToday) {
      _pulseController = AnimationController(
        duration: const Duration(milliseconds: 1200),
        vsync: this,
      );
      _pulseAnimation = Tween<double>(begin: 0.4, end: 1.0).animate(
        CurvedAnimation(
          parent: _pulseController!,
          curve: Curves.easeInOut,
        ),
      );
      _pulseController!.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _pulseController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.record == null) {
      return const SizedBox.shrink();
    }

    final record = widget.record!;
    final isToday = _isToday;

    final baseColor = switch (record.status) {
      StreakDayStatus.active => DS.semanticSuccess,
      StreakDayStatus.frozen => DS.semanticWarning,
      StreakDayStatus.missed => DS.neutral300,
    };

    final textColor = record.status == StreakDayStatus.missed
        ? DS.textSecondary
        : DS.textOnPrimary;

    // Overlay icon for active / frozen days
    final overlayIcon = switch (record.status) {
      StreakDayStatus.active => Icons.local_fire_department,
      StreakDayStatus.frozen => Icons.ac_unit,
      StreakDayStatus.missed => null,
    };

    return FadeTransition(
      opacity: _fadeAnimation,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: _buildCellContent(
          record: record,
          isToday: isToday,
          baseColor: baseColor,
          textColor: textColor,
          overlayIcon: overlayIcon,
        ),
      ),
    );
  }

  Widget _buildCellContent({
    required StreakDayRecord record,
    required bool isToday,
    required Color baseColor,
    required Color textColor,
    required IconData? overlayIcon,
  }) {
    // Active days get a slight gradient background (darker at bottom)
    final decoration = record.status == StreakDayStatus.active
        ? BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                baseColor,
                Color.lerp(baseColor, Colors.black, 0.15)!,
              ],
            ),
            borderRadius: DS.borderRadius8,
          )
        : BoxDecoration(
            color: baseColor,
            borderRadius: DS.borderRadius8,
          );

    Widget cell = Container(
      decoration: decoration,
      child: Stack(
        children: [
          // Day number
          Center(
            child: Text(
              '${record.day.day}',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightSemibold,
                color: textColor,
              ),
            ),
          ),
          // Overlay icon (fire or snowflake) in top-right corner
          if (overlayIcon != null)
            Positioned(
              top: 1,
              right: 1,
              child: Icon(
                overlayIcon,
                size: 10,
                color: textColor.withValues(alpha: 0.7),
              ),
            ),
        ],
      ),
    );

    // Today: pulsing border glow
    if (isToday && _pulseAnimation != null) {
      cell = AnimatedBuilder(
        animation: _pulseAnimation!,
        builder: (context, child) => Container(
          decoration: BoxDecoration(
            borderRadius: DS.borderRadius8,
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary
                    .withValues(alpha: 0.5 * _pulseAnimation!.value),
                blurRadius: 6 * _pulseAnimation!.value,
                spreadRadius: 1 * _pulseAnimation!.value,
              ),
            ],
          ),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: DS.borderRadius8,
              border: Border.all(
                color: DS.brandPrimary
                    .withValues(alpha: 0.6 + 0.4 * _pulseAnimation!.value),
                width: 2,
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(6), // inside the border
              child: child,
            ),
          ),
        ),
        child: cell,
      );
    }

    return cell;
  }
}

// ---------------------------------------------------------------------------
// _RiskHintCard: Slide in from right with bounce + haptic on critical
// ---------------------------------------------------------------------------

class _RiskHintCard extends StatefulWidget {
  const _RiskHintCard({
    required this.isCritical,
    required this.background,
    required this.borderColor,
    required this.text,
  });

  final bool isCritical;
  final Color background;
  final Color borderColor;
  final String text;

  @override
  State<_RiskHintCard> createState() => _RiskHintCardState();
}

class _RiskHintCardState extends State<_RiskHintCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<Offset> _slideAnimation;
  late final Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0.3, 0),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.elasticOut,
      ),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0, 0.5, curve: Curves.easeOut),
    );

    _controller.forward();

    if (widget.isCritical) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.warning));
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: widget.background,
            borderRadius: DS.borderRadius16,
            border: Border.all(color: widget.borderColor),
          ),
          child: Row(
            children: [
              Icon(
                widget.isCritical
                    ? Icons.warning_amber_rounded
                    : Icons.info_outline,
                color: widget.borderColor,
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  widget.text,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textPrimary,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
}

class _StreakInsightBanner extends StatelessWidget {
  const _StreakInsightBanner({
    required this.stats,
    required this.totalCheckins,
  });

  final StreakStats stats;
  final int totalCheckins;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.06),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.15)),
      ),
      child: Row(
        children: [
          Icon(Icons.lightbulb_outline, size: 18, color: DS.brandPrimary),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              context.l10n.streakInsightBanner(totalCheckins, stats.currentStreak),
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textPrimary,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
