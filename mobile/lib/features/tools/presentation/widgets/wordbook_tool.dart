// ignore_for_file: avoid_dynamic_calls, unawaited_futures, discarded_futures

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/vocabulary/data/repositories/local_vocabulary_repository.dart';
import 'package:sparkle/features/vocabulary/presentation/providers/local_vocabulary_provider.dart';

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
  List<VocabWordItem> _sessionWords = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _searchController.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _startReview() {
    final dueWords = ref.read(localVocabularyProvider).dueWords;
    if (dueWords.isEmpty) {
      return;
    }

    setState(() {
      _sessionWords = List.from(dueWords);
      _isReviewMode = true;
      _currentReviewIndex = 0;
      _showAnswer = false;
    });
  }

  Future<void> _handleReview(bool remembered) async {
    if (_currentReviewIndex < _sessionWords.length) {
      final word = _sessionWords[_currentReviewIndex];
      final startTime = DateTime.now();
      await ref.read(localVocabularyProvider.notifier).recordReview(
            word.id,
            remembered,
            responseTimeMs: DateTime.now().difference(startTime).inMilliseconds,
          );
      if (!mounted) {
        return;
      }
      HapticFeedback.lightImpact();
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

  void _showImportanceDialog(VocabWordItem word) {
    var selectedImportance = word.importance;

    showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('设置重要程度'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                word.word,
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
                      label: '$starValue 星',
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
              label: '取消',
              onPressed: () => Navigator.pop(context),
            ),
            SparkleButton(
              label: '保存',
              onPressed: () async {
                await ref
                    .read(localVocabularyProvider.notifier)
                    .updateImportance(word.id, selectedImportance);
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
    final state = ref.watch(localVocabularyProvider);
    return _isReviewMode
        ? _buildReviewMode()
        : ToolShell(
            surface: widget.surface,
            icon: Icons.menu_book_rounded,
            title: '生词本',
            subtitle: '把查词结果变成可复习资产。支持搜索、重要度筛选和快闪式复习。',
            accentColor: DS.success,
            fillHeight: true,
            heroChips: [
              ToolHeroChip(
                label: '${state.totalCount} 个词条',
                accentColor: DS.success,
                icon: Icons.bookmarks_rounded,
              ),
              ToolHeroChip(
                label: '${state.dueCount} 个待复习',
                accentColor: DS.success,
                icon: Icons.schedule_rounded,
              ),
            ],
            body: Column(
              children: [
                Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing12,
                  children: [
                    ToolMetricCard(
                      label: '总词条',
                      value: '${state.totalCount}',
                      accentColor: DS.success,
                      icon: Icons.library_books_rounded,
                    ),
                    ToolMetricCard(
                      label: '待复习',
                      value: '${state.dueCount}',
                      accentColor: DS.warning,
                      icon: Icons.pending_actions_rounded,
                    ),
                    ToolMetricCard(
                      label: '高重要度',
                      value: '${state.statistics['highImportance'] as int? ?? 0}',
                      accentColor: DS.warning,
                      icon: Icons.star_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                ToolSectionCard(
                  accentColor: DS.success,
                  title: '筛选与搜索',
                  subtitle: '先用筛选缩小范围，再用搜索定位具体词条。',
                  child: Column(
                    children: [
                      TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          hintText: '搜索单词或释义',
                          prefixIcon: const Icon(Icons.search_rounded),
                          suffixIcon: _searchController.text.isEmpty
                              ? null
                              : IconButton(
                                  onPressed: () {
                                    _searchController.clear();
                                    ref
                                        .read(localVocabularyProvider.notifier)
                                        .clearSearch();
                                    setState(() {});
                                  },
                                  icon: const Icon(Icons.close_rounded),
                                ),
                        ),
                        onChanged:
                            ref.read(localVocabularyProvider.notifier).search,
                      ),
                      const SizedBox(height: DS.spacing16),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Wrap(
                          spacing: DS.spacing10,
                          runSpacing: DS.spacing10,
                          children: [
                            ToolChoiceChip(
                              label: '全部',
                              selected: state.filter == VocabFilter.all,
                              onTap: () => ref
                                  .read(localVocabularyProvider.notifier)
                                  .setFilter(VocabFilter.all),
                              accentColor: DS.success,
                            ),
                            ToolChoiceChip(
                              label: '待复习',
                              selected:
                                  state.filter == VocabFilter.dueForReview,
                              onTap: () => ref
                                  .read(localVocabularyProvider.notifier)
                                  .setFilter(VocabFilter.dueForReview),
                              accentColor: DS.warning,
                              icon: Icons.schedule_rounded,
                            ),
                            ToolChoiceChip(
                              label: '重要词',
                              selected:
                                  state.filter == VocabFilter.highImportance,
                              onTap: () => ref
                                  .read(localVocabularyProvider.notifier)
                                  .setFilter(VocabFilter.highImportance),
                              accentColor: DS.warning,
                              icon: Icons.star_rounded,
                            ),
                          ],
                        ),
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
                    tabs: [
                      Tab(text: '待复习 (${state.dueCount})'),
                      Tab(text: '全部 (${state.totalCount})'),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildWordList(state.dueWords, isReviewList: true),
                      _buildWordList(state.words, isReviewList: false),
                    ],
                  ),
                ),
              ],
            ),
            footer: state.dueCount == 0
                ? null
                : SparkleButton(
                    label: '开始复习',
                    onPressed: _startReview,
                    icon: const Icon(Icons.play_arrow_rounded),
                    expand: true,
                  ),
          );
  }

  Widget _buildWordList(List<VocabWordItem> words, {required bool isReviewList}) {
    if (words.isEmpty) {
      return ToolSectionCard(
        accentColor: isReviewList ? DS.warning : DS.success,
        child: ToolEmptyState(
          icon: isReviewList
              ? Icons.check_circle_outline_rounded
              : Icons.library_books_outlined,
          title: isReviewList ? '当前没有待复习单词' : '生词本还是空的',
          description: isReviewList
              ? '继续通过查词工具积累新词，或者稍后再来复习。'
              : '先去查词，把值得反复看的词条收进来。',
          accentColor: isReviewList ? DS.warning : DS.success,
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
            final confirmed = await showDialog<bool>(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text('删除单词'),
                content: Text('确定要从生词本中删除 "${word.word}" 吗？'),
                actions: [
                  SparkleButton.ghost(
                    label: '取消',
                    onPressed: () => Navigator.pop(context, false),
                  ),
                  SparkleButton.destructive(
                    label: '删除',
                    onPressed: () => Navigator.pop(context, true),
                  ),
                ],
              ),
            );
            if ((confirmed ?? false) && mounted) {
              await ref.read(localVocabularyProvider.notifier).delete(word.id);
            }
          },
        );
      },
    );
  }

  Widget _buildReviewMode() {
    final word = _sessionWords[_currentReviewIndex];

    return ToolShell(
      surface: widget.surface,
      icon: Icons.auto_stories_rounded,
      title: '复习模式',
      subtitle: '以快闪卡片方式确认是否记住当前词条。',
      accentColor: DS.warning,
      heroChips: [
        ToolHeroChip(
          label: '${_currentReviewIndex + 1} / ${_sessionWords.length}',
          accentColor: DS.warning,
          icon: Icons.layers_rounded,
        ),
        ToolHeroChip(
          label: _showAnswer ? '答案已展开' : '点击卡片看答案',
          accentColor: DS.warning,
          icon: Icons.visibility_rounded,
        ),
      ],
      body: Column(
        children: [
          Expanded(
            child: ToolSectionCard(
              accentColor: _showAnswer ? DS.success : DS.warning,
              fillHeight: true,
              title: word.word,
              subtitle: word.phonetic,
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
                            _showAnswer ? word.definition ?? '暂无释义' : '点击显示释义',
                            textAlign: TextAlign.center,
                            style:
                                Theme.of(context).textTheme.headlineSmall?.copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: DS.fontWeightBold,
                                      height: 1.35,
                                    ),
                          ),
                          if (_showAnswer && word.exampleSentence != null) ...[
                            const SizedBox(height: DS.spacing16),
                            Text(
                              word.exampleSentence!,
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
      footer: _showAnswer
          ? Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    label: '不认识',
                    variant: ButtonVariant.ghost,
                    onPressed: () => _handleReview(false),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: SparkleButton(
                    label: '认识',
                    onPressed: () => _handleReview(true),
                    icon: const Icon(Icons.check_rounded),
                  ),
                ),
              ],
            )
          : Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    label: '退出复习',
                    variant: ButtonVariant.ghost,
                    onPressed: () => setState(() => _isReviewMode = false),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: SparkleButton(
                    label: '显示答案',
                    onPressed: () => setState(() => _showAnswer = true),
                    icon: const Icon(Icons.visibility_rounded),
                  ),
                ),
              ],
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

  final VocabWordItem word;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => ToolSectionCard(
        accentColor: word.isDueForReview ? DS.warning : DS.success,
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
                        word.word,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      if (word.phonetic != null) ...[
                        const SizedBox(height: DS.spacing4),
                        Text(
                          word.phonetic!,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: DS.textSecondary,
                                fontStyle: FontStyle.italic,
                              ),
                        ),
                      ],
                      const SizedBox(height: DS.spacing8),
                      Text(
                        word.definition ?? '暂无释义',
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
                            label: word.isDueForReview
                                ? '今天到期'
                                : '还有 ${word.daysUntilReview ?? 0} 天',
                            accentColor:
                                word.isDueForReview ? DS.warning : DS.success,
                            icon: Icons.schedule_rounded,
                          ),
                          ToolHeroChip(
                            label: '重要度 ${word.importance}',
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
