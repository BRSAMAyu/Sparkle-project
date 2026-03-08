import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/curiosity_capsule_card.dart';

class CuriosityCapsuleScreen extends ConsumerWidget {
  const CuriosityCapsuleScreen({this.highlightId, super.key});
  final String? highlightId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final capsuleState = ref.watch(capsuleProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
        ),
        title: const Text('好奇心胶囊'),
      ),
      child: capsuleState.when(
        data: (capsules) => capsules.isEmpty
            ? _buildEmptyState()
            : RefreshIndicator(
                onRefresh: () =>
                    ref.read(capsuleProvider.notifier).fetchTodayCapsules(),
                child: ContentConstraint(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                    itemCount: capsules.length,
                    itemBuilder: (context, index) {
                      final capsule = capsules[index];
                      final isHighlight =
                          highlightId != null && capsule.id == highlightId;
                      return CuriosityCapsuleCard(
                        capsule: capsule,
                        highlighted: isHighlight,
                        initiallyExpanded: isHighlight,
                      );
                    },
                  ),
                ),
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('加载失败: $err')),
      ),
    );
  }

  Widget _buildEmptyState() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.lightbulb_outline,
              size: 64,
              color: DS.brandPrimary.withValues(alpha: 0.3),
            ),
            const SizedBox(height: DS.lg),
            Text(
              '今天还没有新的好奇心胶囊',
              style: TextStyle(color: DS.textPrimary, fontSize: 16),
            ),
            const SizedBox(height: DS.sm),
            Text(
              '继续学习，激发更多灵感吧！',
              style: TextStyle(color: DS.textSecondary, fontSize: 14),
            ),
          ],
        ),
      );
}
