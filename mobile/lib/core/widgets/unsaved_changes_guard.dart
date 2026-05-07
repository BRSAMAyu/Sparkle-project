import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Wraps a form screen with [PopScope] to guard against accidental back
/// navigation when there are unsaved changes.
///
/// Usage:
/// ```dart
/// UnsavedChangesGuard(
///   isDirty: _hasTextChanges,
///   child: Scaffold(...),
/// )
/// ```
class UnsavedChangesGuard extends StatelessWidget {
  const UnsavedChangesGuard({
    required this.isDirty,
    required this.child,
    super.key,
    this.discardTitle,
    this.discardMessage,
    this.keepEditingLabel,
    this.discardLabel,
  });

  /// Whether the form has unsaved changes.
  final bool isDirty;

  /// The wrapped form content.
  final Widget child;

  /// Dialog title when confirming discard. Defaults to a generic message.
  final String? discardTitle;

  /// Dialog body when confirming discard.
  final String? discardMessage;

  /// Label for the "keep editing" button.
  final String? keepEditingLabel;

  /// Label for the "discard" button.
  final String? discardLabel;

  Future<bool> _confirmDiscard(BuildContext context) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: DS.surfacePrimary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: DS.border.withValues(alpha: 0.5)),
        ),
        title: Text(discardTitle ?? 'Discard changes?'),
        content: Text(discardMessage ?? 'You have unsaved changes. Discard?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(keepEditingLabel ?? 'Keep Editing'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(discardLabel ?? 'Discard'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  @override
  Widget build(BuildContext context) => PopScope(
        canPop: !isDirty,
        onPopInvokedWithResult: (didPop, result) async {
          if (didPop) return;
          final shouldPop = await _confirmDiscard(context);
          if (shouldPop && context.mounted) {
            Navigator.of(context).pop();
          }
        },
        child: child,
      );
}
