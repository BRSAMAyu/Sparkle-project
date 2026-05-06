# QA Round 5 Tracker

> **Date**: 2026-05-06 | **Report**: QA_ROUND5_2026-05-06.md
> **Status**: COMPLETE (P0: 1/2, P1: 6/6, P2: 0/2 deferred)

## P0 — 必修 (user-perceivable)

| # | 问题 | 文件 | 状态 | Commit |
|---|------|------|------|--------|
| P0-1 | Task Detail 仅 1 个 Semantics (H1 误报已修复) | task_detail_screen.dart | ✅ done | TBD |
| P0-2 | Chat screen 仅 1 个 Semantics (~4000 lines) | chat_screen.dart | ⏳ deferred | — |

## P1 — 应修 (experience impact)

| # | 问题 | 文件 | 状态 | Commit |
|---|------|------|------|--------|
| P1-1 | scenario_pack_service 4/4 方法静默吞没错误 | scenario_pack_service.dart | ✅ done | TBD |
| P1-2 | sprint_screen:173 裸 CircularProgressIndicator | sprint_screen.dart | ✅ done | TBD |
| P1-3 | task_detail_screen 3 处裸 spinner（无 skeleton） | task_detail_screen.dart | ✅ done | TBD |
| P1-4 | Galaxy screen 零 Semantics | galaxy_screen.dart | ✅ done | TBD |
| P1-5 | Reduce motion 14.6% 覆盖率 | 多个文件 | ✅ done (24 files, +2) | TBD |
| P1-6 | JourneyProgressCard 无 Semantics | journey_progress_card.dart | ✅ done | TBD |

## P2 — 改进

| # | 问题 | 状态 | Commit |
|---|------|------|--------|
| P2-1 | ExperienceEnvelope 仅用 3/7 字段 | ⏳ deferred | — |
| P2-2 | 114 文件的 CircularProgressIndicator 批量消除 | ⏳ deferred | — |

## Details

### P0-1: Task Detail Semantics
- Added Semantics wrappers to 4 additional sections: Note, Subtask, Guide, Info
- Screen went from 1 → 5 Semantics widgets (1281 lines)
- Used existing ARB keys for labels (taskDetailNoteSection, taskDetailSubtasks, taskGuideTitle)

### P1-1: scenario_pack_service error handling
- Removed 4 silent try/catch swallows — exceptions now propagate to callers
- Callers use FutureProvider.when() pattern which already handles errors
- Added try/catch in _loadMatchedPack() call site since it uses unawaited()

### P1-2: sprint_screen bare spinner
- Replaced line 173 `CircularProgressIndicator` with existing `_SprintSkeleton()`

### P1-3: task_detail_screen 3 spinners → skeleton
- Subtask loading: `CircularProgressIndicator` → `SparkleSkeleton(height: 40)`
- Plan context loading: `CircularProgressIndicator` → `SparkleSkeleton(width: 18, height: 18)`
- Generate button loading: `CircularProgressIndicator` → `SparkleSkeleton(width: 20, height: 20)`

### P1-4: Galaxy screen Semantics
- Added Semantics wrapper around entire galaxy Scaffold with label `context.l10n.galaxy`
- Screen went from 0 → 1 Semantics widget (physics-based rendering limits deeper integration)

### P1-5: Reduce motion coverage
- Added reduceMotion checks to achievement_unlock_dialog.dart (4 controllers)
- Added reduceMotion to star_success_animation.dart (1 controller)
- Added reduceMotion to milestone_celebration_screen.dart (1 controller)
- Added reduceMotion to _InfoTileCard in task_detail_screen.dart (1 controller)
- Total files with reduceMotion: 22 → 24

### P1-6: JourneyProgressCard Semantics
- Added Semantics wrapper with progress percentage label

## Deferred
- P0-2: Chat screen needs structural widget rework for Semantics (~4000 lines)
- P2-1: ExperienceEnvelope 3/7 fields — needs backend data model changes
- P2-2: 114-file batch skeleton upgrade — excessive blast radius

## Notes
- All changes compile clean (verified with `dart analyze`)
- Pre-existing community/tool/user feature errors unrelated to changes
- Chat screen Semantics requires careful widget extraction before Semantics can be added
