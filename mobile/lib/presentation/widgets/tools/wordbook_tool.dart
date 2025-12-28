import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

/// 生词本工具 - 查看和复习生词
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

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    // 获取复习列表
    ref.read(vocabularyProvider.notifier).fetchReviewList();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _startReview() {
    setState(() {
      _isReviewMode = true;
      _currentReviewIndex = 0;
      _showAnswer = false;
    });
  }

  Future<void> _handleReview(bool success) async {
    final reviewList = ref.read(vocabularyProvider).reviewList;
    if (_currentReviewIndex < reviewList.length) {
      final word = reviewList[_currentReviewIndex];
      await ref.read(vocabularyProvider.notifier).recordReview(
        word['id'].toString(),
        success,
      );
      HapticFeedback.lightImpact();
    }

    // 移动到下一个
    final newList = ref.read(vocabularyProvider).reviewList;
    if (_currentReviewIndex >= newList.length) {
      // 复习完成
      setState(() {
        _isReviewMode = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('太棒了！今日复习完成'),
            backgroundColor: AppDesignTokens.success,
          ),
        );
      }
    } else {
      setState(() {
        _showAnswer = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(vocabularyProvider);

    if (_isReviewMode) {
      return _buildReviewMode(state);
    }

    return Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: const BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: BorderRadius.only(
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
                color: AppDesignTokens.neutral300,
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
                child: const Icon(Icons.menu_book_rounded, color: DS.success, size: 24),
              ),
              const SizedBox(width: DS.md),
              Text(
                '生词本',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: AppDesignTokens.fontWeightBold,
                ),
              ),
              const Spacer(),
              // Review count badge
              if (state.reviewList.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.warning,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${state.reviewList.length} 待复习',
                    style: const TextStyle(
                      color: DS.brandPrimary,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.lg),

          // Tab Bar
          DecoratedBox(
            decoration: BoxDecoration(
              color: AppDesignTokens.neutral100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: TabBar(
              controller: _tabController,
              indicator: BoxDecoration(
                color: DS.brandPrimary,
                borderRadius: BorderRadius.circular(10),
                boxShadow: AppDesignTokens.shadowSm,
              ),
              indicatorSize: TabBarIndicatorSize.tab,
              labelColor: DS.success,
              unselectedLabelColor: AppDesignTokens.neutral500,
              dividerColor: Colors.transparent,
              tabs: const [
                Tab(text: '待复习'),
                Tab(text: '全部'),
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
                      _buildReviewList(state.reviewList),
                      _buildAllWords(state.wordbook),
                    ],
                  ),
          ),

          // Start Review Button
          if (state.reviewList.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: CustomButton.primary(
                text: '开始复习',
                icon: Icons.play_arrow_rounded,
                onPressed: _startReview,
                customGradient: const LinearGradient(
                  colors: [DS.success, Color(0xFF66BB6A)],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildReviewList(List<dynamic> reviewList) {
    if (reviewList.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              size: 64,
              color: AppDesignTokens.success.withValues(alpha: 0.5),
            ),
            const SizedBox(height: DS.lg),
            const Text(
              '太棒了！暂无待复习单词',
              style: TextStyle(
                color: AppDesignTokens.neutral500,
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: reviewList.length,
      itemBuilder: (context, index) {
        final word = reviewList[index];
        return _WordCard(
          word: word['word'] ?? '',
          phonetic: word['phonetic'],
          definition: word['definition'] ?? '',
          dueText: _getDueText(word['next_review_at']),
          onTap: () => _startReviewAt(index),
        );
      },
    );
  }

  Widget _buildAllWords(List<dynamic> wordbook) {
    if (wordbook.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.library_books_outlined,
              size: 64,
              color: AppDesignTokens.neutral300,
            ),
            SizedBox(height: DS.lg),
            Text(
              '生词本空空如也',
              style: TextStyle(
                color: AppDesignTokens.neutral500,
                fontSize: 16,
              ),
            ),
            SizedBox(height: DS.sm),
            Text(
              '使用查词工具添加生词',
              style: TextStyle(
                color: AppDesignTokens.neutral400,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: wordbook.length,
      itemBuilder: (context, index) {
        final word = wordbook[index];
        return _WordCard(
          word: word['word'] ?? '',
          phonetic: word['phonetic'],
          definition: word['definition'] ?? '',
          masteryLevel: word['mastery_level'] ?? 0,
        );
      },
    );
  }

  void _startReviewAt(int index) {
    setState(() {
      _isReviewMode = true;
      _currentReviewIndex = index;
      _showAnswer = false;
    });
  }

  String _getDueText(String? nextReviewAt) {
    if (nextReviewAt == null) return '';
    try {
      final date = DateTime.parse(nextReviewAt);
      final now = DateTime.now();
      final diff = date.difference(now);

      if (diff.isNegative) {
        return '已到期';
      } else if (diff.inDays == 0) {
        return '今天到期';
      } else if (diff.inDays == 1) {
        return '明天到期';
      } else {
        return '${diff.inDays}天后';
      }
    } catch (_) {
      return '';
    }
  }

  Widget _buildReviewMode(VocabularyState state) {
    final reviewList = state.reviewList;
    if (_currentReviewIndex >= reviewList.length) {
      return const SizedBox.shrink();
    }

    final word = reviewList[_currentReviewIndex];

    return Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: const BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: BorderRadius.only(
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
                '${_currentReviewIndex + 1} / ${reviewList.length}',
                style: const TextStyle(
                  color: AppDesignTokens.neutral500,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(width: DS.xxxl), // Balance
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
                  boxShadow: AppDesignTokens.shadowMd,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      word['word'] ?? '',
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: AppDesignTokens.fontWeightBold,
                      ),
                    ),
                    if (word['phonetic'] != null) ...[
                      const SizedBox(height: DS.sm),
                      Text(
                        word['phonetic'],
                        style: const TextStyle(
                          color: AppDesignTokens.neutral500,
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
                        color: AppDesignTokens.neutral300,
                      ),
                      const SizedBox(height: DS.xl),
                      Text(
                        word['definition'] ?? '',
                        style: const TextStyle(
                          fontSize: 18,
                          height: 1.5,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ] else ...[
                      const Text(
                        '点击显示释义',
                        style: TextStyle(
                          color: AppDesignTokens.neutral400,
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
                    size: ButtonSize.large,
                  ),
                ),
                const SizedBox(width: DS.lg),
                Expanded(
                  child: CustomButton.primary(
                    text: '认识',
                    icon: Icons.check_rounded,
                    onPressed: () => _handleReview(true),
                    customGradient: AppDesignTokens.successGradient,
                    size: ButtonSize.large,
                  ),
                ),
              ],
            )
          else
            CustomButton.primary(
              text: '显示答案',
              icon: Icons.visibility_rounded,
              onPressed: () => setState(() => _showAnswer = true),
              size: ButtonSize.large,
            ),
        ],
      ),
    );
  }
}

/// 单词卡片组件
class _WordCard extends StatelessWidget {

  const _WordCard({
    required this.word,
    required this.definition, this.phonetic,
    this.dueText,
    this.masteryLevel,
    this.onTap,
  });
  final String word;
  final String? phonetic;
  final String definition;
  final String? dueText;
  final int? masteryLevel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppDesignTokens.neutral200),
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
                          word,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (phonetic != null) ...[
                          const SizedBox(width: DS.sm),
                          Text(
                            phonetic!,
                            style: const TextStyle(
                              color: AppDesignTokens.neutral500,
                              fontSize: 14,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      definition,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppDesignTokens.neutral600,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              if (dueText != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: dueText == '已到期'
                        ? AppDesignTokens.error.withValues(alpha: 0.1)
                        : AppDesignTokens.warning.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    dueText!,
                    style: TextStyle(
                      color: dueText == '已到期'
                          ? AppDesignTokens.error
                          : AppDesignTokens.warning,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              if (masteryLevel != null)
                _MasteryIndicator(level: masteryLevel!),
            ],
          ),
        ),
      ),
    );
}

/// 掌握程度指示器
class _MasteryIndicator extends StatelessWidget {

  const _MasteryIndicator({required this.level});
  final int level;

  @override
  Widget build(BuildContext context) => Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(7, (index) => Container(
          width: 4,
          height: 16,
          margin: const EdgeInsets.only(left: 2),
          decoration: BoxDecoration(
            color: index < level
                ? DS.success
                : AppDesignTokens.neutral200,
            borderRadius: BorderRadius.circular(2),
          ),
        ),),
    );
}
