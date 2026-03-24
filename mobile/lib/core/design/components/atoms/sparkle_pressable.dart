import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Sparkle pressable surface that reads semantic tokens from ThemeExtension.
class SparklePressable extends StatefulWidget {
  const SparklePressable({
    required this.child,
    super.key,
    this.onTap,
    this.onLongPress,
    this.enabled = true,
    this.padding,
    this.margin,
    this.borderRadius,
    this.backgroundColor,
    this.border,
    this.semanticLabel,
    this.feedbackEvent = SensoryFeedbackEvent.tap,
  });

  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final bool enabled;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final BorderRadius? borderRadius;
  final Color? backgroundColor;
  final BorderSide? border;
  final String? semanticLabel;
  final SensoryFeedbackEvent feedbackEvent;

  @override
  State<SparklePressable> createState() => _SparklePressableState();
}

class _SparklePressableState extends State<SparklePressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final radius = widget.borderRadius ?? DS.borderRadius12;
    final background =
        widget.backgroundColor ?? DS.neutral0.withValues(alpha: 0);
    final side = widget.border ?? BorderSide.none;

    return Semantics(
      button: widget.onTap != null,
      enabled: widget.enabled && widget.onTap != null,
      label: widget.semanticLabel,
      child: Container(
        margin: widget.margin,
        child: AnimatedScale(
          scale: _pressed ? 0.97 : 1,
          duration: const Duration(milliseconds: 100),
          curve: Curves.easeOut,
          child: Material(
            color: background,
            shape: RoundedRectangleBorder(borderRadius: radius, side: side),
            child: InkWell(
              onTap: widget.enabled && widget.onTap != null
                  ? () {
                      unawaited(
                        SensoryFeedbackService.emit(widget.feedbackEvent),
                      );
                      widget.onTap?.call();
                    }
                  : null,
              onLongPress: widget.enabled && widget.onLongPress != null
                  ? () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        ),
                      );
                      widget.onLongPress?.call();
                    }
                  : null,
              onHighlightChanged: (highlighted) {
                if (_pressed == highlighted) return;
                setState(() => _pressed = highlighted);
              },
              borderRadius: radius,
              splashColor: DS.brandPrimary.withValues(alpha: 0.12),
              highlightColor: DS.brandPrimary.withValues(alpha: 0.06),
              child: Padding(
                padding: widget.padding ??
                    const EdgeInsets.symmetric(
                      horizontal: DS.spacing12,
                      vertical: DS.spacing8,
                    ),
                child: widget.child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
