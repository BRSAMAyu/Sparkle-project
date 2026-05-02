import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncProtocol = ref.watch(taskCardProtocolProvider(taskId));

    return asyncProtocol.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
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
        title: TaskProtocolPanel._t('为什么是这个任务', 'Why this task'),
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
                  .map((e) => Chip(
                        label: Text(e, style: const TextStyle(fontSize: 10)),
                        visualDensity: VisualDensity.compact,
                        backgroundColor:
                            DS.brandPrimary.withValues(alpha: 0.06),
                      ))
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
      title: TaskProtocolPanel._t('需要的资料', 'Materials needed'),
      children: [
        Text(
          TaskProtocolPanel._t(
            '必读 $mustLoad · 选读 $optional · 附件 $attached$retrievalLabel',
            'Required $mustLoad · Optional $optional · Attached $attached$retrievalLabel',
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
        title: TaskProtocolPanel._t('完成后将更新', 'Will update on completion'),
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: updates
                .take(5)
                .map((key) => Chip(
                      label: Text(key, style: const TextStyle(fontSize: 10)),
                      visualDensity: VisualDensity.compact,
                      backgroundColor:
                          DS.semanticSuccess.withValues(alpha: 0.06),
                    ))
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
        title: TaskProtocolPanel._t('太难？试试这个', 'Too hard? Try this'),
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
