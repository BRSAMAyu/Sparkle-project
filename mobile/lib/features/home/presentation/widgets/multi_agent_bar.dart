import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';

/// Multi Agent Bar Widget
///
/// Horizontal scrolling bar displaying available AI collaboration modes.
/// Positioned on the dashboard between IntentPredictionBar and OmniBar.
///
/// Tapping a mode chip navigates to the chat screen with that mode activated.
class MultiAgentBar extends ConsumerWidget {
  const MultiAgentBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Multi-agent modes (excluding standard)
    final multiAgentModes =
        ChatMode.values.where((m) => m.isMultiAgent).toList();
    final catalog = ref.watch(multiAgentCatalogProvider);
    final expertModes = catalog.when(
      data: (value) => value.experts
          .where((expert) => expert.enabled)
          .take(6)
          .map((expert) => ChatModeExpert(
                expertId: expert.id,
                expertName: expert.displayName,
              ))
          .toList(),
      loading: () => <ChatMode>[],
      error: (_, __) => <ChatMode>[],
    );
    final entryModes = [...multiAgentModes, ...expertModes];

    return MaterialStyler(
      material: AppMaterials.neoGlass.copyWith(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.6),
        borderColor: DS.brandPrimary.withValues(alpha: 0.2),
      ),
      borderRadius: DS.borderRadiusFull,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing8,
      ),
      child: SizedBox(
        height: 44,
        child: Row(
          children: [
            // Title/Icon section
            Icon(
              Icons.auto_awesome,
              size: DS.iconSizeSm,
              color: DS.brandPrimaryConst,
            ),
            const SizedBox(width: DS.spacing8),
            Text(
              'AI协作模式',
              style: TextStyle(
                color: isDark ? DS.neutral100 : DS.neutral900,
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
            const SizedBox(width: DS.spacing12),

            // Mode chips
            Expanded(
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: entryModes.length,
                itemBuilder: (context, index) {
                  final mode = entryModes[index];
                  return _ModeChip(
                    mode: mode,
                    isDark: isDark,
                    onTap: () => _navigateToChatWithMode(context, ref, mode),
                  );
                },
                separatorBuilder: (_, __) => const SizedBox(width: DS.spacing8),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _navigateToChatWithMode(
    BuildContext context,
    WidgetRef ref,
    ChatMode mode,
  ) {
    unawaited(HapticFeedback.lightImpact());
    // Set the mode before navigating
    ref.read(chatModeNotifierProvider.notifier).setMode(mode);
    ref.read(lastMultiAgentModeProvider.notifier).state = mode;
    // Navigate to chat
    unawaited(context.push('/chat'));
  }
}

class _ModeChip extends StatefulWidget {
  const _ModeChip({
    required this.mode,
    required this.isDark,
    required this.onTap,
  });

  final ChatMode mode;
  final bool isDark;
  final VoidCallback onTap;

  @override
  State<_ModeChip> createState() => _ModeChipState();
}

class _ModeChipState extends State<_ModeChip> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final foregroundColor =
        widget.isDark ? const Color(0xFFF1E7DA) : DS.neutral900;
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) {
        setState(() => _isPressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedScale(
        scale: _isPressed ? 0.95 : 1.0,
        duration: AnimationSystem.quick,
        curve: AnimationSystem.smooth,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color:
                widget.mode.color.withValues(alpha: _isPressed ? 0.25 : 0.15),
            borderRadius: DS.borderRadiusFull,
            border: Border.all(
              color:
                  widget.mode.color.withValues(alpha: _isPressed ? 0.5 : 0.3),
              width: _isPressed ? 1.5 : 1.0,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                widget.mode.icon,
                size: DS.iconSizeXs,
                color: foregroundColor,
              ),
              const SizedBox(width: DS.spacing4),
              Text(
                widget.mode.label,
                style: TextStyle(
                  color: foregroundColor,
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
