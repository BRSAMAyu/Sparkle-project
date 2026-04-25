import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';

class LearningPortfolioScreen extends ConsumerWidget {
  const LearningPortfolioScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final portfolioAsync = ref.watch(learningPortfolioProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('我的学习档案'),
      ),
      child: ContentConstraint(
        child: portfolioAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (Object error, StackTrace stackTrace) => _PortfolioErrorState(
            message: error.toString(),
          ),
          data: (LearningPortfolioResult portfolio) {
            if (portfolio.isEmpty) {
              return _PortfolioEmptyState(
                onStartSprint: () => context.push(PlanRoutes.examSprintSetup),
              );
            }

            return ListView(
              padding: const EdgeInsets.all(DS.spacing16),
              children: [
                _PortfolioSummaryCard(portfolio: portfolio),
                const SizedBox(height: DS.spacing16),
                _PortfolioGroupSection(
                  title: '进行中',
                  subtitle: '继续追踪每一门课当前冲刺的节奏与掌握进展。',
                  entries: portfolio.activeEntries,
                ),
                const SizedBox(height: DS.spacing16),
                _PortfolioGroupSection(
                  title: '已完成',
                  subtitle: '回看已经跑完的冲刺，保留每次考试前后的成长轨迹。',
                  entries: portfolio.completedEntries,
                ),
                const SizedBox(height: DS.spacing16),
                _PortfolioGroupSection(
                  title: '计划中',
                  subtitle: '已经排进学习档案，但还没正式开跑的冲刺。',
                  entries: portfolio.plannedEntries,
                ),
                const SizedBox(height: DS.spacing32),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _PortfolioSummaryCard extends StatelessWidget {
  const _PortfolioSummaryCard({required this.portfolio});

  final LearningPortfolioResult portfolio;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFFE7F4EA),
            Color(0xFFF7EFE3),
            Color(0xFFF7F8FC),
          ],
        ),
        border: Border.all(color: const Color(0xFFCED8CE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '所有科目累计掌握节点',
            style: DS.labelLarge.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '${portfolio.totalMasteredNodes}',
            style: DS.displayLarge.copyWith(
              fontWeight: DS.fontWeightBold,
              color: const Color(0xFF224434),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _SummaryPill(label: '进行中 ${portfolio.activeCount}'),
              _SummaryPill(label: '已完成 ${portfolio.completedCount}'),
              _SummaryPill(label: '计划中 ${portfolio.plannedCount}'),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryPill extends StatelessWidget {
  const _SummaryPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFD7DFD7)),
      ),
      child: Text(
        label,
        style: DS.bodySmall.copyWith(
          color: DS.textPrimary,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}

class _PortfolioGroupSection extends StatelessWidget {
  const _PortfolioGroupSection({
    required this.title,
    required this.subtitle,
    required this.entries,
  });

  final String title;
  final String subtitle;
  final List<LearningPortfolioEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: DS.titleLarge.copyWith(fontWeight: DS.fontWeightBold),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          subtitle,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing10),
        if (entries.isEmpty)
          GraphiteCardSurface(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Text(
                '这一组里暂时还没有冲刺记录。',
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ),
          )
        else
          ...entries.map(
            (LearningPortfolioEntry entry) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing12),
              child: _PortfolioEntryCard(entry: entry),
            ),
          ),
      ],
    );
  }
}

class _PortfolioEntryCard extends StatelessWidget {
  const _PortfolioEntryCard({required this.entry});

  final LearningPortfolioEntry entry;

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing10,
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing16,
          ),
          title: Text(
            entry.subject.isEmpty ? entry.planName : entry.subject,
            style: DS.titleMedium.copyWith(fontWeight: DS.fontWeightBold),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: DS.spacing6),
            child: Text(
              _statusLine(entry),
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
          ),
          trailing: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing10,
              vertical: DS.spacing8,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFF3F5F1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFD8DED3)),
            ),
            child: Text(
              '掌握 ${entry.masteredNodesCount} 节点',
              style: DS.labelLarge.copyWith(
                color: const Color(0xFF355543),
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Galaxy 掌握度摘要',
                style: DS.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
            if ((entry.headline ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                entry.headline!,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ],
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _DetailChip(label: _scoreLabel(entry)),
                _DetailChip(label: _modeLabel(entry.sprintMode)),
                if (entry.resultRating != null)
                  _DetailChip(label: '结果评分 ${entry.resultRating}/5'),
                if (entry.selfRating != null)
                  _DetailChip(label: '自评 ${entry.selfRating}/10'),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            _DetailRow(
              title: '最薄弱的点',
              content: _joinDetails(
                entry.weakestPoints.isNotEmpty
                    ? entry.weakestPoints
                    : <String>[
                        ...?[
                          entry.growthArea,
                        ].whereType<String>()
                      ],
                fallback: '这一轮还没有记录到明显薄弱点',
              ),
            ),
            const SizedBox(height: DS.spacing10),
            _DetailRow(
              title: '值得引以为豪的节点',
              content: _joinDetails(
                entry.proudNodes.isNotEmpty
                    ? entry.proudNodes
                    : <String>[
                        ...?[
                          entry.strongestArea,
                        ].whereType<String>()
                      ],
                fallback: '继续推进后，这里会累计你最亮眼的节点',
              ),
            ),
            if ((entry.resultDescription ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              _DetailRow(
                title: '成绩备注',
                content: entry.resultDescription!,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DetailChip extends StatelessWidget {
  const _DetailChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F4EC),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFE2D8C4)),
      ),
      child: Text(
        label,
        style: DS.bodySmall.copyWith(
          color: const Color(0xFF6A5740),
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.title,
    required this.content,
  });

  final String title;
  final String content;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: DS.labelLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          content,
          style: DS.bodyMedium.copyWith(color: DS.textSecondary),
        ),
      ],
    );
  }
}

class _PortfolioEmptyState extends StatelessWidget {
  const _PortfolioEmptyState({required this.onStartSprint});

  final VoidCallback onStartSprint;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5EF),
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFFD5DED1)),
              ),
              child: const Icon(
                Icons.library_books_outlined,
                size: 34,
                color: Color(0xFF5A7563),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '你的学习档案还没有任何冲刺记录',
              textAlign: TextAlign.center,
              style: DS.titleLarge.copyWith(fontWeight: DS.fontWeightBold),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '先创建一门考试冲刺吧。之后每次完成、进行中和计划中的科目，都会在这里自动归档。',
              textAlign: TextAlign.center,
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing20),
            SparkleButton(
              onPressed: onStartSprint,
              label: '去创建考试冲刺',
            ),
          ],
        ),
      ),
    );
  }
}

class _PortfolioErrorState extends StatelessWidget {
  const _PortfolioErrorState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Text(
          '学习档案加载失败：$message',
          textAlign: TextAlign.center,
          style: DS.bodyMedium.copyWith(color: DS.textSecondary),
        ),
      ),
    );
  }
}

String _statusLine(LearningPortfolioEntry entry) {
  final mode = _modeLabel(entry.sprintMode);
  if (entry.isCompleted) {
    final completedOn = _formatDate(entry.completedAt ?? entry.targetDate);
    return '$mode（已完成，$completedOn）';
  }
  if (entry.isActive) {
    final totalDays = _totalDays(entry);
    final currentDay = _currentDay(entry, totalDays);
    final remainingDays = totalDays == null ? null : (totalDays - currentDay);
    if (remainingDays != null) {
      return '$mode · 进行中（第 $currentDay 天，还剩 $remainingDays 天）';
    }
    return '$mode · 进行中';
  }
  return '$mode · 计划中';
}

String _scoreLabel(LearningPortfolioEntry entry) {
  if ((entry.resultDescription ?? '').trim().isNotEmpty) {
    return entry.resultDescription!;
  }
  if (entry.currentScore != null) {
    return '成绩 ${entry.currentScore!.round()} 分';
  }
  return '成绩待记录';
}

String _modeLabel(String? sprintMode) {
  switch (sprintMode) {
    case 'last_24h_cram':
      return '24小时抢救';
    case 'seven_day_survival':
      return '7天冲刺';
    case 'fourteen_day_build_and_retrieve':
      return '14天冲刺';
    case 'standard_exam_sprint':
      return '标准冲刺';
    default:
      return '考试冲刺';
  }
}

String _formatDate(DateTime? value) {
  if (value == null) {
    return '日期待定';
  }
  final local = value.toLocal();
  final year = local.year.toString().padLeft(4, '0');
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  return '$year-$month-$day';
}

String _joinDetails(List<String> values, {required String fallback}) {
  final sanitized = values
      .map((String item) => item.trim())
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
  if (sanitized.isEmpty) {
    return fallback;
  }
  return sanitized.join('、');
}

int? _totalDays(LearningPortfolioEntry entry) {
  if (entry.startedAt == null || entry.targetDate == null) {
    return null;
  }
  return entry.targetDate!
          .difference(
            DateTime(
              entry.startedAt!.year,
              entry.startedAt!.month,
              entry.startedAt!.day,
            ),
          )
          .inDays +
      1;
}

int _currentDay(LearningPortfolioEntry entry, int? totalDays) {
  if (totalDays == null) {
    return 1;
  }
  if (entry.progress <= 0) {
    return 1;
  }
  final current = (entry.progress * totalDays).round();
  if (current < 1) {
    return 1;
  }
  if (current > totalDays) {
    return totalDays;
  }
  return current;
}
