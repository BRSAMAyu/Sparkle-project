import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class SettingsBehaviorExplanation extends StatefulWidget {
  const SettingsBehaviorExplanation({
    required this.notificationDailyCap,
    required this.notificationLevel,
    required this.taskRemindersEnabled,
    required this.taskReminderTimes,
    super.key,
  });

  final int notificationDailyCap;
  final String notificationLevel;
  final bool taskRemindersEnabled;
  final List<int> taskReminderTimes;

  @override
  State<SettingsBehaviorExplanation> createState() =>
      _SettingsBehaviorExplanationState();
}

class _SettingsBehaviorExplanationState
    extends State<SettingsBehaviorExplanation> {
  final Set<String> _expandedKeys = {'accessibility'};

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final items = [
      _ExplanationItem(
        keyName: 'accessibility',
        icon: Icons.accessibility_new_rounded,
        title: l10n.settBehaviorAccessibility,
        body: l10n.settBehaviorAccessibilityBody,
      ),
      _ExplanationItem(
        keyName: 'emotion',
        icon: Icons.self_improvement_rounded,
        title: l10n.settBehaviorEmotion,
        body: l10n.settBehaviorEmotionBody,
      ),
      _ExplanationItem(
        keyName: 'reminders',
        icon: Icons.notifications_active_outlined,
        title: l10n.settBehaviorReminder,
        body: _reminderExplanation(context),
      ),
      _ExplanationItem(
        keyName: 'memory',
        icon: Icons.psychology_outlined,
        title: l10n.settBehaviorMemory,
        body: l10n.settBehaviorMemoryBody,
      ),
      _ExplanationItem(
        keyName: 'materials',
        icon: Icons.auto_stories_outlined,
        title: l10n.settBehaviorMaterials,
        body: l10n.settBehaviorMaterialsBody,
      ),
      _ExplanationItem(
        keyName: 'research',
        icon: Icons.science_outlined,
        title: l10n.settBehaviorResearch,
        body: l10n.settBehaviorResearchBody,
      ),
    ];

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline_rounded),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.settBehaviorTitle,
                      style: DS.titleMedium.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      l10n.settBehaviorSubtitle,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          ...items.map(_buildExplanationTile),
        ],
      ),
    );
  }

  Widget _buildExplanationTile(_ExplanationItem item) {
    final expanded = _expandedKeys.contains(item.keyName);
    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: ExpansionTile(
        initiallyExpanded: expanded,
        leading: Icon(item.icon, color: DS.primaryBase),
        title: Text(item.title),
        tilePadding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
        childrenPadding: const EdgeInsets.fromLTRB(
          DS.spacing12,
          0,
          DS.spacing12,
          DS.spacing12,
        ),
        onExpansionChanged: (value) {
          setState(() {
            if (value) {
              _expandedKeys.add(item.keyName);
            } else {
              _expandedKeys.remove(item.keyName);
            }
          });
        },
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              item.body,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _reminderExplanation(BuildContext context) {
    final l10n = context.l10n;
    final cap = widget.notificationDailyCap <= 0
        ? l10n.settBehaviorReminderNoCap
        : l10n.settBehaviorReminderCap(widget.notificationDailyCap);
    final taskText = widget.taskRemindersEnabled
        ? (widget.taskReminderTimes.isEmpty
            ? l10n.settBehaviorReminderTaskOnNoTime
            : l10n.settBehaviorReminderTaskOnWithTime(
                widget.taskReminderTimes
                    .map((m) => _formatMinutes(context, m))
                    .join(' / '),
              ))
        : l10n.settBehaviorReminderTaskOff;
    final level = _notificationLevel(context, widget.notificationLevel);
    return l10n.settBehaviorReminderBodyEn(cap, level, taskText);
  }

  String _formatMinutes(BuildContext context, int minutes) {
    final l10n = context.l10n;
    if (minutes >= 1440) {
      final days = minutes ~/ 1440;
      return days == 1 ? l10n.settBehaviorDay(days) : l10n.settBehaviorDays(days);
    }
    if (minutes >= 60) {
      final hours = minutes ~/ 60;
      return hours == 1 ? l10n.settBehaviorHour(hours) : l10n.settBehaviorHours(hours);
    }
    return minutes == 1
        ? l10n.settBehaviorMinute(minutes)
        : l10n.settBehaviorMinutes(minutes);
  }

  String _notificationLevel(BuildContext context, String level) {
    final l10n = context.l10n;
    switch (level) {
      case 'minimal':
        return l10n.settBehaviorReminderLevelMinimal;
      case 'verbose':
        return l10n.settBehaviorReminderLevelVerbose;
      case 'standard':
      default:
        return l10n.settBehaviorReminderLevelStandard;
    }
  }
}

class SettingsDataControlsCard extends StatelessWidget {
  const SettingsDataControlsCard({
    required this.growthChronicleHidden,
    required this.memoryHidden,
    required this.saving,
    required this.onExportData,
    required this.onDeleteData,
    required this.onGrowthChronicleHiddenChanged,
    required this.onMemoryHiddenChanged,
    required this.onOpenMemorySettings,
    super.key,
    this.statusMessage,
  });

  final bool growthChronicleHidden;
  final bool memoryHidden;
  final bool saving;
  final VoidCallback onExportData;
  final VoidCallback onDeleteData;
  final ValueChanged<bool> onGrowthChronicleHiddenChanged;
  final ValueChanged<bool> onMemoryHiddenChanged;
  final VoidCallback onOpenMemorySettings;
  final String? statusMessage;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield_outlined),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Text(
                  l10n.settDataControlsTitle,
                  style: DS.titleMedium.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
              if (saving)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            l10n.settDataControlsDesc,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.4,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          _ActionTile(
            icon: Icons.download_outlined,
            title: l10n.settDataExport,
            subtitle: l10n.settDataExportDesc,
            onTap: onExportData,
          ),
          const Divider(height: DS.spacing24),
          _ActionTile(
            icon: Icons.delete_outline_rounded,
            title: l10n.settDataDelete,
            subtitle: l10n.settDataDeleteDesc,
            destructive: true,
            onTap: onDeleteData,
          ),
          const Divider(height: DS.spacing24),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.settDataHideChronicle),
            subtitle: Text(l10n.settDataHideChronicleDesc),
            value: growthChronicleHidden,
            onChanged: saving ? null : onGrowthChronicleHiddenChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.settDataHideMemory),
            subtitle: Text(l10n.settDataHideMemoryDesc),
            value: memoryHidden,
            onChanged: saving ? null : onMemoryHiddenChanged,
            activeThumbColor: DS.primaryBase,
          ),
          const SizedBox(height: DS.spacing4),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: onOpenMemorySettings,
              icon: const Icon(Icons.psychology_outlined),
              label: Text(l10n.settDataManageMemory),
            ),
          ),
          if (statusMessage != null && statusMessage!.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              statusMessage!,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.destructive = false,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final bool destructive;

  @override
  Widget build(BuildContext context) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(icon, color: destructive ? DS.error : DS.primaryBase),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
      );
}

class _ExplanationItem {
  const _ExplanationItem({
    required this.keyName,
    required this.icon,
    required this.title,
    required this.body,
  });

  final String keyName;
  final IconData icon;
  final String title;
  final String body;
}
