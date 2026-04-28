#!/usr/bin/env python3
"""Batch 4: Handle parameterized strings and remaining widget-layer strings."""
import re, os

FEATURES = 'mobile/lib/features'
L10N_IMPORT = "import 'package:sparkle/core/extensions/context_l10n.dart';"

file_edits = {}

def add_edit(filepath, old, new):
    full = os.path.join(FEATURES, filepath)
    if full not in file_edits:
        file_edits[full] = []
    file_edits[full].append((old, new))

# ============= AURORA - remaining widget strings =============
# aurora_core_session_sheet.dart - check if context is available
add_edit('aurora/presentation/widgets/aurora_core_session_sheet.dart',
    "'启动 Aurora 校准失败，请稍后重试。'", "context.l10n.auroraStartFailed")
add_edit('aurora/presentation/widgets/aurora_core_session_sheet.dart',
    "'Aurora 正在准备中…'", "context.l10n.auroraPreparing")
add_edit('aurora/presentation/widgets/aurora_core_session_sheet.dart',
    "'你认为实际情况是…'", "context.l10n.auroraWhatDoYouThink")

# ============= CALENDAR - remaining =============
# calendar_stats_screen.dart - parameterized
add_edit('calendar/presentation/screens/calendar_stats_screen.dart',
    "'结束时间需要晚于开始时间'", "context.l10n.calEndAfterStart")

# ============= COGNITIVE =============
add_edit('cognitive/presentation/screens/pattern_list_screen.dart',
    "'出现 ${pattern.frequency} 次'", "context.l10n.cogPatternFreq(pattern.frequency)")

# ============= ERROR BOOK - remaining =============
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'例如：第三章 牛顿运动定律'", "context.l10n.ebChapterHint")
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'请输入完整的题目内容，或仅上传题目图片...'", "context.l10n.ebQuestionHint")
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'你当时写的错误答案...'", "context.l10n.ebYourAnswerHint")
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'标准答案或正确的解题过程...'", "context.l10n.ebCorrectAnswerHint")
add_edit('error_book/presentation/screens/error_list_screen.dart',
    "'例如：函数、力学、电磁学'", "context.l10n.ebChapterFilterHint")
add_edit('error_book/presentation/screens/review_screen.dart',
    "'没有符合条件的错题'", "context.l10n.ebNoMatchingErrors")
add_edit('error_book/presentation/screens/review_screen.dart',
    "'复习还未完成，确定要退出吗？'", "context.l10n.ebConfirmExitDesc")

# Review performance buttons - long descriptions
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'能准确回忆并理解解题思路'", "context.l10n.ebPerfectRecallHint")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'大致记得，但细节不够清晰'", "context.l10n.ebFuzzyRecallHint")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'想不起来或记错了'", "context.l10n.ebCompleteForgotHint")

# ============= INSIGHTS - remaining =============
add_edit('insights/presentation/screens/learning_insights_overview_screen.dart',
    "'学习洞察还没有可读数据'", "context.l10n.insOverviewEmpty")
add_edit('insights/presentation/screens/learning_insights_overview_screen.dart',
    "'先完成一次学习任务、记录一道错题，或开始一轮仿真，周报和洞察才会开始给出真正有用的反馈。'",
    "context.l10n.insOverviewEmptyDesc")

# Weekly growth narrative - parameterized
add_edit('insights/presentation/widgets/weekly_growth_narrative_card.dart',
    "'第一周'", "context.l10n.insFirstWeek")  # this one might already be done, skip if not found

# ============= MEMORY - remaining =============
add_edit('memory/presentation/screens/memory_settings_screen.dart',
    "'决定哪些内容会被长期记住。'", "context.l10n.memDecideWhat")

# ============= SEED LIBRARY - remaining =============
add_edit('seed_library/presentation/screens/create_library_screen.dart',
    "'输入种子库名称'", "context.l10n.seedNameHint")
add_edit('seed_library/presentation/screens/create_library_screen.dart',
    "'输入种子库描述（可选）'", "context.l10n.seedDescHint")
add_edit('seed_library/presentation/screens/create_library_screen.dart',
    "'输入标签'", "context.l10n.seedTagHint")
add_edit('seed_library/presentation/widgets/seed_item_card.dart',
    "'确定要删除这个内容吗？'", "context.l10n.seedDeleteConfirm")

# ============= SETTINGS - remaining =============
add_edit('settings/presentation/widgets/openclaw_execution_preferences_card.dart',
    "'执行偏好已保存'", "context.l10n.settingsPreferencesSaved")

# ============= TOOLS - remaining parameterized =============
# Speech to text - parameterized
add_edit('tools/presentation/widgets/speech_to_text_tool.dart',
    "'开始一次录音后，文本会实时显示在这里。适合课堂摘录、灵感捕捉和会议补记。'",
    "context.l10n.toolsSttEmptyDesc")

# Notes tool
add_edit('tools/presentation/widgets/notes_tool.dart',
    "'同步中...'", "context.l10n.toolsNotesSyncing")

# Flash capsule - special quote chars in subtitle
# The subtitle has left/right double quotes - need exact match

# Translator tool - remaining parameterized
add_edit('tools/presentation/widgets/translator_tool.dart',
    "'翻译中...'", "context.l10n.toolsTransTranslating")

# Translation feature
add_edit('translation/presentation/widgets/inline_translation_block.dart',
    "'翻译中...'", "context.l10n.transTranslating")
add_edit('translation/presentation/widgets/translation_popover.dart',
    "'保存中...'", "context.l10n.transSaving")

# Wordbook - remaining
add_edit('tools/presentation/widgets/wordbook_tool.dart',
    "'待复习'", "context.l10n.toolsWbDue")

# ============= EXECUTE =============
total_replaced = 0
total_not_found = 0

for filepath, edits in sorted(file_edits.items()):
    if not os.path.exists(filepath):
        print(f"SKIP: {filepath}")
        continue
    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    for old, new in edits:
        if old in content:
            content = content.replace(old, new)
            total_replaced += 1
        else:
            total_not_found += 1
            print(f"  NOT FOUND in {os.path.basename(filepath)}: {old[:60]}")

    if content != original:
        if "context.l10n." in content and "context_l10n.dart" not in content:
            import_pattern = re.compile(r"(import ['\"].*?['\"];)\n", re.MULTILINE)
            imports = list(import_pattern.finditer(content))
            if imports:
                last_import = imports[-1]
                insert_pos = last_import.end()
                content = content[:insert_pos] + L10N_IMPORT + "\n" + content[insert_pos:]

        with open(filepath, 'w') as f:
            f.write(content)
        print(f"UPDATED: {os.path.basename(filepath)} ({len(edits)} edits)")

print(f"\nBatch 4 - Total replaced: {total_replaced}")
print(f"Batch 4 - Total not found: {total_not_found}")
