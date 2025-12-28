import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/vocabulary_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

/// 查词工具 - 快速词典查询
class VocabularyLookupTool extends ConsumerStatefulWidget { // 当前任务ID，用于关联生词

  const VocabularyLookupTool({super.key, this.taskId});
  final String? taskId;

  @override
  ConsumerState<VocabularyLookupTool> createState() => _VocabularyLookupToolState();
}

class _VocabularyLookupToolState extends ConsumerState<VocabularyLookupTool> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    // 自动聚焦输入框
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _lookup() {
    final word = _controller.text.trim();
    if (word.isNotEmpty) {
      ref.read(vocabularyProvider.notifier).lookup(word);
      // 同时获取关联词
      ref.read(vocabularyProvider.notifier).fetchAssociations(word);
    }
  }

  Future<void> _addToWordbook() async {
    final state = ref.read(vocabularyProvider);
    final result = state.lookupResult;
    if (result == null) return;

    final word = result['word'] as String? ?? _controller.text;
    final definitions = result['definitions'];
    var definition = '';

    if (definitions is List && definitions.isNotEmpty) {
      definition = definitions.join('; ');
    } else if (definitions is String) {
      definition = definitions;
    }

    final success = await ref.read(vocabularyProvider.notifier).addToWordbook(
      word: word,
      definition: definition,
      phonetic: result['phonetic'] as String?,
      taskId: widget.taskId,
    );

    if (success && mounted) {
      HapticFeedback.mediumImpact();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('已添加 "$word" 到生词本'),
          backgroundColor: AppDesignTokens.success,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(vocabularyProvider);

    return Container(
      padding: EdgeInsets.all(DS.xl),
      height: 550,
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
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
          SizedBox(height: 20),

          // Header
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: Colors.cyan.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(Icons.search_rounded, color: Colors.cyan, size: 24),
              ),
              SizedBox(width: DS.md),
              Text(
                '查词',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: AppDesignTokens.fontWeightBold,
                ),
              ),
            ],
          ),
          SizedBox(height: 20),

          // Search Input
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  decoration: InputDecoration(
                    hintText: '输入英文单词...',
                    filled: true,
                    fillColor: AppDesignTokens.neutral50,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: Colors.cyan, width: 2),
                    ),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    prefixIcon: Icon(Icons.translate_rounded, color: AppDesignTokens.neutral400),
                  ),
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _lookup(),
                ),
              ),
              SizedBox(width: DS.md),
              SizedBox(
                height: 52,
                child: ElevatedButton(
                  onPressed: state.isLookingUp ? null : _lookup,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.cyan,
                    foregroundColor: DS.brandPrimary,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    padding: EdgeInsets.symmetric(horizontal: 20),
                  ),
                  child: state.isLookingUp
                      ? SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: DS.brandPrimaryConst,
                          ),
                        )
                      : Text('查询'),
                ),
              ),
            ],
          ),
          SizedBox(height: DS.lg),

          // Result Area
          Expanded(
            child: _buildResultArea(state),
          ),

          // Add to Wordbook Button
          if (state.lookupResult != null)
            Padding(
              padding: EdgeInsets.only(top: 16),
              child: CustomButton.primary(
                text: '加入生词本',
                icon: Icons.add_rounded,
                onPressed: state.isLoading ? null : _addToWordbook,
                customGradient: LinearGradient(
                  colors: [Color(0xFF00BCD4), Color(0xFF26C6DA)],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildResultArea(VocabularyState state) {
    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 48,
              color: AppDesignTokens.neutral300,
            ),
            SizedBox(height: DS.md),
            Text(
              state.error!,
              style: TextStyle(color: AppDesignTokens.neutral500),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    if (state.lookupResult == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.menu_book_rounded,
              size: 48,
              color: AppDesignTokens.neutral200,
            ),
            SizedBox(height: DS.md),
            Text(
              '输入单词开始查询',
              style: TextStyle(color: AppDesignTokens.neutral400),
            ),
          ],
        ),
      );
    }

    final result = state.lookupResult!;
    final word = result['word'] as String? ?? '';
    final phonetic = result['phonetic'] as String?;
    final pos = result['pos'] as String?;
    final definitions = result['definitions'];
    final examples = result['examples'];

    return SingleChildScrollView(
      child: Container(
        padding: EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: Colors.cyan.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.cyan.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Word & Phonetic
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  word,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightBold,
                    color: AppDesignTokens.neutral900,
                  ),
                ),
                if (phonetic != null) ...[
                  SizedBox(width: DS.md),
                  Text(
                    phonetic,
                    style: TextStyle(
                      color: AppDesignTokens.neutral500,
                      fontSize: 16,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ],
            ),

            // Part of Speech
            if (pos != null) ...[
              SizedBox(height: DS.sm),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.cyan.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  pos,
                  style: TextStyle(
                    color: Colors.cyan,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
            SizedBox(height: DS.lg),

            // Definitions
            if (definitions != null) ...[
              Text(
                '释义',
                style: TextStyle(
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: AppDesignTokens.neutral700,
                  fontSize: 14,
                ),
              ),
              SizedBox(height: DS.sm),
              ..._buildDefinitions(definitions),
            ],

            // Examples
            if (examples != null && (examples is List && examples.isNotEmpty)) ...[
              SizedBox(height: DS.lg),
              Text(
                '例句',
                style: TextStyle(
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: AppDesignTokens.neutral700,
                  fontSize: 14,
                ),
              ),
              SizedBox(height: DS.sm),
              ..._buildExamples(examples),
            ],

            // Associations
            if (state.associations.isNotEmpty) ...[
              SizedBox(height: DS.lg),
              Text(
                '相关词汇',
                style: TextStyle(
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: AppDesignTokens.neutral700,
                  fontSize: 14,
                ),
              ),
              SizedBox(height: DS.sm),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: state.associations.map((assoc) =>
                  ActionChip(
                    label: Text(assoc),
                    onPressed: () {
                      _controller.text = assoc;
                      _lookup();
                    },
                    backgroundColor: AppDesignTokens.neutral100,
                    labelStyle: TextStyle(
                      color: AppDesignTokens.neutral700,
                      fontSize: 12,
                    ),
                  ),
                ).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _buildDefinitions(dynamic definitions) {
    if (definitions is List) {
      return definitions.asMap().entries.map((entry) => Padding(
          padding: EdgeInsets.only(bottom: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${entry.key + 1}. ',
                style: TextStyle(
                  color: AppDesignTokens.neutral500,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Expanded(
                child: Text(
                  entry.value.toString(),
                  style: TextStyle(
                    color: AppDesignTokens.neutral700,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        ),).toList();
    } else {
      return [
        Text(
          definitions.toString(),
          style: TextStyle(
            color: AppDesignTokens.neutral700,
            height: 1.4,
          ),
        ),
      ];
    }
  }

  List<Widget> _buildExamples(dynamic examples) {
    if (examples is List) {
      return examples.take(3).map((example) => Padding(
          padding: EdgeInsets.only(bottom: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.format_quote_rounded,
                size: 16,
                color: AppDesignTokens.neutral400,
              ),
              SizedBox(width: DS.sm),
              Expanded(
                child: Text(
                  example.toString(),
                  style: TextStyle(
                    color: AppDesignTokens.neutral600,
                    fontStyle: FontStyle.italic,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        ),).toList();
    }
    return [];
  }
}
