import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// GOV-015: Unified transparency dashboard showing all data Sparkle uses.
class DataUsageDashboardScreen extends StatelessWidget {
  const DataUsageDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Your Data & Privacy'),
        backgroundColor: DS.surfacePrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          _SectionHeader(
            icon: Icons.psychology_outlined,
            title: 'What Sparkle Knows About You',
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.person_outline,
            title: 'Profile & Goals',
            description: 'Your name, goals, plans, and task history are used to personalize learning paths.',
            dataTypes: ['Goals', 'Plans', 'Tasks', 'Achievements'],
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.auto_awesome_outlined,
            title: 'AI Understanding',
            description: 'Cognitive patterns, learning style, and mastery estimates help Sparkle adapt to you.',
            dataTypes: ['Cognitive patterns', 'Mastery estimates', 'Learning style', 'Error patterns'],
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.history_rounded,
            title: 'Memory & History',
            description: 'Chat history and growth chronicle entries are stored to maintain conversation continuity.',
            dataTypes: ['Chat messages', 'Growth chronicle', 'Spine traces'],
          ),
          const SizedBox(height: DS.spacing24),
          _SectionHeader(
            icon: Icons.share_outlined,
            title: 'What Is Shared',
          ),
          const SizedBox(height: DS.spacing12),
          _DataCard(
            icon: Icons.group_outlined,
            title: 'Community',
            description: 'Anonymous error patterns and resource quality ratings are shared to help peers learn.',
            dataTypes: ['Anonymous error patterns', 'Resource ratings'],
          ),
          const SizedBox(height: DS.spacing24),
          _SectionHeader(
            icon: Icons.security_outlined,
            title: 'Your Controls',
          ),
          const SizedBox(height: DS.spacing12),
          _ControlTile(
            icon: Icons.visibility_off_outlined,
            title: 'Hide chronicle entries',
            subtitle: 'Hidden entries are invisible to AI but never deleted',
          ),
          _ControlTile(
            icon: Icons.delete_outline,
            title: 'Request data deletion',
            subtitle: 'All your data can be permanently removed on request',
          ),
          _ControlTile(
            icon: Icons.download_outlined,
            title: 'Export your data',
            subtitle: 'Download a complete copy of everything Sparkle stores',
          ),
          const SizedBox(height: DS.spacing32),
          Text(
            'Sparkle never sells your data. All personalization is for your benefit only.',
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
        borderRadius: BorderRadius.circular(DS.radiusMd),
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
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: DS.textPrimary),
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
                        borderRadius: BorderRadius.circular(DS.radiusSm),
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
      title: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: DS.textPrimary)),
      subtitle: Text(subtitle, style: TextStyle(fontSize: 12, color: DS.textTertiary)),
    );
  }
}
