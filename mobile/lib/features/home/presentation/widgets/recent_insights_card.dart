import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class RecentInsightsCard extends ConsumerStatefulWidget {
  const RecentInsightsCard({super.key});

  @override
  ConsumerState<RecentInsightsCard> createState() => _RecentInsightsCardState();
}

class _RecentInsightsCardState extends ConsumerState<RecentInsightsCard> {
  static const _collapsedPrefKey = 'dashboard.recent_insights_card.collapsed';

  bool _isCollapsed = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadCollapsedPreference());
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(notificationCenterProvider.notifier).loadNotifications(),
      );
    });
  }

  Future<void> _loadCollapsedPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final collapsed = prefs.getBool(_collapsedPrefKey) ?? false;
    if (!mounted) return;
    setState(() {
      _isCollapsed = collapsed;
    });
  }

  Future<void> _setCollapsed(bool value) async {
    if (_isCollapsed == value) return;
    setState(() {
      _isCollapsed = value;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_collapsedPrefKey, value);
  }

  @override
  Widget build(BuildContext context) {
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');
    final notificationState = ref.watch(notificationCenterProvider);
    final systemUpdates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );

    final insightEntries = <_InsightEntry>[
      ...notificationState.notifications
          .where(
            (item) =>
                (item.type ?? '').startsWith('theater_') ||
                item.type == 'learning_report_ready' ||
                item.type == 'simulation_session_ready',
          )
          .map(
            (item) => _InsightEntry(
              type: item.type ?? '',
              title: item.title,
              subtitle: item.content,
              metadata: item.metadata,
              createdAt: item.createdAt,
            ),
          ),
      ...systemUpdates
          .where(
            (item) =>
                (item['type']?.toString().startsWith('theater_') ?? false) ||
                item['type']?.toString() == 'learning_report_ready' ||
                item['type']?.toString() == 'simulation_session_ready',
          )
          .map(
            (item) => _InsightEntry(
              type: item['type']?.toString() ?? '',
              title: item['title']?.toString() ??
                  (context.l10n.recentInsightsTitle),
              subtitle: item['description']?.toString() ?? '',
              metadata: Map<String, dynamic>.from(
                item['metadata'] as Map? ?? const {},
              ),
              createdAt: _parseCreatedAt(item['created_at']),
            ),
          ),
    ]..sort((a, b) => b.createdAt.compareTo(a.createdAt));

    final dedupedEntries = <_InsightEntry>[];
    final seenKeys = <String>{};
    for (final entry in insightEntries) {
      final key =
          '${entry.type}|${entry.title}|${entry.createdAt.toIso8601String()}';
      if (seenKeys.add(key)) {
        dedupedEntries.add(entry);
      }
    }
    final recentEntries = dedupedEntries.take(2).toList();

    if (recentEntries.isEmpty) {
      return const SizedBox.shrink();
    }

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          tone: DashboardSurfaceTone.summary,
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.auto_graph_rounded,
                accentColor: DS.brandPrimary,
                title: context.l10n.recentInsightsTitle,
                summary: _isCollapsed
                    ? (isChinese
                        ? '已收起最近洞察，需要时可随时展开查看。'
                        : 'Recent insights are collapsed. Expand them whenever you want another look.')
                    : (isChinese
                        ? '最近 ${recentEntries.length} 条与你学习动线相关的更新。'
                        : 'Latest ${recentEntries.length} updates related to your learning flow.'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      decoration: BoxDecoration(
                        color: DS.surfaceOverlay,
                        borderRadius: DS.borderRadiusFull,
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Text(
                        '${recentEntries.length}',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                    const SizedBox(width: DS.spacing6),
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 32,
                      onPressed: () => unawaited(_setCollapsed(!_isCollapsed)),
                      icon: Icon(
                        _isCollapsed
                            ? Icons.keyboard_arrow_down_rounded
                            : Icons.keyboard_arrow_up_rounded,
                        size: 18,
                      ),
                    ),
                  ],
                ),
              ),
              AnimatedSwitcher(
                duration: DS.durationFast,
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                child: _isCollapsed
                    ? const SizedBox(
                        key: ValueKey('collapsed'),
                        height: 0,
                      )
                    : Column(
                        key: const ValueKey('expanded'),
                        children: [
                          const SizedBox(height: DS.spacing8),
                          ...recentEntries.map(
                            (item) => _InsightRow(
                              icon: item.type == 'learning_report_ready'
                                  ? Icons.article_outlined
                                  : item.type == 'simulation_session_ready'
                                      ? Icons.groups_rounded
                                      : Icons.auto_graph_rounded,
                              title: item.title,
                              subtitle: item.subtitle,
                              onTap: () => _openNotificationInsight(
                                context,
                                type: item.type,
                                metadata: item.metadata,
                              ),
                            ),
                          ),
                        ],
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  DateTime _parseCreatedAt(Object? raw) {
    if (raw is DateTime) {
      return raw;
    }
    if (raw is int) {
      return DateTime.fromMillisecondsSinceEpoch(raw * 1000);
    }
    if (raw is String) {
      return DateTime.tryParse(raw) ?? DateTime.fromMillisecondsSinceEpoch(0);
    }
    return DateTime.fromMillisecondsSinceEpoch(0);
  }

  void _openNotificationInsight(
    BuildContext context, {
    required String type,
    required Map<String, dynamic> metadata,
  }) {
    if (type == 'learning_report_ready') {
      final payload = metadata['report_payload'];
      if (payload is Map<String, dynamic>) {
        unawaited(
          context.push(
            ReportRoutes.learningReport,
            extra: LearningReport.fromJson(payload),
          ),
        );
        return;
      }
      if (payload is Map) {
        unawaited(
          context.push(
            ReportRoutes.learningReport,
            extra: LearningReport.fromJson(Map<String, dynamic>.from(payload)),
          ),
        );
        return;
      }
      unawaited(context.push('/notification-center'));
      return;
    }

    if (type == 'simulation_session_ready') {
      final deepLink = metadata['deep_link']?.toString();
      if (deepLink != null && deepLink.isNotEmpty) {
        unawaited(context.push(deepLink));
        return;
      }
      unawaited(context.push('/simulation'));
      return;
    }

    final deepLink = metadata['deep_link']?.toString();
    if (deepLink != null && deepLink.isNotEmpty) {
      unawaited(context.push(deepLink));
      return;
    }
    unawaited(context.push('/theater'));
  }
}

class _InsightEntry {
  const _InsightEntry({
    required this.type,
    required this.title,
    required this.subtitle,
    required this.metadata,
    required this.createdAt,
  });

  final String type;
  final String title;
  final String subtitle;
  final Map<String, dynamic> metadata;
  final DateTime createdAt;
}

class _InsightRow extends StatelessWidget {
  const _InsightRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          margin: const EdgeInsets.only(bottom: DS.spacing8),
          padding: const EdgeInsets.all(DS.spacing10),
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.72),
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, size: 16, color: DS.brandPrimary),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Icon(
                Icons.chevron_right_rounded,
                size: 18,
                color: DS.textTertiary,
              ),
            ],
          ),
        ),
      );
}
