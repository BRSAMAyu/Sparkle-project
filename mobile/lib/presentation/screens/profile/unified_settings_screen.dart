import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/presentation/providers/settings_provider.dart';
import 'package:sparkle/presentation/providers/theme_provider.dart';
import 'package:sparkle/presentation/widgets/settings/learning_mode_control.dart';
import 'package:sparkle/presentation/widgets/settings/weekly_agenda_grid.dart';
import 'package:sparkle/presentation/widgets/chaos/chaos_control_dialog.dart';

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
    final l10n = AppLocalizations.of(context)!;
    final enterToSend = ref.watch(enterToSendProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.schedulePreferences), // Using generic settings title from l10n or keeping consistent
        actions: [
          TextButton(
            onPressed: () {
              // TODO: Save all settings
              Navigator.pop(context);
            },
            child: Text(l10n.confirm),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(Icons.psychology, l10n.learningMode),
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

            _buildSectionHeader(Icons.schedule, l10n.weeklyAgenda),
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

            _buildSectionHeader(Icons.brightness_6, l10n.theme),
            const SizedBox(height: AppDesignTokens.spacing16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.theme),
              subtitle: Text('${l10n.lightMode}/${l10n.darkMode}'),
              trailing: DropdownButton<ThemeMode>(
                value: ref.watch(themeModeProvider),
                underline: const SizedBox.shrink(),
                onChanged: (ThemeMode? newValue) {
                  if (newValue != null) {
                    ref.read(themeModeProvider.notifier).state = newValue;
                  }
                },
                items: [
                  DropdownMenuItem(value: ThemeMode.system, child: Text(l10n.followSystem)),
                  DropdownMenuItem(value: ThemeMode.light, child: Text(l10n.lightMode)),
                  DropdownMenuItem(value: ThemeMode.dark, child: Text(l10n.darkMode)),
                ],
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing32),

            _buildSectionHeader(Icons.touch_app, l10n.interactionSettings),
            const SizedBox(height: AppDesignTokens.spacing16),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.enterToSend),
              subtitle: Text(l10n.enterToSendDescription),
              value: enterToSend,
              onChanged: (v) => ref.read(enterToSendProvider.notifier).setEnabled(v),
              activeThumbColor: AppDesignTokens.primaryBase,
            ),
            const SizedBox(height: AppDesignTokens.spacing32),

            _buildSectionHeader(Icons.notifications, l10n.notificationSettings),
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

            const SizedBox(height: AppDesignTokens.spacing64),
            Center(
              child: GestureDetector(
                onLongPress: () {
                  showDialog(
                    context: context,
                    builder: (context) => const ChaosControlDialog(),
                  );
                },
                child: const Text(
                  'Sparkle v2.1.0-stable\n© 2025 Sparkle Team',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey, fontSize: 10),
                ),
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing32),
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