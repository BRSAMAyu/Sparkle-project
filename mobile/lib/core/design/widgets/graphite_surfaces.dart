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
  });

  final Widget child;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;
  final bool extendBodyBehindAppBar;
  final bool safeArea;
  final EdgeInsetsGeometry? padding;
  final Gradient? backgroundGradient;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      decoration: BoxDecoration(
        gradient: backgroundGradient ?? DS.deepSpaceGradient,
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
      backgroundColor: DS.surfaceCanvas,
      appBar: appBar,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: bottomNavigationBar,
      body: body,
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
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    final content = Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: DS.surfaceOverlay,
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
  });

  final Widget child;
  final String? title;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              color: DS.surfaceOverlay,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(28),
              ),
              border: Border(
                top: BorderSide(color: DS.borderSubtle),
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
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
                  const SizedBox(height: 16),
                  Text(
                    title!,
                    style: DS.titleLarge.copyWith(color: DS.textPrimary),
                  ),
                ],
                const SizedBox(height: 16),
                child,
              ],
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
  Widget build(BuildContext context) {
    return Row(
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
}
