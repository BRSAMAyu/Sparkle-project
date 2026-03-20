import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';

Color _mix(Color a, Color b, double t) => Color.lerp(a, b, t) ?? a;

Color _shiftLightness(Color color, double amount) {
  final hsl = HSLColor.fromColor(color);
  final lightness = (hsl.lightness + amount).clamp(0.0, 1.0);
  return hsl.withLightness(lightness).toColor();
}

class ToolShell extends StatefulWidget {
  const ToolShell({
    required this.surface,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accentColor,
    required this.body,
    super.key,
    this.headerAction,
    this.heroChips = const <Widget>[],
    this.fillHeight = false,
    this.footer,
    this.maxWidth = 980,
    this.compactHeader = false,
  });

  final ToolSurface surface;
  final IconData icon;
  final String title;
  final String subtitle;
  final Color accentColor;
  final Widget body;
  final Widget? headerAction;
  final List<Widget> heroChips;
  final bool fillHeight;
  final Widget? footer;
  final double maxWidth;
  final bool compactHeader;

  @override
  State<ToolShell> createState() => _ToolShellState();
}

class _ToolShellState extends State<ToolShell> {
  static const _headerPrefPrefix = 'tool_shell.header_hidden.';

  bool _headerCollapsed = false;

  bool get _isSheet => widget.surface == ToolSurface.sheet;
  bool get _effectiveCompactHeader => widget.compactHeader || _headerCollapsed;

  @override
  void initState() {
    super.initState();
    unawaited(_loadHeaderPreference());
  }

  Future<void> _loadHeaderPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final nextValue =
        prefs.getBool('$_headerPrefPrefix${widget.title}') ?? false;
    if (!mounted) {
      return;
    }
    setState(() {
      _headerCollapsed = nextValue;
    });
  }

  Future<void> _toggleHeaderCollapsed() async {
    final nextValue = !_headerCollapsed;
    setState(() {
      _headerCollapsed = nextValue;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('$_headerPrefPrefix${widget.title}', nextValue);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final panelColor = _mix(
      DS.surfaceOverlay,
      widget.accentColor,
      isDark ? 0.08 : 0.03,
    );
    final heroStart = _mix(
      DS.surfacePrimaryElevated,
      widget.accentColor,
      isDark ? 0.24 : 0.12,
    );
    final heroEnd = _mix(
      DS.surfacePrimary,
      widget.accentColor,
      isDark ? 0.06 : 0.03,
    );
    final heroIconColor =
        _shiftLightness(widget.accentColor, isDark ? 0.12 : -0.04);
    final iconSurface = _mix(
      DS.surfacePrimary,
      widget.accentColor,
      isDark ? 0.20 : 0.10,
    );
    final borderColor = _mix(
      DS.borderStrong,
      widget.accentColor,
      isDark ? 0.18 : 0.10,
    );

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: widget.fillHeight ? MainAxisSize.max : MainAxisSize.min,
      children: [
        if (_isSheet)
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing16),
            child: Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.borderStrong,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
          ),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [heroStart, heroEnd],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: borderColor),
            boxShadow: [
              BoxShadow(
                color:
                    widget.accentColor.withValues(alpha: isDark ? 0.12 : 0.08),
                blurRadius: isDark ? 28 : 24,
                offset: const Offset(0, 16),
              ),
              BoxShadow(
                color: DS.textPrimary.withValues(alpha: isDark ? 0.08 : 0.04),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: EdgeInsets.all(
              _effectiveCompactHeader ? DS.spacing16 : DS.spacing24,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: _effectiveCompactHeader ? 40 : 52,
                      height: _effectiveCompactHeader ? 40 : 52,
                      decoration: BoxDecoration(
                        color: iconSurface,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: widget.accentColor.withValues(
                            alpha: isDark ? 0.34 : 0.18,
                          ),
                        ),
                      ),
                      child: Icon(
                        widget.icon,
                        color: heroIconColor,
                        size: _effectiveCompactHeader ? 20 : 26,
                      ),
                    ),
                    SizedBox(
                      width:
                          _effectiveCompactHeader ? DS.spacing10 : DS.spacing16,
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.title,
                            maxLines: _effectiveCompactHeader ? 1 : 2,
                            overflow: TextOverflow.ellipsis,
                            style: (_effectiveCompactHeader
                                    ? Theme.of(context).textTheme.titleLarge
                                    : Theme.of(context).textTheme.headlineSmall)
                                ?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                              height: 1.05,
                            ),
                          ),
                          if (!_headerCollapsed) ...[
                            SizedBox(
                              height: _effectiveCompactHeader
                                  ? DS.spacing6
                                  : DS.spacing8,
                            ),
                            Text(
                              widget.subtitle,
                              maxLines: _effectiveCompactHeader ? 2 : 3,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: _effectiveCompactHeader ? 1.4 : 1.5,
                                  ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (widget.headerAction != null) ...[
                      const SizedBox(width: DS.spacing12),
                      widget.headerAction!,
                    ],
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 32,
                      onPressed: _toggleHeaderCollapsed,
                      icon: Icon(
                        _headerCollapsed
                            ? Icons.visibility_off_rounded
                            : Icons.visibility_rounded,
                        size: 18,
                      ),
                    ),
                  ],
                ),
                if (!_headerCollapsed && widget.heroChips.isNotEmpty) ...[
                  SizedBox(
                    height:
                        _effectiveCompactHeader ? DS.spacing10 : DS.spacing16,
                  ),
                  Wrap(
                    spacing:
                        _effectiveCompactHeader ? DS.spacing8 : DS.spacing10,
                    runSpacing:
                        _effectiveCompactHeader ? DS.spacing8 : DS.spacing10,
                    children: widget.heroChips,
                  ),
                ],
              ],
            ),
          ),
        ),
        SizedBox(height: _effectiveCompactHeader ? DS.spacing12 : DS.spacing20),
        if (widget.fillHeight)
          Expanded(child: widget.body)
        else if (_isSheet)
          Flexible(child: SingleChildScrollView(child: widget.body))
        else
          widget.body,
        if (widget.footer != null) ...[
          SizedBox(
            height: _effectiveCompactHeader ? DS.spacing12 : DS.spacing20,
          ),
          widget.footer!,
        ],
      ],
    );

    final contentBody = !widget.fillHeight && !_isSheet
        ? SingleChildScrollView(
            padding: EdgeInsets.zero,
            child: content,
          )
        : content;

    final root = DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            panelColor,
            _mix(panelColor, DS.surfacePrimary, isDark ? 0.18 : 0.3),
          ],
        ),
        borderRadius: BorderRadius.circular(_isSheet ? 32 : 32),
        border: Border.all(color: borderColor.withValues(alpha: 0.82)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.24 : 0.06),
            blurRadius: isDark ? 40 : 28,
            offset: const Offset(0, 18),
          ),
          BoxShadow(
            color: DS.textPrimary.withValues(alpha: isDark ? 0.05 : 0.03),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          DS.spacing20,
          _isSheet ? DS.spacing16 : DS.spacing20,
          DS.spacing20,
          DS.spacing20,
        ),
        child: contentBody,
      ),
    );

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: widget.maxWidth,
          maxHeight: _isSheet
              ? math.min(MediaQuery.sizeOf(context).height * 0.88, 940)
              : double.infinity,
        ),
        child: root,
      ),
    );
  }
}

class ToolSectionCard extends StatelessWidget {
  const ToolSectionCard({
    required this.child,
    super.key,
    this.title,
    this.subtitle,
    this.trailing,
    this.accentColor,
    this.padding = const EdgeInsets.all(DS.spacing18),
    this.fillHeight = false,
  });

  final Widget child;
  final String? title;
  final String? subtitle;
  final Widget? trailing;
  final Color? accentColor;
  final EdgeInsetsGeometry padding;
  final bool fillHeight;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final accent = accentColor ?? DS.brandPrimary;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: _mix(
          DS.surfacePrimary,
          accent,
          isDark ? 0.08 : 0.03,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: _mix(
            DS.borderSubtle,
            accent,
            isDark ? 0.16 : 0.08,
          ),
        ),
      ),
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: fillHeight ? MainAxisSize.max : MainAxisSize.min,
          children: [
            if (title != null || trailing != null) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (title != null)
                          Text(
                            title!,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                        if (subtitle != null) ...[
                          const SizedBox(height: DS.spacing4),
                          Text(
                            subtitle!,
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.4,
                                    ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (trailing != null) ...[
                    const SizedBox(width: DS.spacing12),
                    trailing!,
                  ],
                ],
              ),
              const SizedBox(height: DS.spacing16),
            ],
            if (fillHeight) Expanded(child: child) else child,
          ],
        ),
      ),
    );
  }
}

class ToolMetricCard extends StatelessWidget {
  const ToolMetricCard({
    required this.label,
    required this.value,
    required this.accentColor,
    super.key,
    this.caption,
    this.icon,
  });

  final String label;
  final String value;
  final String? caption;
  final IconData? icon;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final background = _mix(
      DS.surfacePrimary,
      accentColor,
      isDark ? 0.14 : 0.08,
    );
    final border = _mix(
      accentColor,
      DS.borderStrong,
      isDark ? 0.40 : 0.55,
    );
    return DecoratedBox(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: border.withValues(alpha: 0.72)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 16, color: accentColor),
                  const SizedBox(width: DS.spacing6),
                ],
                Text(
                  label,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: DS.textSecondary,
                        fontWeight: DS.fontWeightMedium,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    height: 1.0,
                  ),
            ),
            if (caption != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                caption!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class ToolChoiceChip extends StatelessWidget {
  const ToolChoiceChip({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.accentColor,
    super.key,
    this.icon,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color accentColor;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final background = selected
        ? _mix(
            DS.surfacePrimary,
            accentColor,
            isDark ? 0.26 : 0.14,
          )
        : DS.surfacePrimary.withValues(alpha: isDark ? 0.24 : 0.88);
    final border = selected
        ? accentColor.withValues(alpha: isDark ? 0.52 : 0.30)
        : DS.borderSubtle;
    final foreground = selected
        ? DS.textPrimary
        : _mix(DS.textSecondary, accentColor, isDark ? 0.08 : 0.10);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: AnimatedContainer(
        duration: DS.durationFast,
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: border),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: accentColor.withValues(alpha: isDark ? 0.16 : 0.10),
                    blurRadius: 18,
                    offset: const Offset(0, 8),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 16, color: foreground),
              const SizedBox(width: DS.spacing8),
            ],
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: foreground,
                    fontWeight:
                        selected ? DS.fontWeightBold : DS.fontWeightMedium,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class ToolHeroChip extends StatelessWidget {
  const ToolHeroChip({
    required this.label,
    required this.accentColor,
    super.key,
    this.icon,
  });

  final String label;
  final Color accentColor;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: _mix(
          DS.surfacePrimary,
          accentColor,
          isDark ? 0.18 : 0.09,
        ),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: accentColor.withValues(alpha: isDark ? 0.34 : 0.22),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 16, color: accentColor),
              const SizedBox(width: DS.spacing6),
            ],
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemiBold,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class ToolMetricRow extends StatelessWidget {
  const ToolMetricRow({
    required this.children,
    super.key,
  });

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final useWrap = screenWidth < 360 || children.length > 3;

    if (useWrap) {
      return Wrap(
        spacing: DS.spacing12,
        runSpacing: DS.spacing12,
        children: children,
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) const SizedBox(width: DS.spacing12),
          Expanded(child: children[i]),
        ],
      ],
    );
  }
}

class ToolEmptyState extends StatelessWidget {
  const ToolEmptyState({
    required this.icon,
    required this.title,
    required this.description,
    super.key,
    this.accentColor,
    this.action,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color? accentColor;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final accent = accentColor ?? DS.brandPrimary;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing20,
          vertical: DS.spacing24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: _mix(
                  DS.surfacePrimary,
                  accent,
                  isDark ? 0.20 : 0.08,
                ),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: accent.withValues(alpha: isDark ? 0.36 : 0.18),
                ),
              ),
              child: Icon(icon, size: 34, color: accent),
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              description,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.5,
                  ),
            ),
            if (action != null) ...[
              const SizedBox(height: DS.spacing16),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
