import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class GraphiteScaffold extends StatelessWidget {
  const GraphiteScaffold({
    required this.child,
    super.key,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
    this.extendBodyBehindAppBar = false,
    this.safeArea = true,
    this.padding,
    this.backgroundGradient,
    this.role,
    this.motionToken = SparkleMotionToken.standard,
  });

  final Widget child;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;
  final bool extendBodyBehindAppBar;
  final bool safeArea;
  final EdgeInsetsGeometry? padding;
  final Gradient? backgroundGradient;
  final SparklePageRole? role;
  final SparkleMotionToken motionToken;

  @override
  Widget build(BuildContext context) {
    final duration = DS.motionDuration(
      motionToken,
      reduceMotion: context.reduceMotion,
    );
    final curve = DS.motionCurve(motionToken);
    final body = AnimatedContainer(
      duration: duration,
      curve: curve,
      decoration: BoxDecoration(
        gradient: backgroundGradient ??
            (role != null
                ? DS.pageGradientForRole(role!)
                : DS.deepSpaceGradient),
      ),
      child: safeArea
          ? SafeArea(
              top: !extendBodyBehindAppBar,
              bottom: false,
              child: Padding(
                padding: padding ?? EdgeInsets.zero,
                child: child,
              ),
            )
          : Padding(
              padding: padding ?? EdgeInsets.zero,
              child: child,
            ),
    );

    return Scaffold(
      backgroundColor:
          role != null ? DS.pageScaffoldBackground(role!) : DS.surfaceCanvas,
      appBar: appBar,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: bottomNavigationBar,
      body: _GraphiteEntranceMotion(
        motionToken: motionToken,
        child: body,
      ),
    );
  }
}

class GraphitePageHeader extends StatelessWidget
    implements PreferredSizeWidget {
  const GraphitePageHeader({
    required this.title,
    super.key,
    this.subtitle,
    this.leading,
    this.actions,
    this.bottom,
    this.centerTitle = false,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final List<Widget>? actions;
  final PreferredSizeWidget? bottom;
  final bool centerTitle;

  @override
  Size get preferredSize => Size.fromHeight(
        subtitle == null ? 64 : 86 + (bottom?.preferredSize.height ?? 0),
      );

  @override
  Widget build(BuildContext context) {
    final titleBlock = Column(
      crossAxisAlignment:
          centerTitle ? CrossAxisAlignment.center : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(title, style: DS.headingLarge.copyWith(color: DS.textPrimary)),
        if (subtitle != null) ...[
          const SizedBox(height: 4),
          Text(
            subtitle!,
            style: DS.bodyMedium.copyWith(color: DS.textSecondary),
          ),
        ],
      ],
    );

    return AppBar(
      leading: leading,
      titleSpacing: 20,
      centerTitle: centerTitle,
      title: titleBlock,
      actions: actions,
      bottom: bottom,
    );
  }
}

class GraphiteCardSurface extends StatelessWidget {
  const GraphiteCardSurface({
    required this.child,
    super.key,
    this.padding = const EdgeInsets.all(20),
    this.margin,
    this.onTap,
    this.borderColor,
    this.backgroundColor,
    this.surfaceRole,
    this.motionToken = SparkleMotionToken.standard,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final Color? borderColor;
  final Color? backgroundColor;
  final SparkleSurfaceRole? surfaceRole;
  final SparkleMotionToken motionToken;

  @override
  Widget build(BuildContext context) {
    final duration = DS.motionDuration(
      motionToken,
      reduceMotion: context.reduceMotion,
    );
    final content = AnimatedContainer(
      duration: duration,
      curve: DS.motionCurve(motionToken),
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: backgroundColor ??
            (surfaceRole != null
                ? DS.surfaceRoleColor(surfaceRole!)
                : DS.surfaceOverlay),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: borderColor ?? DS.borderSubtle,
        ),
        boxShadow: DS.shadowMd,
      ),
      child: child,
    );

    if (onTap == null) return content;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: content,
    );
  }
}

class GraphiteModalSurface extends StatelessWidget {
  const GraphiteModalSurface({
    required this.child,
    super.key,
    this.title,
    this.padding = const EdgeInsets.fromLTRB(20, 16, 20, 20),
    this.surfaceRole = SparkleSurfaceRole.modal,
    this.borderRadius = const BorderRadius.vertical(top: Radius.circular(28)),
    this.showHandle = true,
    this.expandChild = false,
  });

  final Widget child;
  final String? title;
  final EdgeInsetsGeometry padding;
  final SparkleSurfaceRole surfaceRole;
  final BorderRadiusGeometry borderRadius;
  final bool showHandle;
  final bool expandChild;

  @override
  Widget build(BuildContext context) {
    final duration = DS.motionDuration(
      SparkleMotionToken.standard,
      reduceMotion: context.reduceMotion,
    );
    return _GraphiteEntranceMotion(
      motionToken: SparkleMotionToken.scene,
      offsetY: 0.028,
      beginScale: 0.985,
      child: SafeArea(
        top: false,
        child: ClipRRect(
          borderRadius: borderRadius,
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
            child: AnimatedContainer(
              duration: duration,
              curve: DS.motionCurve(SparkleMotionToken.standard),
              padding: padding,
              decoration: BoxDecoration(
                color: DS.surfaceRoleColor(surfaceRole),
                borderRadius: borderRadius,
                border: Border.all(
                  color: DS.borderSubtle,
                ),
              ),
              child: Column(
                mainAxisSize: expandChild ? MainAxisSize.max : MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (showHandle)
                    Center(
                      child: Container(
                        width: 36,
                        height: 4,
                        decoration: BoxDecoration(
                          color: DS.borderStrong,
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                    ),
                  if (title != null) ...[
                    if (showHandle) const SizedBox(height: 16),
                    Text(
                      title!,
                      style: DS.titleLarge.copyWith(color: DS.textPrimary),
                    ),
                    const SizedBox(height: 12),
                  ] else if (showHandle)
                    const SizedBox(height: 16),
                  if (expandChild) Expanded(child: child) else child,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class GraphiteSectionTitle extends StatelessWidget {
  const GraphiteSectionTitle({
    required this.title,
    super.key,
    this.trailing,
  });

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Text(
            title,
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          if (trailing != null) trailing!,
        ],
      );
}

class SparklePageScaffold extends StatelessWidget {
  const SparklePageScaffold({
    required this.child,
    required this.role,
    super.key,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
    this.extendBodyBehindAppBar = false,
    this.safeArea = true,
    this.padding,
    this.backgroundGradient,
    this.motionToken = SparkleMotionToken.standard,
  });

  final Widget child;
  final SparklePageRole role;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;
  final bool extendBodyBehindAppBar;
  final bool safeArea;
  final EdgeInsetsGeometry? padding;
  final Gradient? backgroundGradient;
  final SparkleMotionToken motionToken;

  @override
  Widget build(BuildContext context) => GraphiteScaffold(
        role: role,
        appBar: appBar,
        floatingActionButton: floatingActionButton,
        bottomNavigationBar: bottomNavigationBar,
        extendBodyBehindAppBar: extendBodyBehindAppBar,
        safeArea: safeArea,
        padding: padding,
        backgroundGradient: backgroundGradient,
        motionToken: motionToken,
        child: child,
      );
}

class _GraphiteEntranceMotion extends StatelessWidget {
  const _GraphiteEntranceMotion({
    required this.child,
    required this.motionToken,
    this.offsetY = 0.02,
    this.beginScale = 0.992,
  });

  final Widget child;
  final SparkleMotionToken motionToken;
  final double offsetY;
  final double beginScale;

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) return child;

    final duration = DS.motionDuration(motionToken);
    final curve = DS.motionCurve(motionToken);

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: duration,
      curve: curve,
      child: child,
      builder: (context, value, child) {
        final eased = Curves.easeOutCubic.transform(value);
        final translateY = (1 - eased) * 18;
        final scale = beginScale + ((1 - beginScale) * eased);
        final opacity = (value * 1.15).clamp(0, 1);

        return Transform.translate(
          offset: Offset(0, translateY + ((1 - eased) * offsetY * 60)),
          child: Transform.scale(
            scale: scale,
            child: Opacity(
              opacity: opacity.toDouble(),
              child: child,
            ),
          ),
        );
      },
    );
  }
}
