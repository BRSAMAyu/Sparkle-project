#!/usr/bin/env python3
"""Batch 5: Final pass - handle all remaining widget-layer parameterized strings."""
import re, os

FEATURES = 'mobile/lib/features'
L10N_IMPORT = "import 'package:sparkle/core/extensions/context_l10n.dart';"

file_edits = {}
def add_edit(filepath, old, new):
    full = os.path.join(FEATURES, filepath)
    if full not in file_edits:
        file_edits[full] = []
    file_edits[full].append((old, new))

# ============= PARAMETERIZED STRINGS =============
# These use Dart string interpolation with $ or ${}

# Translator tool - error messages with $e
add_edit('tools/presentation/widgets/translator_tool.dart',
    "_errorMessage = '翻译出错: $e';",
    "_errorMessage = context.l10n.toolsTransError(e.toString());")
add_edit('tools/presentation/widgets/translator_tool.dart',
    "AppFeedback.error(context, '加入单词本失败: $e');",
    "AppFeedback.error(context, context.l10n.toolsTransAddWordFailed(e.toString()));")

# Flash capsule - error messages
add_edit('tools/presentation/widgets/flash_capsule_tool.dart',
    "AppFeedback.error(context, '加载历史胶囊失败: $e');",
    "AppFeedback.error(context, context.l10n.toolsFlashLoadFailed(e.toString()));")
add_edit('tools/presentation/widgets/flash_capsule_tool.dart',
    "AppFeedback.error(context, '记录失败: $e');",
    "AppFeedback.error(context, context.l10n.toolsFlashSaveFailed(e.toString()));")

# Vocabulary lookup - entry count with ${}
# Note: ${package.entryCount} needs a method call

# Focus stats - streak with ${}
# Note: ${state.streakDays} needs a method call

# Insights - error messages
add_edit('insights/presentation/screens/learning_forecast_screen.dart',
    "'加载失败: $e'",
    "context.l10n.insLoadFailed(e.toString())")
add_edit('insights/presentation/widgets/learning_path_dialog.dart',
    "'创建失败：$e'",
    "context.l10n.insCreateFailed(e.toString())")

# Calendar - error messages
add_edit('calendar/presentation/screens/calendar_stats_screen.dart',
    "'创建日程失败：$e'",
    "context.l10n.calCreateEventFailed(e.toString())")

# Error book - error messages
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'图片上传失败: $e'",
    "context.l10n.ebImageUploadFailed(e.toString())")
add_edit('error_book/presentation/screens/add_error_screen.dart',
    "'加载错题失败: $error'",
    "context.l10n.ebLoadErrorFailed(error.toString())")
add_edit('error_book/presentation/screens/review_screen.dart',
    "'提交失败: $e'",
    "context.l10n.ebSubmitFailed(e.toString())")

# Memory - error messages
add_edit('memory/presentation/screens/memory_settings_screen.dart',
    "'加载记忆设置失败: $e'",
    "context.l10n.memLoadSettingsFailed(e.toString())")
add_edit('memory/presentation/screens/memory_settings_screen.dart',
    "'保存失败: $e'",
    "context.l10n.memSaveFailed(e.toString())")

# Seed library - error messages
add_edit('seed_library/presentation/screens/create_library_screen.dart',
    "'创建失败：$e'",
    "context.l10n.seedCreateFailed(e.toString())")

# Translation popover - error messages
add_edit('translation/presentation/widgets/translation_popover.dart',
    "'未知错误: $e'",
    "context.l10n.transUnknownError(e.toString())")
add_edit('translation/presentation/widgets/translation_popover.dart',
    "'翻译中...'",
    "context.l10n.transTranslating")

# Aurora calibration strip - error message
add_edit('aurora/presentation/widgets/aurora_calibration_strip.dart',
    "'提交校准反馈失败：$error'",
    "context.l10n.auroraFeedbackFailed(error.toString())")

# Memory routes - error message
add_edit('memory/memory_routes.dart',
    "'记忆详情参数缺失'",
    "context.l10n.memDetailMissing")

# Review performance buttons - labels with special chars
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'完全记住了 ✓'",
    "context.l10n.ebPerfectRecall")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'有点模糊 ≈'",
    "context.l10n.ebFuzzyRecall")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart',
    "'完全忘记了 ✗'",
    "context.l10n.ebCompleteForgot")

# Memory settings - long description
add_edit('memory/presentation/screens/memory_settings_screen.dart',
    "'Stage 18 默认关闭。只有你显式开启后，系统才会发送承诺跟进或活跃恢复提醒。'",
    "context.l10n.memCommitmentStageNote")
add_edit('memory/presentation/screens/memory_settings_screen.dart',
    "'你可以收窄系统默认的 22:00-08:00，但不能把提醒扩张到这段时间里。'",
    "context.l10n.memQuietHoursNote")

# Insights learning path dialog - remaining parameterized
# These have ${node.name} and $e in them - need special handling

# Flash capsule subtitle with special quotes
add_edit('tools/presentation/widgets/flash_capsule_tool.dart',
    "'例如：三角函数求导、牛顿第二定律...'",
    "context.l10n.toolsFlashKnowledgeHint")
add_edit('tools/presentation/widgets/flash_capsule_tool.dart',
    "'记录你是怎么错的、卡在什么地方、下次要如何避免。'",
    "context.l10n.toolsFlashErrorDescHint")

# Wordbook - remaining parameterized strings
add_edit('tools/presentation/widgets/wordbook_tool.dart',
    "'确定要从生词本中删除 '",
    "context.l10n.toolsWbDeleteConfirm + ' '")
add_edit('tools/presentation/widgets/wordbook_tool.dart',
    "' 吗？'",
    "context.l10n.toolsWbDeleteSuffix")

# Wordbook - empty states
add_edit('tools/presentation/widgets/wordbook_tool.dart',
    "'当前没有待复习单词'",
    "context.l10n.toolsWbEmptyNoDue")
add_edit('tools/presentation/widgets/wordbook_tool.dart',
    "'生词本还是空的'",
    "context.l10n.toolsWbEmpty")

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

print(f"\nBatch 5 - Total replaced: {total_replaced}")
print(f"Batch 5 - Total not found: {total_not_found}")
