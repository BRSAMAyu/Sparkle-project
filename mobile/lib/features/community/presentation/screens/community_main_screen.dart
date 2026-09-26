import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_tab_content.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_tab.dart';
import 'package:sparkle/features/community/presentation/widgets/partners_tab.dart';

/// Community tab main screen — 3-tab collaboration-first architecture
/// (S-03 表面收敛：小队/冲刺/今日打卡/成果反馈是核心，公共 feed 降级)。
///
/// Tab 0: 群组协作 Groups (default) — squads entry, today check-in,
///        artifact feedback, my groups, discovery
/// Tab 1: 伙伴 Partners — accountability hub, partnerships, friends
/// Tab 2: 动态 Feed — public posts (demoted: last tab, not the core surface)
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
    _tabController
      ..removeListener(_onTabChanged)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // S-03（v2）标签/内容对位锁：children 顺序 = [Groups, Partners, Feed]
    // （v1 收敛 41d83f83 改了 children 漏改本表，首 Tab 曾挂「伙伴」标签
    // 渲染群组内容）。顺序唯一事实源在此与下方 TabBarView 一一对应。
    final tabLabels = [
      context.l10n.communityTabGroups,
      context.l10n.communityTabPartners,
      context.l10n.communityTabFeed,
    ];

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      // FAB-UNIFY：组件已自带最大尺寸语义（fabGeometry 钉死方形几何），
      // HYGIENE-DEBT 的急救 SizedBox 包装去重，调用点只声明视觉档。
      floatingActionButton: _currentIndex == 2
          ? SparkleIconButton.fabGeometry(
              size: DS.touchTargetMinSize,
              icon: const Icon(Icons.edit),
              semanticLabel: context.l10n.communityCreatePost,
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                unawaited(context.push(CommunityRoutes.postsCreate));
              },
            )
          : null,
      child: SafeArea(
        child: NestedScrollView(
          headerSliverBuilder: (context, innerBoxIsScrolled) => [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.communityTitle,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: DS.sm),
                    Text(
                      context.l10n.communitySubtitle,
                      style: TextStyle(fontSize: 14, color: DS.textSecondary),
                    ),
                    // S-03 验收「seed/demo group 明确标演示」：demo 模式下
                    // 全社群表面（群组/伙伴/动态）顶部挂常驻演示声明，
                    // mock/seed 数据不冒充真实社群行为。
                    if (DemoDataService.isDemoMode) ...[
                      const SizedBox(height: DS.sm),
                      _DemoModeBanner(),
                    ],
                  ],
                ),
              ),
            ),
            SliverPersistentHeader(
              pinned: true,
              delegate: _TabBarDelegate(
                TabBar(
                  controller: _tabController,
                  labelColor: DS.textPrimary,
                  unselectedLabelColor: DS.textSecondary,
                  indicatorColor: DS.brandPrimary,
                  indicatorSize: TabBarIndicatorSize.label,
                  labelStyle: const TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                  unselectedLabelStyle: const TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: FontWeight.normal,
                  ),
                  tabs: tabLabels.map((label) => Tab(text: label)).toList(),
                ),
              ),
            ),
          ],
          body: TabBarView(
            controller: _tabController,
            children: const [
              GroupsTab(),
              PartnersTab(),
              FeedTabContent(),
            ],
          ),
        ),
      ),
    );
  }
}

/// 演示模式声明条：常驻、非 dismissible——demo/seed 数据必须一直可辨识，
/// 不冒充真实社群（S-03 验收项）。令牌样式，无字面量色彩。
class _DemoModeBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.md,
          vertical: DS.sm,
        ),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: DS.warning.withValues(alpha: 0.35)),
        ),
        child: Row(
          children: [
            Icon(
              Icons.science_outlined,
              size: 16,
              color: DS.warning,
            ),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Text(
                context.l10n.demoModeBanner,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
            ),
          ],
        ),
      );
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  const _TabBarDelegate(this.tabBar);

  final TabBar tabBar;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) =>
      ColoredBox(
        color: DS.surfacePrimary,
        child: tabBar,
      );

  @override
  double get maxExtent => tabBar.preferredSize.height;

  @override
  double get minExtent => tabBar.preferredSize.height;

  @override
  bool shouldRebuild(_TabBarDelegate oldDelegate) =>
      tabBar != oldDelegate.tabBar;
}
