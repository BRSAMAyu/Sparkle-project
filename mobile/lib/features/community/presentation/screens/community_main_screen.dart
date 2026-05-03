import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_tab_content.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_tab.dart';
import 'package:sparkle/features/community/presentation/widgets/partners_tab.dart';

/// Community tab main screen — 3-tab flat architecture.
///
/// Tab 0: 伙伴 Partners (default) — accountability hub, partnerships, friends
/// Tab 1: 动态 Feed — social posts with filters
/// Tab 2: 群组 Groups — study groups and recommendations
class CommunityMainScreen extends ConsumerStatefulWidget {
  const CommunityMainScreen({super.key});

  @override
  ConsumerState<CommunityMainScreen> createState() =>
      _CommunityMainScreenState();
}

class _CommunityMainScreenState extends ConsumerState<CommunityMainScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(_onTabChanged);
  }

  void _onTabChanged() {
    if (_tabController.indexIsChanging) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    if (mounted) setState(() => _currentIndex = _tabController.index);
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final tabLabels = [
      zh ? '伙伴' : 'Partners',
      zh ? '动态' : 'Feed',
      zh ? '群组' : 'Groups',
    ];

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      floatingActionButton: _currentIndex == 1
          ? SparkleIconButton(
              icon: const Icon(Icons.edit),
              onPressed: () {
                unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
                unawaited(context.push(CommunityRoutes.postsCreate));
              },
            )
          : null,
      child: SafeArea(
        child: Column(
          children: [
            // Title + TabBar
            Padding(
              padding: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    zh ? '社群' : 'Community',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  Text(
                    zh ? '和伙伴一起成长' : 'Grow together with partners',
                    style: TextStyle(fontSize: 14, color: DS.textSecondary),
                  ),
                  const SizedBox(height: DS.md),
                  TabBar(
                    controller: _tabController,
                    isScrollable: false,
                    labelColor: DS.textPrimary,
                    unselectedLabelColor: DS.textSecondary,
                    indicatorColor: DS.brandPrimary,
                    indicatorSize: TabBarIndicatorSize.label,
                    indicatorWeight: 2,
                    labelStyle: TextStyle(
                      fontSize: DS.fontSizeSm,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                    unselectedLabelStyle: TextStyle(
                      fontSize: DS.fontSizeSm,
                      fontWeight: FontWeight.normal,
                    ),
                    tabs: tabLabels.map((label) => Tab(text: label)).toList(),
                  ),
                ],
              ),
            ),
            // Tab content
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: const [
                  PartnersTab(),
                  FeedTabContent(),
                  GroupsTab(),
                ], // ignore: prefer_if_elements_to_conditional_expressions
              ),
            ),
          ],
        ),
      ),
    );
  }
}
