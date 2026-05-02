# Sparkle User-Visible Experience Bridge Report — 2026-05-02

## Scope

本轮执行 `Sparkle 完全体体验收口计划` 的第一条纵向体验链：把 Aurora / Spine / Goal / Growth / Community 的后端能力聚合成用户可以直接感知的产品表面。重点不是新增孤立功能，而是让用户在首页与社区首屏看到：

- Sparkle 当前如何理解我，以及它可能哪里误读了。
- 当前目标的最低达标线、进度、下一步和知识地图瓶颈。
- 连胜不只是天数，而是带证据的坚持质量。
- 社区默认是目标问责空间，而不是普通社交 feed。

## Changes

### Backend

- 新增 `backend/app/api/v1/experience.py`，提供体验聚合 BFF：
  - `GET /experience/understanding-snapshot`
  - `GET /experience/goal-detail/{goal_id}`，支持 `current` / `active`
  - `GET /experience/growth-dashboard`
  - `GET /experience/community-accountability`
- 在 `backend/app/api/v1/router.py` 注册 experience router。
- 聚合复用现有能力：`AuroraControlSurfaceService`、`GrowthDashboardService`、`ProgressNarrativeService`、`Goal` ORM、`Plan`、`Task`、`GoalWorldGraph`、`UserStreakStats`、`FocusSession`。

### Mobile

- 新增 `features/experience` 数据层和 provider：
  - `UnderstandingSnapshot`
  - `GoalDetailSnapshot`
  - `ExperienceGrowthDashboard`
  - `StreakQuality`
  - `CommunityAccountabilitySnapshot`
- 新增用户可见组件：
  - `UnderstandingSnapshotCard`
  - `GoalDetailSnapshotCard`
  - `GrowthQualityCard`
  - `CommunityAccountabilityHubCard`
- 首页接入理解快照、目标详情和坚持质量卡。
- 社区首屏接入目标问责卡，强化“承诺 / 伙伴 / 进度”优先级。
- 清理首页中未接线的私有占位 slot，避免 analyzer 硬错误。

## Acceptance Evidence

| Check | Result |
|---|---|
| `python3 -m py_compile backend/app/api/v1/experience.py backend/app/api/v1/router.py` | PASS |
| `cd backend && ruff check app/api/v1/experience.py app/api/v1/router.py` | PASS |
| `cd backend && black --check app/api/v1/experience.py app/api/v1/router.py` | PASS |
| `cd mobile && flutter analyze --no-fatal-infos ...experience... dashboard_screen.dart community_screen.dart` | PASS, info-only style findings remain |

## Remaining Experience Work

- Source explanation is already partly covered by `ContextReceiptBar` / citation strip; next pass should unify it into a named `SourceExplanationCard` surface in chat metadata tray.
- Goal detail currently opens through plan navigation; a dedicated route can further polish the goal-centered mental model.
- Community accountability endpoint is intentionally conservative; it should be backed by richer partner/commitment data after the current UI frame is stable.
- Full visual QA still needs device screenshots after the shared worktree settles.
