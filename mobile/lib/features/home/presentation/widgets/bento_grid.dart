import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';

class BentoGrid extends StatelessWidget {
  const BentoGrid({required this.children, super.key});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => StaggeredGrid.count(
        crossAxisCount: 2, // 2 columns
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        children: children,
      );
}
