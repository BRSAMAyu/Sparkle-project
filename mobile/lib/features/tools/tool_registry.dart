import 'package:flutter/material.dart';
import 'package:sparkle/features/document/views/document_cleaner_sheet.dart';
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
      title: '语音转文字',
      description: '实时录音转写为文本',
      icon: Icons.mic_rounded,
      category: ToolCategory.input,
      defaultOrder: 10,
      searchTerms: const ['asr', '语音', '转写', '录音'],
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
      title: '文档清洗',
      description: '用 GLM OCR 清洗 PDF/Word/PPT',
      icon: Icons.auto_awesome_motion_rounded,
      category: ToolCategory.input,
      defaultOrder: 20,
      searchTerms: const ['ocr', '文档', '清洗', 'pdf'],
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
      title: '专注模式',
      description: '进入任务专注主界面',
      icon: Icons.center_focus_strong_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 30,
      searchTerms: const ['focus', '专注', '任务'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/focus',
    ),
    ToolDefinition(
      id: 'focus_timer',
      title: '专注计时',
      description: '正计时与倒计时一体化',
      icon: Icons.hourglass_bottom_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 40,
      searchTerms: const ['计时器', 'timer', '专注'],
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
      title: '番茄钟',
      description: '默认 25 分钟工作周期',
      icon: Icons.timer_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 50,
      searchTerms: const ['番茄钟', 'pomodoro'],
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
      title: '计算器',
      description: '快速演算与表达式计算',
      icon: Icons.calculate_outlined,
      category: ToolCategory.efficiency,
      defaultOrder: 60,
      searchTerms: const ['计算', '公式', 'calculator'],
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
      title: '闪念笔记',
      description: '随手记录当前想法',
      icon: Icons.edit_note_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 70,
      searchTerms: const ['笔记', '备忘', '记录'],
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
      title: '呼吸练习',
      description: '快速切换节奏恢复专注',
      icon: Icons.air_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 80,
      searchTerms: const ['呼吸', '放松'],
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
      title: '专注统计',
      description: '查看今日与本周专注数据',
      icon: Icons.bar_chart_rounded,
      category: ToolCategory.efficiency,
      defaultOrder: 90,
      searchTerms: const ['统计', '专注', '数据'],
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
      title: '翻译',
      description: '快速翻译并保存记录',
      icon: Icons.translate_rounded,
      category: ToolCategory.study,
      defaultOrder: 100,
      searchTerms: const ['translate', '翻译'],
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
      title: '查词',
      description: '查询单词并加入生词本',
      icon: Icons.search_rounded,
      category: ToolCategory.study,
      defaultOrder: 110,
      searchTerms: const ['词典', '查词', '单词'],
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
      title: '生词本',
      description: '查看本地生词并复习',
      icon: Icons.menu_book_rounded,
      category: ToolCategory.study,
      defaultOrder: 120,
      searchTerms: const ['单词本', '生词', '复习'],
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
      title: '错题本',
      description: '浏览与管理错题记录',
      icon: Icons.assignment_late_rounded,
      category: ToolCategory.study,
      defaultOrder: 130,
      searchTerms: const ['错题', 'errors'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/errors',
    ),
    ToolDefinition(
      id: 'review_plan',
      title: '复习计划',
      description: '进入今日复习计划页',
      icon: Icons.event_note_rounded,
      category: ToolCategory.study,
      defaultOrder: 140,
      searchTerms: const ['复习', 'review', '计划'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/review-plan',
    ),
    ToolDefinition(
      id: 'learning_forecast',
      title: '学习预测',
      description: '查看学习趋势与风险',
      icon: Icons.show_chart_rounded,
      category: ToolCategory.study,
      defaultOrder: 150,
      searchTerms: const ['预测', 'forecast'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/learning/forecast',
    ),
    ToolDefinition(
      id: 'flash_capsule',
      title: '闪念胶囊',
      description: '快速记录当前问题与错题灵感',
      icon: Icons.lightbulb_outline_rounded,
      category: ToolCategory.study,
      defaultOrder: 160,
      searchTerms: const ['错题', '闪念', '胶囊'],
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
      title: '认知模式',
      description: '查看行为定式与认知洞察',
      icon: Icons.psychology_rounded,
      category: ToolCategory.cognition,
      defaultOrder: 170,
      searchTerms: const ['认知', '模式', '洞察'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/cognitive/patterns',
    ),
    ToolDefinition(
      id: 'curiosity_capsule',
      title: '好奇心胶囊',
      description: '浏览当前触发的洞察线索',
      icon: Icons.tips_and_updates_rounded,
      category: ToolCategory.cognition,
      defaultOrder: 180,
      searchTerms: const ['好奇心', '胶囊', 'curiosity'],
      supportedContexts: const {
        ToolLaunchContext.home,
        ToolLaunchContext.toolLibrary,
      },
      routeBuilder: (_) => '/curiosity-capsule',
    ),
    ToolDefinition(
      id: 'seed_library',
      title: '种子库',
      description: '浏览官方与社区知识库',
      icon: Icons.auto_stories_rounded,
      category: ToolCategory.study,
      defaultOrder: 190,
      searchTerms: const ['种子', '知识库', 'library', 'seed'],
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
