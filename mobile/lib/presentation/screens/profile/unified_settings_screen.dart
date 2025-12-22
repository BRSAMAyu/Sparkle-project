import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/theme_provider.dart';
import 'package:sparkle/presentation/widgets/settings/learning_mode_control.dart';
import 'package:sparkle/presentation/widgets/settings/weekly_agenda_grid.dart';

class UnifiedSettingsScreen extends ConsumerStatefulWidget {
  const UnifiedSettingsScreen({super.key});

  @override
  ConsumerState<UnifiedSettingsScreen> createState() => _UnifiedSettingsScreenState();
}

class _UnifiedSettingsScreenState extends ConsumerState<UnifiedSettingsScreen> {
  // Mock State
  double _depth = 0.5;
  double _curiosity = 0.5;
  bool _notificationsEnabled = true;
  bool _smartReminders = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('个人偏好设置'),
        actions: [
          TextButton(
            onPressed: () {
              // TODO: Save all settings
              Navigator.pop(context);
            },
            child: const Text('保存'),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(Icons.psychology, '学习模式'),
            const SizedBox(height: AppDesignTokens.spacing16),
            const Text(
              '拖动控制点，调整你的AI辅导风格',
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            LearningModeControl(
              depth: _depth,
              curiosity: _curiosity,
              onChanged: (d, c) {
                setState(() {
                  _depth = d;
                  _curiosity = c;
                });
              },
            ),
            const SizedBox(height: AppDesignTokens.spacing32),

            _buildSectionHeader(Icons.schedule, '每周日程'),
            const SizedBox(height: AppDesignTokens.spacing16),
            const Text(
              '框选时间段：红色繁忙，绿色碎片(AI提醒)，蓝色休息',
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            WeeklyAgendaGrid(
              onChanged: (data) {
                // Handle updates
              },
            ),
            const SizedBox(height: AppDesignTokens.spacing32),

            _buildSectionHeader(Icons.brightness_6, '显示设置'),
            const SizedBox(height: AppDesignTokens.spacing16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('外观模式'),
              subtitle: const Text('选择浅色或深色界面体验'),
              trailing: DropdownButton<ThemeMode>(
                value: ref.watch(themeModeProvider),
                underline: const SizedBox.shrink(),
                onChanged: (ThemeMode? newValue) {
                  if (newValue != null) {
                    ref.read(themeModeProvider.notifier).state = newValue;
                  }
                },
                items: const [
                  DropdownMenuItem(value: ThemeMode.system, child: Text('跟随系统')),
                  DropdownMenuItem(value: ThemeMode.light, child: Text('浅色模式')),
                  DropdownMenuItem(value: ThemeMode.dark, child: Text('深色模式')),
                ],
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing32),

            _buildSectionHeader(Icons.notifications, '通知设置'),
            const SizedBox(height: AppDesignTokens.spacing16),
            SwitchListTile(
              title: const Text('启用通知'),
              value: _notificationsEnabled,
              onChanged: (v) => setState(() => _notificationsEnabled = v),
              activeThumbColor: AppDesignTokens.primaryBase,
            ),
            SwitchListTile(
              title: const Text('智能碎片时间提醒'),
              subtitle: const Text('在绿色时间段主动推送微任务'),
              value: _smartReminders,
              onChanged: (v) => setState(() => _smartReminders = v),
              activeThumbColor: AppDesignTokens.primaryBase,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(IconData icon, String title) {
    return Row(
      children: [
        Icon(icon, color: AppDesignTokens.primaryBase),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
