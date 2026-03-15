// ignore_for_file: inference_failure_on_instance_creation

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/features/translation/presentation/providers/translation_history_provider.dart';
import 'package:sparkle/features/translation/translation_routes.dart';

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
  String toString() => name;
}

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
  const TranslatorTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

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

  Language _sourceLanguage = supportedLanguages[0];
  Language _targetLanguage = supportedLanguages[2];

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _translate() async {
    if (_inputController.text.trim().isEmpty) {
      AppFeedback.info(context, '请输入要翻译的文本');
      return;
    }

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
          final translatedText =
              (data['translation'] ?? data['translated_text']) as String? ?? '';
          setState(() {
            _output = translatedText;
            _currentRating = 3;
            _isFavorited = false;
          });
          await _saveTranslation(translatedText);
        } else {
          final meta = data['meta'] as Map<String, dynamic>?;
          setState(() {
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
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _swapLanguages() {
    if (_sourceLanguage.code == 'auto') {
      setState(() {
        _targetLanguage = supportedLanguages[1];
      });
      return;
    }
    setState(() {
      final temp = _sourceLanguage;
      _sourceLanguage = _targetLanguage;
      _targetLanguage = temp;
      if (_output.isNotEmpty) {
        _inputController.text = _output;
        _output = '';
      }
    });
  }

  Future<void> _saveTranslation(String translatedText) async {
    try {
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
        return;
      }

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
    } catch (e) {
      debugPrint('Error auto-saving translation: $e');
    }
  }

  void _updateRating(int rating) {
    setState(() {
      _currentRating = rating;
    });
    if (_currentTranslationId != null) {
      unawaited(
        ref
            .read(translationHistoryProvider.notifier)
            .updateRating(_currentTranslationId!, rating),
      );
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
    unawaited(Clipboard.setData(ClipboardData(text: _output)));
    AppFeedback.info(context, '已复制到剪贴板');
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.prismPurple;
    final inputLength = _inputController.text.trim().length;
    final outputLength = _output.trim().length;

    return ToolShell(
      surface: widget.surface,
      icon: Icons.translate_rounded,
      title: '翻译',
      subtitle: '面向学习和任务场景的双栏翻译器，支持自动存档、评分和收藏，便于后续回看。',
      accentColor: accent,
      compactHeader: true,
      headerAction: SparkleIconButton(
        onPressed: () => unawaited(context.push(TranslationRoutes.history)),
        icon: const Icon(Icons.history_rounded),
        variant: ButtonVariant.ghost,
      ),
      heroChips: [
        ToolHeroChip(
          label: '${_sourceLanguage.name} → ${_targetLanguage.name}',
          accentColor: accent,
          icon: Icons.swap_horiz_rounded,
        ),
        ToolHeroChip(
          label: _isFavorited ? '已收藏' : '自动保存历史',
          accentColor: accent,
          icon: _isFavorited ? Icons.favorite_rounded : Icons.archive_rounded,
        ),
      ],
      body: Column(
        children: [
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              ToolMetricCard(
                label: '输入长度',
                value: '$inputLength',
                accentColor: accent,
                icon: Icons.edit_note_rounded,
                caption: '建议控制在可读段落内',
              ),
              ToolMetricCard(
                label: '输出长度',
                value: '$outputLength',
                accentColor: accent,
                icon: Icons.auto_fix_high_rounded,
                caption: _isLoading ? '翻译生成中' : '翻译完成后可复制',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: '语言方向',
            subtitle: '自动检测用于快速起步，也可以切成手动源语言。',
            trailing: SparkleButton(
              label: '交换',
              variant: ButtonVariant.ghost,
              onPressed: _swapLanguages,
              icon: const Icon(Icons.swap_horiz_rounded),
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 560;
                final sourceDropdown = _LanguageDropdown(
                  value: _sourceLanguage,
                  items: supportedLanguages,
                  onChanged: (lang) => setState(() => _sourceLanguage = lang),
                );
                final targetDropdown = _LanguageDropdown(
                  value: _targetLanguage,
                  items: supportedLanguages
                      .where((language) => language.code != 'auto')
                      .toList(),
                  onChanged: (lang) => setState(() => _targetLanguage = lang),
                );

                if (compact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      sourceDropdown,
                      const SizedBox(height: DS.spacing12),
                      targetDropdown,
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: sourceDropdown),
                    const SizedBox(width: DS.spacing12),
                    Expanded(child: targetDropdown),
                  ],
                );
              },
            ),
          ),
          const SizedBox(height: DS.spacing16),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 720;
              final inputCard = ToolSectionCard(
                accentColor: accent,
                title: '原文',
                subtitle: '支持多行粘贴，适合段落翻译。',
                trailing: IconButton(
                  onPressed: () {
                    setState(() {
                      _inputController.clear();
                      _output = '';
                    });
                  },
                  icon: const Icon(Icons.close_rounded),
                ),
                child: SizedBox(
                  height: compact ? 220 : 250,
                  child: TextField(
                    controller: _inputController,
                    maxLines: null,
                    expands: true,
                    textAlignVertical: TextAlignVertical.top,
                    decoration: const InputDecoration(
                      hintText: '输入要翻译的文本...',
                      border: InputBorder.none,
                    ),
                  ),
                ),
              );
              final outputCard = ToolSectionCard(
                accentColor: accent,
                title: '译文',
                subtitle: '翻译完成后可复制、收藏和打分。',
                trailing: _output.isEmpty
                    ? null
                    : IconButton(
                        onPressed: _toggleFavorite,
                        icon: Icon(
                          _isFavorited
                              ? Icons.favorite_rounded
                              : Icons.favorite_border_rounded,
                          color: _isFavorited ? DS.error : DS.textSecondary,
                        ),
                      ),
                child: _isLoading
                    ? Center(
                        child: CircularProgressIndicator(color: accent),
                      )
                    : _errorMessage != null
                        ? ToolEmptyState(
                            icon: Icons.error_outline_rounded,
                            title: '翻译未完成',
                            description: _errorMessage!,
                            accentColor: DS.error,
                          )
                        : _output.isEmpty
                            ? ToolEmptyState(
                                icon: Icons.translate_rounded,
                                title: '等待翻译结果',
                                description: '点击下方翻译按钮后，结果会显示在这里。',
                                accentColor: accent,
                              )
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(
                                    height: 160,
                                    child: SingleChildScrollView(
                                      child: SelectableText(
                                        _output,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyLarge
                                            ?.copyWith(
                                              color: DS.textPrimary,
                                              height: 1.6,
                                            ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: DS.spacing16),
                                  Wrap(
                                    spacing: DS.spacing10,
                                    runSpacing: DS.spacing10,
                                    children: List.generate(
                                      5,
                                      (index) => ToolChoiceChip(
                                        label: '${index + 1} 星',
                                        selected: _currentRating == index + 1,
                                        onTap: () => _updateRating(index + 1),
                                        accentColor: accent,
                                        icon: Icons.star_rounded,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
              );

              if (compact) {
                return Column(
                  children: [
                    inputCard,
                    const SizedBox(height: DS.spacing16),
                    SizedBox(height: 360, child: outputCard),
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: SizedBox(height: 410, child: inputCard)),
                  const SizedBox(width: DS.spacing16),
                  Expanded(child: SizedBox(height: 410, child: outputCard)),
                ],
              );
            },
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final copyButton = SparkleButton(
            label: '复制译文',
            variant: ButtonVariant.ghost,
            onPressed: _output.isEmpty ? null : _copyToClipboard,
            icon: const Icon(Icons.copy_rounded),
            expand: true,
          );
          final translateButton = SparkleButton(
            label: _isLoading ? '翻译中...' : '开始翻译',
            onPressed: _isLoading ? null : _translate,
            icon: const Icon(Icons.auto_fix_high_rounded),
            loading: _isLoading,
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                copyButton,
                const SizedBox(height: DS.spacing12),
                translateButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: copyButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: translateButton),
            ],
          );
        },
      ),
    );
  }
}

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
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<Language>(
              isDense: true,
              isExpanded: true,
              value: value,
              items: items
                  .map(
                    (language) => DropdownMenuItem<Language>(
                      value: language,
                      child: Text(
                        language.toString(),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (language) {
                if (language != null) {
                  onChanged(language);
                }
              },
            ),
          ),
        ),
      );
}
