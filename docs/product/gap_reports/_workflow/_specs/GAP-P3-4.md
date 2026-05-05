# GAP-P3-4: 数据删除/导出 — Data Sovereignty (GROW-009+)

> **Source**: GROW-009 (Achievement/Growth Recall Gap Report) + GDPR Compliance Layer
> **Date**: 2026-05-06
> **Author**: Claude Opus Plan Agent
> **Level**: L3 (Cross-Boundary — Python backend API + Flutter settings UI + MinIO storage)
> **Effort**: M (3-5 days)
> **Status**: Draft

---

## 1. Objectives

### 1.1 Why This Exists

GROW-009 identifies two critical gaps:

1. **No delete functionality** — GrowthChronicle entries can be hidden or rejected but never permanently deleted. The broader account purge (scheduled 30 days after soft-delete) is a blunt instrument that does not allow individual chronicle entry deletion.
2. **No export functionality** — The existing `GET /users/me/export` endpoint covers basic models but is missing 10+ data categories (chronicle, cognitive fragments, memory, Galaxy, community, etc.) and has no per-category control.

Beyond GROW-009, a GDPR-style data sovereignty audit reveals three additional gaps:

3. **No MinIO file cleanup on purge** — The 30-day `purge_deleted_account` Celery task deletes DB rows but does not remove user-uploaded files from MinIO (avatars, document uploads, group files, Galaxy assets).
4. **No instant-delete option** — GDPR Article 17 "Right to Erasure" allows users to demand immediate deletion rather than waiting 30 days.
5. **No email notification** — Users receive no confirmation email after data export is delivered or after account deletion completes.

### 1.2 Goals

- Add per-entry `delete_entry()` to `GrowthChronicleService` with REST API
- Expand `GET /users/me/export` to cover all data categories (target: complete coverage)
- Add per-category export filtering via query parameters
- Add MinIO object cleanup to `purge_deleted_account` Celery task
- Add `DELETE /users/me` for instant hard-delete (with extended confirmation)
- Add email notification for export readiness and deletion confirmation
- Add Flutter UI for chronicle entry deletion and export progress
- Ensure the data_usage_dashboard_screen is linked from settings

### 1.3 Non-Goals

- **Not building a S3 replication/deletion dashboard** — MinIO cleanup is automated, no admin UI.
- **Not changing the soft-delete default behavior** — 30-day grace period remains the default; instant-delete is an opt-in elevated confirmation flow.
- **Not adding a data retention policy engine** — Retention periods are hardcoded per data type in this spec.
- **Not building a third-party data deletion relay** — This spec only covers Sparkle-stored data.

---

## 2. Current State Assessment

### 2.1 Existing Data Export Endpoint

Located at `backend/app/api/v1/data_export.py` — `GET /users/me/export`.

**Currently exports** (10 categories):
- `profile` — User model fields (excludes `password_hash`)
- `plans` — all Plan rows
- `tasks` — all Task rows
- `error_book` — all ErrorRecord rows
- `focus_sessions` — all FocusSession rows
- `calendar_events` — all CalendarEvent rows
- `chat_sessions` — all ChatSession rows
- `achievements` — all UserAchievement rows
- `notifications` — all Notification rows
- `notification_interactions` — all NotificationInteraction rows
- `user_settings` — UserSettings (with fallback if table missing)

**Missing categories** (11+):
- `chronicle` — GrowthChronicle entries (Redis + DB)
- `cognitive_fragments` — CognitiveFragment model
- `behavior_patterns` — BehaviorPattern model
- `memory` — Memory model records
- `galaxy_nodes` — UserNodeStatus model
- `chat_messages` — Individual ChatMessage records (not just sessions)
- `community_data` — Friend relationships, group memberships, community posts
- `curiosity_capsules` — Capsule + feedback + favorites
- `execution_records` — Execution intent, record, audit log
- `shop_purchases` — Purchase history, consumables, photon transactions
- `user_devices` — Device registration records

**Rate limiting**: Redis-based, 60-second cooldown. Returns ZIP via `StreamingResponse`.

### 2.2 Existing Account Deletion Flow

Located at `backend/app/api/v1/users.py` lines 531-597 — `POST /users/me/delete-account`.

**Flow**:
1. Validates confirmation text must be exactly `DELETE`
2. Re-authenticates via password or social provider
3. Soft-deletes: anonymizes username/email, clears social IDs, sets `is_active=False`, calls `soft_delete()`
4. Revokes all sessions
5. Schedules Celery task `purge_deleted_account` with 30-day `countdown`
6. Returns success message with 30-day recovery window notice

**Existing Celery purge task** at `backend/app/core/celery_tasks.py` lines 2380-2444:

Currently purges (16 tables):
- ChatMessage, ChatSession, Task, Plan, ErrorRecord, FocusSession, CalendarEvent
- UserAchievement, UserStreakStats, UserStreakDays, Notification, NotificationInteraction
- UserNodeStatus, UserSettings, BehaviorPattern, CognitiveFragment

**Missing models to purge**:
- UserDevice
- ShopPurchase, UserConsumable, PhotonTransactionHistory
- CuriosityCapsule, CapsuleFeedback, CapsuleFavorite, CapsuleGenerationJob
- Community models (Friend, GroupMember, CommunityPost, etc.)
- FileStorage records
- ExecutionIntent, ExecutionRecord, ExecutionAuditLog
- AuthAuditLog, DataAccessLog, SecurityAuditLog
- Memory models
- LoginAttempt
- CanvasConnectionProfile, Accountability models
- DecisionRecord, InterventionOutcome, CandidateActionFeedback
- DistilledStrategyCache
- GrowthChronicleSnapshot (Aurora model)

### 2.3 Existing MinIO Storage

Located at `backend/app/services/document_upload_storage.py`.

Key operations available:
- `delete_object(object_key)` — deletes a single object from MinIO
- `object_exists(object_key)` — checks existence
- `list_objects` — NOT exposed (needed for purge)

**Known object key patterns** (need cleanup):
- `uploads/avatars/{filename}` — user avatar uploads
- `documents/{user_id}/{file_id}.*` — user document uploads
- `group/{group_id}/files/{file_id}.*` — group-shared files
- `galaxy/nodes/{node_id}/assets/*` — Galaxy node attachments

**Current purge gap**: The Celery task deletes DB rows for uploaded-file metadata (models like `FileStorage`, `UserFile`) but does NOT call MinIO `delete_object()` to actually remove the stored bytes.

### 2.4 Existing GrowthChronicle Service

Located at `backend/app/signals/growth_chronicle.py`.

Methods available:
- `add_entry()` — create
- `hide_entry()` — set user_hidden=True
- `edit_entry()` — update narrative text
- `confirm_entry()` / `reject_entry()` — set user_status
- `get_chronicle()` — list visible entries
- `get_confirmed_entries()` — list confirmed entries
- `build_return_case_file()` — return-case-file generation

**Missing**: `delete_entry()` — permanently removes entry from Redis list AND DB snapshot.

Storage: Redis list under `spine:chronicle:{user_id}`, plus PostgreSQL `GrowthChronicleSnapshot` table.

### 2.5 Existing Flutter UI

- **`ExportDataScreen`** (`mobile/lib/features/user/presentation/screens/export_data_screen.dart`) — Full UI with ZIP download via `UserRepository.exportUserData()` and system share sheet. Uses `SharePlus` to share the ZIP.
- **`DeleteAccountScreen`** (`mobile/lib/features/user/presentation/screens/delete_account_screen.dart`) — Full UI with confirmation text field, password/social re-auth, double-confirmation dialog.
- **`SettingsDataControlsCard`** (`mobile/lib/features/settings/presentation/widgets/settings_behavior_explanation.dart` line 238) — Card widget in settings showing export, delete, hide chronicle, and hide memory toggles.
- **`DataUsageDashboardScreen`** (`mobile/lib/features/settings/presentation/screens/data_usage_dashboard_screen.dart`) — Static info screen showing "what data is collected" but has NO active navigation to export/delete screens.
- **`ProfileScreen`** — has export/delete buttons at lines 792 and 820.

### 2.6 Existing API Endpoints

| Method | Path | File | Status |
|--------|------|------|--------|
| `GET` | `/users/me/export` | `data_export.py:55` | EXISTS — needs expansion |
| `POST` | `/users/me/delete-account` | `users.py:531` | EXISTS — soft-delete |
| None | None (chronicle delete) | — | MISSING |
| None | None (instant hard-delete) | — | MISSING |
| None | None (export notification) | — | MISSING |

### 2.7 Existing Celery Task

| Task | File | Status |
|------|------|--------|
| `purge_deleted_account` | `celery_tasks.py:2380` | EXISTS — needs MinIO + missing models |
| None (export notification) | — | MISSING |

### 2.8 Existing Email Service

Located at `backend/app/core/email_service.py`. Supports sending HTML emails via aiosmtplib (SMTP). Already used for password reset and email verification.

### 2.9 Gap Summary

| # | Gap | Location | Effort |
|---|-----|----------|--------|
| G1 | No chronicle entry delete | `growth_chronicle.py`, `growth.py` | Low |
| G2 | Incomplete export categories | `data_export.py` | Medium |
| G3 | No per-category export filter | `data_export.py` | Low |
| G4 | No MinIO cleanup on purge | `celery_tasks.py`, `document_upload_storage.py` | Medium |
| G5 | Missing models in purge task | `celery_tasks.py` | Low |
| G6 | No instant-delete endpoint | New file or `users.py` | Medium |
| G7 | No export/deletion email | `celery_tasks.py`, `email_service.py` | Low |
| G8 | Static data_usage_dashboard_screen | Flutter screen | Low |
| G9 | No chronicle entry delete in Flutter | Flutter UI | Low |

---

## 3. File Inventory

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/data_sovereignty_service.py` | Unified service for export expansion, MinIO cleanup, instant-delete orchestration |
| `backend/app/tests/unit/services/test_data_sovereignty_service.py` | Tests for the new service |

### Files to Modify

| File | Change Description |
|------|-------------------|
| **Python Backend** | |
| `backend/app/api/v1/data_export.py` | Add missing categories, add per-category `?categories=` query param filter, add async export-ready notification |
| `backend/app/api/v1/users.py` | Add `DELETE /users/me/instant-delete` endpoint for GDPR right to erasure |
| `backend/app/api/v1/growth.py` | Add `DELETE /growth/chronicle/{entry_id}` endpoint |
| `backend/app/signals/growth_chronicle.py` | Add `delete_entry()` method to `GrowthChronicleService` |
| `backend/app/core/celery_tasks.py` | Extend `purge_deleted_account` with missing models + MinIO cleanup; add `notify_export_ready` task |
| `backend/app/core/celery_schedule.py` | Register new periodic tasks if needed |
| `backend/app/services/document_upload_storage.py` | Add `list_objects(prefix)` method for MinIO bulk cleanup |
| `backend/schemas/user.py` | Add `InstantDeleteRequest` Pydantic schema |
| **Flutter** | |
| `mobile/lib/features/user/presentation/screens/export_data_screen.dart` | Add progress indicator, add category selection, connect to backend updates |
| `mobile/lib/features/insights/presentation/pages/growth_chronicle_page.dart` | Add "Delete" button with confirmation per entry |
| `mobile/lib/features/settings/presentation/screens/data_usage_dashboard_screen.dart` | Add active links to export and delete screens |
| `mobile/lib/core/network/api_endpoints.dart` | Add new API endpoint constants |
| `mobile/lib/features/user/data/repositories/user_repository.dart` | Add chronicle delete, instant-delete, filtered export methods |

### Files Not Modified (No Change Needed)

| File | Reason |
|------|--------|
| `backend/app/core/email_service.py` | Already supports arbitrary emails via `_send()` — new templates use existing infrastructure |
| `backend/app/aurora/privacy.py` | PII redaction is orthogonal to data sovereignty (redaction happens at input time, deletion at account level) |
| `backend/app/api/v1/router.py` | All new endpoints are added to existing routers |
| `mobile/lib/features/user/presentation/screens/delete_account_screen.dart` | Existing flow works; instant-delete can be an additional option in the existing screen |
| `mobile/lib/features/settings/presentation/widgets/settings_behavior_explanation.dart` | `SettingsDataControlsCard` already has onExportData/onDeleteData callbacks — no structural change needed |

---

## 4. Implementation Steps

### Phase 1: ChroniclEntry Delete (GROW-009 core)

**Step 1.1 — Add `delete_entry()` to GrowthChronicleService**

In `backend/app/signals/growth_chronicle.py`, add:

```python
async def delete_entry(self, user_id: str, entry_id: str) -> bool:
    """Permanently delete a chronicle entry. Removes from Redis AND durable storage.
    
    Returns True if entry was found and deleted, False if not found.
    This is the only way to permanently remove a chronicle entry — hide_entry()
    and reject_entry() preserve the data with status flags.
    """
    key = _CHRONICLE_KEY.format(user_id=user_id)
    entries = await self._load_entries(user_id)
    before = len(entries)
    entries = [e for e in entries if e.entry_id != entry_id]
    if len(entries) == before:
        return False  # entry not found
    await self._save_entries(user_id, entries)
    logger.info("GrowthChronicle entry deleted: user={} entry={}", user_id, entry_id)
    return True
```

The `_save_entries()` method already writes to both Redis and `GrowthChronicleSnapshot` (durable storage), so removing the entry from the list before saving ensures deletion from both stores.

Implementation notes:
- `_save_entries()` at line 454 already calls `_save_durable_entries()` — no separate DB cleanup needed.
- No WATCH needed for delete; the load-modify-save pattern is atomic enough for this use case and matches the existing pattern used by `confirm_entry()` and `reject_entry()`.

**Step 1.2 — Add API endpoint in `growth.py`**

```python
from fastapi import HTTPException

@router.delete("/chronicle/{entry_id}")
async def delete_chronicle_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a single chronicle entry.
    
    GROW-009: Users can permanently remove chronicle entries they no longer
    want in their growth narrative. Unlike hide_entry() which preserves data
    with a visibility flag, this removes the entry entirely.
    """
    redis = cache_service.redis
    chronicle = GrowthChronicleService(redis, db_session=db)
    deleted = await chronicle.delete_entry(str(current_user.id), entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chronicle entry not found")
    return {"detail": "Entry permanently deleted"}
```

**Step 1.3 — Add Flutter chronicle entry delete**

In `mobile/lib/features/insights/presentation/pages/growth_chronicle_page.dart`:

- Add a delete button (destructive, with confirmation dialog) to each chronicle entry
- The existing `_updateStatus()` method pattern (line 93-120) should be followed — use SnackBar undo with a 5-second timeout, then actually DELETE on timeout expiry
- Add `deleteChronicleEntry(entryId)` to the relevant provider/repository

API endpoint constant:
```dart
static String chronicleEntry(String entryId) => '/growth/chronicle/$entryId';
```

### Phase 2: Expand Data Export

**Step 2.1 — Add missing categories to `data_export.py`**

The existing `_query()` helper at line 79 works generically for any model with a `user_id` field. Add these missing categories:

```python
datasets: dict[str, Any] = {
    # ... existing categories ...
    
    # NEW: GAP-P3-4 expansions
    "chat_messages": await _query(ChatMessage),
    "cognitive_fragments": await _query(CognitiveFragment),
    "memory_entries": await _query(MemoryEntry),  # or appropriate memory model
    "curiosity_capsules": await _query(CuriosityCapsule),
    "photon_transactions": await _query(PhotonTransactionHistory),
    "user_devices": await _query(UserDevice),
    "execution_intents": await _query(ExecutionIntent),
    "execution_records": await _query(ExecutionRecord),
}
```

Models to import:
```python
from app.models.chat import ChatMessage  # (already imported via ChatSession context, add explicitly)
from app.models.cognitive import CognitiveFragment, BehaviorPattern
from app.models.curiosity_capsule import CuriosityCapsule, CapsuleFeedback, CapsuleFavorite
from app.models.user import UserDevice
from app.models.execution_intent import ExecutionIntent
from app.models.execution_record import ExecutionRecord
from app.models.photon_transaction import PhotonTransactionHistory
from app.models.shop_purchase import ShopPurchase, UserConsumable
```

**Step 2.2 — Add per-category filtering**

Add an optional `categories` query parameter:

```python
@router.get("/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    categories: str | None = Query(None, description="Comma-separated category names, e.g. 'profile,tasks,chat_messages'"),
) -> StreamingResponse:
```

If `categories` is provided, only export those categories (whitelist filter). If omitted, export ALL categories.

Validation: return 400 if any requested category is unrecognized.

**Step 2.3 — Add chronicle to export**

The chronicle lives in Redis, not in a standard SQL model. Add a special case:

```python
# Export chronicle entries (stored in Redis, not a direct query)
try:
    chronicle_service = GrowthChronicleService(redis, db_session=db)
    chronicle_entries = await chronicle_service.get_chronicle(str(uid), limit=1000)
    datasets["chronicle"] = [e.to_dict() for e in chronicle_entries]
except Exception:
    datasets["chronicle"] = []
```

**Step 2.4 — Add async export notification**

For large exports (>50MB estimated), add a Celery-based async export:
- A new `celery_tasks.py` task `generate_export_async` that runs the export, stores the ZIP to MinIO with a presigned URL, and emails the user
- The sync `GET /users/me/export` remains for small exports
- Add a new `POST /users/me/export/request` that triggers async export and returns a task ID

### Phase 3: MinIO Cleanup on Purge

**Step 3.1 — Add `list_objects()` to DocumentUploadStorage**

In `backend/app/services/document_upload_storage.py`:

```python
def list_objects(self, *, prefix: str, max_keys: int = 1000) -> list[str]:
    """List object keys under a prefix. Used for bulk cleanup."""
    keys: list[str] = []
    client = _internal_client()
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys)
    for page in pages:
        contents = page.get("Contents", [])
        for obj in contents:
            key = obj.get("Key")
            if key:
                keys.append(key)
    return keys
```

**Step 3.2 — Extend Celery purge task with MinIO cleanup**

In `backend/app/core/celery_tasks.py`, after the DB deletion loop and before `session.delete(user)`:

```python
# GAP-P3-4: Clean up MinIO objects
try:
    from app.services.document_upload_storage import document_upload_storage
    
    user_prefixes = [
        f"uploads/avatars/{user_id}",
        f"documents/{user_id}/",
        f"galaxy/nodes/",  # filter by user-owned nodes in Galaxy service
    ]
    for prefix in user_prefixes:
        try:
            object_keys = document_upload_storage.list_objects(prefix=prefix)
            for key in object_keys:
                document_upload_storage.delete_object(object_key=key)
                deleted_count += 1
            logger.info("  MinIO cleanup for prefix '{}': {} objects deleted", prefix, len(object_keys))
        except Exception as minio_err:
            logger.warning("  MinIO cleanup failed for prefix '{}': {}", prefix, minio_err)
    
    # Also handle avatar directly (UUID-based filename, no user_id prefix)
    # Query FileStorage model for all user files and delete each
    from app.models.file_storage import FileStorage
    user_files = await session.execute(
        select(FileStorage).where(FileStorage.user_id == uid)
    )
    for file_record in user_files.scalars():
        if file_record.storage_path:
            try:
                document_upload_storage.delete_object(object_key=file_record.storage_path)
            except Exception:
                pass
except Exception as minio_err:
    logger.warning("MinIO cleanup failed for user {}: {}", user_id, minio_err)
```

**Step 3.3 — Add missing models to purge table list**

Add to the `tables` list in `purge_deleted_account`:

```python
tables: list[tuple[type, str]] = [
    # ... existing 16 tables ...
    # NEW: GAP-P3-4 additions
    (UserDevice, "user_id"),
    (ShopPurchase, "user_id"),
    (UserConsumable, "user_id"),
    (PhotonTransactionHistory, "user_id"),
    (LoginAttempt, "user_id"),
    (ExecutionIntent, "user_id"),
    (ExecutionRecord, "user_id"),
    (CapsuleFeedback, "user_id"),
    (CapsuleFavorite, "user_id"),
    (CapsuleGenerationJob, "user_id"),
    (AuthAuditLog, "user_id"),
    (DataAccessLog, "user_id"),
    (CandidateActionFeedback, "user_id"),
    (DistilledStrategyCache, "user_id"),
    # GrowthChronicleSnapshot (Aurora model — special import)
]
```

For `GrowthChronicleSnapshot` (Aurora model, imported dynamically), add:
```python
try:
    from app.aurora.runtime_v1.models import GrowthChronicleSnapshot
    tables.append((GrowthChronicleSnapshot, "user_id"))
except ImportError:
    pass
```

For community models and accountability models, also add:
```python
try:
    from app.models.community import Friend, GroupMember, CommunityPost, CommunityPostInteraction
    tables.extend([
        (Friend, "user_id"),  # or "requester_id" / "addressee_id" — check schema
        (GroupMember, "user_id"),
        (CommunityPost, "user_id"),
    ])
except ImportError:
    pass

try:
    from app.models.accountability import AccountabilityPartnership, AccountabilityCheckin
    tables.extend([
        (AccountabilityPartnership, "user_id"),  # check actual FK field name
        (AccountabilityCheckin, "user_id"),
    ])
except ImportError:
    pass
```

IMPORTANT: Verify FK field names for each model before adding. Some community models may use `requester_id`, `addressee_id`, or `owner_id` instead of `user_id`.

### Phase 4: Instant-Delete Endpoint (GDPR Right to Erasure)

**Step 4.1 — Add Pydantic schema**

In `backend/app/schemas/user.py`, add:

```python
class InstantDeleteRequest(BaseModel):
    """Request for immediate account deletion (GDPR Art. 17)."""
    confirmation: str = Field(..., description="Must be 'DELETE'")
    password: str | None = Field(default=None, description="Password for re-authentication")
    provider: str | None = Field(default=None, description="Social provider name")
    provider_token: str | None = Field(default=None, description="Social provider token")
    acknowledge_data_loss: bool = Field(default=False, description="Must be True to confirm understanding that data is unrecoverable")
```

**Step 4.2 — Add endpoint in `users.py`**

```python
@router.delete("/me")
async def instant_delete_account(
    payload: InstantDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 17: Right to erasure — immediate account deletion.
    
    Unlike POST /users/me/delete-account which soft-deletes with a 30-day
    recovery window, this endpoint hard-deletes all user data immediately.
    Requires additional acknowledgment of data loss.
    """
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="请输入 DELETE 以确认注销")
    if not payload.acknowledge_data_loss:
        raise HTTPException(status_code=400, detail="请确认你了解数据将立即永久删除且不可恢复")
    
    # Re-authentication (same logic as existing delete_account)
    if current_user.registration_source == "guest":
        pass
    elif payload.password:
        if not current_user.password_login_enabled:
            raise HTTPException(status_code=400, detail="当前账号未启用密码登录，请使用社交验证")
        if not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(status_code=403, detail="密码错误")
    elif payload.provider and payload.provider_token:
        await _require_social_reauth(current_user, payload.provider, payload.provider_token)
    else:
        raise HTTPException(status_code=400, detail="请使用密码或社交账号重新验证身份")
    
    # Log the deletion request
    auth_audit_service.schedule_log(
        AuthAuditAction.ACCOUNT_DELETE,
        user_id=str(current_user.id),
        request=request,
        metadata={"mode": "instant_erasure"},
    )
    
    # Execute immediate purge synchronously via Celery (eager mode)
    from app.core.celery_tasks import purge_deleted_account_immediate
    purge_deleted_account_immediate.apply_async(args=[str(current_user.id)])
    
    # Revoke sessions immediately
    await set_user_revoked_before(str(current_user.id), _utcnow_naive())
    await auth_session_service.revoke_all_sessions_for_user(
        db, user_id=str(current_user.id), ttl_seconds=SESSION_TTL_SECONDS,
    )
    
    # Send confirmation email (fire-and-forget)
    try:
        from app.core.celery_tasks import notify_deletion_complete
        notify_deletion_complete.delay(str(current_user.id), current_user.email)
    except Exception:
        pass
    
    return {"detail": "账号已立即永久删除。你将在注册邮箱中收到确认邮件。"}
```

**Step 4.3 — Create corresponding Celery task**

```python
@celery_app.task(bind=True, max_retries=1, name="app.core.celery_tasks.purge_deleted_account_immediate")
def purge_deleted_account_immediate(self, user_id: str) -> dict:
    """Same as purge_deleted_account but runs immediately (no 30-day wait)."""
    # Reuse the same purge logic, but without the is_active check
    # ... (identical to purge_deleted_account but allow active users too)
```

For DRY, refactor `purge_deleted_account` to accept a `force: bool = False` parameter:
```python
def _execute_purge(user_id: str, *, force: bool = False) -> dict:
    """Core purge logic shared by 30-day and instant-delete paths."""
    # ... existing logic, but skip the `is_active` check if force=True

@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.purge_deleted_account")
def purge_deleted_account(self, user_id: str) -> dict:
    return _execute_purge(user_id, force=False)

@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.purge_deleted_account_immediate")
def purge_deleted_account_immediate(self, user_id: str) -> dict:
    return _execute_purge(user_id, force=True)
```

### Phase 5: Email Notifications

**Step 5.1 — Add notification templates to EmailService**

In `backend/app/core/email_service.py`, add:

```python
async def send_export_ready_email(self, to_email: str, download_url: str, username: str | None = None) -> bool:
    """Notify user that their data export is ready for download."""
    subject = "Your Sparkle data export is ready / 你的 Sparkle 数据导出已就绪"
    html = self._build_export_ready_html(download_url=download_url, username=username or "")
    return await self._send(to_email, subject, html)

async def send_deletion_confirmation_email(self, to_email: str, username: str | None = None, is_instant: bool = False) -> bool:
    """Confirm that account deletion has been completed."""
    if is_instant:
        subject = "Your Sparkle account has been deleted / 你的 Sparkle 账号已删除"
        html = self._build_instant_deletion_html(username=username or "")
    else:
        subject = "Your Sparkle account deletion is scheduled / 你的 Sparkle 账号删除已安排"
        html = self._build_scheduled_deletion_html(username=username or "")
    return await self._send(to_email, subject, html)

def _build_export_ready_html(self, download_url: str, username: str) -> str:
    greeting = f"Hello {username}," if username else "Hello,"
    return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>Your Sparkle Data Export</h2>
    <p>{greeting}</p>
    <p>Your data export is ready. The download link will expire in 48 hours.</p>
    <p><a href="{download_url}" style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Download Export</a></p>
    <p>If you did not request this export, please secure your account immediately.</p>
  </body>
</html>
"""

def _build_instant_deletion_html(self, username: str) -> str:
    greeting = f"Hello {username}," if username else "Hello,"
    return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>Account Deletion Confirmed</h2>
    <p>{greeting}</p>
    <p>Your Sparkle account and all associated data have been permanently deleted.</p>
    <p>If you did not request this deletion, please contact support immediately.</p>
  </body>
</html>
"""

def _build_scheduled_deletion_html(self, username: str) -> str:
    greeting = f"Hello {username}," if username else "Hello,"
    return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>Account Deletion Scheduled</h2>
    <p>{greeting}</p>
    <p>Your Sparkle account deletion has been scheduled. Your data will be permanently deleted in 30 days.</p>
    <p>If you want to cancel this request, please log in and restore your account within 30 days.</p>
  </body>
</html>
"""
```

**Step 5.2 — Add Celery tasks for email notifications**

```python
@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.notify_export_ready")
def notify_export_ready(self, user_id: str, email: str, download_url: str, username: str | None = None) -> None:
    """Send export-ready notification email."""
    result = email_service.send_export_ready_email(email, download_url, username)
    logger.info("Export notification sent to {}: {}", email, result)

@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.notify_deletion_complete")
def notify_deletion_complete(self, user_id: str, email: str, is_instant: bool = False) -> None:
    """Send deletion confirmation email before user record is removed."""
    result = email_service.send_deletion_confirmation_email(email, is_instant=is_instant)
    logger.info("Deletion notification sent to {}: {}", email, result)
```

### Phase 6: Flutter UI Updates

**Step 6.1 — Wire data_usage_dashboard_screen to export/delete**

In `mobile/lib/features/settings/presentation/screens/data_usage_dashboard_screen.dart`:

- Replace static `_ControlTile` widgets with active navigation:
  - "Export your data" → navigates to `UserRoutes.exportData`
  - "Request data deletion" → navigates to `UserRoutes.deleteAccount`
  - "View chronicle entries" → navigates to growth chronicle page

```dart
_ControlTile(
  icon: Icons.download_outlined,
  title: 'Export your data',
  subtitle: 'Download a complete copy of everything Sparkle stores',
  onTap: () => context.push(UserRoutes.exportData),
),
_ControlTile(
  icon: Icons.delete_outline,
  title: 'Request data deletion',
  subtitle: 'All your data can be permanently removed on request',
  destructive: true,
  onTap: () => context.push(UserRoutes.deleteAccount),
),
```

**Step 6.2 — Add category selection to ExportDataScreen**

Add optional checkboxes for data categories:
- "Export All" (default, checked)
- Individual category toggles
- Only shown when backend returns category listing

**Step 6.3 — Add chronicle entry delete to growth_chronicle_page.dart**

- Add a "Delete permanently" option in the entry action sheet (alongside confirm/edit/reject)
- Show confirmation dialog: "This will permanently remove this entry. Continue?"
- On confirm, call `DELETE /growth/chronicle/{entry_id}`
- Show success/failure snackbar

---

## 5. Test Plan

### 5.1 Unit Tests — `test_data_sovereignty_service.py`

**Test Class 1: Chronicle Delete**

| Test | Coverage |
|------|----------|
| `test_delete_entry_removes_from_redis` | Entry removed from Redis list |
| `test_delete_entry_removes_from_db` | Entry removed from GrowthChronicleSnapshot |
| `test_delete_entry_not_found` | Returns False for unknown entry_id |
| `test_delete_entry_preserves_other_entries` | Only targeted entry removed |
| `test_delete_entry_twice` | Second call returns False |
| `test_delete_entry_empty_chronicle` | Graceful when no entries exist |

**Test Class 2: Export Coverage**

| Test | Coverage |
|------|----------|
| `test_export_all_categories` | All expected categories present in ZIP |
| `test_export_filtered_categories` | Only requested categories included |
| `test_export_invalid_category` | Returns 400 for unknown category |
| `test_export_no_duplicate_categories` | Each key appears exactly once |
| `test_export_rate_limit` | 429 after too-frequent requests |
| `test_export_chronicle_included` | Chronicle entries from Redis are in export |

**Test Class 3: MinIO Cleanup**

| Test | Coverage |
|------|----------|
| `test_list_objects_by_prefix` | Returns matching keys for user prefix |
| `test_list_objects_empty_prefix` | Empty list when no objects match |
| `test_delete_object_called_on_purge` | MinIO delete_object called for each user file |
| `test_purge_handles_minio_failure` | Purge continues despite MinIO errors |
| `test_purge_cleans_avatar` | Avatar object deleted from uploads/avatars/ |

**Test Class 4: Instant Delete**

| Test | Coverage |
|------|----------|
| `test_instant_delete_requires_acknowledgment` | 400 if acknowledge_data_loss=False |
| `test_instant_delete_triggers_purge_immediate` | Celery task dispatched immediately |
| `test_instant_delete_revokes_sessions` | All sessions revoked |
| `test_instant_delete_logs_audit` | AuthAuditAction.ACCOUNT_DELETE logged |
| `test_instant_delete_sends_email` | Email task dispatched |

**Test Class 5: Email Notifications**

| Test | Coverage |
|------|----------|
| `test_export_ready_email` | Correct subject and download URL in body |
| `test_instant_deletion_email` | Correct subject and body for instant delete |
| `test_scheduled_deletion_email` | Correct subject and body for scheduled delete |
| `test_email_disabled_graceful` | No error when EMAIL_ENABLED=False |

### 5.2 Integration Tests

| Test | Coverage |
|------|----------|
| `test_full_export_download` | Real HTTP request returns valid ZIP |
| `test_export_zip_contains_expected_files` | Verified JSON files inside ZIP |
| `test_chronicle_delete_via_api` | DELETE endpoint + verify gone via GET |
| `test_purge_deleted_account_full` | Full end-to-end purge including MinIO |

### 5.3 Migration Verification

| Check | Method |
|-------|--------|
| Existing export still works | Run existing export, verify same shape + new fields |
| Existing delete still works | Verify soft-delete flow unchanged |
| Existing chronicle entries not lost | Delete one entry, verify others preserved |
| MinIO objects recoverable | After purge, verify objects deleted via MinIO console |

---

## 6. Acceptance Criteria

### P0 — Must Have (Blocking)

- [ ] **AC1**: `GrowthChronicleService.delete_entry()` permanently removes entries from both Redis and PostgreSQL
- [ ] **AC2**: `DELETE /growth/chronicle/{entry_id}` returns 404 for unknown entry and 200 on success
- [ ] **AC3**: `GET /users/me/export` covers ALL data categories (no model left behind)
- [ ] **AC4**: `GET /users/me/export?categories=profile,tasks` only exports requested categories
- [ ] **AC5**: MinIO objects (avatars, documents, files) are deleted during `purge_deleted_account`
- [ ] **AC6**: `DELETE /users/me` enables GDPR right to erasure with immediate hard-delete
- [ ] **AC7**: All existing tests pass without modification

### P1 — Should Have

- [ ] **AC8**: Email notification sent on export completion (async path)
- [ ] **AC9**: Email notification sent on deletion confirmation (both scheduled and instant)
- [ ] **AC10**: Missing models (UserDevice, ShopPurchase, etc.) added to purge table list
- [ ] **AC11**: `document_upload_storage.list_objects(prefix)` is available for bulk cleanup
- [ ] **AC12**: Flutter chronicle entry delete UI shows confirmation dialog before deleting
- [ ] **AC13**: data_usage_dashboard_screen has working navigation links to export and delete screens

### P2 — Nice to Have

- [ ] **AC14**: Export progress indicator in Flutter UI (for large async exports)
- [ ] **AC15**: Instant-delete option in Flutter delete_account_screen (radio: "30-day grace" vs "immediate")
- [ ] **AC16**: Export category selector in Flutter ExportDataScreen
- [ ] **AC17**: Audit log entries for all delete/export operations (already partially exists)

### Verification Method

```
# Unit tests
cd backend && pytest tests/unit/services/test_data_sovereignty_service.py -v --cov=app.services.data_sovereignty_service

# Integration
cd backend && pytest tests/ -v -k "export or purge or chronicle_delete" --no-header

# Manual test — chronicle delete
python -c "
import asyncio, json
from fakeredis import FakeRedis
from app.signals.growth_chronicle import GrowthChronicleService, ChronicleEntry
redis = FakeRedis()
svc = GrowthChronicleService(redis)
entry = ChronicleEntry(entry_id='test-1', user_id='u1', entry_type='milestone', timestamp='now', title='Test', narrative='test', evidence_refs=[], user_editable=True)
asyncio.run(svc.add_entry('u1', entry))
print('Before:', len(asyncio.run(svc.get_chronicle('u1'))))
asyncio.run(svc.delete_entry('u1', 'test-1'))
print('After:', len(asyncio.run(svc.get_chronicle('u1'))))
"

# MinIO cleanup check
python -c "
from app.services.document_upload_storage import document_upload_storage
keys = document_upload_storage.list_objects(prefix='documents/')
print(f'{len(keys)} objects under documents/')
"

# Export endpoint
curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/v1/users/me/export -o /tmp/export.zip
unzip -l /tmp/export.zip | head -40
```

---

## 7. Design Decisions

### DD1: Chronicle Delete = Hard Delete, Not Soft Delete
- **Decision**: `delete_entry()` physically removes the entry from Redis AND the durable DB snapshot.
- **Rationale**: GROW-009 explicitly requires permanent deletion. Soft-delete flags already exist (`user_hidden`, `rejected`). A "trash" pattern adds complexity without clear GDPR benefit.
- **Trade-off**: No recovery after deletion. Mitigated by confirmation dialog in Flutter UI.

### DD2: Export Uses Sync StreamingResponse by Default, Async for Large
- **Decision**: `GET /users/me/export` remains a synchronous streaming endpoint. A new `POST /users/me/export/request` triggers async generation with email delivery.
- **Rationale**: Most users have <10MB of data, which streams in <2 seconds via `StreamingResponse`. Async only needed for power users with 100MB+ of documents/chat history.
- **Trade-off**: Two export paths duplicate some logic. Mitigated by extracting shared data collection into `DataSovereigntyService`.

### DD3: MinIO Cleanup via Prefix Scan, Not DB-Backed
- **Decision**: The purge task scans MinIO by known prefix patterns rather than querying the `FileStorage` model for all object keys.
- **Rationale**: Not all uploaded objects have matching DB rows (orphaned uploads, failed uploads, prefixed temp files). Prefix scan catches everything.
- **Trade-off**: Slower than DB-backed enumeration for small user data sets. Mitigated by bounded prefix scope (`documents/{user_id}/`, `uploads/avatars/...`).

### DD4: Instant-Delete is a Separate Endpoint, Not a Flag
- **Decision**: `DELETE /users/me` is a separate endpoint from `POST /users/me/delete-account`.
- **Rationale**: The confirmation and acknowledgment requirements differ significantly. Instant-delete requires `acknowledge_data_loss: True` plus standard re-auth. The soft-delete path has a 30-day recovery window. Mixing into one endpoint with optional flags is more error-prone.
- **Trade-off**: Endpoint proliferation. Mitigated by Flutter UI presenting both options in the same screen with clear labels.

### DD5: GrowthChronicleSnapshot Uses `deleted_at` for Soft-Delete
- **Decision**: The `GrowthChronicleSnapshot` model already has a `deleted_at` field (visible in `_load_durable_entries()` at line 470). The delete_entry method should set `deleted_at` on the snapshot rather than deleting the row.
- **Rationale**: The snapshot is a single JSON blob per user, not per-entry. Removing the entire snapshot row would lose all entries. Instead, the snapshot is updated with the entry removed from the JSON payload.
- **Trade-off**: DB row persists. Acceptable because the snapshot row is a single record per user with no PII in columns (only in JSON payload).

### DD6: Email Templates Are Bilingual (English + Chinese)
- **Decision**: Email subjects and body include both English and Chinese text, matching the existing i18n pattern used by Flutter.
- **Rationale**: APP_NAME locale is not available at email send time. Bilingual templates ensure the user understands regardless of their UI language setting.
- **Trade-off**: Longer subject lines. Acceptable — email clients truncate long subjects gracefully.

### DD7: No Changes to DataUsageDashboardScreen Architecture
- **Decision**: The data_usage_dashboard_screen stays as a static info screen; only navigation links are added.
- **Rationale**: Adding backend-driven data usage descriptions (what data types exist, how they're used) would require a new API endpoint and is out of scope for GROW-009.
- **Trade-off**: Data type descriptions are hardcoded in Flutter and may drift from actual data model. Acceptable for current scope.

---

## 8. Dependencies

### 8.1 Internal Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| `GrowthChronicleService` from `app.signals.growth_chronicle` | Chronicle entry delete | Low — stable service |
| `DocumentUploadStorage` from `app.services.document_upload_storage` | MinIO cleanup | Low — stable wrapper |
| `EmailService` from `app.core.email_service` | Email notifications | Low — existing service |
| `AuthAuditService` from `app.core.auth_audit_service` | Audit logging | Low — existing pattern |
| `User` model from `app.models.user` | User data export/deletion | Low — core model |
| Existing `purge_deleted_account` | Shared purge logic | Low — existing extension point |

### 8.2 External Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| Redis | Chronicle storage, rate limiting, Celery broker | Low — already in stack |
| PostgreSQL | Durable storage for all model data | Low — already in stack |
| MinIO (boto3) | File object cleanup | Low — already in stack |
| aiosmtplib | Email sending | Low — already in stack |

### 8.3 No New Dependencies

This project does not require any new pip or pub dependencies. All tools (Redis, PostgreSQL, MinIO/boto3, aiosmtplib, Celery) are already in the project.

---

## 9. Open Questions

### Q1: Should export include AI model inferred data (cognitive fragments, behavior patterns)?
- **Context**: `CognitiveFragment` and `BehaviorPattern` are AI-generated inferences from raw data. Exporting them may confuse users (they are probabilities, not facts). Not exporting them violates the principle of "complete data export."
- **Proposed**: Include them with a clear disclaimer JSON key: `"cognitive_fragments": { "data": [...], "disclaimer": "These are AI-generated inferences with confidence scores, not verified facts." }`.

### Q2: How should community data deletion handle multi-user data?
- **Context**: If user A deletes their account, what happens to group messages where A participated, or friend relationships where other users referenced A?
- **Proposed**: Anonymize (set user_id to NULL or replace with "[deleted]") rather than cascade-delete. Group messages, community posts, and accountability check-ins should retain the content but anonymize the author.

### Q3: Should the instant-delete endpoint be synchronous or async?
- **Context**: GDPR requires "without undue delay." A synchronous endpoint would block the HTTP response until all data is purged (potentially 30+ seconds for power users). Async means the user gets a 202 Accepted but no immediate visual confirmation.
- **Proposed**: Async with immediate session revocation. Return 202 Accepted with a message that deletion has started and a confirmation email will be sent. The user is logged out on the client side and cannot log back in.

### Q4: Should we add a "Cancel Deletion" endpoint for the 30-day grace period?
- **Context**: The current soft-delete flow says "contact customer support" for recovery. This could be a self-service endpoint.
- **Proposed**: Not in scope for GAP-P3-4. Add a self-service recovery endpoint as a separate follow-up. The current support-contact flow is adequate.

### Q5: What is the MinIO bucket isolation strategy?
- **Context**: Multiple object key prefixes exist (`documents/`, `uploads/`, `group/`, `galaxy/`). The purge task needs to clean all of them.
- **Proposed**: Maintain a registry of known prefixes in `DataSovereigntyService`. New features that add MinIO storage must register their prefix. For now, scan all known prefixes plus query `FileStorage` model for any non-standard paths.

### Q6: How do we handle concurrent write during export?
- **Context**: If a user triggers an export while the system is actively writing new data, the export may contain incomplete transactions or miss recently written data.
- **Proposed**: No serializability guarantee for export. This is acceptable — the export is a point-in-time snapshot, not a transactional backup. Document this behavior in the export UI.

### Q7: Should Galaxy graph data be exported?
- **Context**: Galaxy nodes (`UserNodeStatus`) are user-specific but also cross-reference shared knowledge nodes. A full Galaxy export could include shared node references.
- **Proposed**: Export `UserNodeStatus` records (user's mastery levels, position, favorites) but not the shared `KnowledgeNode` definitions. If the user wants to save their knowledge graph position, export the node IDs and mastery levels as reference points.

---

## Appendix A: Data Export Category Registry

| Category | Model | Status | Notes |
|----------|-------|--------|-------|
| `profile` | `User` | EXISTS | Excludes `hashed_password` |
| `plans` | `Plan` | EXISTS | |
| `tasks` | `Task` | EXISTS | |
| `error_book` | `ErrorRecord` | EXISTS | |
| `focus_sessions` | `FocusSession` | EXISTS | |
| `calendar_events` | `CalendarEvent` | EXISTS | |
| `chat_sessions` | `ChatSession` | EXISTS | |
| `chat_messages` | `ChatMessage` | **NEW** | Individual messages |
| `achievements` | `UserAchievement` | EXISTS | |
| `notifications` | `Notification` | EXISTS | |
| `notification_interactions` | `NotificationInteraction` | EXISTS | |
| `user_settings` | `UserSettings` | EXISTS | |
| `chronicle` | `ChronicleEntry` (Redis+DB) | **NEW** | Via GrowthChronicleService |
| `cognitive_fragments` | `CognitiveFragment` | **NEW** | With disclaimer |
| `behavior_patterns` | `BehaviorPattern` | **NEW** | With disclaimer |
| `curiosity_capsules` | `CuriosityCapsule` | **NEW** | Includes feedback, favorites |
| `photon_transactions` | `PhotonTransactionHistory` | **NEW** | |
| `shop_purchases` | `ShopPurchase` | **NEW** | Includes consumables |
| `user_devices` | `UserDevice` | **NEW** | |
| `execution_intents` | `ExecutionIntent` | **NEW** | |
| `execution_records` | `ExecutionRecord` | **NEW** | |

## Appendix B: MinIO Object Key Patterns

| Pattern | Description | Cleanup Method |
|---------|-------------|---------------|
| `uploads/avatars/{user_id}.{ext}` | User avatar images | Prefix scan `uploads/avatars/{user_id}` |
| `documents/{user_id}/{file_id}.{ext}` | User document uploads | Prefix scan `documents/{user_id}/` |
| `group/{group_id}/files/{file_id}.{ext}` | Group-shared files | Query FileStorage model for user_id + delete each |
| `galaxy/nodes/{node_id}/assets/*` | Galaxy node assets | Query UserNodeStatus for nodes + delete each |

## Appendix C: Celery Task Registry

| Task Name | Schedule | Purpose |
|-----------|----------|---------|
| `purge_deleted_account` | Scheduled (30d after delete) | Soft-delete expiration → hard purge |
| `purge_deleted_account_immediate` | On-demand | GDPR instant erasure |
| `notify_export_ready` | On-demand (async export) | Email user with download link |
| `notify_deletion_complete` | On-demand | Email user after deletion |

## Appendix D: Flutter Route Changes

| Route | Screen | Action |
|-------|--------|--------|
| `UserRoutes.exportData` | `ExportDataScreen` | EXISTING — enhance with category selection |
| `UserRoutes.deleteAccount` | `DeleteAccountScreen` | EXISTING — add instant-delete option |
| Chronic entry action | `growth_chronicle_page.dart` | NEW — delete button in entry actions |

## Appendix E: Architecture Flow Diagrams

### Chronicle Entry Delete Flow
```
Flutter UI (delete button + confirm dialog)
  → DELETE /growth/chronicle/{entry_id}
  → GrowthChronicleService.delete_entry()
    → Load Redis list → filter out entry → save Redis list
    → Load DB snapshot → remove entry from payload → save DB snapshot
  → Return 200/404
  → Flutter UI removes entry from list + shows snackbar
```

### Instant Delete Flow (GDPR Art. 17)
```
Flutter UI (instant-delete option + double confirm)
  → DELETE /users/me { confirmation: "DELETE", acknowledge_data_loss: true, password: "..." }
  → Re-authenticate (password or social)
  → Log audit event
  → Dispatch purge_deleted_account_immediate Celery task
    → Delete all DB rows (all tables including new additions)
    → Clean up MinIO objects
  → Revoke all sessions
  → Dispatch notify_deletion_complete email task
  → Return 202 Accepted
  → Flutter UI logs out + redirects to login
  → User receives confirmation email
```

### Export Flow
```
Flutter UI (export button → category selection if advanced)
  → GET /users/me/export[?categories=profile,tasks]
  → Query all requested model tables
  → Fetch chronicle from Redis
  → Package as ZIP (streaming)
  → Return StreamingResponse
  → Flutter writes to temp file → opens system share sheet
```

---

## Appendix F: Security & Privacy Considerations

1. **Email addresses in export**: User's email is included in profile export by default. This is expected (user exports their own data).
2. **Password hashes excluded**: Export explicitly excludes `hashed_password` (already in code).
3. **MinIO presigned URLs**: Export stored in MinIO uses presigned URLs with 48-hour expiry.
4. **Rate limiting**: Export rate-limited to once per 60 seconds (already in code).
5. **Authentication required**: All endpoints require valid JWT + active user session.
6. **Audit trail**: All delete operations (chronicle entry, account) are logged via `AuthAuditService`.
7. **Email notifications**: Deletion confirmation sent to registered email (not shown in UI to prevent account-takeover-based deletion).
8. **No data remnants**: MinIO cleanup ensures file storage bytes are removed, not just DB metadata.

---

*End of spec.*
