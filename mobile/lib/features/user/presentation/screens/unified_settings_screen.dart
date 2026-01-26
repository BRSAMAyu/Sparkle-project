import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/utils/chaos/chaos_control_dialog.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/sync_center_screen.dart';
import 'package:sparkle/features/user/presentation/widgets/learning_mode_control.dart';
import 'package:sparkle/features/user/presentation/widgets/preference_controller_2d.dart';
import 'package:sparkle/features/user/presentation/widgets/weekly_agenda_grid.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class UnifiedSettingsScreen extends ConsumerStatefulWidget {
  const UnifiedSettingsScreen({super.key});

  @override
  ConsumerState<UnifiedSettingsScreen> createState() =>
      _UnifiedSettingsScreenState();
}

class _UnifiedSettingsScreenState extends ConsumerState<UnifiedSettingsScreen> {
  // Mock State
  double _depth = 0.5;
  double _curiosity = 0.5;
  bool _notificationsEnabled = true;
  bool _smartReminders = true;
  bool _isGenerating = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!; // l10n should always be available in a build context
    final enterToSend = ref.watch(enterToSendProvider);
    final transparentMode = ref.watch(transparentModeProvider);
    final transparencyLevel = ref.watch(transparencyLevelProvider);
    final systemUpdateLevel = ref.watch(systemUpdateLevelProvider);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n
            .schedulePreferences,), // Using generic settings title from l10n or keeping consistent
        actions: [
          TextButton(
            onPressed: () {
              // TODO: Save all settings
              if (context.mounted) {
                context.pop();
              }
            },
            child: Text(l10n.confirm),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(Icons.psychology, l10n.learningMode),
            const SizedBox(height: DS.spacing16),
            Text(
              '拖动控制点，调整你的AI辅导风格',
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
            ),
            const SizedBox(height: DS.spacing16),
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
            const SizedBox(height: DS.spacing32),

            // ========== 胶囊生成区域 ==========
            _buildSectionHeader(Icons.auto_awesome, '胶囊生成'),
            const SizedBox(height: DS.spacing16),
            Text(
              '调整偏好并生成专属好奇心胶囊',
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
            ),
            const SizedBox(height: DS.spacing16),

            // 二维控制面板
            PreferenceController2D(
              initialDepth: _depth,
              initialCuriosity: _curiosity,
              onPreferenceChanged: (offset) {
                setState(() {
                  _curiosity = offset.dx;
                  _depth = offset.dy;
                });
              },
            ),
            const SizedBox(height: DS.spacing16),

            // 生成预览卡片
            CapsuleGenerationPreview(
              depthPreference: _depth,
              curiosityPreference: _curiosity,
            ),
            const SizedBox(height: DS.spacing16),

            // 立即生成按钮
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isGenerating
                    ? null
                    : () => _requestCapsuleGeneration(context),
                icon: _isGenerating
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_awesome),
                label: Text(_isGenerating ? '生成中...' : '立即生成胶囊'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: DS.primaryBase,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                  shape: const RoundedRectangleBorder(
                    borderRadius: DS.borderRadius12,
                  ),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.schedule, l10n.weeklyAgenda),
            const SizedBox(height: DS.spacing16),
            Text(
              '框选时间段：红色繁忙，绿色碎片(AI提醒)，蓝色休息',
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
            ),
            const SizedBox(height: DS.spacing16),
            WeeklyAgendaGrid(
              onChanged: (data) {
                // Handle updates
              },
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.brightness_6, l10n.theme),
            const SizedBox(height: DS.spacing16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.theme),
              subtitle: Text('${l10n.lightMode}/${l10n.darkMode}'),
              trailing: DropdownButton<AppThemeMode>(
                value: ref.watch(appThemeModeProvider),
                underline: const SizedBox.shrink(),
                onChanged: (AppThemeMode? newValue) {
                  if (newValue != null) {
                    ref.read(themeManagerProvider).setAppThemeMode(newValue);
                  }
                },
                items: [
                  DropdownMenuItem(
                      value: AppThemeMode.system,
                      child: Text(l10n.followSystem),),
                  DropdownMenuItem(
                      value: AppThemeMode.light, child: Text(l10n.lightMode),),
                  DropdownMenuItem(
                      value: AppThemeMode.dark, child: Text(l10n.darkMode),),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.touch_app, l10n.interactionSettings),
            const SizedBox(height: DS.spacing16),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.enterToSend),
              subtitle: Text(l10n.enterToSendDescription),
              value: enterToSend,
              onChanged: (v) =>
                  ref.read(enterToSendProvider.notifier).setEnabled(v),
              activeThumbColor: DS.primaryBase,
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.notifications, l10n.notificationSettings),
            const SizedBox(height: DS.spacing16),
            SwitchListTile(
              title: const Text('启用通知'),
              value: _notificationsEnabled,
              onChanged: (v) => setState(() => _notificationsEnabled = v),
              activeThumbColor: DS.primaryBase,
            ),
            SwitchListTile(
              title: const Text('智能碎片时间提醒'),
              subtitle: const Text('在绿色时间段主动推送微任务'),
              value: _smartReminders,
              onChanged: (v) => setState(() => _smartReminders = v),
              activeThumbColor: DS.primaryBase,
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.visibility, '透明模式'),
            const SizedBox(height: DS.spacing16),
            SwitchListTile(
              title: const Text('启用透明模式'),
              subtitle: const Text('显示状态与资源消耗概览'),
              value: transparentMode,
              onChanged: (v) => ref
                  .read(transparencyLevelProvider.notifier)
                  .setLevel(v ? 2 : 0),
              activeThumbColor: DS.primaryBase,
            ),
            if (transparentMode) ...[
              const SizedBox(height: DS.spacing8),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('透明度级别'),
                subtitle: const Text('基础/标准/高级'),
                trailing: DropdownButton<int>(
                  value: transparencyLevel,
                  underline: const SizedBox.shrink(),
                  onChanged: (level) {
                    if (level != null) {
                      ref.read(transparencyLevelProvider.notifier).setLevel(level);
                    }
                  },
                  items: const [
                    DropdownMenuItem(value: 0, child: Text('关闭')),
                    DropdownMenuItem(value: 1, child: Text('基础')),
                    DropdownMenuItem(value: 2, child: Text('标准')),
                    DropdownMenuItem(value: 3, child: Text('高级')),
                  ],
                ),
              ),
            ],
            const SizedBox(height: DS.spacing16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('系统反馈级别'),
              subtitle: const Text('控制系统更新提示的详细程度'),
              trailing: DropdownButton<int>(
                value: systemUpdateLevel,
                underline: const SizedBox.shrink(),
                onChanged: (level) {
                  if (level != null) {
                    ref.read(systemUpdateLevelProvider.notifier).setLevel(level);
                  }
                },
                items: const [
                  DropdownMenuItem(value: 0, child: Text('静默')),
                  DropdownMenuItem(value: 1, child: Text('摘要')),
                  DropdownMenuItem(value: 2, child: Text('详细')),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing32),
            _buildSectionHeader(Icons.sync, '同步'),
            const SizedBox(height: DS.spacing16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.sync),
              title: const Text('同步中心'),
              subtitle: const Text('查看离线队列状态与重试'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.of(context).push<void>(
                  MaterialPageRoute<void>(
                    builder: (_) => const SyncCenterScreen(),
                  ),
                );
              },
            ),
            const SizedBox(height: DS.spacing64),
            Center(
              child: GestureDetector(
                onLongPress: () {
                  showDialog<void>(
                    context: context,
                    builder: (context) => const ChaosControlDialog(),
                  );
                },
                child: Text(
                  'Sparkle v2.1.0-stable\n© 2025 Sparkle Team',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: DS.brandPrimaryConst, fontSize: 10),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing32),
          ],
        ),
      ),
    );
  }

  Future<void> _requestCapsuleGeneration(BuildContext context) async {
    setState(() => _isGenerating = true);

    try {
      final notifier = ref.read(generationJobsProvider.notifier);

      // 根据好奇心偏好计算生成数量
      final requestedCount = _curiosity < 0.3
          ? 1
          : _curiosity < 0.7
              ? 2
              : 3;

      final taskId = await notifier.requestBatchGeneration(
        depthPreference: _depth,
        curiosityPreference: _curiosity,
        requestedCount: requestedCount,
      );

      if (mounted) {
        if (taskId != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('✨ 胶囊生成任务已创建'),
              backgroundColor: DS.success,
              action: SnackBarAction(
                label: '查看',
                textColor: Colors.white,
                onPressed: () {
                  // TODO: 导航到任务状态页
                },
              ),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('生成失败，请稍后重试'),
              backgroundColor: DS.error,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('生成失败: $e'),
            backgroundColor: DS.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  Widget _buildSectionHeader(IconData icon, String title) => Row(
        children: [
          Icon(icon, color: DS.primaryBase),
          const SizedBox(width: DS.sm),
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
