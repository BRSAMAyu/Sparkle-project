import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/user/data/models/redeem_code_result.dart';

/// D-REDEEM · 兑换码对话框（设置页入口 → 输入 → 核销 → toast 反馈）。
///
/// 网络面通过 [onRedeem] 注入（widget 测试可注入 fake，不起网络）；
/// 设计规范：只消费 core/design 令牌与组件（DS.* / SparkleButton），无裸组件新增。
class RedeemCodeDialog extends StatefulWidget {
  const RedeemCodeDialog({
    required this.onRedeem,
    super.key,
  });

  final Future<RedeemCodeResult> Function(String code) onRedeem;

  /// 设置页入口的统一打开方式。
  static Future<void> show(
    BuildContext context, {
    required Future<RedeemCodeResult> Function(String code) onRedeem,
  }) =>
      showDialog<void>(
        context: context,
        builder: (_) => RedeemCodeDialog(onRedeem: onRedeem),
      );

  @override
  State<RedeemCodeDialog> createState() => _RedeemCodeDialogState();
}

class _RedeemCodeDialogState extends State<RedeemCodeDialog> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _submitting = false;

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _controller.text.trim();
    if (code.isEmpty || _submitting) {
      return;
    }
    setState(() => _submitting = true);
    final l10n = context.l10n;
    try {
      final result = await widget.onRedeem(code);
      if (!mounted) {
        return;
      }
      if (result.isSuccess) {
        final dateLabel = result.expiresAt == null
            ? '--'
            : MaterialLocalizations.of(context).formatShortDate(result.expiresAt!);
        Navigator.of(context).pop();
        AppFeedback.success(
          context,
          l10n.redeemCodeSuccess(result.tier ?? 'pro', dateLabel),
        );
        return;
      }
      final message = switch (result.status) {
        RedeemCodeStatus.invalid => l10n.redeemCodeInvalid,
        RedeemCodeStatus.expired => l10n.redeemCodeExpired,
        RedeemCodeStatus.exhausted => l10n.redeemCodeExhausted,
        _ => l10n.redeemCodeError,
      };
      AppFeedback.error(context, message);
    } catch (_) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.redeemCodeError);
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      backgroundColor: DS.surfacePrimary,
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
      title: Row(
        children: [
          Icon(Icons.redeem_rounded, color: DS.brandPrimary, size: 22),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              l10n.redeemCodeTitle,
              style: DS.titleMedium.copyWith(color: DS.textPrimary),
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.redeemCodeSubtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          TextField(
            controller: _controller,
            focusNode: _focusNode,
            autofocus: true,
            enabled: !_submitting,
            textCapitalization: TextCapitalization.characters,
            style: DS.bodyMedium.copyWith(color: DS.textPrimary),
            decoration: InputDecoration(
              hintText: l10n.redeemCodeHint,
              hintStyle: DS.bodySmall.copyWith(color: DS.textTertiary),
              filled: true,
              fillColor: DS.surfaceSecondary,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              border: const OutlineInputBorder(borderRadius: DS.borderRadius12),
            ),
            onSubmitted: (_) => unawaited(_submit()),
          ),
        ],
      ),
      actions: [
        SparkleButton(
          label: MaterialLocalizations.of(context).cancelButtonLabel,
          variant: ButtonVariant.ghost,
          onPressed: _submitting
              ? null
              : () => Navigator.of(context).pop(),
        ),
        SparkleButton(
          label: l10n.redeemCodeAction,
          onPressed: () => unawaited(_submit()),
          loading: _submitting,
        ),
      ],
    );
  }
}
