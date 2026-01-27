import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:sparkle/core/design/design_system.dart';

class BentoGrid extends StatelessWidget {
  const BentoGrid({required this.children, super.key});
  final List<Widget> children;

  int _crossAxisCount(BuildContext context) {
    final category = ResponsiveSystem.getCategory(context);
    switch (category) {
      case DeviceCategory.tablet:
        return 3;
      case DeviceCategory.desktop:
        return 4;
      case DeviceCategory.tv:
        return 6;
      case DeviceCategory.watch:
      case DeviceCategory.phone:
      case DeviceCategory.phablet:
        return 2;
    }
  }

  @override
  Widget build(BuildContext context) => StaggeredGrid.count(
        crossAxisCount: _crossAxisCount(context),
        mainAxisSpacing: DS.spacing12,
        crossAxisSpacing: DS.spacing12,
        children: children,
      );
}
