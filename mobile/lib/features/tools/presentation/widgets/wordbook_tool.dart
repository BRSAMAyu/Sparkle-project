// ignore_for_file: avoid_dynamic_calls, unawaited_futures, discarded_futures

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/features/vocabulary/data/repositories/local_vocabulary_repository.dart';
import 'package:sparkle/features/vocabulary/presentation/providers/local_vocabulary_provider.dart';

/// 生词本工具 - 查看和复习生词 (本地存储版本)
class WordbookTool extends ConsumerStatefulWidget {
  const WordbookTool({super.key});

  @override
  ConsumerState<WordbookTool> createState() => _WordbookToolState();
}

class _WordbookToolState extends ConsumerState<WordbookTool>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isReviewMode = false;
  int _currentReviewIndex = 0;
  bool _showAnswer = false;
  List<VocabWordItem> _sessionWords = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _startReview() {
    final dueWords = ref.read(localVocabularyProvider).dueWords;
    if (dueWords.isEmpty) return;

    setState(() {
      _sessionWords = List.from(dueWords); // Create snapshot for session
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

      HapticFeedback.lightImpact();
    }

    // Advance to next word in session
    if (_currentReviewIndex >= _sessionWords.length - 1) {
      // Review complete
      setState(() {
        _isReviewMode = false;
        _sessionWords = [];
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_getReviewCompletionMessage()),
            backgroundColor: DS.success,
          ),
        );
      }
    } else {
      setState(() {
        _currentReviewIndex++;
        _showAnswer = false;
      });
    }
  }

  String _getReviewCompletionMessage() {
    // We can check the *actual* remaining count from provider if we want,
    // or just say "Session Complete".
    // The provider's dueCount might still have items if we didn't review all of them in one go?
    // But _startReview takes ALL due words.
    return '复习完成！';
  }

  void _showImportanceDialog(VocabWordItem word) {
    var selectedImportance = word.importance;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('设置重要程度'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                word.word,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: DS.lg),
              const Text('选择重要程度'),
              const SizedBox(height: DS.md),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final starValue = index + 1;
                  return Column(
                    children: [
                      GestureDetector(
                        onTap: () {
                          setDialogState(() {
                            selectedImportance = starValue;
                          });
                        },
                        child: Icon(
                          Icons.star,
                          size: 36,
                          color: selectedImportance >= starValue
                              ? Colors.amber
                              : DS.neutral300,
                        ),
                      ),
                      Text(
                        '$starValue',
                        style: TextStyle(
                          fontSize: 10,
                          color: DS.neutral600,
                        ),
                      ),
                    ],
                  );
                }),
              ),
              const SizedBox(height: DS.md),
              Text(
                _getImportanceLabel(selectedImportance),
                style: TextStyle(
                  fontSize: 12,
                  color: DS.neutral500,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () async {
                await ref
                    .read(localVocabularyProvider.notifier)
                    .updateImportance(word.id, selectedImportance);
                if (mounted) Navigator.pop(context);
              },
              child: const Text('确定'),
            ),
          ],
        ),
      ),
    );
  }

  String _getImportanceLabel(int importance) {
    switch (importance) {
      case 1:
        return '偶尔需要';
      case 2:
        return '不太重要';
      case 3:
        return '一般';
      case 4:
        return '比较重要';
      case 5:
        return '非常重要';
      default:
        return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(localVocabularyProvider);

    if (_isReviewMode) {
      return _buildReviewMode(state);
    }

    return Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: DS.success.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child:
                    Icon(Icons.menu_book_rounded, color: DS.success, size: 24),
              ),
              const SizedBox(width: DS.md),
              Text(
                '生词本',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const Spacer(),
              // Review count badge
              if (state.dueCount > 0)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: DS.warning,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${state.dueCount} 待复习',
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.lg),

          // Filter chips
          if (state.totalCount > 0)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _FilterChip(
                    label: '全部',
                    count: state.totalCount,
                    isSelected: state.filter == VocabFilter.all,
                    onTap: () => ref
                        .read(localVocabularyProvider.notifier)
                        .setFilter(VocabFilter.all),
                  ),
                  const SizedBox(width: DS.sm),
                  _FilterChip(
                    label: '待复习',
                    count: state.dueCount,
                    isSelected: state.filter == VocabFilter.dueForReview,
                    onTap: () => ref
                        .read(localVocabularyProvider.notifier)
                        .setFilter(VocabFilter.dueForReview),
                  ),
                  const SizedBox(width: DS.sm),
                  _FilterChip(
                    label: '重要',
                    count: state.statistics['highImportance'] as int? ?? 0,
                    isSelected: state.filter == VocabFilter.highImportance,
                    icon: Icons.star,
                    onTap: () => ref
                        .read(localVocabularyProvider.notifier)
                        .setFilter(VocabFilter.highImportance),
                  ),
                ],
              ),
            ),

          const SizedBox(height: DS.lg),

          // Tab Bar
          DecoratedBox(
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: TabBar(
              controller: _tabController,
              indicator: BoxDecoration(
                color: DS.brandPrimaryConst,
                borderRadius: BorderRadius.circular(10),
                boxShadow: DS.shadowSm,
              ),
              indicatorSize: TabBarIndicatorSize.tab,
              labelColor: DS.success,
              unselectedLabelColor: DS.neutral500,
              dividerColor: Colors.transparent,
              tabs: [
                Tab(text: '待复习 (${state.dueCount})'),
                Tab(text: '全部 (${state.totalCount})'),
              ],
            ),
          ),
          const SizedBox(height: DS.lg),

          // Content
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _buildWordList(state.dueWords, isReviewList: true),
                      _buildWordList(state.words, isReviewList: false),
                    ],
                  ),
          ),

          // Start Review Button
          if (state.dueCount > 0)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: CustomButton.primary(
                text: '开始复习',
                icon: Icons.play_arrow_rounded,
                onPressed: _startReview,
                customGradient: LinearGradient(
                  colors: [DS.successConst, const Color(0xFF66BB6A)],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildWordList(List<VocabWordItem> words, {required bool isReviewList}) {
    if (words.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isReviewList
                  ? Icons.check_circle_outline_rounded
                  : Icons.library_books_outlined,
              size: 64,
              color: isReviewList
                  ? DS.success.withValues(alpha: 0.5)
                  : DS.neutral300,
            ),
            const SizedBox(height: DS.lg),
            Text(
              isReviewList ? '太棒了！暂无待复习单词' : '生词本空空如也',
              style: TextStyle(
                color: DS.neutral500,
                fontSize: 16,
              ),
            ),
            if (!isReviewList) ...[
              const SizedBox(height: DS.sm),
              Text(
                '使用查词工具添加生词',
                style: TextStyle(
                  color: DS.neutral400,
                  fontSize: 14,
                ),
              ),
            ],
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: words.length,
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
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('取消'),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    style: FilledButton.styleFrom(backgroundColor: DS.error),
                    child: const Text('删除'),
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

  Widget _buildReviewMode(LocalVocabularyState state) {
    if (_currentReviewIndex >= _sessionWords.length) {
      return const SizedBox.shrink();
    }

    final word = _sessionWords[_currentReviewIndex];

    return Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        children: [
          // Progress
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => setState(() => _isReviewMode = false),
              ),
              Text(
                '${_currentReviewIndex + 1} / ${_sessionWords.length}',
                style: TextStyle(
                  color: DS.neutral500,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(width: DS.xxxl),
            ],
          ),
          const SizedBox(height: DS.xxl),

          // Flashcard
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _showAnswer = true),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.xl),
                decoration: BoxDecoration(
                  gradient: _showAnswer
                      ? const LinearGradient(
                          colors: [Color(0xFFE8F5E9), Color(0xFFC8E6C9)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        )
                      : const LinearGradient(
                          colors: [Color(0xFFFFF8E1), Color(0xFFFFECB3)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: DS.shadowMd,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      word.word,
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: DS.fontWeightBold,
                              ),
                    ),
                    if (word.phonetic != null) ...[
                      const SizedBox(height: DS.sm),
                      Text(
                        word.phonetic!,
                        style: TextStyle(
                          color: DS.neutral500,
                          fontSize: 18,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ],
                    const SizedBox(height: DS.xl),
                    if (_showAnswer) ...[
                      Container(
                        width: 60,
                        height: 2,
                        color: DS.neutral300,
                      ),
                      const SizedBox(height: DS.xl),
                      Text(
                        word.definition ?? '暂无释义',
                        style: const TextStyle(
                          fontSize: 18,
                          height: 1.5,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      if (word.exampleSentence != null) ...[
                        const SizedBox(height: DS.md),
                        Text(
                          word.exampleSentence!,
                          style: TextStyle(
                            color: DS.neutral600,
                            fontSize: 14,
                            fontStyle: FontStyle.italic,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ] else ...[
                      Text(
                        '点击显示释义',
                        style: TextStyle(
                          color: DS.neutral400,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: DS.xl),

          // Review buttons
          if (_showAnswer)
            Row(
              children: [
                Expanded(
                  child: CustomButton.secondary(
                    text: '不认识',
                    icon: Icons.close_rounded,
                    onPressed: () => _handleReview(false),
                    size: CustomButtonSize.large,
                  ),
                ),
                const SizedBox(width: DS.lg),
                Expanded(
                  child: CustomButton.primary(
                    text: '认识',
                    icon: Icons.check_rounded,
                    onPressed: () => _handleReview(true),
                    customGradient: DS.successGradient,
                    size: CustomButtonSize.large,
                  ),
                ),
              ],
            )
          else
            CustomButton.primary(
              text: '显示答案',
              icon: Icons.visibility_rounded,
              onPressed: () => setState(() => _showAnswer = true),
              size: CustomButtonSize.large,
            ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.count,
    this.icon,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final int? count;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? DS.success : DS.neutral100,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? DS.success : DS.neutral200,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 16,
                color: isSelected ? DS.brandPrimaryConst : DS.neutral600,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: TextStyle(
                color: isSelected ? DS.brandPrimaryConst : DS.neutral700,
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
            if (count != null) ...[
              const SizedBox(width: 4),
              Text(
                '($count)',
                style: TextStyle(
                  color: isSelected ? DS.brandPrimaryConst : DS.neutral600,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
}

/// 单词卡片组件 (本地版本)
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
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: 12),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: DS.neutral200),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            word.word,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (word.phonetic != null) ...[
                            const SizedBox(width: DS.sm),
                            Text(
                              word.phonetic!,
                              style: TextStyle(
                                color: DS.neutral500,
                                fontSize: 14,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: DS.xs),
                      Text(
                        word.definition ?? '暂无释义',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: DS.neutral600,
                          fontSize: 14,
                        ),
                      ),
                      if (word.daysUntilReview != null) ...[
                        const SizedBox(height: DS.sm),
                        Text(
                          word.isDueForReview ? '今天到期' : '还有 ${word.daysUntilReview} 天',
                          style: TextStyle(
                            color: word.isDueForReview ? DS.warning : DS.neutral400,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Importance stars
                GestureDetector(
                  onTap: onTap,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(5, (index) => Icon(
                        Icons.star,
                        size: 16,
                        color: index < word.importance ? Colors.amber : DS.neutral300,
                      ),),
                  ),
                ),
                const SizedBox(width: DS.sm),
                IconButton(
                  iconSize: 18,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  icon: Icon(
                    Icons.delete_outline,
                    color: DS.error.withValues(alpha: 0.7),
                  ),
                  onPressed: onDelete,
                ),
              ],
            ),
          ),
        ),
      );
}
