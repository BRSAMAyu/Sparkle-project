#!/usr/bin/env python3
"""Phase 2: Replace hardcoded Chinese strings in Dart files with context.l10n.xxx references."""
import re, os, sys

BASE = '/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features'

# Map: Chinese string -> (l10n_key, has_params)
# Only user-visible strings (Text, title, label, hint, etc.)
REPLACEMENTS = {
    # Focus Timer Tool
    "focus_timer_tool.dart": [
        ("'番茄钟'", "context.l10n.toolsFocusPomodoro"),
        ("'专注计时'", "context.l10n.toolsFocusStopwatch"),
        ("'把单次专注收束成稳定节奏。适合复习块、冲刺块和长时深潜。'", "context.l10n.toolsFocusPomodoroSubtitle"),
        ("'正计时和倒计时同台使用，适合任务推进、自由练习和时间校准。'", "context.l10n.toolsFocusStopwatchSubtitle"),
        ("'倒计时模式'", "context.l10n.toolsCountdownMode"),
        ("'正计时模式'", "context.l10n.toolsStopwatchMode"),
        ("'进行中'", "context.l10n.toolsStatusRunning"),
        ("'待开始'", "context.l10n.toolsStatusPending"),
        ("'主计时盘'", "context.l10n.toolsMainTimer"),
        ("'直接开始、暂停或重置。计时完成后会给出本地提示。'", "context.l10n.toolsMainTimerDesc"),
        ("'当前时长'", "context.l10n.toolsCurrentDuration"),
        ("'预计结束'", "context.l10n.toolsEstimatedEnd"),
        ("'背景音'", "context.l10n.toolsBgAudio"),
        ("'计时期间播放，有助于进入专注状态。'", "context.l10n.toolsBgAudioDesc"),
        ("'计时设置'", "context.l10n.toolsTimerSettings"),
        ("'先选模式，再选时长。'", "context.l10n.toolsTimerSettingsDesc"),
        ("'正计时'", "context.l10n.toolsCountUp"),
        ("'倒计时'", "context.l10n.toolsCountDown"),
        ("'重置'", "context.l10n.toolsReset"),
        ("'切到倒计时'", "context.l10n.toolsSwitchToCountdown"),
        ("'切到正计时'", "context.l10n.toolsSwitchToStopwatch"),
        ("'番茄时段已完成 🎉'", "context.l10n.toolsPomodoroCompleteEmoji"),
        ("'倒计时已结束'", "context.l10n.toolsCountdownEnded"),
        ("'开放'", "context.l10n.toolsOpenDuration"),
        ("'单次目标时长'", "context.l10n.toolsSingleGoalDuration"),
        ("'适合追踪投入长度'", "context.l10n.toolsTrackEffort"),
        ("'不限'", "context.l10n.toolsNoLimit"),
        ("'由你主动暂停'", "context.l10n.toolsPauseManually"),
        ("'方便衔接下一段计划'", "context.l10n.toolsPlan衔接"),
    ],
}

# Actually, let me do it differently - process each file directly with targeted replacements

def process_file(filepath, replacements, needs_import=True):
    """Process a single file, applying replacements."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"  Replaced: {old[:50]}...")
        else:
            print(f"  NOT FOUND: {old[:50]}...")

    # Add import if needed and not already present
    if needs_import and "context.l10n." in content and "context_l10n.dart" not in content:
        # Find last import line
        import_pattern = re.compile(r"(import ['\"].*?['\"];)\n", re.MULTILINE)
        imports = list(import_pattern.finditer(content))
        if imports:
            last_import = imports[-1]
            insert_pos = last_import.end()
            content = content[:insert_pos] + "import 'package:sparkle/core/extensions/context_l10n.dart';\n" + content[insert_pos:]
            print(f"  Added context_l10n import")

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False


# ============= PROCESS ALL FILES =============

print("=" * 60)
print("Processing FOCUS TIMER TOOL")
print("=" * 60)
process_file(f"{BASE}/tools/presentation/widgets/focus_timer_tool.dart", [
    # Build method strings
    ("'番茄钟'", "context.l10n.toolsFocusPomodoro"),
    ("'专注计时'", "context.l10n.toolsFocusStopwatch"),
    ("'把单次专注收束成稳定节奏。适合复习块、冲刺块和长时深潜。'", "context.l10n.toolsFocusPomodoroSubtitle"),
    ("'正计时和倒计时同台使用，适合任务推进、自由练习和时间校准。'", "context.l10n.toolsFocusStopwatchSubtitle"),
    ("'倒计时模式'", "context.l10n.toolsCountdownMode"),
    ("'正计时模式'", "context.l10n.toolsStopwatchMode"),
    ("'进行中'", "context.l10n.toolsStatusRunning"),
    ("'待开始'", "context.l10n.toolsStatusPending"),
    ("'主计时盘'", "context.l10n.toolsMainTimer"),
    ("'直接开始、暂停或重置。计时完成后会给出本地提示。'", "context.l10n.toolsMainTimerDesc"),
    ("'当前时长'", "context.l10n.toolsCurrentDuration"),
    ("'预计结束'", "context.l10n.toolsEstimatedEnd"),
    ("'背景音'", "context.l10n.toolsBgAudio"),
    ("'计时期间播放，有助于进入专注状态。'", "context.l10n.toolsBgAudioDesc"),
    ("'计时设置'", "context.l10n.toolsTimerSettings"),
    ("'先选模式，再选时长。'", "context.l10n.toolsTimerSettingsDesc"),
    ("'正计时'", "context.l10n.toolsCountUp"),
    ("'倒计时'", "context.l10n.toolsCountDown"),
    ("'重置'", "context.l10n.toolsReset"),
    ("'切到倒计时'", "context.l10n.toolsSwitchToCountdown"),
    ("'切到正计时'", "context.l10n.toolsSwitchToStopwatch"),
    ("'番茄时段已完成 🎉'", "context.l10n.toolsPomodoroCompleteEmoji"),
    ("'倒计时已结束'", "context.l10n.toolsCountdownEnded"),
    ("'开放'", "context.l10n.toolsOpenDuration"),
    ("'单次目标时长'", "context.l10n.toolsSingleGoalDuration"),
    ("'适合追踪投入长度'", "context.l10n.toolsTrackEffort"),
    ("'不限'", "context.l10n.toolsNoLimit"),
    ("'由你主动暂停'", "context.l10n.toolsPauseManually"),
    ("'方便衔接下一段计划'", "context.l10n.toolsPlan衔接"),
])

print("\nDone processing focus_timer_tool.dart")
