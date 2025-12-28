import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/presentation/widgets/home/curiosity_capsule_card.dart';

class CuriosityCapsuleScreen extends ConsumerWidget {
  const CuriosityCapsuleScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final capsuleState = ref.watch(capsuleProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('好奇心胶囊'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: capsuleState.when(
        data: (capsules) => capsules.isEmpty
            ? _buildEmptyState()
            : RefreshIndicator(
                onRefresh: () => ref.read(capsuleProvider.notifier).fetchTodayCapsules(),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  itemCount: capsules.length,
                  itemBuilder: (context, index) => CuriosityCapsuleCard(capsule: capsules[index]),
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
          Icon(Icons.lightbulb_outline, size: 64, color: DS.brandPrimary.withValues(alpha: 0.3)),
          const SizedBox(height: DS.lg),
          Text(
            '今天还没有新的好奇心胶囊',
            style: TextStyle(color: DS.brandPrimaryConst, fontSize: 16),
          ),
          const SizedBox(height: DS.sm),
          Text(
            '继续学习，激发更多灵感吧！',
            style: TextStyle(color: DS.brandPrimaryConst, fontSize: 14),
          ),
        ],
      ),
    );
}
