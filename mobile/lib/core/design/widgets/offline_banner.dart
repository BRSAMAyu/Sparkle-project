import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/offline/connectivity_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Global offline banner that watches [isOnlineProvider] and shows a
/// non-intrusive warning banner when the device has no connectivity.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);
    if (isOnline) return const SizedBox.shrink();

    final l10n = AppLocalizations.of(context)!;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16, vertical: DS.spacing8),
      decoration: BoxDecoration(
        color: DS.warning.withValues(alpha: 0.12),
        border: Border(
          bottom: BorderSide(color: DS.warning.withValues(alpha: 0.3)),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            Icon(Icons.cloud_off_rounded, size: 16, color: DS.warning),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                l10n.offlineBannerMessage,
                style: DS.bodySmall.copyWith(color: DS.warning),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
