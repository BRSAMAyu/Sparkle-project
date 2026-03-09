import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';

class DashboardCardGrid extends StatelessWidget {
  const DashboardCardGrid({
    required this.cards,
    super.key,
  });

  static const double gridCardHeight = 184;

  final List<Widget> cards;

  @override
  Widget build(BuildContext context) => DashboardEntrance(
        index: 7,
        slideOffset: Offset.zero,
        child: AlignedGridView.count(
          crossAxisCount: 2,
          mainAxisSpacing: DS.spacing12,
          crossAxisSpacing: DS.spacing12,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: cards.length,
          itemBuilder: (context, index) => SizedBox(
            height: DashboardCardGrid.gridCardHeight,
            child: cards[index],
          ),
        ),
      );
}
