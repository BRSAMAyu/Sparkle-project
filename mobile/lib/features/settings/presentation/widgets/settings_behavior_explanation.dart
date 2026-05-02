import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
    final zh = I18nService.instance.isChinese;
    final items = [
      _ExplanationItem(
        keyName: 'accessibility',
        icon: Icons.accessibility_new_rounded,
        title: zh ? '无障碍' : 'Accessibility',
        body: zh
            ? '当你开启高对比度、降低动效或放大字体时，Sparkle 会把这些偏好应用到主要学习界面、知识星图、对话和任务执行流程，优先保证可读、可触达和低负荷。'
            : 'When you enable high contrast, reduced motion, or larger text, Sparkle applies those preferences across core learning surfaces, Galaxy, chat, and task execution so the interface stays readable, reachable, and lower load.',
      ),
      _ExplanationItem(
        keyName: 'emotion',
        icon: Icons.self_improvement_rounded,
        title: zh ? '情绪自适应' : 'Emotion adaptive',
        body: zh
            ? '当 Sparkle 识别到疲劳、压力或认知负荷较高时，会使用更柔和的颜色、更大的文字、更少动画，并减少挑战感提示。手动固定后，自动适应会让位给你的选择。'
            : 'When Sparkle detects fatigue, pressure, or high cognitive load, it softens colors, increases text comfort, reduces animation, and tones down challenge cues. Manual overrides take priority over automatic adaptation.',
      ),
      _ExplanationItem(
        keyName: 'reminders',
        icon: Icons.notifications_active_outlined,
        title: zh ? '提醒频率' : 'Reminder frequency',
        body: _reminderExplanation(zh),
      ),
      _ExplanationItem(
        keyName: 'memory',
        icon: Icons.psychology_outlined,
        title: zh ? '记忆控制' : 'Memory controls',
        body: zh
            ? 'Sparkle 会记住学习目标、偏好、承诺和你明确允许的经历线索，用来保持对话连续和任务跟进；不会把被屏蔽的来源或关闭的记忆类型写入长期记忆。'
            : 'Sparkle remembers goals, preferences, commitments, and explicitly allowed episode signals to keep conversations continuous and follow-ups relevant. Blocked sources and disabled memory types are not written into long-term memory.',
      ),
      _ExplanationItem(
        keyName: 'materials',
        icon: Icons.auto_stories_outlined,
        title: zh ? '资料使用' : 'Study materials',
        body: zh
            ? '你的学习资料会用于检索相关上下文、生成任务建议、解释知识点和构建知识星图；不会被用于公开社区内容或研究分析，除非你在对应设置里明确允许。'
            : 'Your study materials are used for retrieval, task suggestions, explanations, and Galaxy construction. They are not used for public community content or research analysis unless you explicitly allow that setting.',
      ),
      _ExplanationItem(
        keyName: 'research',
        icon: Icons.science_outlined,
        title: zh ? '研究参与' : 'Research participation',
        body: zh
            ? '加入研究意味着部分去标识化学习行为、错误模式和资源质量信号可被汇总分析，用来改进 Sparkle；原始私密对话、个人身份信息和被你隐藏的内容不会进入研究数据。'
            : 'Joining research allows de-identified learning behavior, error patterns, and resource quality signals to be aggregated to improve Sparkle. Raw private chats, identity details, and hidden content are excluded.',
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
                      zh
                          ? 'Sparkle 如何使用这些设置'
                          : 'How Sparkle Uses These Settings',
                      style: DS.titleMedium.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      zh
                          ? '展开任一区域，查看你的选择会怎样影响 Sparkle 的行为。'
                          : 'Expand any area to see how your choices affect Sparkle behavior.',
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

  String _reminderExplanation(bool zh) {
    final cap = widget.notificationDailyCap <= 0
        ? (zh ? '不会发送智能提醒' : 'will not send smart reminders')
        : (zh
            ? '每天最多 ${widget.notificationDailyCap} 次智能提醒'
            : 'up to ${widget.notificationDailyCap} smart reminders per day');
    final taskText = widget.taskRemindersEnabled
        ? (widget.taskReminderTimes.isEmpty
            ? (zh
                ? '任务提醒已开启，但未设置具体提前量'
                : 'task reminders are on, with no lead times set')
            : (zh
                ? '任务会在 ${widget.taskReminderTimes.map(_formatMinutesZh).join(' / ')} 前提醒'
                : 'tasks remind you ${widget.taskReminderTimes.map(_formatMinutesEn).join(' / ')} before due time'))
        : (zh ? '任务提醒已关闭' : 'task reminders are off');
    final level = zh
        ? _notificationLevelZh(widget.notificationLevel)
        : _notificationLevelEn(widget.notificationLevel);
    return zh
        ? '当前设置下，Sparkle $cap，通知详细度为$level；$taskText。安静时段和已关闭类型会优先拦截非紧急提醒。'
        : 'With the current setup, Sparkle $cap at $level detail; $taskText. Quiet hours and disabled types suppress non-urgent reminders first.';
  }

  String _formatMinutesZh(int minutes) {
    if (minutes >= 1440) {
      return '${minutes ~/ 1440} 天';
    }
    if (minutes >= 60) {
      return '${minutes ~/ 60} 小时';
    }
    return '$minutes 分钟';
  }

  String _formatMinutesEn(int minutes) {
    if (minutes >= 1440) {
      final days = minutes ~/ 1440;
      return '$days day${days == 1 ? '' : 's'}';
    }
    if (minutes >= 60) {
      final hours = minutes ~/ 60;
      return '$hours hour${hours == 1 ? '' : 's'}';
    }
    return '$minutes minute${minutes == 1 ? '' : 's'}';
  }

  String _notificationLevelZh(String level) {
    switch (level) {
      case 'minimal':
        return '简洁';
      case 'verbose':
        return '详细';
      case 'standard':
      default:
        return '标准';
    }
  }

  String _notificationLevelEn(String level) {
    switch (level) {
      case 'minimal':
        return 'minimal';
      case 'verbose':
        return 'detailed';
      case 'standard':
      default:
        return 'standard';
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
    final zh = I18nService.instance.isChinese;
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
                  zh ? '数据控制' : 'Data Controls',
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
            zh
                ? '导出、删除和隐藏入口集中在这里，所有操作都会说明后果。'
                : 'Export, deletion, and hiding controls live here, with clear consequences for each action.',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.4,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          _ActionTile(
            icon: Icons.download_outlined,
            title: zh ? '导出我的数据' : 'Export My Data',
            subtitle: zh
                ? '生成包含账号资料、学习记录、设置和可导出记忆的压缩包。'
                : 'Create a ZIP archive with account profile, learning records, settings, and exportable memory data.',
            onTap: onExportData,
          ),
          const Divider(height: DS.spacing24),
          _ActionTile(
            icon: Icons.delete_outline_rounded,
            title: zh ? '删除我的数据' : 'Delete My Data',
            subtitle: zh
                ? '进入确认流程。删除账号会移除个人资料、偏好和历史记录，且不可恢复。'
                : 'Open the confirmation flow. Account deletion removes personal data, preferences, and history, and cannot be undone.',
            destructive: true,
            onTap: onDeleteData,
          ),
          const Divider(height: DS.spacing24),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(zh ? '隐藏我的成长编年史' : 'Hide My Growth Chronicle'),
            subtitle: Text(
              zh
                  ? '隐藏后，成长叙事入口默认不展示编年史内容；数据不会因此删除。'
                  : 'When hidden, growth narrative surfaces do not show chronicle content by default. This does not delete the data.',
            ),
            value: growthChronicleHidden,
            onChanged: saving ? null : onGrowthChronicleHiddenChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(zh ? '隐藏我的记忆' : 'Hide My Memory'),
            subtitle: Text(
              zh
                  ? '隐藏后，记忆面板和可见记忆引用会默认收起；长期记忆写入规则请进入记忆设置调整。'
                  : 'When hidden, memory panels and visible memory references are collapsed by default. Use Memory Settings to change long-term memory write rules.',
            ),
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
              label: Text(zh ? '管理记忆写入规则' : 'Manage memory write rules'),
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
