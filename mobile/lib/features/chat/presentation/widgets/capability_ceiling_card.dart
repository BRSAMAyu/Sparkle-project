import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';

/// A card shown when AI hits its capability ceiling.
///
/// Offers contextual alternatives:
/// - Switch to a more capable mode (e.g., deep_analysis, expert_auto)
/// - Continue in current mode with adjusted expectations
/// - Dismiss
///
/// This widget does NOT create backend seams — it simply presents
/// mode-switch alternatives that already exist in the system.
class CapabilityCeilingCard extends ConsumerStatefulWidget {
  const CapabilityCeilingCard({
    required this.ceilingData,
    super.key,
  });

  /// Data payload from the backend or local detection.
  /// Expected keys:
  /// - `reason`: String — what the AI couldn't do
  /// - `suggested_modes`: List<String> — API values of suggested modes
  /// - `fallback_message`: String — message when no alternatives available
  final Map<String, dynamic> ceilingData;

  @override
  ConsumerState<CapabilityCeilingCard> createState() =>
      _CapabilityCeilingCardState();
}

class _CapabilityCeilingCardState
    extends ConsumerState<CapabilityCeilingCard> {
  bool _dismissed = false;

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();

    final l10n = I18nService.instance.l10n;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final reason =
        widget.ceilingData['reason']?.toString() ?? l10n.capabilityCeilingDefault;
    final suggestedRaw =
        widget.ceilingData['suggested_modes'] as List<dynamic>? ?? [];
    final suggestedModes = suggestedRaw
        .map((e) => ChatMode.fromApiValue(e.toString()))
        .where((m) => m.isMultiAgent)
        .toList();

    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: isDark
            ? DS.warningAccent.withValues(alpha: 0.08)
            : DS.warningAccent.withValues(alpha: 0.06),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.warningAccent.withValues(alpha: 0.25),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.info_outline_rounded,
                size: DS.iconSizeSm,
                color: DS.warningAccent,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                l10n.capabilityCeilingTitle,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.warningAccent,
                ),
              ),
              const Spacer(),
              _DismissButton(
                onTap: () => setState(() => _dismissed = true),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),

          // Reason
          Text(
            reason,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: isDark ? DS.textSecondary : DS.neutral600,
            ),
          ),

          // Suggested alternatives
          if (suggestedModes.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.capabilityCeilingAlternatives,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: isDark ? DS.textSecondary : DS.neutral600,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: suggestedModes.map((mode) => _ModeSuggestionChip(
                  mode: mode,
                  onTap: () {
                    ref
                        .read(chatModeNotifierProvider.notifier)
                        .setModeWithFeedback(mode, context);
                    ref.read(lastMultiAgentModeProvider.notifier).state = mode;
                    setState(() => _dismissed = true);
                  },
                ),).toList(),
            ),
          ],

          // Continue anyway
          const SizedBox(height: DS.spacing8),
          _ContinueButton(
            onTap: () => setState(() => _dismissed = true),
          ),
        ],
      ),
    );
  }
}

class _ModeSuggestionChip extends StatelessWidget {
  const _ModeSuggestionChip({
    required this.mode,
    required this.onTap,
  });

  final ChatMode mode;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        onPressed: onTap,
        avatar: Icon(mode.icon, size: DS.iconSizeXs, color: mode.color),
        label: Text(
          mode.label,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: mode.color,
          ),
        ),
        backgroundColor: mode.color.withValues(alpha: 0.08),
        side: BorderSide(color: mode.color.withValues(alpha: 0.3)),
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius8),
      );
}

class _DismissButton extends StatelessWidget {
  const _DismissButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Icon(
          Icons.close_rounded,
          size: DS.iconSizeXs,
          color: DS.textTertiary,
        ),
      );
}

class _ContinueButton extends StatelessWidget {
  const _ContinueButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = I18nService.instance.l10n;
    return GestureDetector(
      onTap: onTap,
      child: Text(
        l10n.capabilityCeilingContinue,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          color: DS.textTertiary,
          decoration: TextDecoration.underline,
        ),
      ),
    );
  }
}
