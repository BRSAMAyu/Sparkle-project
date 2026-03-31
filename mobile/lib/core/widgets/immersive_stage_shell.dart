import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum ImmersiveStageTrayMode { hidden, peek, expanded }

class ImmersiveStageShell extends StatelessWidget {
  const ImmersiveStageShell({
    required this.topBar,
    required this.body,
    super.key,
    this.drawer,
    this.isDrawerOpen = false,
    this.onDismissDrawer,
    this.bottomTray,
    this.bottomTrayMode = ImmersiveStageTrayMode.hidden,
    this.topBarHeight = 68,
    this.bodyPadding = const EdgeInsets.fromLTRB(16, 16, 16, 16),
    this.bottomTrayPeekHeight = 78,
    this.bottomTrayExpandedMaxHeightFactor = 0.46,
    this.overlay,
  });

  final Widget topBar;
  final Widget body;
  final Widget? drawer;
  final bool isDrawerOpen;
  final VoidCallback? onDismissDrawer;
  final Widget? bottomTray;
  final ImmersiveStageTrayMode bottomTrayMode;
  final double topBarHeight;
  final EdgeInsetsGeometry bodyPadding;
  final double bottomTrayPeekHeight;
  final double bottomTrayExpandedMaxHeightFactor;
  final Widget? overlay;

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final safeTop = mediaQuery.padding.top;
    final safeBottom = mediaQuery.padding.bottom;
    final keyboardInset = mediaQuery.viewInsets.bottom;

    return LayoutBuilder(
      builder: (context, constraints) {
        final trayHeight = _resolveTrayHeight(
          maxHeight: constraints.maxHeight,
          keyboardInset: keyboardInset,
        );
        final bodyBottomInset = trayHeight > 0 ? trayHeight + 14 : 0.0;
        final topOffset = safeTop + 8;

        return Stack(
          children: [
            Positioned.fill(
              top: topOffset + topBarHeight + 12,
              child: Padding(
                padding: bodyPadding.add(
                  EdgeInsets.only(
                    bottom: bodyBottomInset,
                  ),
                ),
                child: body,
              ),
            ),
            Positioned(
              top: topOffset,
              left: 16,
              right: 16,
              child: _ImmersiveChrome(
                height: topBarHeight,
                child: topBar,
              ),
            ),
            if (bottomTray != null && trayHeight > 0)
              Positioned(
                left: 16,
                right: 16,
                bottom: math.max(12, safeBottom + 12) + keyboardInset,
                child: SizedBox(
                  height: trayHeight,
                  child: _ImmersiveChrome(
                    child: bottomTray!,
                  ),
                ),
              ),
            if (overlay != null) Positioned.fill(child: overlay!),
            if (drawer != null && isDrawerOpen) ...[
              Positioned.fill(
                child: GestureDetector(
                  onTap: onDismissDrawer,
                  child: ColoredBox(
                    color: Colors.black.withValues(alpha: 0.18),
                  ),
                ),
              ),
              Positioned(
                top: topOffset + topBarHeight + 12,
                left: constraints.maxWidth < 720 ? 16 : null,
                right: 16,
                bottom: math.max(12, safeBottom + 12) + keyboardInset,
                width: constraints.maxWidth < 720
                    ? null
                    : math.min(420, constraints.maxWidth * 0.42),
                child: _ImmersiveChrome(
                  child: drawer!,
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  double _resolveTrayHeight({
    required double maxHeight,
    required double keyboardInset,
  }) {
    if (bottomTray == null || bottomTrayMode == ImmersiveStageTrayMode.hidden) {
      return 0;
    }
    if (bottomTrayMode == ImmersiveStageTrayMode.peek) {
      return bottomTrayPeekHeight;
    }
    return math.max(
      220,
      math.min(
        maxHeight * bottomTrayExpandedMaxHeightFactor,
        maxHeight - keyboardInset - 140,
      ),
    );
  }
}

class _ImmersiveChrome extends StatelessWidget {
  const _ImmersiveChrome({
    required this.child,
    this.height,
  });

  final Widget child;
  final double? height;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            scheme.surface.withValues(alpha: 0.96),
            scheme.surfaceContainerHigh.withValues(alpha: 0.94),
          ],
        ),
        border: Border.all(
          color: DS.borderSubtle.withValues(alpha: 0.78),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 28,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: Material(
          color: Colors.transparent,
          child: child,
        ),
      ),
    );
  }
}
