import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// GOV-015: Unified transparency dashboard showing all data Sparkle uses.
class DataUsageDashboardScreen extends StatelessWidget {
  const DataUsageDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return Scaffold(
      appBar: AppBar(
        title: Text(l.dataUsagePrivacyTitle),
        backgroundColor: DS.surfacePrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          _SectionHeader(
            icon: Icons.psychology_outlined,
            title: l.dataUsageKnowsTitle,
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.person_outline,
            title: l.dataUsageProfileCardTitle,
            description: l.dataUsageProfileCardDesc,
            dataTypes: [
              l.dataUsageTagGoals,
              l.dataUsageTagPlans,
              l.dataUsageTagTasks,
              l.dataUsageTagAchievements,
            ],
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.auto_awesome_outlined,
            title: l.dataUsageAiCardTitle,
            description: l.dataUsageAiCardDesc,
            dataTypes: [
              l.dataUsageTagCognitivePatterns,
              l.dataUsageTagMasteryEstimates,
              l.dataUsageTagLearningStyle,
              l.dataUsageTagErrorPatterns,
            ],
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.history_rounded,
            title: l.dataUsageMemoryCardTitle,
            description: l.dataUsageMemoryCardDesc,
            dataTypes: [
              l.dataUsageTagChatMessages,
              l.dataUsageTagGrowthChronicle,
              l.dataUsageTagSpineTraces,
            ],
          ),
          const SizedBox(height: DS.spacing24),
          _SectionHeader(
            icon: Icons.share_outlined,
            title: l.dataUsageSharedTitle,
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.group_outlined,
            title: l.dataUsageCommunityCardTitle,
            description: l.dataUsageCommunityCardDesc,
            dataTypes: [
              l.dataUsageTagAnonErrors,
              l.dataUsageTagResourceRatings,
            ],
          ),
          const SizedBox(height: DS.spacing24),
          _SectionHeader(
            icon: Icons.security_outlined,
            title: l.dataUsageControlsTitle,
          ),
          const SizedBox(height: DS.spacing12),
          _ControlTile(
            icon: Icons.visibility_off_outlined,
            title: l.dataUsageHideChronicle,
            subtitle: l.dataUsageHideChronicleDesc,
          ),
          _ControlTile(
            icon: Icons.delete_outline,
            title: l.dataUsageDeleteData,
            subtitle: l.dataUsageDeleteDataDesc,
          ),
          _ControlTile(
            icon: Icons.download_outlined,
            title: l.dataUsageExportData,
            subtitle: l.dataUsageExportDataDesc,
          ),
          const SizedBox(height: DS.spacing32),
          Text(
            l.dataUsageFooter,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: DS.textTertiary),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: DS.brandPrimary),
        const SizedBox(width: DS.spacing8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
                color: DS.textPrimary,
              ),
        ),
      ],
    );
  }
}

class _DataCard extends StatelessWidget {
  const _DataCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.dataTypes,
  });

  final IconData icon;
  final String title;
  final String description;
  final List<String> dataTypes;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Text(
                title,
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: DS.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            description,
            style: TextStyle(fontSize: 13, color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing4,
            children: dataTypes
                .map((t) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary12,
                        borderRadius: BorderRadius.circular(DS.radius8),
                      ),
                      child: Text(t, style: TextStyle(fontSize: 11, color: DS.brandPrimary)),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _ControlTile extends StatelessWidget {
  const _ControlTile({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: DS.textSecondary),
      title: Text(title, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: DS.textPrimary)),
      subtitle: Text(subtitle, style: TextStyle(fontSize: 12, color: DS.textTertiary)),
    );
  }
}
