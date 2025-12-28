  import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 布局类型枚举
enum LayoutType {
  mobile,  // 手机：< 768px
  tablet,  // 平板：768px - 1024px
  desktop, // 桌面：>= 1024px
}

/// 获取当前布局类型
LayoutType getLayoutType(BuildContext context) {
  final width = MediaQuery.of(context).size.width;
  if (width >= AppDesignTokens.breakpointDesktop) return LayoutType.desktop;
  if (width >= AppDesignTokens.breakpointTablet) return LayoutType.tablet;
  return LayoutType.mobile;
}

/// 布局类型扩展
extension LayoutTypeExtension on BuildContext {
  LayoutType get layoutType => getLayoutType(this);

  bool get isMobile => layoutType == LayoutType.mobile;
  bool get isTablet => layoutType == LayoutType.tablet;
  bool get isDesktop => layoutType == LayoutType.desktop;
}

/// 响应式脚手架 - 自动切换导航布局
///
/// - 移动端：底部导航栏
/// - 平板：左侧NavigationRail
/// - 桌面：展开式NavigationDrawer（侧边栏）
class ResponsiveScaffold extends StatelessWidget {

  const ResponsiveScaffold({
    required this.body, required this.destinations, required this.currentIndex, required this.onDestinationSelected, super.key,
    this.floatingActionButton,
    this.appBar,
    this.title,
  });
  final Widget body;
  final List<NavigationDestination> destinations;
  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget? floatingActionButton;
  final PreferredSizeWidget? appBar;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final layoutType = getLayoutType(context);

    switch (layoutType) {
      case LayoutType.desktop:
        return _buildDesktopLayout(context);
      case LayoutType.tablet:
        return _buildTabletLayout(context);
      case LayoutType.mobile:
        return _buildMobileLayout(context);
    }
  }

  /// 移动端布局：底部导航栏
  Widget _buildMobileLayout(BuildContext context) => Scaffold(
      appBar: appBar,
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: onDestinationSelected,
        destinations: destinations,
      ),
      floatingActionButton: floatingActionButton,
    );

  /// 平板布局：侧边NavigationRail
  Widget _buildTabletLayout(BuildContext context) => Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: currentIndex,
            onDestinationSelected: onDestinationSelected,
            labelType: NavigationRailLabelType.all,
            destinations: destinations
                .map((d) => NavigationRailDestination(
                      icon: d.icon,
                      selectedIcon: d.selectedIcon ?? d.icon,
                      label: Text(d.label),
                    ),)
                .toList(),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Scaffold(
              appBar: appBar,
              body: body,
              floatingActionButton: floatingActionButton,
            ),
          ),
        ],
      ),
    );

  /// 桌面布局：展开式侧边栏NavigationDrawer
  Widget _buildDesktopLayout(BuildContext context) => Scaffold(
      body: Row(
        children: [
          SizedBox(
            width: 280,
            child: NavigationDrawer(
              selectedIndex: currentIndex,
              onDestinationSelected: onDestinationSelected,
              children: [
                // Logo和标题
                Padding(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing24),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.local_fire_department,
                        color: AppDesignTokens.primaryBase,
                        size: 32,
                      ),
                      const SizedBox(width: AppDesignTokens.spacing12),
                      Text(
                        title ?? 'Sparkle',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                    ],
                  ),
                ),
                const Divider(),
                // 导航项
                ...destinations.map((d) => NavigationDrawerDestination(
                      icon: d.icon,
                      selectedIcon: d.selectedIcon ?? d.icon,
                      label: Text(d.label),
                    ),),
              ],
            ),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Scaffold(
              appBar: appBar,
              body: body,
              floatingActionButton: floatingActionButton,
            ),
          ),
        ],
      ),
    );
}

/// 内容宽度约束包装器
///
/// 根据屏幕尺寸自动限制内容最大宽度，提升大屏幕阅读体验
class ContentConstraint extends StatelessWidget {

  const ContentConstraint({
    required this.child, super.key,
    this.padding,
    this.enabled = true,
  });
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) return child;

    final layoutType = getLayoutType(context);

    double maxWidth;
    double horizontalPadding;

    switch (layoutType) {
      case LayoutType.desktop:
        maxWidth = AppDesignTokens.contentMaxWidthDesktop;
        horizontalPadding = AppDesignTokens.spacing32;
      case LayoutType.tablet:
        maxWidth = AppDesignTokens.contentMaxWidthTablet;
        horizontalPadding = AppDesignTokens.spacing24;
      case LayoutType.mobile:
        maxWidth = double.infinity;
        horizontalPadding = AppDesignTokens.spacing16;
    }

    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Padding(
          padding: padding ??
              EdgeInsets.symmetric(horizontal: horizontalPadding),
          child: child,
        ),
      ),
    );
  }
}

/// 响应式网格布局
///
/// 自动根据屏幕尺寸调整列数：
/// - 桌面：3列
/// - 平板：2列
/// - 手机：1列
class ResponsiveGrid extends StatelessWidget {

  const ResponsiveGrid({
    required this.children, super.key,
    this.spacing = AppDesignTokens.spacing16,
    this.childAspectRatio,
  });
  final List<Widget> children;
  final double spacing;
  final double? childAspectRatio;

  @override
  Widget build(BuildContext context) {
    final layoutType = getLayoutType(context);

    int crossAxisCount;
    switch (layoutType) {
      case LayoutType.desktop:
        crossAxisCount = 3;
      case LayoutType.tablet:
        crossAxisCount = 2;
      case LayoutType.mobile:
        crossAxisCount = 1;
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: spacing,
        mainAxisSpacing: spacing,
        childAspectRatio: childAspectRatio ?? (layoutType == LayoutType.mobile ? 1.2 : 1.5),
      ),
      itemCount: children.length,
      itemBuilder: (context, index) => children[index],
    );
  }
}

/// 响应式列布局（Sliver版本，用于CustomScrollView）
class ResponsiveSliverGrid extends StatelessWidget {

  const ResponsiveSliverGrid({
    required this.children, super.key,
    this.spacing = AppDesignTokens.spacing16,
    this.childAspectRatio,
  });
  final List<Widget> children;
  final double spacing;
  final double? childAspectRatio;

  @override
  Widget build(BuildContext context) {
    final layoutType = getLayoutType(context);

    int crossAxisCount;
    switch (layoutType) {
      case LayoutType.desktop:
        crossAxisCount = 3;
      case LayoutType.tablet:
        crossAxisCount = 2;
      case LayoutType.mobile:
        crossAxisCount = 1;
    }

    return SliverGrid(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: spacing,
        mainAxisSpacing: spacing,
        childAspectRatio: childAspectRatio ?? (layoutType == LayoutType.mobile ? 1.2 : 1.5),
      ),
      delegate: SliverChildBuilderDelegate(
        (context, index) => children[index],
        childCount: children.length,
      ),
    );
  }
}

/// 响应式双栏布局
///
/// 桌面/平板：左右双栏（主内容+侧边栏）
/// 手机：单栏（只显示主内容）
class ResponsiveTwoColumn extends StatelessWidget {

  const ResponsiveTwoColumn({
    required this.main, required this.sidebar, super.key,
    this.sidebarWidth = 320,
  });
  final Widget main;
  final Widget sidebar;
  final double sidebarWidth;

  @override
  Widget build(BuildContext context) {
    final layoutType = getLayoutType(context);

    if (layoutType == LayoutType.mobile) {
      // 手机端只显示主内容
      return main;
    }

    // 平板和桌面显示双栏
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: main),
        const SizedBox(width: AppDesignTokens.spacing16),
        SizedBox(
          width: sidebarWidth,
          child: sidebar,
        ),
      ],
    );
  }
}
