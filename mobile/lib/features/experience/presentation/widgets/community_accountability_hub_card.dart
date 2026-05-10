import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';

class CommunityAccountabilityHubCard extends ConsumerWidget {
  const CommunityAccountabilityHubCard({
    super.key,
    this.onCreateCommitment,
    this.onFindPartners,
  });

  final VoidCallback? onCreateCommitment;
  final VoidCallback? onFindPartners;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncValue = ref.watch(communityAccountabilitySnapshotProvider);
    return asyncValue.when(
      data: (snapshot) => _CommunityAccountabilitySurface(
        snapshot: snapshot,
        onCreateCommitment: onCreateCommitment,
        onFindPartners: onFindPartners,
      ),
      loading: () => const SizedBox(
        height: 160,
        child: Center(child: SparkleListSkeleton(count: 1)),
      ),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(communityAccountabilitySnapshotProvider),
      ),
    );
  }
}

class _CommunityAccountabilitySurface extends StatelessWidget {
  const _CommunityAccountabilitySurface({
    required this.snapshot,
    this.onCreateCommitment,
    this.onFindPartners,
  });

  final CommunityAccountabilitySnapshot snapshot;
  final VoidCallback? onCreateCommitment;
  final VoidCallback? onFindPartners;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing14),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.success.withValues(alpha: 0.18),
        padding: const EdgeInsets.all(DS.spacing14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: DS.success.withValues(alpha: 0.12),
                    borderRadius: DS.borderRadius16,
                  ),
                  child: Icon(
                    Icons.handshake_rounded,
                    color: DS.success,
                    size: 21,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.accountabilitySpaceTitle,
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: DS.fontSizeXs,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        snapshot.summary.isNotEmpty
                            ? snapshot.summary
                            : l10n.accountabilitySpaceSummary,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontSize: DS.fontSizeSm,
                          height: 1.52,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                if (onCreateCommitment != null)
                  SparkleButton.primary(
                    label: l10n.accountabilitySetCommitment,
                    icon: const Icon(Icons.flag_rounded),
                    onPressed: onCreateCommitment!,
                  ),
                if (onFindPartners != null)
                  SparkleButton.ghost(
                    label: l10n.accountabilityFindPartners,
                    icon: const Icon(Icons.group_add_rounded),
                    onPressed: onFindPartners!,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
