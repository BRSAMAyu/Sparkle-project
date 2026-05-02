# Sparkle Data Export / Delete Flow Map

> Created: 2026-05-01 | Purpose: C25 compliance deliverable — map existing API surface for GDPR data subject rights

## 1. Data Export Flow

### API Endpoint
```
GET /api/v1/me/export
Authorization: Bearer <JWT>
```

### Implementation
`backend/app/api/v1/data_export.py`

### Flow
1. User requests export (Settings → Privacy → Export Data, or direct API call)
2. Server rate-limits exports to 1 per 60 seconds per user (Redis-based, graceful fallback if Redis unavailable)
3. Server queries all user-owned data from 11 data categories:
   - Profile, Plans, Tasks, ErrorBook, FocusSessions, CalendarEvents, ChatSessions, Achievements, Notifications, NotificationInteractions, UserSettings
4. Data is serialized to JSON (passwords redacted, timestamps ISO-formatted)
5. JSON files are packaged into a ZIP archive
6. ZIP is streamed to the user with `Content-Disposition: attachment`

### Format
```
sparkle_export_YYYYMMDD_HHMMSS.zip
└── sparkle_export_YYYYMMDD_HHMMSS/
    ├── profile.json
    ├── plans.json
    ├── tasks.json
    ├── error_book.json
    ├── focus_sessions.json
    ├── calendar_events.json
    ├── chat_sessions.json
    ├── achievements.json
    ├── notifications.json
    ├── notification_interactions.json
    └── user_settings.json
```

### Gaps Tracked
| ID | Gap | Priority | Status |
|----|-----|----------|--------|
| DX-001 | No Flutter UI screen for data export (API only, no settings integration) | P2 | Tracked for C22/follow-up |
| DX-002 | Chat messages content (not just session metadata) not included in export | P2 | Tracked — chat history is accessible via API |
| DX-003 | Galaxy/knowledge graph nodes not included in export | P2 | Add `galaxy_nodes.json` category |
| DX-004 | Community posts/shares not included in export | P3 | Add community content category |

## 2. Account Deletion Flow

### API Endpoint
```
POST /api/v1/me/delete
Authorization: Bearer <JWT>
Body: { "password": "<current>", "provider": "google|apple|wechat", "provider_token": "<token>" }
```

### Implementation
`backend/app/api/v1/users.py` (lines ~500-573)

### Flow
1. **Re-authentication**: User must verify identity via password or social provider token
2. **Immediate anonymization** (soft delete):
   - `is_active = False`
   - Username → `deleted_<uuid12>`
   - Email → `deleted_<uuid>@deleted.local`
   - Nickname → `"Deleted User"`
   - Avatar URL → `None`
   - Social IDs (Google, Apple, WeChat) → `None`
   - Email verified → `False`
   - Password login → disabled
   - All active sessions revoked
3. **30-day grace period**: Data retained in anonymized form for recovery
4. **Hard delete scheduled**: Celery task `purge_deleted_account` fires after 30 days
5. **Permanent purge**: All remaining records permanently deleted

### Recovery
During the 30-day grace period, users can contact support to restore their account. After 30 days, deletion is irreversible.

### Gaps Tracked
| ID | Gap | Priority | Status |
|----|-----|----------|--------|
| DL-001 | No admin dashboard for viewing pending account deletions | P3 | Tracked |
| DL-002 | Hard-delete Celery task not verified with integration test | P2 | Add to C30 E2E suite |
| DL-003 | No bulk export/deletion API for admin compliance requests | P3 | Tracked |

## 3. Privacy Controls Inventory

### Existing
| Control | Location | Type |
|---------|----------|------|
| Data export API | `GET /api/v1/me/export` | API |
| Account deletion | `POST /api/v1/me/delete` | API |
| User profile update | `PUT /api/v1/me` | API |
| Preferences update | `PUT /api/v1/me/preferences` | API |
| PII redaction (Aurora) | `backend/app/aurora/privacy.py` | Backend |
| Chat history visibility | `UserSettings.transparency_level` | Model |
| AI reasoning mode | `UserSettings.ai_reasoning_mode` | Model |
| Notification control | `UserSettings.task_reminders_enabled` | Model |

### Gaps
| ID | Gap | Priority | Status |
|----|-----|----------|--------|
| PC-001 | No explicit "AI Memory" toggle (enable/disable profile learning) | P1 | Tracked |
| PC-002 | No UI for viewing/deleting individual learned profile items | P1 | Tracked |
| PC-003 | No "Download My Data" button in Flutter settings | P2 | API exists, UI missing |
| PC-004 | No "Delete Account" flow in Flutter settings (API only) | P2 | API exists, UI missing |
| PC-005 | No data retention period setting | P3 | Default is 30-day soft delete |

## 4. Sensitive AI Memory Data Map

| Data Category | Storage | Encrypted | User-Visible | Deletable |
|--------------|---------|-----------|-------------|-----------|
| Explicit preferences (user-stated) | PostgreSQL `profile_preferences` | No (DB-level) | Yes (chat + profile) | Yes |
| Inferred preferences (tentative) | PostgreSQL `profile_preferences` with `_confidence` + `_status=tentative` | No (DB-level) | Yes (profile) | Yes |
| Cognitive behavior fragments | PostgreSQL `cognitive_fragments` | No (DB-level) | No (internal) | Via account delete |
| Bayesian posterior state | Redis + PostgreSQL | No | No (internal) | Via account delete |
| Correction history | PostgreSQL via `CorrectionFeedbackProcessor` | No (DB-level) | Partially (chat) | Via account delete |
| Task completion patterns | PostgreSQL `tasks` + `focus_sessions` | No (DB-level) | Yes (insights) | Via account delete |
| Emotional/motivation signals | PostgreSQL + Redis cache | No (DB-level) | Partially (Aurora band) | Via account delete |

**Data classification note**: All AI memory data is classified as "personal data" under GDPR. None of it is shared with third parties beyond the LLM provider (for the current request context only, with PII redacted).
