import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/seed_library_routes.dart';
import 'package:sparkle/features/settings/presentation/screens/transparency_settings_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

const _defaultAiSystemPreferences = TransparencyPreferences(
  enabled: true,
  showTokenUsage: true,
  showAgentSwitching: true,
  showReasoningSteps: true,
  displayMode: TransparencyDisplayMode.collapsedFloating,
  autoCollapseOnComplete: true,
  allowPerTurnDismiss: true,
);

class ChatSettingsScreen extends ConsumerWidget {
  const ChatSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences =
        ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
            _defaultAiSystemPreferences;
    final notifier = ref.read(transparencyPreferencesNotifierProvider.notifier);
    final showChatContextToggle = ref.watch(showChatContextToggleProvider);
    final showChatPredictionDock = ref.watch(showChatPredictionDockProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider);
    final chatPureMode = ref.watch(chatPureModeProvider);
    final seedLibraryEnabled = ref.watch(chatSeedLibraryEnabledProvider);
    final subscriptionState = ref.watch(subscriptionsProvider);
    final enabledSeedSubscriptions = subscriptionState.subscriptions
        .where((subscription) => subscription.isEnabled)
        .toList()
      ..sort((a, b) => b.priority.compareTo(a.priority));
    final enabledSeedCount = enabledSeedSubscriptions.length;
    final enabledSeedNames = enabledSeedSubscriptions
        .map((subscription) => subscription.library?.name.trim() ?? '')
        .where((name) => name.isNotEmpty)
        .take(3)
        .toList();

    final seedTitle = switch ((
      subscriptionState.isLoading,
      seedLibraryEnabled,
      enabledSeedCount,
    )) {
      (true, _, _) => '正在同步种子库状态',
      (_, false, _) => '种子库增强默认关闭',
      (_, true, > 0) => '当前接入 $enabledSeedCount 个已启用种子库',
      _ => '已开启种子库增强，但还没有可用种子库',
    };

    final seedSubtitle = seedLibraryEnabled
        ? enabledSeedNames.isEmpty
            ? '开启后会从下一条消息开始按种子库增强。'
            : '当前生效：${enabledSeedNames.join('、')}'
        : '关闭时所有对话都不会注入种子库，避免上下文污染。';

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: const Text('对话设置'),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.md),
          children: [
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: Padding(
                padding: const EdgeInsets.all(DS.md),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.spacing10),
                      decoration: BoxDecoration(
                        color: DS.surfaceOverlay,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Icon(
                        Icons.tune_rounded,
                        color: DS.primaryBase,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '对话体验',
                            style: DS.titleLarge.copyWith(
                              color: DS.textPrimary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: DS.spacing4),
                          Text(
                            '集中调整聊天页的展示方式、预测组件和种子库增强能力。',
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.md),
            Text(
              '种子库',
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: DS.sm),
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('开启种子库增强'),
                    subtitle: const Text('为当前聊天注入已启用的种子库内容与回答风格。'),
                    value: seedLibraryEnabled,
                    onChanged: (value) {
                      unawaited(
                        ref
                            .read(chatSeedLibraryEnabledProvider.notifier)
                            .setEnabled(value),
                      );
                    },
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.library_books_outlined),
                    title: Text(seedTitle),
                    subtitle: Text(seedSubtitle),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => context.push(SeedLibraryRoutes.libraries),
                  ),
                  if (subscriptionState.error != null) ...[
                    const Divider(height: 1),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        DS.md,
                        DS.sm,
                        DS.md,
                        DS.md,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.error_outline_rounded,
                            size: 18,
                            color: DS.error,
                          ),
                          const SizedBox(width: DS.spacing8),
                          Expanded(
                            child: Text(
                              subscriptionState.error!,
                              style: DS.bodySmall.copyWith(color: DS.error),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              '界面与能力',
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: '显示 AI 系统面板',
              subtitle: '默认开启，在聊天页直接展示协作与推理能力。',
              value: preferences.enabled,
              onChanged: notifier.setEnabled,
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: '纯净模式',
              subtitle: '聊天中只保留文字消息，隐藏消息下方的附加卡片与反馈组件。',
              value: chatPureMode,
              onChanged: (value) =>
                  ref.read(chatPureModeProvider.notifier).setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: '显示顶部选择条',
              subtitle: '控制聊天页收起/展开的计划、模式和档位入口。',
              value: showChatContextToggle,
              onChanged: (value) => ref
                  .read(showChatContextToggleProvider.notifier)
                  .setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: '显示预测组件',
              subtitle: '控制输入框上方的行为预测与快捷建议。',
              value: showChatPredictionDock,
              onChanged: (value) => ref
                  .read(showChatPredictionDockProvider.notifier)
                  .setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: '显示透明胶囊',
              subtitle: '控制底部悬浮的 AI 完成情况与透明化信息。',
              value: showChatTransparencyCapsule,
              onChanged: (value) => ref
                  .read(showChatTransparencyCapsuleProvider.notifier)
                  .setEnabled(value),
            ),
            if (preferences.enabled) ...[
              const SizedBox(height: DS.lg),
              Text(
                '透明化细项',
                style: DS.titleMedium.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: '显示 Token 与成本',
                subtitle: '展示本轮用量、成本估算和系统资源消耗。',
                value: preferences.showTokenUsage,
                onChanged: notifier.setShowTokenUsage,
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: '显示 Agent 协作',
                subtitle: '展示参与的专家、职责分工和模型协同。',
                value: preferences.showAgentSwitching,
                onChanged: notifier.setShowAgentSwitching,
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: '显示推理时间线',
                subtitle: '展示关键步骤、审查与反思过程。',
                value: preferences.showReasoningSteps,
                onChanged: notifier.setShowReasoningSteps,
              ),
            ],
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: ListTile(
                leading: const Icon(Icons.settings_outlined),
                title: const Text('打开高级设置'),
                subtitle: const Text('进入透明模式的详细配置页面。'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  unawaited(
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => const TransparencySettingsScreen(),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsToggleCard extends StatelessWidget {
  const _SettingsToggleCard({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: SwitchListTile(
          title: Text(title),
          subtitle: Text(subtitle),
          value: value,
          onChanged: onChanged,
        ),
      );
}
