#!/usr/bin/env python3
"""Batch 3: Replace remaining hardcoded Chinese strings including parameterized ones."""
import re, os

FEATURES = 'mobile/lib/features'
L10N_IMPORT = "import 'package:sparkle/core/extensions/context_l10n.dart';"

# For data layer files without context, we use a direct AppLocalizations lookup pattern
# or we keep them as-is if they're truly not user-facing

# Many of these remaining strings are in non-build contexts (data layer, providers)
# For data/repository files: we need to check if context is available
# For providers: they may not have BuildContext

# Let's handle them case by case

file_edits = {}

def add_edit(filepath, old, new):
    full = os.path.join(FEATURES, filepath)
    if full not in file_edits:
        file_edits[full] = []
    file_edits[full].append((old, new))

# ============= REMAINING SIMPLE REPLACEMENTS (build context available) =============

# Breathing tool - two '停留' entries
add_edit('tools/presentation/widgets/breathing_tool.dart', "'停留'", "context.l10n.toolsBreathHold")

# Notes tool hint
add_edit('tools/presentation/widgets/notes_tool.dart', "'把刚刚闪过的想法先放进来...'", "context.l10n.toolsNotesHint")

# Simulation descriptions
add_edit('simulation/presentation/screens/simulation_screen.dart', "'通过连续追问拆解前提，适合澄清模糊概念与推理漏洞。'", "context.l10n.simSocraticDesc")
add_edit('simulation/presentation/screens/simulation_screen.dart', "'专注识别错因、纠偏路径与验证方式，适合查漏补缺。'", "context.l10n.simErrorDiagDesc")

# Aurora
add_edit('aurora/presentation/widgets/aurora_calibration_strip.dart', "'不对'", "context.l10n.auroraNotRight")
add_edit('aurora/presentation/widgets/aurora_calibration_strip.dart', "'以后别这样判断'", "context.l10n.auroraDontJudge")
add_edit('aurora/presentation/widgets/aurora_core_session_sheet.dart', "'退出校准'", "context.l10n.auroraExitCalibration")

# Register screen - agreement texts with Chinese quotes
add_edit('auth/presentation/screens/register_screen.dart', "'我已阅读并同意《用户协议》'", "context.l10n.authAgreeTerms")
add_edit('auth/presentation/screens/register_screen.dart', "'我已阅读并同意《隐私政策》'", "context.l10n.authAgreePrivacy")

# Calendar daily detail - time labels
add_edit('calendar/presentation/screens/daily_detail_screen.dart', "'提前 5 分钟'", "context.l10n.cal5MinBefore")
add_edit('calendar/presentation/screens/daily_detail_screen.dart', "'提前 15 分钟'", "context.l10n.cal15MinBefore")
add_edit('calendar/presentation/screens/daily_detail_screen.dart', "'提前 30 分钟'", "context.l10n.cal30MinBefore")
add_edit('calendar/presentation/screens/daily_detail_screen.dart', "'提前 1 小时'", "context.l10n.cal1HourBefore")

# Calendar agent stats
add_edit('calendar/presentation/widgets/agent_stats_dashboard.dart', "'总执行次数'", "context.l10n.calTotalExecutions")
add_edit('calendar/presentation/widgets/agent_stats_dashboard.dart', "'平均耗时'", "context.l10n.calAvgDuration")
add_edit('calendar/presentation/widgets/agent_stats_dashboard.dart', "'会话数'", "context.l10n.calSessionCount")

# Calendar smart schedule chip
add_edit('calendar/presentation/widgets/smart_schedule_chip.dart', '"推荐时段"', "context.l10n.calSuggestedSlot")

# Cognitive
add_edit('cognitive/presentation/screens/capsule/capsule_detail_screen.dart', "'它可能已经被移除，或者还没有完成生成。'", "context.l10n.cogCapsuleUnavailableDesc")

# Error book - more
add_edit('error_book/presentation/screens/error_list_screen.dart', "'仅显示待复习'", "context.l10n.ebShowDueOnly")
add_edit('error_book/presentation/screens/error_list_screen.dart', "'全部'", "context.l10n.ebAll")
add_edit('error_book/presentation/widgets/subject_chips.dart', "'全部'", "context.l10n.ebAll")

# Insights - overview screen remaining
add_edit('insights/presentation/screens/learning_insights_overview_screen.dart', "'继续上次推演'", "context.l10n.insContinueSim")
add_edit('insights/presentation/screens/learning_insights_overview_screen.dart', "'继续上次学习仿真'", "context.l10n.insContinueLearnSim")
add_edit('insights/presentation/screens/learning_insights_overview_screen.dart', "'已有可继续内容'", "context.l10n.insHasContinue")

# Insights - forecast screen remaining
add_edit('insights/presentation/screens/learning_forecast_screen.dart', "'预测数据暂时还没准备好'", "context.l10n.insForecastEmpty")
add_edit('insights/presentation/screens/learning_forecast_screen.dart', "'还没有足够数据生成稳定推荐。'", "context.l10n.insNotEnoughData")

# Insights - learning path dialog remaining
add_edit('insights/presentation/widgets/learning_path_dialog.dart', "'无需前置知识，可以直接开始学习！'", "context.l10n.insNoPrereq")

# Memory settings - long descriptions
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'关闭后会暂停新的记忆写入，但不会删除历史记录。'", "context.l10n.memDisableDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'总开关。关闭后 Stage 18 主动提醒会全部停用。'", "context.l10n.memProactiveMaster")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'只针对你明确表达过、且已经逾期的承诺事项。'", "context.l10n.memCommitmentFollowupDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'只针对曾经连续活跃、且 72 小时未活跃的情况。'", "context.l10n.memActivityRecoveryDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'记录回答风格、学习节奏和常见偏好。'", "context.l10n.memPreferenceDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'记录已确认的长期目标和阶段意图。'", "context.l10n.memGoalsDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'记录对后续决策有帮助的关键事件与反馈。'", "context.l10n.memExperienceDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'允许系统从聊天中推断短期经历；每条都必须可见、可撤销。'", "context.l10n.memAiAutoMemoryDesc")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'越高越积极，但也会记录更多上下文。'", "context.l10n.memSensitivityNote")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'不希望长期存储的偏好项可以在这里关闭。'", "context.l10n.memExcludeNote")
add_edit('memory/presentation/screens/memory_settings_screen.dart', "'限制哪些入口不会写入长期记忆。'", "context.l10n.memSourceLimit")

# Seed library - more
add_edit('seed_library/presentation/screens/seed_library_list_screen.dart', "'仅看官方'", "context.l10n.seedOfficialFilter")
add_edit('seed_library/presentation/screens/seed_library_list_screen.dart', "'仅看精选'", "context.l10n.seedFeaturedFilter")
add_edit('seed_library/presentation/screens/seed_library_list_screen.dart', "'优先查看系统维护或官方推荐的种子库'", "context.l10n.seedOfficialFilterDesc")
add_edit('seed_library/presentation/screens/seed_library_list_screen.dart', "'筛出被标记为优先推荐的优质种子库'", "context.l10n.seedFeaturedFilterDesc")
add_edit('seed_library/presentation/widgets/seed_item_card.dart', "'删除内容'", "context.l10n.seedDeleteContent")

# Settings - more
add_edit('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'自动延长长任务超时'", "context.l10n.settingsAutoExtend")
add_edit('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'允许系统基于历史自动建议升级信任'", "context.l10n.settingsAutoSuggestTrust")

# Translator tool - subtitle with special quotes
# The '把一闪而过的疑点...' uses left/right double quotes
add_edit('tools/presentation/widgets/flash_capsule_tool.dart', "'选择科目、错误类型，再补充知识点和描述。'", "context.l10n.toolsFlashContentDesc")

# Vocabulary lookup - description texts
add_edit('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'输入英文单词后回车或点击查询。Oxford 词典优先，本地离线包会先于网络命中。'", "context.l10n.toolsVocabInputDesc")
add_edit('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查询完成后可以直接收藏到生词本，并继续生成例句。'", "context.l10n.toolsVocabResultHint")

# Wordbook - remaining
add_edit('tools/presentation/widgets/wordbook_tool.dart', "'先用筛选缩小范围，再用搜索定位具体词条。'", "context.l10n.toolsWbFilterDesc")
add_edit('tools/presentation/widgets/wordbook_tool.dart', "'以快闪卡片方式确认是否记住当前词条。'", "context.l10n.toolsWbReviewDesc")

# Translation feature - remaining
add_edit('translation/presentation/widgets/translatable_text.dart', "'已保存到生词卡'", "context.l10n.transSavedToWordCard")

# Review performance - remaining
add_edit('error_book/presentation/widgets/review_performance_buttons.dart', "'下次会提前复习'", "context.l10n.ebForgotHint")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart', "'保持复习间隔'", "context.l10n.ebFuzzyHint")
add_edit('error_book/presentation/widgets/review_performance_buttons.dart', "'延长复习间隔'", "context.l10n.ebRememberedHint")

# Error book - more descriptions
add_edit('error_book/presentation/screens/add_error_screen.dart', "'填写后便于按章节筛选复习'", "context.l10n.ebChapterHelper")
add_edit('error_book/presentation/screens/add_error_screen.dart', "'题目文字和题目图片二选一即可，推荐两者都填以提升分析质量'", "context.l10n.ebQuestionHelper")
add_edit('error_book/presentation/screens/error_list_screen.dart', "'和顶部\u201c待复习\u201d标签页配合使用'", "context.l10n.ebShowDueDesc")

# Insights - learning path dialog
add_edit('insights/presentation/widgets/learning_path_dialog.dart', "'快速生成任务路径'", "context.l10n.insQuickPath")
add_edit('insights/presentation/widgets/learning_path_dialog.dart', "'生成完整计划'", "context.l10n.insFullPlan")

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
            print(f"  NOT FOUND in {os.path.basename(filepath)}: {old[:50]}")

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

print(f"\nBatch 3 - Total replaced: {total_replaced}")
print(f"Batch 3 - Total not found: {total_not_found}")
