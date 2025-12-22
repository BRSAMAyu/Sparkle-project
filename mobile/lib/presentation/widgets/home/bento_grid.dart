
import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';

class BentoGrid extends StatelessWidget {
  final List<Widget> children;

  const BentoGrid({required this.children, super.key});

  @override
  Widget build(BuildContext context) {
    return StaggeredGrid.count(
      crossAxisCount: 2, // 2 columns
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      children: children,
    );
  }
}
