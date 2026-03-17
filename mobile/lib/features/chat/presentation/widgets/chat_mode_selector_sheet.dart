import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';
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
    final catalog = ref.watch(multiAgentCatalogProvider);
    final expertModes = catalog.when(
      data: (value) => value.experts
          .where((expert) => expert.enabled)
          .map((expert) => ChatModeExpert(
                expertId: expert.id,
                displayName: expert.displayName,
              ),)
          .toList(),
      loading: () => <ChatMode>[],
      error: (_, __) => <ChatMode>[],
    );

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
                    context.l10n.chatModeSelectorTitle,
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
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Mode options
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(context).size.height * 0.7,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ...ChatMode.values.map(
                      (mode) => _ModeListTile(
                        mode: mode,
                        isSelected: currentMode == mode,
                        isDark: isDark,
                      ),
                    ),
                    if (expertModes.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing8),
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing20,
                        ),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            context.l10n.chatModeExpertDirect,
                            style: TextStyle(
                              fontSize: DS.fontSizeXs,
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.neutral500,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      ...expertModes.map(
                        (mode) => _ModeListTile(
                          mode: mode,
                          isSelected: currentMode == mode,
                          isDark: isDark,
                        ),
                      ),
                    ],
                    const SizedBox(height: DS.spacing8),
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing20,
                      ),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          context.l10n.chatModeCustomTeamLabel,
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.neutral500,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    _TeamEntryTile(isDark: isDark),
                    const SizedBox(height: DS.spacing16),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Sentinel returned when user wants to open the team builder instead of
/// selecting a predefined mode.
const openTeamBuilderSentinel = '_open_team_builder_';

class _TeamEntryTile extends StatelessWidget {
  const _TeamEntryTile({required this.isDark});

  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final color = context.colorExtensions.chatModeIndigo;
    return InkWell(
      onTap: () {
        unawaited(HapticFeedback.lightImpact());
        // Pop with sentinel string — the caller (pill) handles opening
        // the team sheet to avoid using a dead context.
        Navigator.pop(context, openTeamBuilderSentinel);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing20,
          vertical: DS.spacing16,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.15),
                borderRadius: DS.borderRadius12,
              ),
              child: Icon(
                Icons.groups_rounded,
                color: color,
                size: DS.iconSizeBase,
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.chatModeCustomTeamTitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightMedium,
                      color: isDark ? DS.textPrimary : DS.neutral900,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    context.l10n.chatModeCustomTeamSubtitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.neutral500,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: DS.neutral400,
              size: DS.iconSizeBase,
            ),
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
          unawaited(HapticFeedback.lightImpact());
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
