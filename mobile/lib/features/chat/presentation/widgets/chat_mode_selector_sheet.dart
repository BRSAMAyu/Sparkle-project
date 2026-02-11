import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';

/// Chat Mode Selector Sheet
///
/// Bottom sheet for selecting a chat mode.
/// Shows all available modes with their icons, labels, and descriptions.
class ChatModeSelectorSheet extends ConsumerWidget {
  const ChatModeSelectorSheet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currentMode = ref.watch(chatModeProvider);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceSecondary : DS.surfacePrimaryElevated,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(DS.spacing24),
        ),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Container(
              width: DS.spacing40,
              height: DS.spacing4,
              margin: const EdgeInsets.symmetric(vertical: DS.spacing12),
              decoration: BoxDecoration(
                color: isDark ? DS.neutral700 : DS.neutral300,
                borderRadius: BorderRadius.circular(DS.spacing4 / 2),
              ),
            ),

            // Header
            Padding(
              padding: const EdgeInsets.only(
                left: DS.spacing20,
                right: DS.spacing20,
                bottom: DS.spacing12,
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.auto_awesome,
                    color: DS.primaryBase,
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    '选择AI协作模式',
                    style: TextStyle(
                      fontSize: DS.fontSizeLg,
                      fontWeight: DS.fontWeightBold,
                      color: isDark ? DS.textPrimary : DS.neutral900,
                    ),
                  ),
                  const Spacer(),
                  SparkleIconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                    variant: ButtonVariant.ghost,
                    size: DS.touchTargetMinSize,
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Mode options
            ...ChatMode.values.map(
              (mode) => _ModeListTile(
                mode: mode,
                isSelected: currentMode == mode,
                isDark: isDark,
              ),
            ),

            const SizedBox(height: DS.spacing16),
          ],
        ),
      ),
    );
  }
}

class _ModeListTile extends StatelessWidget {
  const _ModeListTile({
    required this.mode,
    required this.isSelected,
    required this.isDark,
  });

  final ChatMode mode;
  final bool isSelected;
  final bool isDark;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          Navigator.pop(context, mode);
        },
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing20,
            vertical: DS.spacing16,
          ),
          decoration: BoxDecoration(
            color: isSelected
                ? mode.color.withValues(alpha: 0.1)
                : DS.surfacePrimary.withValues(alpha: 0),
            border: Border(
              left: BorderSide(
                color: isSelected
                    ? mode.color
                    : DS.surfacePrimary.withValues(alpha: 0),
                width: 4,
              ),
            ),
          ),
          child: Row(
            children: [
              // Icon container
              Container(
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: mode.color.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius12,
                ),
                child: Icon(
                  mode.icon,
                  color: mode.color,
                  size: DS.iconSizeBase,
                ),
              ),
              const SizedBox(width: DS.spacing16),

              // Text content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      mode.label,
                      style: TextStyle(
                        fontSize: DS.fontSizeBase,
                        fontWeight: isSelected
                            ? DS.fontWeightSemibold
                            : DS.fontWeightMedium,
                        color: isDark ? DS.textPrimary : DS.neutral900,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      mode.description,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.neutral500,
                      ),
                    ),
                  ],
                ),
              ),

              // Selection indicator
              if (isSelected)
                Icon(
                  Icons.check_circle,
                  color: mode.color,
                  size: DS.iconSizeBase,
                ),
            ],
          ),
        ),
      );
}
