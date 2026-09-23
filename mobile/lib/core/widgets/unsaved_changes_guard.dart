import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Wraps a form screen with [PopScope] to guard against accidental back
/// navigation when there are unsaved changes.
///
/// N27（A-SPEC5 v1.5）：一切含用户输入的屏必须挂本组件（isDirty 判定照
/// add_error_screen 的「控制器非空」模式），返回/切域时确认——「输入是劳动」。
///
/// Usage:
/// ```dart
/// UnsavedChangesGuard(
///   isDirty: _hasTextChanges,
///   child: Scaffold(...),
/// )
/// ```
///
/// Dialog copy defaults to the generic `formUnsaved*` l10n keys; pass
/// [discardTitle]/[discardMessage]/[keepEditingLabel]/[discardLabel] to
/// override with domain-specific wording.
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

  /// Dialog title when confirming discard. Defaults to a localized message.
  final String? discardTitle;

  /// Dialog body when confirming discard. Defaults to a localized message.
  final String? discardMessage;

  /// Label for the "keep editing" button. Defaults to a localized label.
  final String? keepEditingLabel;

  /// Label for the "discard" button. Defaults to a localized label.
  final String? discardLabel;

  Future<bool> _confirmDiscard(BuildContext context) async {
    final l10n = context.l10n;
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: DS.surfacePrimary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: DS.border.withValues(alpha: 0.5)),
        ),
        title: Text(discardTitle ?? l10n.formUnsavedTitle),
        content: Text(discardMessage ?? l10n.formUnsavedMessage),
        actions: [
          // CAPSULE-VARIANT 对话框按钮归一：继续编辑=取消类 → ghost 档；
          // 放弃=Destructive 文字动作（破坏性但不弹实心底）→ ghost + 语义色前景。
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: keepEditingLabel ?? l10n.formUnsavedKeepEditing,
          ),
          SparkleButton(
            onPressed: () => Navigator.of(context).pop(true),
            variant: ButtonVariant.ghost,
            foregroundColor: DS.error,
            label: discardLabel ?? l10n.formUnsavedDiscard,
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
