import 'package:flutter/material.dart';
import 'package:sparkle/core/design/tokens_v2/responsive_system.dart';
import 'package:sparkle/core/design/tokens_v2/spacing_token.dart';

/// Responsive scaffold that adapts navigation patterns across device categories.
///
/// - Mobile: bottom navigation bar
/// - Tablet: NavigationRail
/// - Desktop/TV: NavigationDrawer
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
  final List<NavigationDestination> destinations;
  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget? floatingActionButton;
  final PreferredSizeWidget? appBar;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final category = ResponsiveSystem.getCategory(context);

    switch (category) {
      case DeviceCategory.desktop:
      case DeviceCategory.tv:
        return _buildDesktopLayout(context);
      case DeviceCategory.tablet:
        return _buildTabletLayout(context);
      case DeviceCategory.watch:
      case DeviceCategory.phone:
      case DeviceCategory.phablet:
        return _buildMobileLayout(context);
    }
  }

  /// Mobile layout: bottom navigation bar
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

  /// Tablet layout: NavigationRail
  Widget _buildTabletLayout(BuildContext context) => Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: currentIndex,
              onDestinationSelected: onDestinationSelected,
              labelType: NavigationRailLabelType.all,
              destinations: destinations
                  .map(
                    (d) => NavigationRailDestination(
                      icon: d.icon,
                      selectedIcon: d.selectedIcon ?? d.icon,
                      label: Text(d.label),
                    ),
                  )
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

  /// Desktop layout: NavigationDrawer
  Widget _buildDesktopLayout(BuildContext context) => Scaffold(
        body: Row(
          children: [
            SizedBox(
              width: ResponsiveSpacing.sidebarWidth(context),
              child: NavigationDrawer(
                selectedIndex: currentIndex,
                onDestinationSelected: onDestinationSelected,
                children: [
                  Padding(
                    padding: const EdgeInsets.all(SpacingSystem.xl),
                    child: Row(
                      children: [
                        Icon(
                          Icons.local_fire_department,
                          color: Theme.of(context).colorScheme.primary,
                          size: 32,
                        ),
                        const SizedBox(width: SpacingSystem.md),
                        Text(
                          title ?? 'Sparkle',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                      ],
                    ),
                  ),
                  const Divider(),
                  ...destinations.map(
                    (d) => NavigationDrawerDestination(
                      icon: d.icon,
                      selectedIcon: d.selectedIcon ?? d.icon,
                      label: Text(d.label),
                    ),
                  ),
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
    final horizontalPadding = ContentConstraintSystem.horizontalPadding(context);

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
        const SizedBox(width: SpacingSystem.lg),
        SizedBox(
          width: sidebarWidth,
          child: sidebar,
        ),
      ],
    );
  }
}
