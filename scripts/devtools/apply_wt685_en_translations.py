#!/usr/bin/env python3
"""Apply the wt685 V3-FIX-362 EN translation batch to mobile/lib/l10n/app_en.arb.

One-shot, explicit map (no machine translation): every entry was hand-translated
from the zh template value, matching house terminology (Error Book/error for
错题, check-in for 打卡, Sprint for 冲刺, foresight hint for 前瞻提示) and
sentence-case for messages/hints/status lines.

Keys intentionally NOT translated (residual review list, house-consistent
adequate copy — see REPORT): ebAddError/ebEditError/ebSaveError/
errorBookAddError/errorBookAddFirst/sendMessageLabel/communityTaskTitleField +
15 faithful single-token labels ('Title'/'Failed'/'Error'/'Success' where the
en value already equals the zh meaning).

Run from repo root: python3 scripts/devtools/apply_wt685_en_translations.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TRANSLATIONS: dict[str, str] = {
    # ── chat family ──
    "chatActionErrorTitle": "Action error",
    "chatActionStatusFailed": "Failed",
    "chatActionTitleAddError": "Add error",
    "chatBlockedInputTitle": "Input blocked",
    "chatCollabTimelineTitle": "Collaboration timeline",
    "chatExecutionFailed": "Execution failed",
    "chatFocusSprintDefaultTitle": "Focus sprint",
    "chatModeCustomTeamDesc": "Pick specific AI assistants to form your own team",
    "chatModeSuggestionTitle": "Mode suggestion",
    "chatNextActionsRetryHint": "Tap to retry",
    "chatNextActionsTitle": "Next actions",
    "chatNotificationGroupMessage": "Group message",
    "chatOptionalNotesHint": "Optional notes...",
    "chatOrchestrationTraceTitle": "Orchestration trace",
    "chatPlanEmptySubtitle": "No plans yet — go ahead and create one",
    "chatPlanEmptyTitle": "No plans yet",
    "chatReflectionFailed": "Reflection failed",
    "chatWorkflowDebateSubtitle": "Explore from multiple angles",
    "chatWorkflowDebateTitle": "Debate mode",
    "chatWorkflowDelegationSubtitle": "Delegate to specialist assistants",
    "chatWorkflowDelegationTitle": "Delegation mode",
    "chatWorkflowParallelSubtitle": "Work on multiple tasks in parallel",
    "chatWorkflowStatusError": "Error",
    # ── community family ──
    "communityAgentPromptHint": "Enter a prompt...",
    "communityChatTitle": "Community chat",
    "communityCheckInDurationLabel": "Duration",
    "communityCheckInMessageHint": "Share how it went...",
    "communityCheckInMessageLabel": "Check-in note",
    "communityCheckInSuccess": "Check-in successful!",
    "communityCheckInTitle": "Daily check-in",
    "communityFileSharedSuccess": "File shared",
    "communityMessageInputHint": "Type a message...",
    # ── doc cleaner / error book / execution ──
    "docCleanerFailedTitle": "Cleaning failed",
    "errorBookImageLoadFailed": "Failed to load image",
    "executionSelfVerificationHint": "Self-check hint",
    "fcCalculationError": "Calculation error",
    "fileStatusFailed": "Upload failed",
    "galaxyNodeImageError": "Image-based error",
    # ── memory / foresight ──
    "memoryPanelForesightHint": "Foresight hint",
    "userForesightHint": "Foresight hint",
    # ── password ──
    "passwordSetHint": "Enter a password of at least 8 characters",
    "passwordSetLabel": "Set password",
    "passwordSetSuccess": "Password set",
    "passwordSetTitle": "Set password",
    # ── plan family ──
    "planArchiveMessage": "Once archived, this plan moves to history. Archive it?",
    "planArchiveTitle": "Archive plan",
    "planArchivedSuccess": "Plan archived",
    "planContextTitle": "Plan context",
    "planDetailLoadError": "Failed to load plan",
    "planDetailTitle": "Plan details",
    "planProgressLabel": "Plan progress",
    "planRestoredSuccess": "Plan restored",
    "planReviewAdditionalNotesHint": "Add a note (optional)...",
    "planReviewRejectReasonTitle": "Reason for rejection",
    # ── regen family ──
    "regenCustomHint": "Describe the changes you want...",
    "regenDescFailed": "Regeneration failed",
    "regenImprovementsTitle": "Improvement suggestions",
    "regenProgressTitle": "Regeneration progress",
    "regenResultFailed": "Generation failed",
    "regenResultSuccess": "Generated",
    "regenRetryMessage": "Tap to retry",
    "regenTitleFailed": "Regeneration failed",
    # ── review rating family ──
    "reviewRatingAccuracyTitle": "Accuracy",
    "reviewRatingCommentsHint": "Write your feedback...",
    "reviewRatingCommentsTitle": "Your feedback",
    "reviewRatingInaccuratePointHint": "Describe what was off...",
    "reviewRatingInaccuratePointsTitle": "What was off",
    "reviewRatingSpecificityTitle": "Specificity",
    "reviewRatingSubmitFailed": "Submission failed",
    "reviewRatingSubmitSuccess": "Feedback submitted",
    "reviewRatingSubtitle": "Your feedback helps me improve",
    "reviewRatingTagsTitle": "Pick tags",
    "reviewRatingTitle": "Rate this reply",
    # ── security / sprint family ──
    "securityLogActionLoginFailed": "Login failed",
    "sprintActionAbandonSubtitle": "Give up the current sprint",
    "sprintActionAbandonTitle": "Abandon sprint",
    "sprintActionCompleteSubtitle": "Mark this sprint as done",
    "sprintActionCompleteTitle": "Finish sprint",
    "sprintActionExtendSubtitle": "Extend the sprint",
    "sprintActionExtendTitle": "Extend sprint",
    "sprintActionsTitle": "Sprint actions",
    "sprintConfirmAbandonDesc": "Abandon this sprint? Unfinished tasks will be kept.",
    "sprintConfirmAbandonTitle": "Confirm abandon",
    "sprintConfirmCompleteDesc": "Sprint finished — mark it as done?",
    "sprintConfirmCompleteTitle": "Confirm completion",
    "sprintDurationDaysLabel": "Days",
    "sprintDurationLabel": "Duration",
    "sprintEndDateLabel": "End date",
    "sprintExtendTitle": "Extend sprint",
    "sprintInfoTitle": "Sprint info",
    "sprintProgressTitle": "Sprint progress",
    "sprintStartDateLabel": "Start date",
    "sprintStatsTitle": "Sprint stats",
    "sprintStatusLabel": "Sprint status",
    "sprintTaskSummaryTitle": "Task summary",
    "statusFailed": "Failed",
    # ── task family ──
    "taskChatAssistantTitle": "Task assistant",
    "taskChatInputHint": "Type a message...",
    "taskCreateSuccess": "Task created",
    "taskCreateTitle": "Create task",
    "taskDeadlineLabel": "Deadline",
    "taskDeleteTitle": "Delete task",
    "taskDifficultyLabel": "Difficulty",
    "taskEnergyCostLabel": "Energy cost",
    "taskEstimatedDurationLabel": "Estimated time",
    "taskExecutionCompleteTitle": "Finish task",
    "taskExecutionNoteHint": "Add a note...",
    "taskExecutionNoteLabel": "Execution note",
    "taskExecutionSyncFailed": "Sync failed",
    "taskExecutionTimerLabel": "Timer",
    "taskGenerateGuideSubtitle": "AI is writing the execution guide...",
    "taskGenerateGuideTitle": "Generate execution guide",
    "taskGuideTitle": "Task guide",
    "taskNudgeTitle": "Task suggestion",
    "taskReminderEnableSubtitle": "Turn on task reminders",
    "taskReminderEnableTitle": "Turn on reminders",
    "taskReminderInfoTitle": "About reminders",
    "taskReminderRefreshSuccess": "Reminders refreshed",
    "taskReminderSettingsTitle": "Reminder settings",
    "taskReminderTimesTitle": "Reminder times",
    "taskTagsHint": "Add tags...",
    "taskTagsLabel": "Tags",
    "taskTitleHint": "Enter a task title...",
    "taskTitleLabel": "Task title",
    "taskTypeLabel": "Task type",
    "toolsTransFailed": "Translation failed",
    # ── singles with more specific zh meaning ──
    "contentReviewReflectionFailedShort": "Optimization failed",
    "executionStatusFailed": "Execution failed",
    "operationFailed": "Operation failed",
    "studyMaterialsStatusFailed": "Processing failed",
    # ── weekly agenda ──
    "weeklyAgendaCollapsedHint": "Expand to see the full week",
    "weeklyAgendaEmptyHint": "Nothing scheduled this week",
}


def main() -> int:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    arb_path = repo / "mobile/lib/l10n/app_en.arb"
    data = json.loads(arb_path.read_text(encoding="utf-8"))

    missing = [k for k in TRANSLATIONS if k not in data]
    if missing:
        print(f"ABORT: keys missing from app_en.arb: {missing}")
        return 1

    changed = 0
    for k, v in TRANSLATIONS.items():
        if data[k] != v:
            data[k] = v
            changed += 1
    # preserve key order + 2-space indent like the checked-in artifact
    ordered = {k: data[k] for k in data}
    arb_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied: {changed} values changed (map size {len(TRANSLATIONS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
