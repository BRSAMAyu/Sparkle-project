// ignore_for_file: inference_failure_on_instance_creation

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/translation/presentation/providers/translation_history_provider.dart';
import 'package:sparkle/features/translation/presentation/screens/translation_history_screen.dart';

/// 支持的语言
class Language {
  const Language({
    required this.code,
    required this.name,
    this.flag,
  });

  final String code;
  final String name;
  final String? flag;

  @override
  String toString() => flag != null ? '$flag $name' : name;
}

/// 支持的语言列表
const supportedLanguages = [
  Language(code: 'auto', name: '自动检测', flag: '🔍'),
  Language(code: 'zh', name: '中文', flag: '🇨🇳'),
  Language(code: 'en', name: 'English', flag: '🇺🇸'),
  Language(code: 'ja', name: '日本語', flag: '🇯🇵'),
  Language(code: 'ko', name: '한국어', flag: '🇰🇷'),
  Language(code: 'fr', name: 'Français', flag: '🇫🇷'),
  Language(code: 'de', name: 'Deutsch', flag: '🇩🇪'),
  Language(code: 'es', name: 'Español', flag: '🇪🇸'),
  Language(code: 'ru', name: 'Русский', flag: '🇷🇺'),
];

class TranslatorTool extends ConsumerStatefulWidget {
  const TranslatorTool({super.key});

  @override
  ConsumerState<TranslatorTool> createState() => _TranslatorToolState();
}

class _TranslatorToolState extends ConsumerState<TranslatorTool> {
  final TextEditingController _inputController = TextEditingController();
  String _output = '';
  bool _isLoading = false;
  String? _errorMessage;
  Id? _currentTranslationId;
  int _currentRating = 3;
  bool _isFavorited = false;

  // 默认：自动检测 -> 英语
  Language _sourceLanguage = supportedLanguages[0]; // auto
  Language _targetLanguage = supportedLanguages[2]; // English

  Future<void> _translate() async {
    if (_inputController.text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _output = '';
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);

      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.translationTranslate,
        data: {
          'text': _inputController.text,
          'source_language': _sourceLanguage.code,
          'target_language': _targetLanguage.code,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final success = data['success'] as bool? ?? false;

        if (success) {
          // Backend returns `translation` (not `translated_text`).
          final translatedText =
              (data['translation'] ?? data['translated_text']) as String? ?? '';
          setState(() {
            _output = translatedText;
            _currentRating = 3;
            _isFavorited = false;
          });

          // Auto-save translation
          _saveTranslation(translatedText);
        } else {
          setState(() {
            // Backend error is usually nested under `meta.error`.
            final meta = data['meta'] as Map<String, dynamic>?;
            _errorMessage =
                (meta?['error'] ?? data['error_message']) as String? ?? '翻译失败';
          });
        }
      } else {
        setState(() {
          _errorMessage = '网络错误: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = '翻译出错: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _swapLanguages() {
    if (_sourceLanguage.code == 'auto') {
      // 自动检测不能交换，只切换目标语言
      setState(() {
        // 将目标语言设为中文
        _targetLanguage = supportedLanguages[1];
      });
    } else {
      setState(() {
        final temp = _sourceLanguage;
        _sourceLanguage = _targetLanguage;
        _targetLanguage = temp;

        // 同时交换输入输出的文本
        if (_output.isNotEmpty) {
          _inputController.text = _output;
          _output = '';
        }
      });
    }
  }

  Future<void> _saveTranslation(String translatedText) async {
    try {
      // Check for similar existing translation
      final similar =
          await ref.read(translationHistoryProvider.notifier).findSimilar(
                originalText: _inputController.text,
                sourceLanguage: _sourceLanguage.code,
                targetLanguage: _targetLanguage.code,
              );

      if (similar != null) {
        if (mounted) {
          setState(() {
            _currentTranslationId = similar.id;
            _currentRating = similar.rating;
            _isFavorited = similar.isFavorited;
          });
        }
      } else {
        final id =
            await ref.read(translationHistoryProvider.notifier).saveTranslation(
                  originalText: _inputController.text,
                  translatedText: translatedText,
                  sourceLanguage: _sourceLanguage.code,
                  targetLanguage: _targetLanguage.code,
                  rating: _currentRating,
                  isFavorited: _isFavorited,
                );
        if (mounted) {
          setState(() {
            _currentTranslationId = id;
          });
        }
      }
    } catch (e) {
      debugPrint('Error auto-saving translation: $e');
      // Non-critical error, suppressing UI alert to avoid interrupting user flow
    }
  }

  void _updateRating(int rating) {
    setState(() {
      _currentRating = rating;
    });
    if (_currentTranslationId != null) {
      ref
          .read(translationHistoryProvider.notifier)
          .updateRating(_currentTranslationId!, rating);
    }
  }

  Future<void> _toggleFavorite() async {
    final newValue = !_isFavorited;
    setState(() {
      _isFavorited = newValue;
    });
    if (_currentTranslationId != null) {
      await ref
          .read(translationHistoryProvider.notifier)
          .toggleFavorite(_currentTranslationId!);
    }
  }

  void _copyToClipboard() {
    Clipboard.setData(ClipboardData(text: _output));
    AppFeedback.info(context, '已复制到剪贴板');
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.xl),
        height: 580,
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(24),
            topRight: Radius.circular(24),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 拖动条
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
            const SizedBox(height: DS.lg),

            // 标题
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    color: DS.prismPurple.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(DS.spacing8),
                  ),
                  child: Icon(Icons.translate, color: DS.prismPurple),
                ),
                const SizedBox(width: DS.sm),
                Text(
                  '快速翻译',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                // 关闭按钮
                SparkleIconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close),
                  variant: ButtonVariant.ghost,
                  size: DS.touchTargetMinSize,
                ),
              ],
            ),
            const SizedBox(height: DS.lg),

            // 语言选择器
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: DS.md, vertical: DS.sm),
              decoration: BoxDecoration(
                color: DS.neutral50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: DS.neutral200),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: _LanguageDropdown(
                      value: _sourceLanguage,
                      items: supportedLanguages,
                      onChanged: (lang) =>
                          setState(() => _sourceLanguage = lang),
                    ),
                  ),
                  // 交换按钮
                  SparkleIconButton(
                    onPressed: _swapLanguages,
                    icon: const Icon(Icons.swap_horiz),
                    semanticLabel: '交换语言',
                    variant: ButtonVariant.ghost,
                    size: DS.touchTargetMinSize,
                  ),
                  Expanded(
                    child: _LanguageDropdown(
                      value: _targetLanguage,
                      items: supportedLanguages
                          .where((l) => l.code != 'auto')
                          .toList(),
                      onChanged: (lang) =>
                          setState(() => _targetLanguage = lang),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),

            // 输入框
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.neutral50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _errorMessage != null ? DS.error : DS.neutral200,
                  ),
                ),
                child: TextField(
                  controller: _inputController,
                  maxLines: null,
                  expands: true,
                  decoration: const InputDecoration(
                    hintText: '输入要翻译的文本...',
                    border: InputBorder.none,
                  ),
                ),
              ),
            ),
            const SizedBox(height: DS.md),

            // 翻译按钮
            SizedBox(
              height: 48,
              child: SparkleButton(
                label: _isLoading ? '翻译中...' : '翻译',
                onPressed: _translate,
                icon: const Icon(Icons.translate),
                variant: ButtonVariant.primary,
                loading: _isLoading,
                disabled: _isLoading,
                expand: true,
              ),
            ),
            const SizedBox(height: DS.md),

            // 错误提示
            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.error.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: DS.error.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: DS.error, size: 20),
                    const SizedBox(width: DS.sm),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: TextStyle(color: DS.error, fontSize: 12),
                      ),
                    ),
                    InkWell(
                      borderRadius: DS.borderRadiusFull,
                      onTap: () => setState(() => _errorMessage = null),
                      child: const Padding(
                        padding: EdgeInsets.all(DS.spacing4),
                        child: Icon(Icons.close, size: 16),
                      ),
                    ),
                  ],
                ),
              ),

            // 输出区域
            if (_output.isNotEmpty || !_isLoading)
              Container(
                padding: const EdgeInsets.all(DS.md),
                height: 120,
                decoration: BoxDecoration(
                  color: DS.prismPurple.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                  border:
                      Border.all(color: DS.prismPurple.withValues(alpha: 0.2)),
                ),
                child: _isLoading
                    ? Center(
                        child: CircularProgressIndicator(color: DS.prismPurple),
                      )
                    : SingleChildScrollView(
                        child: Text(
                          _output.isEmpty ? '翻译结果将显示在这里' : _output,
                          style: TextStyle(
                            color:
                                _output.isEmpty ? DS.neutral400 : DS.neutral900,
                            fontSize: 14,
                          ),
                        ),
                      ),
              ),

            // 复制按钮
            if (_output.isNotEmpty && !_isLoading)
              Padding(
                padding: const EdgeInsets.only(top: DS.sm),
                child: SparkleButton.ghost(
                  label: '复制结果',
                  onPressed: _copyToClipboard,
                  icon: const Icon(Icons.copy, size: 16),
                ),
              ),

            // Rating and Favorite buttons
            if (_output.isNotEmpty && !_isLoading)
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: DS.md, vertical: DS.sm),
                decoration: BoxDecoration(
                  color: DS.neutral50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: DS.neutral200),
                ),
                child: Row(
                  children: [
                    // Rating label
                    Text(
                      '重要程度',
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.neutral600,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(width: DS.sm),

                    // Star rating
                    ...List.generate(5, (index) {
                      final starValue = index + 1;
                      return GestureDetector(
                        onTap: () => _updateRating(starValue),
                        child: Icon(
                          Icons.star,
                          size: 24,
                          color: _currentRating >= starValue
                              ? DS.warning
                              : DS.neutral300,
                        ),
                      );
                    }),

                    const Spacer(),

                    // Favorite button
                    Tooltip(
                      message: _isFavorited ? '取消收藏' : '收藏',
                      child: InkWell(
                        borderRadius: DS.borderRadiusFull,
                        onTap: _toggleFavorite,
                        child: Padding(
                          padding: const EdgeInsets.all(DS.spacing4),
                          child: Icon(
                            _isFavorited ? Icons.star : Icons.star_border,
                            color: _isFavorited ? DS.warning : DS.neutral500,
                            size: 20,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(width: DS.sm),

                    // History button
                    SparkleButton.ghost(
                      label: '历史',
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (context) =>
                                const TranslationHistoryScreen(),
                          ),
                        );
                      },
                      icon: const Icon(Icons.history, size: 16),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }
}

/// 语言选择下拉框
class _LanguageDropdown extends StatelessWidget {
  const _LanguageDropdown({
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final Language value;
  final List<Language> items;
  final ValueChanged<Language> onChanged;

  @override
  Widget build(BuildContext context) => DropdownButtonHideUnderline(
        child: DropdownButtonFormField<Language>(
          initialValue: value,
          items: items
              .map(
                (lang) => DropdownMenuItem(
                  value: lang,
                  child: Text(
                    lang.toString(),
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
              )
              .toList(),
          onChanged: (lang) {
            if (lang != null) onChanged(lang);
          },
          decoration: const InputDecoration(
            border: InputBorder.none,
            contentPadding: EdgeInsets.symmetric(horizontal: DS.sm),
            isDense: true,
          ),
          icon: const Icon(Icons.arrow_drop_down, size: 20),
          style: TextStyle(color: DS.neutral900, fontSize: 13),
          borderRadius: BorderRadius.circular(8),
        ),
      );
}
