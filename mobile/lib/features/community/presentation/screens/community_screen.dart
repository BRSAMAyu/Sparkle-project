import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_tab_content.dart';

/// Standalone feed screen — used by the `/community/feed` route.
/// When embedded in the 3-tab CommunityMainScreen, FeedTabContent is used
/// directly instead.
class CommunityScreen extends ConsumerWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      floatingActionButton: SparkleIconButton(
        icon: const Icon(Icons.edit),
        onPressed: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
          unawaited(context.push(CommunityRoutes.postsCreate));
        },
      ),
      child: SafeArea(
        child: FeedTabContent(
          onCreatePost: () {
            unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
            unawaited(context.push(CommunityRoutes.postsCreate));
          },
        ),
      ),
    );
  }
}
