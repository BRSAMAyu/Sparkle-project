# Changelog

## 1.0.0 - 2026-03-22

### Added
- Unified multi-sensory experience system across Flutter high-traffic flows.
- Five experience profiles covering dashboard, assistant, focus, social, and celebration scenes.
- Shared motion primitives including stagger, exit transition, attention pulse, and reusable confetti.
- Sensory budget enforcement to throttle excessive haptic and audio feedback.
- Route-aware BGM and ambient audio policies with preload and fade handling.
- Accessibility hardening for reduce-motion, large text, semantic labels, and calmer empty/loading/error states.
- Blue/green deployment pipeline, deployment verification, backup, and restore scripts.

### Changed
- Chat, dashboard, task, focus, community, achievement, galaxy, plan, utility, auth, onboarding, and settings screens now use a consistent motion and sensory baseline.
- `ActionCard` specialized cards now default to dedicated layouts instead of being collapsed by generic metadata heuristics.
- Authentication session tracking now uses a PostgreSQL upsert path to avoid duplicate `user_sessions.session_id` failures under repeated live integration runs.
- Backend auth/session logging now degrades safely if `structlog` is unavailable, while dependencies now declare it explicitly.
- Flutter auth repository test storage mock now matches the current secure storage delete signature.
- WebSocket chat service tests now wait deterministically for async event delivery under full-suite load.

### Fixed
- Full Flutter suite regressions caused by collapsed action cards, stale secure storage mocks, and flaky websocket event timing.
- Live local full-stack smoke failures caused by missing backend `structlog` dependency.
- Duplicate source asset under `mobile/assets/icons/`.

### Security
- Backend bare `except:` cleanup completed in app runtime paths.
- TODO/FIXME markers in primary runtime directories were either removed or moved into tracked debt documentation.
- `.env` remains ignored and untracked in repository state; follow provider-side rotation policy for external keys.

### Accessibility
- Reduce-motion now disables shared pulse/shimmer paths where applicable.
- Shared state widgets now expose stronger semantics and safer live regions.
- Large-font rendering for empty/loading/error states is more stable.

### Operations
- Monitoring stack, SLO alerts, baseline production alerts, and incident runbooks are included in repo and referenced by release snapshot.
