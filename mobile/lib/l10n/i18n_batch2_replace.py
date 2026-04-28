#!/usr/bin/env python3
"""Batch 2: Replace remaining hardcoded Chinese strings."""
import re, os

FEATURES = 'mobile/lib/features'
L10N_IMPORT = "import 'package:sparkle/core/extensions/context_l10n.dart';"

EDITS = []
def e(file, old, new):
    EDITS.append((file, old, new))

# ============= BREATHING TOOL - remaining =============
# Two '停留' entries - both are labels. The first batch missed them because they use identical strings.
# We need to handle these as they appear - both are 'label:' context
# Since both '停留' are same string, we can use replace_all

# ============= TRANSLATOR TOOL =============
e('tools/presentation/widgets/translator_tool.dart', "'翻译失败'", "context.l10n.toolsTransFailed")
e('tools/presentation/widgets/translator_tool.dart', "'翻译'", "context.l10n.toolsTransTitle")
e('tools/presentation/widgets/translator_tool.dart', "'面向学习和任务场景的双栏翻译器，支持自动存档、评分和收藏，便于后续回看。'", "context.l10n.toolsTransSubtitle")
e('tools/presentation/widgets/translator_tool.dart', "'已收藏'", "context.l10n.toolsTransFavorited")
e('tools/presentation/widgets/translator_tool.dart', "'自动保存历史'", "context.l10n.toolsTransAutoSave")
e('tools/presentation/widgets/translator_tool.dart', "'输入长度'", "context.l10n.toolsTransInputLen")
e('tools/presentation/widgets/translator_tool.dart', "'输出长度'", "context.l10n.toolsTransOutputLen")
e('tools/presentation/widgets/translator_tool.dart', "'语言方向'", "context.l10n.toolsTransDirection")
e('tools/presentation/widgets/translator_tool.dart', "'自动检测用于快速起步，也可以切成手动源语言。'", "context.l10n.toolsTransDirectionDesc")
e('tools/presentation/widgets/translator_tool.dart', "'交换'", "context.l10n.toolsTransSwap")
e('tools/presentation/widgets/translator_tool.dart', "'原文'", "context.l10n.toolsTransSource")
e('tools/presentation/widgets/translator_tool.dart', "'支持多行粘贴，适合段落翻译。'", "context.l10n.toolsTransSourceDesc")
e('tools/presentation/widgets/translator_tool.dart', "'输入要翻译的文本...'", "context.l10n.toolsTransInputHint")
e('tools/presentation/widgets/translator_tool.dart', "'译文'", "context.l10n.toolsTransTarget")
e('tools/presentation/widgets/translator_tool.dart', "'翻译完成后可复制、收藏和打分。'", "context.l10n.toolsTransTargetDesc")
e('tools/presentation/widgets/translator_tool.dart', "'翻译未完成'", "context.l10n.toolsTransIncomplete")
e('tools/presentation/widgets/translator_tool.dart', "'等待翻译结果'", "context.l10n.toolsTransWaiting")
e('tools/presentation/widgets/translator_tool.dart', "'点击下方翻译按钮后，结果会显示在这里。'", "context.l10n.toolsTransWaitingDesc")
e('tools/presentation/widgets/translator_tool.dart', "'单词本联动'", "context.l10n.toolsTransWordbookLink")
e('tools/presentation/widgets/translator_tool.dart', "'单词翻译结果可以直接加入单词本，并进入后续复习链路。'", "context.l10n.toolsTransWordbookDesc")
e('tools/presentation/widgets/translator_tool.dart', "'加入单词本'", "context.l10n.toolsTransAddWordbook")
e('tools/presentation/widgets/translator_tool.dart', "'复制译文'", "context.l10n.toolsTransCopyResult")
e('tools/presentation/widgets/translator_tool.dart', "'开始翻译'", "context.l10n.toolsTransStart")

# ============= WORDBOOK TOOL =============
e('tools/presentation/widgets/wordbook_tool.dart', "'设置重要程度'", "context.l10n.toolsWbSetImportance")
e('tools/presentation/widgets/wordbook_tool.dart', "'取消'", "context.l10n.toolsWbCancel")
e('tools/presentation/widgets/wordbook_tool.dart', "'保存'", "context.l10n.toolsWbSave")
e('tools/presentation/widgets/wordbook_tool.dart', "'生词本'", "context.l10n.toolsWbTitle")
e('tools/presentation/widgets/wordbook_tool.dart', "'把查词结果变成可复习资产。支持搜索、重要度筛选和快闪式复习。'", "context.l10n.toolsWbSubtitle")
e('tools/presentation/widgets/wordbook_tool.dart', "'总词条'", "context.l10n.toolsWbTotal")
e('tools/presentation/widgets/wordbook_tool.dart', "'高重要度'", "context.l10n.toolsWbHighImportance")
e('tools/presentation/widgets/wordbook_tool.dart', "'筛选与搜索'", "context.l10n.toolsWbFilter")
e('tools/presentation/widgets/wordbook_tool.dart', "'搜索单词或释义'", "context.l10n.toolsWbSearchHint")
e('tools/presentation/widgets/wordbook_tool.dart', "'全部词条'", "context.l10n.toolsWbAll")
e('tools/presentation/widgets/wordbook_tool.dart', "'开始复习'", "context.l10n.toolsWbStartReview")
e('tools/presentation/widgets/wordbook_tool.dart', "'删除单词'", "context.l10n.toolsWbDeleteTitle")
e('tools/presentation/widgets/wordbook_tool.dart', "'删除'", "context.l10n.toolsWbDelete")
e('tools/presentation/widgets/wordbook_tool.dart', "'复习模式'", "context.l10n.toolsWbReviewMode")
e('tools/presentation/widgets/wordbook_tool.dart', "'答案已展开'", "context.l10n.toolsWbAnswerRevealed")
e('tools/presentation/widgets/wordbook_tool.dart', "'点击卡片看答案'", "context.l10n.toolsWbTapForAnswer")
e('tools/presentation/widgets/wordbook_tool.dart', "'不认识'", "context.l10n.toolsWbDontKnow")
e('tools/presentation/widgets/wordbook_tool.dart', "'认识'", "context.l10n.toolsWbKnow")
e('tools/presentation/widgets/wordbook_tool.dart', "'退出复习'", "context.l10n.toolsWbExitReview")
e('tools/presentation/widgets/wordbook_tool.dart', "'显示答案'", "context.l10n.toolsWbShowAnswer")

# ============= VOCABULARY LOOKUP TOOL =============
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'移除'", "context.l10n.toolsVocabRemove")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查词'", "context.l10n.toolsVocabTitle")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'用来做快速词义确认、例句生成和关联词扩展，查询结果可以直接收进本地生词本。'", "context.l10n.toolsVocabSubtitle")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'已在生词本中'", "context.l10n.toolsVocabInWordbook")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'可加入生词本'", "context.l10n.toolsVocabAddToWordbook")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查询输入'", "context.l10n.toolsVocabInput")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'管理离线词典'", "context.l10n.toolsVocabManageOffline")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'下载离线词典'", "context.l10n.toolsVocabDownloadOffline")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'输入英文单词...'", "context.l10n.toolsVocabInputHint")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查询'", "context.l10n.toolsVocabSearch")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查询结果'", "context.l10n.toolsVocabResult")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'词义、例句、关联词和模型生成句都在这里。'", "context.l10n.toolsVocabResultDesc")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'输入单词开始查询'", "context.l10n.toolsVocabStartHint")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'查询暂时失败'", "context.l10n.toolsVocabSearchFailed")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'移出生词本'", "context.l10n.toolsVocabRemoveFromWordbook")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'加入生词本'", "context.l10n.toolsVocabAddToWordbookAction")
e('tools/presentation/widgets/vocabulary_lookup_tool.dart', "'生成例句'", "context.l10n.toolsVocabGenerateExample")

# ============= FLASH CAPSULE TOOL =============
e('tools/presentation/widgets/flash_capsule_tool.dart', "'闪念胶囊'", "context.l10n.toolsFlashTitle")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'记录内容'", "context.l10n.toolsFlashContent")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'知识点'", "context.l10n.toolsFlashKnowledge")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'错误描述'", "context.l10n.toolsFlashErrorDesc")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'知识点长度'", "context.l10n.toolsFlashKnowledgeLen")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'描述长度'", "context.l10n.toolsFlashDescLen")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'认知维度'", "context.l10n.toolsFlashCognitiveDim")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'查看历史'", "context.l10n.toolsFlashViewHistory")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'保存胶囊'", "context.l10n.toolsFlashSaveCapsule")
e('tools/presentation/widgets/flash_capsule_tool.dart', "'选择科目'", "context.l10n.toolsFlashSelectSubject")

# ============= VISUAL ELEMENT REPOSITORY =============
# These are data layer - need special handling since they may not have context
# Skip for now, handle separately

# ============= ERROR BOOK - more =============
e('error_book/presentation/screens/add_error_screen.dart', "'编辑错题'", "context.l10n.ebEditError")
e('error_book/presentation/screens/add_error_screen.dart', "'添加错题'", "context.l10n.ebAddError")
e('error_book/presentation/screens/add_error_screen.dart', "'上传题目图片'", "context.l10n.ebUploadImage")
e('error_book/presentation/screens/add_error_screen.dart', "'重新上传图片'", "context.l10n.ebReuploadImage")
e('error_book/presentation/screens/error_list_screen.dart', "'章节'", "context.l10n.ebChapter")
e('error_book/presentation/screens/error_list_screen.dart', "'全部'", "context.l10n.ebAll")

# ============= REVIEW PERFORMANCE BUTTONS - more =============
# These have multi-line strings that need special handling

# ============= INSIGHTS - more =============
e('insights/presentation/screens/learning_forecast_screen.dart', "'学习预测洞察'", "context.l10n.insForecastTitle")
e('insights/presentation/screens/learning_forecast_screen.dart', "'重新加载'", "context.l10n.insReload")
e('insights/presentation/screens/learning_forecast_screen.dart', "'夜间复盘'", "context.l10n.insNightReview")
e('insights/presentation/screens/learning_forecast_screen.dart', "'学习活跃度分析'", "context.l10n.insActivityAnalysis")
e('insights/presentation/screens/learning_forecast_screen.dart', "'AI 洞察'", "context.l10n.insAiInsights")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'回到驾驶舱'", "context.l10n.insBackToCockpit")

# ============= CALENDAR =============
e('calendar/presentation/screens/calendar_stats_screen.dart', "'推荐时段'", "context.l10n.calSuggestedSlot")
e('calendar/presentation/widgets/smart_schedule_chip.dart', "'推荐时段'", "context.l10n.calSuggestedSlot")

# ============= SETTINGS - more =============
e('settings/presentation/screens/openclaw_settings_screen.dart', "'等待队列已清空'", "context.l10n.settingsQueueCleared")
e('settings/presentation/screens/openclaw_settings_screen.dart', "'重试队列'", "context.l10n.settingsRetryQueue")

# ============= SIMULATION =============
e('simulation/presentation/support/simulation_copy.dart', "'苏格拉底式对话'", "context.l10n.simSocraticCopy")
e('simulation/presentation/support/simulation_copy.dart', "'错因诊断'", "context.l10n.simErrorDiagCopy")

# ============= TRANSLATION FEATURE =============
e('translation/presentation/widgets/inline_translation_block.dart', "'保存到生词卡'", "context.l10n.transSaveToWordCard")
e('translation/presentation/widgets/translation_popover.dart', "'保存失败，请重试'", "context.l10n.transSaveFailed")

# ============= SEED LIBRARY =============
e('seed_library/presentation/screens/create_library_screen.dart', "'创建种子库'", "context.l10n.seedCreateTitle")
e('seed_library/presentation/screens/create_library_screen.dart', "'名称'", "context.l10n.seedNameLabel")
e('seed_library/presentation/screens/create_library_screen.dart', "'描述'", "context.l10n.seedDescLabel")
e('seed_library/presentation/screens/seed_library_list_screen.dart', "'仅官方'", "context.l10n.seedOfficialOnly")
e('seed_library/presentation/screens/seed_library_list_screen.dart', "'仅精选'", "context.l10n.seedFeaturedOnly")

# ============= COGNITIVE =============
e('cognitive/presentation/screens/capsule/capsule_jobs_screen.dart', "'生成任务加载失败'", "context.l10n.cogJobsLoadFailed")
e('cognitive/presentation/screens/curiosity_capsule_screen.dart', "'胶囊列表加载失败'", "context.l10n.cogCapsuleListFailed")

# ============= MEMORY =============
e('memory/presentation/widgets/evidence_cards.dart', "'无法解析证据'", "context.l10n.memEvidenceParseFail")
e('memory/presentation/widgets/evidence_cards.dart', "'回到错题本看'", "context.l10n.memBackToErrorBook")

# ============= VISUAL ELEMENTS SCREEN - more =============
e('visual_elements/presentation/screens/visual_elements_screen.dart', "'高曝光荣耀装扮套组'", "context.l10n.visualHighExposure")
e('visual_elements/presentation/screens/visual_elements_screen.dart', "'装备套装时出现问题'", "context.l10n.visualEquipFailed")
e('visual_elements/presentation/screens/visual_elements_screen.dart', "'卸下套装时出现问题'", "context.l10n.visualUnequipFailed")

# ============= BREATHING - remaining =============
e('tools/presentation/widgets/breathing_tool.dart', "'重置'", "context.l10n.toolsBreathReset")

# ============= EXECUTE =============
file_edits = {}
for filepath, old, new in EDITS:
    full_path = os.path.join(FEATURES, filepath)
    if full_path not in file_edits:
        file_edits[full_path] = []
    file_edits[full_path].append((old, new))

total_replaced = 0
total_not_found = 0

for filepath, edits in sorted(file_edits.items()):
    if not os.path.exists(filepath):
        print(f"SKIP (not found): {filepath}")
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
            print(f"  NOT FOUND in {filepath}: {old[:50]}")

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
        print(f"UPDATED: {filepath} ({len(edits)} edits)")

print(f"\nBatch 2 - Total replaced: {total_replaced}")
print(f"Batch 2 - Total not found: {total_not_found}")
