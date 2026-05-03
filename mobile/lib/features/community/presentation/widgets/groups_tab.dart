import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';

/// Groups tab — wraps existing GroupsHubView which already contains
/// my groups, recommendations, browse/create actions, and RefreshIndicator.
class GroupsTab extends StatelessWidget {
  const GroupsTab({super.key});

  @override
  Widget build(BuildContext context) => const ContentConstraint(
        child: GroupsHubView(
          padding: EdgeInsets.fromLTRB(DS.spacing16, DS.spacing16, DS.spacing16, 80),
        ),
      );
}
