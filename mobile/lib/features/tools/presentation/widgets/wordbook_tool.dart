// ignore_for_file: avoid_dynamic_calls, unawaited_futures, discarded_futures

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/knowledge/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class WordbookTool extends ConsumerStatefulWidget {
  const WordbookTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  ConsumerState<WordbookTool> createState() => _WordbookToolState();
}

class _WordbookToolState extends ConsumerState<WordbookTool>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final TextEditingController _searchController = TextEditingController();

  bool _isReviewMode = false;
  int _currentReviewIndex = 0;
  bool _showAnswer = false;
  List<Map<String, dynamic>> _sessionWords = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _reloadVocabularyData();
    });
    _searchController.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
  }

  Future<void> _reloadVocabularyData({String? search}) async {
    if (!mounted) return;
    final notifier = ref.read(vocabularyProvider.notifier);
    await Future.wait([
      notifier.fetchWordbook(search: search),
      notifier.fetchReviewList(),
      notifier.fetchStats(),
    ]);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _startReview() {
    final dueWords = ref.read(vocabularyProvider).reviewList;
    if (dueWords.isEmpty) {
      return;
    }

    setState(() {
      _sessionWords = dueWords
          .whereType<Map<String, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
      _isReviewMode = true;
      _currentReviewIndex = 0;
      _showAnswer = false;
    });
  }

  Future<void> _handleReview(bool remembered) async {
    if (_currentReviewIndex < _sessionWords.length) {
      final word = _sessionWords[_currentReviewIndex];
      await ref
          .read(vocabularyProvider.notifier)
          .recordReview(word['id'] as String, remembered);
      if (!mounted) {
        return;
      }
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    }

    if (_currentReviewIndex >= _sessionWords.length - 1) {
      setState(() {
        _isReviewMode = false;
        _sessionWords = [];
      });
      AppFeedback.success(context, '本轮复习已完成');
      return;
    }

    setState(() {
      _currentReviewIndex++;
      _showAnswer = false;
    });
  }

  void _showImportanceDialog(Map<String, dynamic> word) {
    var selectedImportance = (word['importance'] as int?) ?? 3;

    showSensoryDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text(context.l10n.toolsWbSetImportance),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                word['word'] as String? ?? '',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              Wrap(
                spacing: DS.spacing8,
                children: List.generate(
                  5,
                  (index) {
                    final starValue = index + 1;
                    return ToolChoiceChip(
                      label: context.l10n.toolsWbStarCount,
                      selected: selectedImportance == starValue,
                      onTap: () {
                        setDialogState(() {
                          selectedImportance = starValue;
                        });
                      },
                      accentColor: DS.warning,
                      icon: Icons.star_rounded,
                    );
                  },
                ),
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              label: context.l10n.toolsWbCancel,
              onPressed: () => Navigator.pop(context),
            ),
            SparkleButton(
              label: context.l10n.toolsWbSave,
              onPressed: () async {
                await ref
                    .read(vocabularyProvider.notifier)
                    .updateImportance(word['id'] as String, selectedImportance);
                if (context.mounted) {
                  Navigator.of(context).pop();
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(vocabularyProvider);
    final stats = state.stats;
    final allWords = state.wordbook
        .whereType<Map<String, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final dueWords = state.reviewList
        .whereType<Map<String, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final filteredAllWords = _filterWords(allWords);
    final filteredDueWords = _filterWords(dueWords);
    final dueCount = stats['due_for_review'] as int? ?? dueWords.length;
    final totalCount = stats['total_words'] as int? ?? allWords.length;
    final byImportance =
        (stats['by_importance'] as Map<String, dynamic>?) ?? const {};
    final highImportance =
        (byImportance['4'] as int? ?? 0) + (byImportance['5'] as int? ?? 0);
    return _isReviewMode
        ? _buildReviewMode()
        : ToolShell(
            surface: widget.surface,
            icon: Icons.menu_book_rounded,
            title: context.l10n.toolsWbTitle,
            subtitle: context.l10n.toolsWbSubtitle,
            accentColor: DS.success,
            compactHeader: true,
            heroChips: [
              ToolHeroChip(
                label: context.l10n.toolsWbTotalCount,
                accentColor: DS.success,
                icon: Icons.bookmarks_rounded,
              ),
              ToolHeroChip(
                label: context.l10n.toolsWbDueCount,
                accentColor: DS.success,
                icon: Icons.schedule_rounded,
              ),
            ],
            body: Column(
              children: [
                ToolMetricRow(
                  children: [
                    ToolMetricCard(
                      label: context.l10n.toolsWbTotal,
                      value: '$totalCount',
                      accentColor: DS.success,
                      icon: Icons.library_books_rounded,
                    ),
                    ToolMetricCard(
                      label: context.l10n.toolsWbDue,
                      value: '$dueCount',
                      accentColor: DS.warning,
                      icon: Icons.pending_actions_rounded,
                    ),
                    ToolMetricCard(
                      label: context.l10n.toolsWbHighImportance,
                      value: '$highImportance',
                      accentColor: DS.warning,
                      icon: Icons.star_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                ToolSectionCard(
                  accentColor: DS.success,
                  title: context.l10n.toolsWbFilter,
                  subtitle: context.l10n.toolsWbFilterDesc,
                  child: Column(
                    children: [
                      TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          hintText: context.l10n.toolsWbSearchHint,
                          prefixIcon: const Icon(Icons.search_rounded),
                          suffixIcon: _searchController.text.isEmpty
                              ? null
                              : IconButton(
                                  onPressed: () {
                                    _searchController.clear();
                                    _reloadVocabularyData();
                                    setState(() {});
                                  },
                                  icon: const Icon(Icons.close_rounded),
                                ),
                        ),
                        onChanged: (value) {
                          _reloadVocabularyData(search: value);
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: DS.success.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: DS.success.withValues(alpha: 0.28),
                      ),
                    ),
                    labelColor: DS.textPrimary,
                    unselectedLabelColor: DS.textSecondary,
                    dividerColor: Colors.transparent,
                    tabs: const [
                      Tab(text: context.l10n.toolsWbDue),
                      Tab(text: context.l10n.toolsWbAll),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                SizedBox(
                  height:
                      (MediaQuery.sizeOf(context).height * 0.4).clamp(280, 420),
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildWordList(filteredDueWords, isReviewList: true),
                      _buildWordList(filteredAllWords, isReviewList: false),
                    ],
                  ),
                ),
              ],
            ),
            footer: dueCount == 0
                ? null
                : SparkleButton(
                    label: context.l10n.toolsWbStartReview,
                    onPressed: _startReview,
                    icon: const Icon(Icons.play_arrow_rounded),
                    expand: true,
                  ),
          );
  }

  List<Map<String, dynamic>> _filterWords(List<Map<String, dynamic>> words) {
    final query = _searchController.text.trim().toLowerCase();
    if (query.isEmpty) {
      return words;
    }
    return words.where((word) {
      final text = [
        word['word'],
        word['definition'],
        word['phonetic'],
      ].whereType<String>().join(' ').toLowerCase();
      return text.contains(query);
    }).toList();
  }

  Widget _buildWordList(
    List<Map<String, dynamic>> words, {
    required bool isReviewList,
  }) {
    if (words.isEmpty) {
      return SingleChildScrollView(
        child: ToolSectionCard(
          accentColor: isReviewList ? DS.warning : DS.success,
          child: ToolEmptyState(
            icon: isReviewList
                ? Icons.check_circle_outline_rounded
                : Icons.library_books_outlined,
            title: isReviewList ? context.l10n.toolsWbEmptyNoDue : context.l10n.toolsWbEmpty,
            description:
                isReviewList ? '继续通过查词工具积累新词，或者稍后再来复习。' : '先去查词，把值得反复看的词条收进来。',
            accentColor: isReviewList ? DS.warning : DS.success,
          ),
        ),
      );
    }

    return ListView.separated(
      itemCount: words.length,
      separatorBuilder: (_, __) => const SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) {
        final word = words[index];
        return _WordCard(
          word: word,
          onTap: () => _showImportanceDialog(word),
          onDelete: () async {
            final confirmed = await showSensoryDialog<bool>(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text(context.l10n.toolsWbDeleteTitle),
                content: Text('${context.l10n.toolsWbDeleteConfirm} "${word['word']}"${context.l10n.toolsWbDeleteSuffix}'),
                actions: [
                  SparkleButton.ghost(
                    label: context.l10n.toolsWbCancel,
                    onPressed: () => Navigator.pop(context, false),
                  ),
                  SparkleButton.destructive(
                    label: context.l10n.toolsWbDelete,
                    onPressed: () => Navigator.pop(context, true),
                  ),
                ],
              ),
            );
            if ((confirmed ?? false) && mounted) {
              await ref
                  .read(vocabularyProvider.notifier)
                  .deleteWordbookEntry(word['id'] as String);
            }
          },
        );
      },
    );
  }

  Widget _buildReviewMode() {
    final word = _sessionWords[_currentReviewIndex];
    final phonetic = word['phonetic'] as String?;
    final definition = word['definition'] as String?;
    final exampleSentence = word['context_sentence'] as String?;

    return ToolShell(
      surface: widget.surface,
      icon: Icons.auto_stories_rounded,
      title: context.l10n.toolsWbReviewMode,
      subtitle: context.l10n.toolsWbReviewDesc,
      accentColor: DS.warning,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: '${_currentReviewIndex + 1} / ${_sessionWords.length}',
          accentColor: DS.warning,
          icon: Icons.layers_rounded,
        ),
        ToolHeroChip(
          label: _showAnswer ? context.l10n.toolsWbAnswerRevealed : context.l10n.toolsWbTapForAnswer,
          accentColor: DS.warning,
          icon: Icons.visibility_rounded,
        ),
      ],
      body: Column(
        children: [
          SizedBox(
            height: (MediaQuery.sizeOf(context).height * 0.35).clamp(240, 360),
            child: ToolSectionCard(
              accentColor: _showAnswer ? DS.success : DS.warning,
              title: word['word'] as String? ?? '',
              subtitle: phonetic,
              child: InkWell(
                onTap: () => setState(() => _showAnswer = true),
                borderRadius: BorderRadius.circular(24),
                child: Ink(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: _showAnswer
                          ? [
                              DS.success.withValues(alpha: 0.18),
                              DS.success.withValues(alpha: 0.08),
                            ]
                          : [
                              DS.warning.withValues(alpha: 0.18),
                              DS.warning.withValues(alpha: 0.08),
                            ],
                    ),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            _showAnswer ? (definition ?? '暂无释义') : '点击显示释义',
                            textAlign: TextAlign.center,
                            style: Theme.of(context)
                                .textTheme
                                .headlineSmall
                                ?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                  height: 1.35,
                                ),
                          ),
                          if (_showAnswer && exampleSentence != null) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              exampleSentence,
                              textAlign: TextAlign.center,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.6,
                                  ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final actions = _showAnswer
              ? <Widget>[
                  SparkleButton(
                    label: context.l10n.toolsWbDontKnow,
                    variant: ButtonVariant.ghost,
                    onPressed: () => _handleReview(false),
                    icon: const Icon(Icons.close_rounded),
                    expand: true,
                  ),
                  SparkleButton(
                    label: context.l10n.toolsWbKnow,
                    onPressed: () => _handleReview(true),
                    icon: const Icon(Icons.check_rounded),
                    expand: true,
                  ),
                ]
              : <Widget>[
                  SparkleButton(
                    label: context.l10n.toolsWbExitReview,
                    variant: ButtonVariant.ghost,
                    onPressed: () => setState(() => _isReviewMode = false),
                    expand: true,
                  ),
                  SparkleButton(
                    label: context.l10n.toolsWbShowAnswer,
                    onPressed: () => setState(() => _showAnswer = true),
                    icon: const Icon(Icons.visibility_rounded),
                    expand: true,
                  ),
                ];

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                actions[0],
                const SizedBox(height: DS.spacing12),
                actions[1],
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: actions[0]),
              const SizedBox(width: DS.spacing12),
              Expanded(child: actions[1]),
            ],
          );
        },
      ),
    );
  }
}

class _WordCard extends StatelessWidget {
  const _WordCard({
    required this.word,
    required this.onTap,
    required this.onDelete,
  });

  final Map<String, dynamic> word;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  bool get _isDueForReview {
    final raw = word['next_review_at'] as String?;
    if (raw == null) {
      return true;
    }
    final date = DateTime.tryParse(raw);
    if (date == null) {
      return true;
    }
    return !date.isAfter(DateTime.now());
  }

  int? get _daysUntilReview {
    final raw = word['next_review_at'] as String?;
    if (raw == null) {
      return null;
    }
    final date = DateTime.tryParse(raw);
    if (date == null) {
      return null;
    }
    return date.difference(DateTime.now()).inDays;
  }

  @override
  Widget build(BuildContext context) => ToolSectionCard(
        accentColor: _isDueForReview ? DS.warning : DS.success,
        child: Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: onTap,
                borderRadius: BorderRadius.circular(20),
                child: Padding(
                  padding: EdgeInsets.zero,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        word['word'] as String? ?? '',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      if ((word['phonetic'] as String?) != null) ...[
                        const SizedBox(height: DS.spacing4),
                        Text(
                          word['phonetic'] as String,
                          style:
                              Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: DS.textSecondary,
                                    fontStyle: FontStyle.italic,
                                  ),
                        ),
                      ],
                      const SizedBox(height: DS.spacing8),
                      Text(
                        word['definition'] as String? ?? '暂无释义',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.5,
                            ),
                      ),
                      const SizedBox(height: DS.spacing10),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          ToolHeroChip(
                            label: _isDueForReview
                                ? '今天到期'
                                : '还有 ${_daysUntilReview ?? 0} 天',
                            accentColor:
                                _isDueForReview ? DS.warning : DS.success,
                            icon: Icons.schedule_rounded,
                          ),
                          ToolHeroChip(
                            label: '重要度 ${word['importance'] ?? 3}',
                            accentColor: DS.warning,
                            icon: Icons.star_rounded,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: DS.spacing12),
            IconButton(
              onPressed: onDelete,
              icon: Icon(
                Icons.delete_outline_rounded,
                color: DS.error.withValues(alpha: 0.8),
              ),
            ),
          ],
        ),
      );
}
