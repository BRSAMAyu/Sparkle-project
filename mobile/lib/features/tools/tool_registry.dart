import 'package:flutter/material.dart';
import 'package:sparkle/features/document/views/document_cleaner_sheet.dart';
import 'package:sparkle/features/reviews/reviews_routes.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/breathing_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/calculator_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/flash_capsule_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/focus_stats_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/focus_timer_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/notes_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/speech_to_text_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/translator_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/vocabulary_lookup_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/wordbook_tool.dart';

class ToolRegistry {
  static const List<String> defaultPinnedToolIds = [
    'speech_to_text',
    'document_cleaner',
    'focus_timer',
    'translator',
    'calculator',
    'vocabulary_lookup',
    'notes',
    'review_plan',
  ];

  static final List<ToolDefinition> _tools = [
    ToolDefinition(
      id: 'speech_to_text',
      title: 'Speech to Text',
      description: 'Real-time speech to text transcription',
      icon: Icons.mic_rounded,
      category: ToolCategory.input,
      defaultOrder: 10,
      searchTerms: const ['asr', '语音', '转写', '录音'],
      searchTermsEn: const ['asr', 'speech', 'voice', 'transcribe', 'record'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => SpeechToTextTool(
        surface: request.surface,
        onTextResult: request.onTextResult,
      ),
    ),
    ToolDefinition(
      id: 'document_cleaner',
      title: 'Document Cleaner',
      description: 'Clean PDF/Word/PPT with GLM OCR',
      icon: Icons.auto_awesome_motion_rounded,
      category: ToolCategory.input,
      defaultOrder: 20,
      searchTerms: const ['ocr', '文档', '清洗', 'pdf'],
      searchTermsEn: const ['ocr', 'document', 'clean', 'pdf'],
      supportsSheet: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.chatInput,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => DocumentCleanerPanel(
        onResult: request.onTextResult,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'focus_mode',
      title: 'Focus Mode',
      description: 'Enter task focus interface',
      icon: Icons.center_focus_strong_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 30,
      searchTerms: const ['focus', '专注', '任务'],
      searchTermsEn: const ['focus', 'task', 'mode'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/focus',
    ),
    ToolDefinition(
      id: 'focus_timer',
      title: 'Focus Timer',
      description: 'Stopwatch and countdown timer in one',
      icon: Icons.hourglass_bottom_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 40,
      searchTerms: const ['计时器', 'timer', '专注'],
      searchTermsEn: const ['timer', 'stopwatch', 'countdown', 'focus'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => FocusTimerTool(
        preset: FocusTimerPreset.stopwatch,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'pomodoro',
      title: 'Pomodoro',
      description: 'Default 25-minute work cycle',
      icon: Icons.timer_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 50,
      searchTerms: const ['番茄钟', 'pomodoro'],
      searchTermsEn: const ['pomodoro', 'tomato', 'timer'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => FocusTimerTool(
        preset: FocusTimerPreset.pomodoro,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'calculator',
      title: 'Calculator',
      description: 'Quick calculation and expression evaluation',
      icon: Icons.calculate_outlined,
      category: ToolCategory.efficiency,
      defaultOrder: 60,
      searchTerms: const ['计算', '公式', 'calculator'],
      searchTermsEn: const ['calculator', 'math', 'formula', 'expression'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => CalculatorTool(surface: request.surface),
    ),
    ToolDefinition(
      id: 'notes',
      title: 'Quick Notes',
      description: 'Jot down your current thoughts',
      icon: Icons.edit_note_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 70,
      searchTerms: const ['笔记', '备忘', '记录'],
      searchTermsEn: const ['notes', 'memo', 'record', 'quick'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => NotesTool(
        taskId: request.taskId,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'breathing',
      title: 'Breathing Exercise',
      description: 'Quick rhythm switch to restore focus',
      icon: Icons.air_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 80,
      searchTerms: const ['呼吸', '放松'],
      searchTermsEn: const ['breathing', 'relax', 'calm'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => BreathingTool(surface: request.surface),
    ),
    ToolDefinition(
      id: 'focus_stats',
      title: 'Focus Stats',
      description: 'View today and this week focus data',
      icon: Icons.bar_chart_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 90,
      searchTerms: const ['统计', '专注', '数据'],
      searchTermsEn: const ['stats', 'focus', 'data', 'chart'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => FocusStatsTool(surface: request.surface),
    ),
    ToolDefinition(
      id: 'translator',
      title: 'Translator',
      description: 'Quick translate and save history',
      icon: Icons.translate_rounded,
      category: ToolCategory.study,
      defaultOrder: 100,
      searchTerms: const ['translate', '翻译'],
      searchTermsEn: const ['translate', 'translator', 'language'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => TranslatorTool(surface: request.surface),
    ),
    ToolDefinition(
      id: 'vocabulary_lookup',
      title: 'Vocabulary Lookup',
      description: 'Look up words and add to wordbook',
      icon: Icons.search_rounded,
      category: ToolCategory.study,
      defaultOrder: 110,
      searchTerms: const ['词典', '查词', '单词'],
      searchTermsEn: const ['dictionary', 'vocabulary', 'word', 'lookup'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => VocabularyLookupTool(
        taskId: request.taskId,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'wordbook',
      title: 'Wordbook',
      description: 'View and review local vocabulary',
      icon: Icons.menu_book_rounded,
      category: ToolCategory.study,
      defaultOrder: 120,
      searchTerms: const ['单词本', '生词', '复习'],
      searchTermsEn: const ['wordbook', 'vocabulary', 'review', 'words'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => WordbookTool(surface: request.surface),
    ),
    ToolDefinition(
      id: 'error_book',
      title: 'Error Book',
      description: 'Browse and manage error records',
      icon: Icons.assignment_late_rounded,
      category: ToolCategory.study,
      defaultOrder: 130,
      searchTerms: const ['错题', 'errors'],
      searchTermsEn: const ['error', 'mistake', 'wrong'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/errors',
    ),
    ToolDefinition(
      id: 'review_plan',
      title: 'Review Plan',
      description: 'View today\'s review plan',
      icon: Icons.event_note_rounded,
      category: ToolCategory.study,
      defaultOrder: 140,
      searchTerms: const ['复习', 'review', '计划'],
      searchTermsEn: const ['review', 'plan', 'study'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => ReviewRoutes.planHub,
    ),
    ToolDefinition(
      id: 'learning_forecast',
      title: 'Learning Forecast',
      description: 'View learning trends and risks',
      icon: Icons.show_chart_rounded,
      category: ToolCategory.study,
      defaultOrder: 150,
      searchTerms: const ['预测', 'forecast'],
      searchTermsEn: const ['forecast', 'trend', 'prediction'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/learning/forecast',
    ),
    ToolDefinition(
      id: 'flash_capsule',
      title: 'Flash Capsule',
      description: 'Quick capture questions and error insights',
      icon: Icons.lightbulb_outline_rounded,
      category: ToolCategory.study,
      defaultOrder: 160,
      searchTerms: const ['错题', '闪念', '胶囊'],
      searchTermsEn: const ['flash', 'capsule', 'capture', 'insight'],
      supportsSheet: true,
      showInTaskQuickPanel: true,
      supportedContexts: const {
        ToolLaunchContext.taskExecution,
        ToolLaunchContext.toolLibrary,
      },
      embeddedBuilder: (request) => FlashCapsuleTool(
        taskId: request.taskId,
        surface: request.surface,
      ),
    ),
    ToolDefinition(
      id: 'cognitive_patterns',
      title: 'Cognitive Patterns',
      description: 'View behavioral patterns and cognitive insights',
      icon: Icons.psychology_rounded,
      category: ToolCategory.cognition,
      defaultOrder: 170,
      searchTerms: const ['认知', '模式', '洞察'],
      searchTermsEn: const ['cognitive', 'pattern', 'insight', 'behavior'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/cognitive/patterns',
    ),
    ToolDefinition(
      id: 'curiosity_capsule',
      title: 'Curiosity Capsule',
      description: 'Browse triggered insight clues',
      icon: Icons.tips_and_updates_rounded,
      category: ToolCategory.cognition,
      defaultOrder: 180,
      searchTerms: const ['好奇心', '胶囊', 'curiosity'],
      searchTermsEn: const ['curiosity', 'capsule', 'insight'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/curiosity-capsule',
    ),
    ToolDefinition(
      id: 'seed_library',
      title: 'Seed Library',
      description: 'Browse official and community knowledge bases',
      icon: Icons.auto_stories_rounded,
      category: ToolCategory.study,
      defaultOrder: 190,
      searchTerms: const ['种子', '知识库', 'library', 'seed'],
      searchTermsEn: const ['seed', 'library', 'knowledge', 'community'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/seed-libraries',
    ),
  ];

  static List<ToolDefinition> get all =>
      [..._tools]..sort((a, b) => a.defaultOrder.compareTo(b.defaultOrder));

  static List<ToolDefinition> get pinnableTools =>
      all.where((tool) => tool.canPin).toList();

  static List<ToolDefinition> taskQuickTools() => all
      .where(
        (tool) =>
            tool.showInTaskQuickPanel &&
            tool.supportsContext(ToolLaunchContext.taskExecution),
      )
      .toList();

  static bool contains(String id) => _tools.any((tool) => tool.id == id);

  static bool isPinnable(String id) => tryGetById(id)?.canPin ?? false;

  static ToolDefinition getById(String id) {
    final tool = tryGetById(id);
    if (tool == null) {
      throw StateError('Unknown tool: $id');
    }
    return tool;
  }

  static ToolDefinition? tryGetById(String id) {
    for (final tool in _tools) {
      if (tool.id == id) {
        return tool;
      }
    }
    return null;
  }
}
