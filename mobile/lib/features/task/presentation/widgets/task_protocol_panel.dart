import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/task/data/models/task_card_protocol.dart';
import 'package:sparkle/features/task/data/repositories/task_card_protocol_repository.dart';

/// TASK-001: Renders the structured TaskCardProtocol fields the audit found
/// missing from the existing task guide:
///
///   • why_this_task: signal source, priority rationale, evidence
///   • materials_protocol: retrieval mode, must-load nodes, optional nodes
///   • updates_after_completion: which state keys this task will refresh
///   • fallback_if_failed: alternative tasks to try if this one is too hard
///
/// Designed to slot into task_execution_screen.dart above the existing
/// TaskGuidePanel. Hides itself when the backend returns no protocol payload
/// (e.g. for legacy tasks without Spine context).
class TaskProtocolPanel extends ConsumerWidget {
  const TaskProtocolPanel({
    required this.taskId,
    super.key,
  });

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncProtocol = ref.watch(taskCardProtocolProvider(taskId));

    return asyncProtocol.when(
      loading: () => const _ProtocolLoadingShimmer(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(taskCardProtocolProvider(taskId)),
      ),
      data: (protocol) {
        if (protocol == null) return const SizedBox.shrink();
        return _ProtocolBody(protocol: protocol);
      },
    );
  }
}

class _ProtocolBody extends StatelessWidget {
  const _ProtocolBody({required this.protocol});
  final TaskCardProtocol protocol;

  @override
  Widget build(BuildContext context) {
    final sections = <Widget>[];

    if (protocol.whyThisTask.hasContent) {
      sections.add(_WhySection(why: protocol.whyThisTask));
    }
    if (protocol.materialsProtocol.hasContent) {
      sections.add(const SizedBox(height: 8));
      sections.add(_MaterialsSection(materials: protocol.materialsProtocol));
    }
    if (protocol.updatesAfterCompletion.isNotEmpty) {
      sections.add(const SizedBox(height: 8));
      sections.add(_UpdatesSection(updates: protocol.updatesAfterCompletion));
    }
    if (protocol.fallbackIfFailed.isNotEmpty) {
      sections.add(const SizedBox(height: 8));
      sections.add(_FallbackSection(fallbacks: protocol.fallbackIfFailed));
    }

    if (sections.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: sections,
      ),
    );
  }
}

class _WhySection extends StatelessWidget {
  const _WhySection({required this.why});
  final WhyThisTask why;

  @override
  Widget build(BuildContext context) => _Section(
        icon: Icons.psychology_outlined,
        title: context.l10n.taskProtocolWhyThisTask,
        children: [
          if ((why.userVisibleReason ?? '').isNotEmpty)
            Text(
              why.userVisibleReason!,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          if ((why.priorityRationale ?? '').isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              why.priorityRationale!,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
          if (why.evidence.isNotEmpty) ...[
            const SizedBox(height: 4),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: why.evidence
                  .take(3)
                  .map((e) => SemanticPill(label: e, tone: PillTone.brand, dense: true))
                  .toList(),
            ),
          ],
        ],
      );
}

class _MaterialsSection extends StatelessWidget {
  const _MaterialsSection({required this.materials});
  final MaterialsProtocol materials;

  @override
  Widget build(BuildContext context) {
    final mustLoad = materials.mustLoadNodeIds.length;
    final optional = materials.optionalNodeIds.length;
    final attached = materials.attachedDocumentIds.length;
    final retrievalLabel = materials.retrievalMode == null
        ? ''
        : ' · ${materials.retrievalMode}';

    return _Section(
      icon: Icons.menu_book_outlined,
      title: context.l10n.taskProtocolMaterialsNeeded,
      children: [
        Text(
          context.l10n.taskProtocolMaterialsCount(
            mustLoad,
            optional,
            attached,
            retrievalLabel,
          ),
          style: TextStyle(color: DS.textSecondary, fontSize: 12),
        ),
      ],
    );
  }
}

class _UpdatesSection extends StatelessWidget {
  const _UpdatesSection({required this.updates});
  final List<String> updates;

  @override
  Widget build(BuildContext context) => _Section(
        icon: Icons.refresh,
        title: context.l10n.taskProtocolUpdatesOnCompletion,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: updates
                .take(5)
                .map((key) => SemanticPill(label: key, tone: PillTone.success, dense: true))
                .toList(),
          ),
        ],
      );
}

class _FallbackSection extends StatelessWidget {
  const _FallbackSection({required this.fallbacks});
  final List<String> fallbacks;

  @override
  Widget build(BuildContext context) => _Section(
        icon: Icons.alt_route,
        title: context.l10n.taskProtocolTooHardTryThis,
        children: [
          ...fallbacks.take(3).map(
                (f) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      Icon(
                        Icons.arrow_right_alt,
                        size: 14,
                        color: DS.brandPrimary,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          f,
                          style: TextStyle(
                            color: DS.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      );
}

class _Section extends StatelessWidget {
  const _Section({
    required this.icon,
    required this.title,
    required this.children,
  });

  final IconData icon;
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: DS.brandPrimary),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ...children,
        ],
      );
}

class _ProtocolLoadingShimmer extends StatefulWidget {
  const _ProtocolLoadingShimmer();

  @override
  State<_ProtocolLoadingShimmer> createState() =>
      _ProtocolLoadingShimmerState();
}

class _ProtocolLoadingShimmerState extends State<_ProtocolLoadingShimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final opacity = 0.3 + 0.3 * _controller.value;
        return Opacity(
          opacity: opacity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _shimmerLine(140, 12),
              const SizedBox(height: DS.spacing8),
              _shimmerLine(100, 10),
              const SizedBox(height: DS.spacing6),
              _shimmerLine(180, 10),
              const SizedBox(height: DS.spacing6),
              _shimmerLine(120, 10),
            ],
          ),
        );
      },
    );

  Widget _shimmerLine(double width, double height) => Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: DS.borderSubtle,
        borderRadius: BorderRadius.circular(4),
      ),
    );
}
