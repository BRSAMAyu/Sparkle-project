#!/usr/bin/env python3
"""Batch replace hardcoded Chinese strings with context.l10n references in Dart files."""
import re, os

FEATURES = 'mobile/lib/features'
L10N_IMPORT = "import 'package:sparkle/core/extensions/context_l10n.dart';"

# (file_path_relative, old_string, new_string)
# Files are relative to FEATURES dir
EDITS = []

def e(file, old, new):
    EDITS.append((file, old, new))

# ============= BREATHING TOOL =============
e('tools/presentation/widgets/breathing_tool.dart', "'快速降噪，适合焦躁和睡前收束。'", "context.l10n.toolsBreathQuickDesc")
e('tools/presentation/widgets/breathing_tool.dart', "'方块呼吸'", "context.l10n.toolsBreathBox")
e('tools/presentation/widgets/breathing_tool.dart', "'均衡稳定，适合进入专注前校准节奏。'", "context.l10n.toolsBreathBoxDesc")
e('tools/presentation/widgets/breathing_tool.dart', "'舒缓呼吸'", "context.l10n.toolsBreathRelax")
e('tools/presentation/widgets/breathing_tool.dart', "'呼长于吸，适合紧张后的恢复。'", "context.l10n.toolsBreathRelaxDesc")
e('tools/presentation/widgets/breathing_tool.dart', "'吸气'", "context.l10n.toolsBreathInhale")
e('tools/presentation/widgets/breathing_tool.dart', "'呼气'", "context.l10n.toolsBreathExhale")
e('tools/presentation/widgets/breathing_tool.dart', "'呼吸练习完成'", "context.l10n.toolsBreathComplete")
e('tools/presentation/widgets/breathing_tool.dart', "'呼吸练习'", "context.l10n.toolsBreathTitle")
e('tools/presentation/widgets/breathing_tool.dart', "'把呼吸节奏做成可执行工具，而不是一次性动画。支持多种模式和不同练习时长，适合在任务间切换状态。'", "context.l10n.toolsBreathSubtitle")
e('tools/presentation/widgets/breathing_tool.dart', "'呼吸舞台'", "context.l10n.toolsBreathStage")
e('tools/presentation/widgets/breathing_tool.dart', "'当前节律'", "context.l10n.toolsBreathCurrentRhythm")
e('tools/presentation/widgets/breathing_tool.dart', "'目标轮数'", "context.l10n.toolsBreathTargetRounds")
e('tools/presentation/widgets/breathing_tool.dart', "'练习配置'", "context.l10n.toolsBreathConfig")
e('tools/presentation/widgets/breathing_tool.dart', "'继续练习'", "context.l10n.toolsBreathContinue")
e('tools/presentation/widgets/breathing_tool.dart', "'暂停练习'", "context.l10n.toolsBreathPause")
e('tools/presentation/widgets/breathing_tool.dart', "'开始练习'", "context.l10n.toolsBreathStart")
e('tools/presentation/widgets/breathing_tool.dart', "'停止练习'", "context.l10n.toolsBreathStop")

# ============= CALCULATOR TOOL =============
e('tools/presentation/widgets/calculator_tool.dart', "'计算器'", "context.l10n.toolsCalcTitle")
e('tools/presentation/widgets/calculator_tool.dart', "'适合任务执行中的快算、表达式验算和连贯多步推导，结果会保留最近记录。'", "context.l10n.toolsCalcSubtitle")
e('tools/presentation/widgets/calculator_tool.dart', "'无历史'", "context.l10n.toolsCalcNoHistory")
e('tools/presentation/widgets/calculator_tool.dart', "'等待计算'", "context.l10n.toolsCalcWaiting")
e('tools/presentation/widgets/calculator_tool.dart', "'结果已就绪'", "context.l10n.toolsCalcResultReady")
e('tools/presentation/widgets/calculator_tool.dart', "'表达式'", "context.l10n.toolsCalcExpression")
e('tools/presentation/widgets/calculator_tool.dart', "'支持括号和连续输入，`ANS` 会回填上一轮计算结果。'", "context.l10n.toolsCalcExpressionDesc")
e('tools/presentation/widgets/calculator_tool.dart', "'准备计算'", "context.l10n.toolsCalcReady")
e('tools/presentation/widgets/calculator_tool.dart', "'复制结果'", "context.l10n.toolsCalcCopyResult")
e('tools/presentation/widgets/calculator_tool.dart', "'计算'", "context.l10n.toolsCalcCompute")
e('tools/presentation/widgets/calculator_tool.dart', "'键盘'", "context.l10n.toolsCalcKeyboard")
e('tools/presentation/widgets/calculator_tool.dart', "'数字键和运算键分层展示，减少高频误触。'", "context.l10n.toolsCalcKeyboardDesc")
e('tools/presentation/widgets/calculator_tool.dart', "'最近记录'", "context.l10n.toolsCalcRecentHistory")
e('tools/presentation/widgets/calculator_tool.dart', "'轻量保留最近 6 次，方便回填和核对。'", "context.l10n.toolsCalcRecentHistoryDesc")
e('tools/presentation/widgets/calculator_tool.dart', "'还没有计算历史'", "context.l10n.toolsCalcNoHistoryLabel")
e('tools/presentation/widgets/calculator_tool.dart', "'完成一次表达式计算后，最近记录会显示在这里。'", "context.l10n.toolsCalcNoHistoryDesc")

# ============= NOTES TOOL =============
e('tools/presentation/widgets/notes_tool.dart', "'同步失败，请稍后再试'", "context.l10n.toolsNotesSyncFailed")
e('tools/presentation/widgets/notes_tool.dart', "'闪念笔记'", "context.l10n.toolsNotesTitle")
e('tools/presentation/widgets/notes_tool.dart', "'用于快速承接灵感、会议碎片和任务切片。内容会自动保存，适合做短时外脑。'", "context.l10n.toolsNotesSubtitle")
e('tools/presentation/widgets/notes_tool.dart', "'等待记录'", "context.l10n.toolsNotesWaiting")
e('tools/presentation/widgets/notes_tool.dart', "'字数'", "context.l10n.toolsNotesCharLabel")
e('tools/presentation/widgets/notes_tool.dart', "'行数'", "context.l10n.toolsNotesLineLabel")
e('tools/presentation/widgets/notes_tool.dart', "'笔记内容'", "context.l10n.toolsNotesContent")
e('tools/presentation/widgets/notes_tool.dart', "'输入时会自动保存，不需要手动提交。'", "context.l10n.toolsNotesContentDesc")
e('tools/presentation/widgets/notes_tool.dart', "'清空'", "context.l10n.toolsNotesClear")
e('tools/presentation/widgets/notes_tool.dart', "'复制内容'", "context.l10n.toolsNotesCopy")
e('tools/presentation/widgets/notes_tool.dart', "'立即保存'", "context.l10n.toolsNotesSaveNow")
e('tools/presentation/widgets/notes_tool.dart', "'同步到棱镜'", "context.l10n.toolsNotesSyncToPrism")

# ============= SPEECH TO TEXT TOOL =============
e('tools/presentation/widgets/speech_to_text_tool.dart', "'语音转文字'", "context.l10n.toolsSttTitle")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'面向真实记录场景的轻量转写台。单次录音最长 30 秒，直接调用当前已接通的 GLM ASR 链路。'", "context.l10n.toolsSttSubtitle")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'字数'", "context.l10n.toolsSttCharCountLabel")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'词数'", "context.l10n.toolsSttWordCountLabel")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'录音控制'", "context.l10n.toolsSttRecordControl")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'点击麦克风开始录音，再次点击结束转写。'", "context.l10n.toolsSttRecordDesc")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'转写结果'", "context.l10n.toolsSttResult")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'结果区支持直接复制，可作为后续写作和总结的原文底稿。'", "context.l10n.toolsSttResultDesc")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'还没有转写内容'", "context.l10n.toolsSttEmpty")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'清空'", "context.l10n.toolsSttClear")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'复制文本'", "context.l10n.toolsSttCopy")
e('tools/presentation/widgets/speech_to_text_tool.dart', "'插入内容'", "context.l10n.toolsSttInsert")

# ============= FOCUS STATS TOOL =============
e('tools/presentation/widgets/focus_stats_tool.dart', "'专注统计'", "context.l10n.toolsStatsTitle")
e('tools/presentation/widgets/focus_stats_tool.dart', "'把计时和专注行为沉淀成结构化洞察，方便你判断节奏是否稳定、是否需要调整工作块长度。'", "context.l10n.toolsStatsSubtitle")
e('tools/presentation/widgets/focus_stats_tool.dart', "'等待数据'", "context.l10n.toolsStatsWaitingData")
e('tools/presentation/widgets/focus_stats_tool.dart', "'今日专注'", "context.l10n.toolsStatsTodayFocus")
e('tools/presentation/widgets/focus_stats_tool.dart', "'本周累计'", "context.l10n.toolsStatsWeekTotal")
e('tools/presentation/widgets/focus_stats_tool.dart', "'日均专注'", "context.l10n.toolsStatsDailyAvg")
e('tools/presentation/widgets/focus_stats_tool.dart', "'本周趋势'", "context.l10n.toolsStatsWeekTrend")
e('tools/presentation/widgets/focus_stats_tool.dart', "'最近 7 天的专注时长变化。'", "context.l10n.toolsStatsWeekTrendDesc")
e('tools/presentation/widgets/focus_stats_tool.dart', "'还没有趋势数据'", "context.l10n.toolsStatsNoTrend")
e('tools/presentation/widgets/focus_stats_tool.dart', "'完成几次专注会话后，这里会形成有参考价值的趋势图。'", "context.l10n.toolsStatsNoTrendDesc")
e('tools/presentation/widgets/focus_stats_tool.dart', "'最近会话'", "context.l10n.toolsStatsRecentSessions")
e('tools/presentation/widgets/focus_stats_tool.dart', "'帮助你回看最近的专注节奏和时长结构。'", "context.l10n.toolsStatsRecentDesc")

# ============= ERROR BOOK REPOSITORY =============
e('error_book/data/repositories/error_book_repository.dart', "'创建错题失败'", "context.l10n.ebCreateFailed")
e('error_book/data/repositories/error_book_repository.dart', "'获取错题列表失败'", "context.l10n.ebListFailed")
e('error_book/data/repositories/error_book_repository.dart', "'获取错题详情失败'", "context.l10n.ebDetailFailed")
e('error_book/data/repositories/error_book_repository.dart', "'更新错题失败'", "context.l10n.ebUpdateFailed")
e('error_book/data/repositories/error_book_repository.dart', "'删除错题失败'", "context.l10n.ebDeleteFailed")
e('error_book/data/repositories/error_book_repository.dart', "'重新分析失败'", "context.l10n.ebAnalysisFailed")
e('error_book/data/repositories/error_book_repository.dart', "'提交复习记录失败'", "context.l10n.ebReviewFailed")
e('error_book/data/repositories/error_book_repository.dart', "'获取今日复习列表失败'", "context.l10n.ebTodayReviewFailed")
e('error_book/data/repositories/error_book_repository.dart', "'获取统计数据失败'", "context.l10n.ebStatsFailed")
e('error_book/data/repositories/error_book_repository.dart', "'获取语义摘要失败'", "context.l10n.ebSummaryFailed")
e('error_book/data/repositories/error_book_repository.dart', "'请求参数错误'", "context.l10n.ebBadParams")

# ============= MEMORY SETTINGS =============
e('memory/presentation/screens/memory_settings_screen.dart', "'记忆控制未启用'", "context.l10n.memNotEnabled")
e('memory/presentation/screens/memory_settings_screen.dart', "'记忆控制不可用'", "context.l10n.memUnavailable")
e('memory/presentation/screens/memory_settings_screen.dart', "'重试'", "context.l10n.memRetry")
e('memory/presentation/screens/memory_settings_screen.dart', "'记忆已启用'", "context.l10n.memEnabled")
e('memory/presentation/screens/memory_settings_screen.dart', "'记忆已暂停'", "context.l10n.memPaused")
e('memory/presentation/screens/memory_settings_screen.dart', "'偏好可控'", "context.l10n.memPrefControlled")
e('memory/presentation/screens/memory_settings_screen.dart', "'启用长期记忆'", "context.l10n.memEnableLongTerm")
e('memory/presentation/screens/memory_settings_screen.dart', "'自我记忆'", "context.l10n.memSelfMemory")
e('memory/presentation/screens/memory_settings_screen.dart', "'人物提及'", "context.l10n.memPeopleMention")
e('memory/presentation/screens/memory_settings_screen.dart', "'关系动态'", "context.l10n.memRelationshipDynamics")
e('memory/presentation/screens/memory_settings_screen.dart', "'承诺事项'", "context.l10n.memCommitments")
e('memory/presentation/screens/memory_settings_screen.dart', "'启用主动提醒'", "context.l10n.memEnableProactive")
e('memory/presentation/screens/memory_settings_screen.dart', "'承诺跟进'", "context.l10n.memCommitmentFollowup")
e('memory/presentation/screens/memory_settings_screen.dart', "'活跃恢复'", "context.l10n.memActivityRecovery")
e('memory/presentation/screens/memory_settings_screen.dart', "'开始时间'", "context.l10n.memStartTime")
e('memory/presentation/screens/memory_settings_screen.dart', "'结束时间'", "context.l10n.memEndTime")
e('memory/presentation/screens/memory_settings_screen.dart', "'查看提醒收件箱'", "context.l10n.memViewInbox")
e('memory/presentation/screens/memory_settings_screen.dart', "'偏好'", "context.l10n.memPreference")
e('memory/presentation/screens/memory_settings_screen.dart', "'目标'", "context.l10n.memGoals")
e('memory/presentation/screens/memory_settings_screen.dart', "'经历'", "context.l10n.memExperience")
e('memory/presentation/screens/memory_settings_screen.dart', "'AI 自动记忆'", "context.l10n.memAiAutoMemory")
e('memory/presentation/screens/memory_settings_screen.dart', "'返回'", "context.l10n.memBack")
e('memory/presentation/screens/memory_settings_screen.dart', "'保存中...'", "context.l10n.memSaving")
e('memory/presentation/screens/memory_settings_screen.dart', "'保存设置'", "context.l10n.memSaveSettings")

# ============= SETTINGS =============
e('settings/presentation/screens/transparency_settings_screen.dart', "'纯净模式'", "context.l10n.settingsPureMode")
e('settings/presentation/screens/transparency_settings_screen.dart', "'折叠悬浮胶囊'", "context.l10n.settingsCollapseFloating")
e('settings/presentation/screens/transparency_settings_screen.dart', "'底部抽屉'", "context.l10n.settingsBottomDrawer")
e('settings/presentation/screens/transparency_settings_screen.dart', "'仅详情页'", "context.l10n.settingsDetailOnly")
e('settings/presentation/screens/transparency_settings_screen.dart', "'完成后自动折叠'", "context.l10n.settingsAutoCollapse")
e('settings/presentation/screens/transparency_settings_screen.dart', "'允许单轮关闭'", "context.l10n.settingsAllowSingleClose")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'确认'", "context.l10n.settingsConfirm")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'全部通知'", "context.l10n.settingsAllNotifications")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'仅关键节点'", "context.l10n.settingsCriticalOnly")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'安静模式'", "context.l10n.settingsQuietMode")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'每日上限'", "context.l10n.settingsDailyLimit")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'每月上限'", "context.l10n.settingsMonthlyLimit")
e('settings/presentation/widgets/openclaw_execution_preferences_card.dart', "'保存执行偏好'", "context.l10n.settingsSavePreferences")
e('settings/presentation/widgets/openclaw_pairing_scanner_sheet.dart', "'取消'", "context.l10n.toolsWbCancel")

# ============= SIMULATION =============
e('simulation/presentation/screens/simulation_screen.dart', "'苏格拉底对话'", "context.l10n.simSocratic")
e('simulation/presentation/screens/simulation_screen.dart', "'错误诊断'", "context.l10n.simErrorDiag")
e('simulation/presentation/screens/simulation_screen.dart', "'苏格拉底'", "context.l10n.simSocraticShort")
e('simulation/presentation/screens/simulation_screen.dart', "'怀疑者'", "context.l10n.simSkeptic")
e('simulation/presentation/screens/simulation_screen.dart', "'拆解者'", "context.l10n.simBreakdown")
e('simulation/presentation/screens/simulation_screen.dart', "'应用者'", "context.l10n.simApplicator")
e('simulation/presentation/screens/simulation_screen.dart', "'错因分析师'", "context.l10n.simErrorAnalyst")
e('simulation/presentation/screens/simulation_screen.dart', "'纠偏教练'", "context.l10n.simCorrectCoach")
e('simulation/presentation/screens/simulation_screen.dart', "'验证者'", "context.l10n.simValidator")
e('simulation/presentation/screens/simulation_screen.dart', "'题面解构者'", "context.l10n.simDeconstructor")
e('simulation/presentation/screens/simulation_screen.dart', "'迁移教练'", "context.l10n.simTransferCoach")
e('simulation/presentation/screens/simulation_screen.dart', "'生成'", "context.l10n.simGenerate")
e('simulation/presentation/screens/simulation_screen.dart', "'刷新'", "context.l10n.simRefresh")

# ============= COGNITIVE =============
e('cognitive/presentation/screens/capsule/capsule_detail_screen.dart', "'这枚胶囊暂时不可用'", "context.l10n.cogCapsuleUnavailable")
e('cognitive/presentation/screens/capsule/capsule_detail_screen.dart', "'胶囊打开失败'", "context.l10n.cogCapsuleOpenFailed")

# ============= INSIGHTS =============
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'学习洞察'", "context.l10n.insOverviewTitle")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'学习仿真'", "context.l10n.insSimLabel")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'推演剧场'", "context.l10n.insTheaterLabel")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'打开推演'", "context.l10n.insOpenSim")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'学习报告'", "context.l10n.insReportLabel")
e('insights/presentation/screens/learning_insights_overview_screen.dart', "'查看报告'", "context.l10n.insViewReport")
e('insights/presentation/widgets/learning_path_dialog.dart', "'查看详情'", "context.l10n.insViewDetail")
e('insights/presentation/widgets/learning_path_dialog.dart', "'生成任务卡'", "context.l10n.insGenTaskCard")
e('insights/presentation/widgets/learning_path_dialog.dart', "'生成学习计划'", "context.l10n.insGenPlan")
e('insights/presentation/widgets/learning_path_dialog.dart', "'目标节点'", "context.l10n.insTargetNode")
e('insights/presentation/widgets/learning_path_dialog.dart', "'可选拓展'", "context.l10n.insOptionalExtend")
e('insights/presentation/widgets/learning_path_dialog.dart', "'重试加载'", "context.l10n.insRetryLoad")
e('insights/presentation/widgets/weekly_growth_narrative_card.dart', "'收起'", "context.l10n.insCollapse")
e('insights/presentation/widgets/weekly_growth_narrative_card.dart', "'展开'", "context.l10n.insExpand")
e('insights/presentation/widgets/weekly_growth_narrative_card.dart', "'第一周'", "context.l10n.insFirstWeek")
e('insights/presentation/widgets/weekly_growth_narrative_card.dart', "'重试'", "context.l10n.insRetry")
e('insights/presentation/widgets/predictive_insights_card.dart', "'预测下次学习时间'", "context.l10n.insPredictNext")

# ============= CALENDAR =============
e('calendar/presentation/screens/daily_detail_screen.dart', "'标题'", "context.l10n.calTitle")
e('calendar/presentation/screens/daily_detail_screen.dart', "'全天'", "context.l10n.calAllDay")
e('calendar/presentation/screens/daily_detail_screen.dart', "'开始时间'", "context.l10n.calStartTime")
e('calendar/presentation/screens/daily_detail_screen.dart', "'结束时间'", "context.l10n.calEndTime")
e('calendar/presentation/screens/daily_detail_screen.dart', "'地点'", "context.l10n.calLocation")
e('calendar/presentation/screens/daily_detail_screen.dart', "'描述'", "context.l10n.calDescription")
e('calendar/presentation/screens/daily_detail_screen.dart', "'提醒'", "context.l10n.calReminderLabel")
e('calendar/presentation/screens/daily_detail_screen.dart', "'开始时'", "context.l10n.calAtStart")
e('calendar/presentation/screens/daily_detail_screen.dart', "'取消'", "context.l10n.calCancel")
e('calendar/presentation/screens/daily_detail_screen.dart', "'保存'", "context.l10n.calSave")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'连续天数'", "context.l10n.calStreakDays")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'活跃天数'", "context.l10n.calActiveDays")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'完成任务'", "context.l10n.calCompletedTasks")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'专注时长'", "context.l10n.calFocusDuration")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'最热的一天'", "context.l10n.calHottestDay")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'当前主线'", "context.l10n.calCurrentMainGoal")
e('calendar/presentation/screens/calendar_stats_screen.dart', "'成就势能'", "context.l10n.calAchievementMomentum")

# ============= AUTH =============
e('auth/presentation/screens/legal_document_screen.dart', "'用户协议'", "context.l10n.authTermsOfService")
e('auth/presentation/screens/legal_document_screen.dart', "'隐私政策'", "context.l10n.authPrivacyPolicy")
e('auth/presentation/screens/reset_password_screen.dart', "'重置密码'", "context.l10n.authResetPassword")
e('auth/presentation/screens/reset_password_screen.dart', "'重置码'", "context.l10n.authResetCode")
e('auth/presentation/screens/reset_password_screen.dart', "'新密码'", "context.l10n.authNewPassword")
e('auth/presentation/screens/reset_password_screen.dart', "'确认新密码'", "context.l10n.authConfirmNewPassword")
e('auth/presentation/screens/reset_password_screen.dart', "'确认重置'", "context.l10n.authConfirmReset")

# ============= REPORT =============
e('report/presentation/widgets/mastery_radar_chart.dart', "'至少需要 3 个知识点才能绘制雷达图。'", "context.l10n.reportRadarMinNodes")

# ============= TRANSLATION FEATURE =============
e('translation/presentation/widgets/translatable_text.dart', "'翻译'", "context.l10n.transTranslate")
e('translation/presentation/widgets/translatable_text.dart', "'复制'", "context.l10n.transCopy")
e('translation/presentation/widgets/translation_popover.dart', "'已保存'", "context.l10n.transSaved")
e('translation/presentation/widgets/translation_popover.dart', "'生词卡'", "context.l10n.transWordCard")

# ============= AURORA =============
e('aurora/presentation/widgets/aurora_calibration_strip.dart', "'确认'", "context.l10n.auroraConfirm")
e('aurora/presentation/widgets/aurora_core_session_sheet.dart', "'退出校准'", "context.l10n.auroraExitCalibration")
e('aurora/presentation/widgets/aurora_core_session_sheet.dart', "'关闭'", "context.l10n.auroraClose")
e('aurora/presentation/widgets/aurora_core_session_sheet.dart', "'取消'", "context.l10n.toolsWbCancel")
e('aurora/presentation/widgets/aurora_core_session_sheet.dart', "'发送'", "context.l10n.auroraSend")

# ============= SEED LIBRARY =============
e('seed_library/presentation/widgets/seed_item_card.dart', "'分享'", "context.l10n.seedShare")
e('seed_library/presentation/widgets/seed_item_card.dart', "'编辑'", "context.l10n.seedEdit")
e('seed_library/presentation/widgets/seed_item_card.dart', "'删除'", "context.l10n.seedDelete")
e('seed_library/presentation/widgets/seed_item_card.dart', "'取消'", "context.l10n.toolsWbCancel")

# ============= ERROR BOOK =============
e('error_book/presentation/screens/add_error_screen.dart', "'移除'", "context.l10n.ebRemove")
e('error_book/presentation/screens/add_error_screen.dart', "'保存中...'", "context.l10n.ebSaving")
e('error_book/presentation/screens/add_error_screen.dart', "'保存'", "context.l10n.ebSave")
e('error_book/presentation/screens/add_error_screen.dart', "'章节（可选）'", "context.l10n.ebChapterOptional")
e('error_book/presentation/screens/add_error_screen.dart', "'题目内容'", "context.l10n.ebQuestionContent")
e('error_book/presentation/screens/add_error_screen.dart', "'你的答案 *'", "context.l10n.ebYourAnswer")
e('error_book/presentation/screens/add_error_screen.dart', "'正确答案 *'", "context.l10n.ebCorrectAnswer")
e('error_book/presentation/screens/review_screen.dart', "'隐藏'", "context.l10n.ebHide")
e('error_book/presentation/screens/review_screen.dart', "'查看答案'", "context.l10n.ebViewAnswer")
e('error_book/presentation/screens/review_screen.dart', "'查看 AI 分析'", "context.l10n.ebViewAnalysis")
e('error_book/presentation/screens/review_screen.dart', "'返回'", "context.l10n.ebBack")
e('error_book/presentation/screens/review_screen.dart', "'返回列表'", "context.l10n.ebBackToList")
e('error_book/presentation/screens/review_screen.dart', "'再来一轮'", "context.l10n.ebAnotherRound")
e('error_book/presentation/screens/review_screen.dart', "'重试'", "context.l10n.ebRetry")
e('error_book/presentation/screens/review_screen.dart', "'确认退出'", "context.l10n.ebConfirmExit")
e('error_book/presentation/screens/review_screen.dart', "'继续复习'", "context.l10n.ebContinueReview")
e('error_book/presentation/screens/review_screen.dart', "'退出'", "context.l10n.ebExit")

# Review performance buttons
e('error_book/presentation/widgets/review_performance_buttons.dart', "'忘记了'", "context.l10n.ebForgot")
e('error_book/presentation/widgets/review_performance_buttons.dart', "'有点模糊'", "context.l10n.ebFuzzy")
e('error_book/presentation/widgets/review_performance_buttons.dart', "'记住了'", "context.l10n.ebRemembered")
e('error_book/presentation/widgets/review_performance_buttons.dart', "'取消'", "context.l10n.toolsWbCancel")

# Subject chips
e('error_book/presentation/widgets/subject_chips.dart', "'数学'", "context.l10n.ebMath")
e('error_book/presentation/widgets/subject_chips.dart', "'物理'", "context.l10n.ebPhysics")
e('error_book/presentation/widgets/subject_chips.dart', "'化学'", "context.l10n.ebChemistry")
e('error_book/presentation/widgets/subject_chips.dart', "'生物'", "context.l10n.ebBiology")
e('error_book/presentation/widgets/subject_chips.dart', "'英语'", "context.l10n.ebEnglish")
e('error_book/presentation/widgets/subject_chips.dart', "'语文'", "context.l10n.ebChinese")
e('error_book/presentation/widgets/subject_chips.dart', "'其他'", "context.l10n.ebOther")

# Visual elements screen
e('visual_elements/presentation/screens/visual_elements_screen.dart', "'自由搭配'", "context.l10n.visualMixMatch")
e('visual_elements/presentation/screens/visual_elements_screen.dart', "'清除筛选'", "context.l10n.visualClearFilter")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'影响场景'", "context.l10n.visualAffectedScenes")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'收藏进度'", "context.l10n.visualCollectionProgress")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'套装部件'", "context.l10n.visualSetParts")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'正在体验'", "context.l10n.visualPreviewing")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'当前外观'", "context.l10n.visualCurrentLook")
e('visual_elements/presentation/widgets/visual_element_preview_dialog.dart', "'点按切换'", "context.l10n.visualTapToggle")

# Memory widgets
e('memory/presentation/widgets/evidence_cards.dart', "'证据记录'", "context.l10n.memEvidenceRecord")
e('memory/presentation/widgets/evidence_cards.dart', "'去星图看'", "context.l10n.memGoGalaxy")
e('memory/presentation/widgets/evidence_cards.dart', "'去错题本看'", "context.l10n.memGoErrorBook")
e('memory/presentation/widgets/evidence_cards.dart', "'打开相关对话'", "context.l10n.memOpenRelatedChat")
e('memory/presentation/widgets/evidence_cards.dart', "'打开原对话'", "context.l10n.memOpenOriginalChat")
e('memory/presentation/widgets/evidence_drawer.dart', "'证据记录'", "context.l10n.memEvidenceRecord")
e('memory/presentation/widgets/unresolved_conflicts_section.dart', "'跳过'", "context.l10n.memSkip")

# Register screen
e('auth/presentation/screens/register_screen.dart', "'查看用户协议'", "context.l10n.authViewTerms")
e('auth/presentation/screens/register_screen.dart', "'查看隐私政策'", "context.l10n.authViewPrivacy")

# ============= EXECUTE REPLACEMENTS =============
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

    # Add import if content has context.l10n references
    if content != original:
        if "context.l10n." in content and "context_l10n.dart" not in content:
            # Find last import line
            import_pattern = re.compile(r"(import ['\"].*?['\"];)\n", re.MULTILINE)
            imports = list(import_pattern.finditer(content))
            if imports:
                last_import = imports[-1]
                insert_pos = last_import.end()
                content = content[:insert_pos] + L10N_IMPORT + "\n" + content[insert_pos:]

        with open(filepath, 'w') as f:
            f.write(content)
        print(f"UPDATED: {filepath} ({len(edits)} edits)")

print(f"\nTotal replaced: {total_replaced}")
print(f"Total not found: {total_not_found}")
print(f"Total files updated: {len([f for f in file_edits if os.path.exists(f)])}")
