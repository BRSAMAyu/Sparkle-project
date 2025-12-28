import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/domain/models/learning_path_node.dart';
import 'package:sparkle/presentation/providers/learning_path_provider.dart';

class LearningPathDialog extends ConsumerWidget {
  final String targetNodeId;
  final String targetNodeName;

  const LearningPathDialog({
    required this.targetNodeId, required this.targetNodeName, super.key,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pathAsync = ref.watch(learningPathProvider(targetNodeId));

    return Container(
      padding: const EdgeInsets.all(24.0),
      height: MediaQuery.of(context).size.height * 0.6,
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Learning Path to "$targetNodeName"',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: DS.lg),
          Expanded(
            child: pathAsync.when(
              data: (path) {
                if (path.isEmpty) {
                  return const Center(child: Text('No prerequisites found. You can start learning!'));
                }
                return ListView.builder(
                  itemCount: path.length,
                  itemBuilder: (context, index) {
                    final node = path[index];
                    final isLast = index == path.length - 1;
                    return _buildTimelineItem(context, node, isLast);
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, stack) => Center(child: Text('Error: $err')),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem(BuildContext context, LearningPathNode node, bool isLast) {
    Color statusColor;
    IconData statusIcon;

    switch (node.status) {
      case 'mastered':
        statusColor = DS.success;
        statusIcon = Icons.check_circle;
        break;
      case 'unlocked':
        statusColor = Colors.orange;
        statusIcon = Icons.lock_open;
        break;
      case 'locked':
      default:
        statusColor = DS.brandPrimary;
        statusIcon = Icons.lock;
        break;
    }

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: statusColor.withOpacity(0.2),
                ),
                padding: const EdgeInsets.all(DS.sm),
                child: Icon(statusIcon, color: statusColor, size: 20),
              ),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 2,
                    color: DS.brandPrimary.withOpacity(0.3),
                    margin: const EdgeInsets.symmetric(vertical: 4),
                  ),
                ),
            ],
          ),
          const SizedBox(width: DS.lg),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    node.name,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: node.isTarget ? Theme.of(context).primaryColor : null,
                        ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    node.status.toUpperCase(),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: statusColor,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
