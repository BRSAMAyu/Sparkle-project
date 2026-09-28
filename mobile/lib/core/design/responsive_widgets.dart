import 'package:flutter/material.dart';
import 'package:sparkle/core/design/tokens_v2/responsive_system.dart';
import 'package:sparkle/core/navigation/shell/shell.dart';

/// Responsive scaffold that adapts navigation patterns across width tiers.
///
/// V4-F04 升级：槽位解析改为宽度档（`resolveShellNavSlot`，断点唯一
/// 权威 `LayoutBreakpoints`）——
/// - 手机/窄窗（<768 或窄短边横屏）：底部导航栏；
/// - 平板（768–1199）：NavigationRail（图标+全部标签）；
/// - 桌面/宽窗（≥1200，含 1280×720 桌面窗口）：常驻侧栏
///   （extended rail + 品牌头，替换旧 NavigationDrawer 内嵌误用）。
/// 五 Tab 路由合同（StatefulShellRoute 五分支）零触碰。
class ResponsiveScaffold extends StatelessWidget {
  const ResponsiveScaffold({
    required this.body,
    required this.destinations,
    required this.currentIndex,
    required this.onDestinationSelected,
    super.key,
    this.floatingActionButton,
    this.appBar,
    this.title,
  });
  final Widget body;

  /// Shell 目的地（图标语义独立模型，三档呈现面共用）。
  final List<ShellDestination> destinations;
  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget? floatingActionButton;
  final PreferredSizeWidget? appBar;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final slot = resolveShellNavSlot(MediaQuery.of(context).size);

    switch (slot) {
      case ShellNavSlot.sideNav:
        return _buildSideNavLayout(context);
      case ShellNavSlot.sideRail:
        return _buildSideRailLayout(context);
      case ShellNavSlot.bottomBar:
        return _buildBottomBarLayout(context);
    }
  }

  /// 手机/窄窗：底部导航栏（+ 像素档装饰沿，classic 零差量）。
  Widget _buildBottomBarLayout(BuildContext context) => Scaffold(
        appBar: appBar,
        // 键盘合同（验收「键盘打开不越界」）：键盘弹出时 Scaffold 消费
        // viewInsets——body 收缩、底栏抬升至键盘上方保持可见。显式钉住
        // 默认值作为 Shell 键盘契约的可 grep 锚点。
        resizeToAvoidBottomInset: true,
        body: body,
        bottomNavigationBar: ShellBottomBar(
          destinations: destinations,
          currentIndex: currentIndex,
          onDestinationSelected: onDestinationSelected,
        ),
        floatingActionButton: floatingActionButton,
      );

  /// NavigationRail 目的地映射（底栏/rail/侧栏三档共用同一语义模型）。
  List<NavigationRailDestination> _railDestinations() => destinations
      .map(
        (d) => NavigationRailDestination(
          icon: shellNavIconFor(d, selected: false),
          selectedIcon: shellNavIconFor(d, selected: true),
          // 语义独立：rail 目的地无 tooltip 参数，可访问名称由
          // label 文本与图标位 Semantics（角标）承载。
          label: Text(d.label),
        ),
      )
      .toList();

  /// 平板：左侧 NavigationRail（图标+全部标签）。
  Widget _buildSideRailLayout(BuildContext context) => Scaffold(
        resizeToAvoidBottomInset: true,
        body: Row(
          children: [
            // SafeArea：刘海/打孔与手势条下导航面不越界（无 inset 时
            // 零填充，视觉与升级前逐位一致）。
            SafeArea(
              child: NavigationRail(
                selectedIndex: currentIndex,
                onDestinationSelected: onDestinationSelected,
                labelType: NavigationRailLabelType.all,
                destinations: _railDestinations(),
              ),
            ),
            const VerticalDivider(thickness: 1, width: 1),
            Expanded(
              child: Scaffold(
                appBar: appBar,
                resizeToAvoidBottomInset: true,
                body: body,
                floatingActionButton: floatingActionButton,
              ),
            ),
          ],
        ),
      );

  /// 桌面/宽窗（≥1200）：常驻侧栏。
  ///
  /// 替换旧「NavigationDrawer 内嵌进定宽 SizedBox」的误用（drawer 组件
  /// 语义是模态抽屉，常驻侧栏用 extended rail 承载），保留品牌头与既有
  /// 侧栏宽度权威（ResponsiveSpacing.sidebarWidth）。
  Widget _buildSideNavLayout(BuildContext context) {
    final sidebarWidth = ResponsiveSpacing.sidebarWidth(context);
    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: Row(
        children: [
          SafeArea(
            child: SizedBox(
              width: sidebarWidth,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(32),
                    child: Row(
                      children: [
                        Icon(
                          Icons.local_fire_department,
                          color: Theme.of(context).colorScheme.primary,
                          size: 32,
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Text(
                            title ?? 'Sparkle',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Divider(),
                  Expanded(
                    child: NavigationRail(
                      selectedIndex: currentIndex,
                      onDestinationSelected: onDestinationSelected,
                      // extended = 常驻侧栏语义（图标+行内标签）。
                      extended: true,
                      labelType: NavigationRailLabelType.none,
                      minExtendedWidth: sidebarWidth,
                      destinations: _railDestinations(),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Scaffold(
              appBar: appBar,
              resizeToAvoidBottomInset: true,
              body: body,
              floatingActionButton: floatingActionButton,
            ),
          ),
        ],
      ),
    );
  }
}

/// Content width constraint wrapper for large screens.
class ContentConstraint extends StatelessWidget {
  const ContentConstraint({
    required this.child,
    super.key,
    this.padding,
    this.enabled = true,
  });
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) return child;

    final maxWidth = ContentConstraintSystem.maxWidth(context);
    final horizontalPadding =
        ContentConstraintSystem.horizontalPadding(context);

    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Padding(
          padding:
              padding ?? EdgeInsets.symmetric(horizontal: horizontalPadding),
          child: child,
        ),
      ),
    );
  }
}

/// Responsive grid layout (non-sliver).
class ResponsiveGrid extends StatelessWidget {
  const ResponsiveGrid({
    required this.children,
    super.key,
    this.spacing = 16.0,
    this.childAspectRatio,
  });
  final List<Widget> children;
  final double spacing;
  final double? childAspectRatio;

  @override
  Widget build(BuildContext context) {
    final crossAxisCount = ResponsiveGridSystem.columns(context);
    final resolvedSpacing = spacing;
    final resolvedAspectRatio =
        childAspectRatio ?? ResponsiveGridSystem.aspectRatio(context);

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: resolvedSpacing,
        mainAxisSpacing: resolvedSpacing,
        childAspectRatio: resolvedAspectRatio,
      ),
      itemCount: children.length,
      itemBuilder: (context, index) => children[index],
    );
  }
}

/// Responsive sliver grid layout.
class ResponsiveSliverGrid extends StatelessWidget {
  const ResponsiveSliverGrid({
    required this.children,
    super.key,
    this.spacing = 16.0,
    this.childAspectRatio,
  });
  final List<Widget> children;
  final double spacing;
  final double? childAspectRatio;

  @override
  Widget build(BuildContext context) {
    final crossAxisCount = ResponsiveGridSystem.columns(context);
    final resolvedSpacing = spacing;
    final resolvedAspectRatio =
        childAspectRatio ?? ResponsiveGridSystem.aspectRatio(context);

    return SliverGrid(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: resolvedSpacing,
        mainAxisSpacing: resolvedSpacing,
        childAspectRatio: resolvedAspectRatio,
      ),
      delegate: SliverChildBuilderDelegate(
        (context, index) => children[index],
        childCount: children.length,
      ),
    );
  }
}

/// Responsive two-column layout.
class ResponsiveTwoColumn extends StatelessWidget {
  const ResponsiveTwoColumn({
    required this.main,
    required this.sidebar,
    super.key,
    this.sidebarWidth = 320,
  });
  final Widget main;
  final Widget sidebar;
  final double sidebarWidth;

  @override
  Widget build(BuildContext context) {
    final category = ResponsiveSystem.getCategory(context);
    final isMobile = category == DeviceCategory.watch ||
        category == DeviceCategory.phone ||
        category == DeviceCategory.phablet;

    if (isMobile) return main;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: main),
        const SizedBox(width: 24),
        SizedBox(
          width: sidebarWidth,
          child: sidebar,
        ),
      ],
    );
  }
}
