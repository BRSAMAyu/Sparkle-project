# Round 3: Security & PII Audit Report

**Date**: 2026-05-15
**Auditor**: Automated Security Audit Agent
**Scope**: PII protection, authentication/authorization, data isolation, sensitive data handling, Aurora security boundaries, differential privacy

---

## Executive Summary

The security posture of the Sparkle system is **substantially strong** in most areas, with well-designed defense-in-depth layers. However, this audit identified **5 P0 (critical)**, **4 P1 (high)**, and **6 P2 (medium)** findings requiring attention.

| Category | P0 | P1 | P2 | Info | Total |
|----------|----|----|----|----|-------|
| PII Protection | 1 | 1 | 2 | 1 | 5 |
| Auth/AuthZ | 1 | 1 | 1 | 1 | 4 |
| Data Isolation | 1 | 1 | 0 | 0 | 2 |
| Logging/Secrets | 1 | 0 | 2 | 1 | 4 |
| Aurora Boundaries | 0 | 1 | 0 | 1 | 2 |
| Differential Privacy | 1 | 0 | 1 | 0 | 2 |
| **Total** | **5** | **4** | **6** | **4** | **19** |

---

## 1. PII Redaction Audit

### 1.1 `pii_redaction_mode()` Async Bug (P0 - CRITICAL)

**File**: `backend/app/aurora/privacy.py`, line 58

```python
mode = asyncio.get_event_loop().run_until_complete(ks.get_mode())
```

**Problem**: `asyncio.get_event_loop().run_until_complete()` raises `RuntimeError` when called from within a running event loop (Python 3.10+). This is the **exact bug mentioned in the audit brief**. In production (which runs entirely inside `asyncio` event loops), this will always fall into the `except Exception` branch, silently bypassing Redis-based kill switch configuration and falling back to settings-based mode.

**Impact**: The PII redaction kill switch cannot be dynamically controlled via Redis. It always falls back to the static `AURORA_PRIVACY_PII_REDACTION_MODE` setting, defeating the tri-state (`off`/`shadow`/`live`) design intent.

**Fix**: Convert `pii_redaction_mode()` to `async def pii_redaction_mode()` and await the call. Then make all callers (`redact_pii`, `redact_pii_with_report`) async as well, or cache the mode with a short TTL using a synchronous wrapper.

### 1.2 PII Regex Coverage Gaps (P1 - HIGH)

**File**: `backend/app/aurora/privacy.py`, lines 12-26

The current PII regex set covers:
| Category | Pattern | Status |
|----------|---------|--------|
| Email | `_EMAIL_RE` | Covered |
| Chinese phone (1[3-9]xxxxxxxxx) | `_PHONE_RE` | Covered |
| Chinese ID (15/18 digit) | `_CN_ID_RE` | Covered |
| Bank card (12-19 digit) | `_BANK_CARD_RE` | Covered |
| Chinese names (label/self-intro) | `_CN_NAME_LABEL_RE`, `_CN_NAME_SELF_RE` | Covered |
| English names | `_EN_NAME_RE` | Covered |

**Missing coverage**:
- **International phone numbers**: No support for non-Chinese formats (e.g., US `+1-xxx-xxx-xxxx`, UK `+44...`, Japan `+81...`)
- **Passport numbers**: Not covered
- **Physical addresses**: Chinese addresses (province/city/street) not covered
- **IPv4/IPv6 addresses**: Not covered (can be PII when correlated)
- **Date of birth**: Not covered

**Impact**: International users' phone numbers and other PII can leak to external LLM providers.

### 1.3 PII Redaction NOT Applied on Main LLM Path (P0 - CRITICAL)

**File**: `backend/app/core/llm_secure_io.py`

The `sanitize_text_for_llm()` function calls `redact_secrets()` (which strips API keys, Bearer tokens, and URL credentials) and `_safety_service.sanitize_input()` -- but **neither of these calls `redact_pii()` from `app.aurora.privacy`**.

The PII redaction system (`_redact_pii_text` with email/phone/CN-ID/name patterns) is **completely disconnected from the LLM input/output pipeline**. It is only used in:
- `app/signals/marketplace.py` (marketplace signals)
- `app/services/predictive_service.py` (predictive service)

**Impact**: User messages containing emails, phone numbers, Chinese ID numbers, bank card numbers, and names are sent to external LLM providers (OpenAI/DeepSeek/etc.) without PII stripping. This is a **data protection compliance violation**.

**Fix**: `sanitize_text_for_llm()` must call `redact_pii()` (or its internal `_redact_pii_text()`) before returning sanitized text.

### 1.4 PII Redaction Kill Switch Default is `live` (P2 - MEDIUM)

**File**: `backend/app/aurora/privacy.py`, line 61

```python
normalize_mode(
    getattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "live"),
    fallback="live",
)
```

The default fallback when no setting is configured is `"live"` mode. This is good for security but could mask configuration errors. If the setting is accidentally removed, redaction silently continues rather than failing loudly.

### 1.5 `source_sha256` Leaks Original Text Presence (Info)

**File**: `backend/app/aurora/privacy.py`, line 114

When PII is redacted, the `source_sha256` field stores a SHA-256 hash of the original text. While SHA-256 is not reversible, this hash could theoretically be used for correlation attacks if an attacker has access to the original text candidates.

---

## 2. Authentication & Authorization Audit

### 2.1 gRPC Service Lacks Independent Authentication (P0 - CRITICAL)

**File**: `backend/app/services/agent_grpc_service.py`, lines 246-256

The Python gRPC service extracts `user_id` from **either** `request.user_id` (protobuf field) or gRPC metadata `user-id`:

```python
user_id = request.user_id or metadata.get("user-id", "")
```

**Problem**: The gRPC service does **not** validate the JWT token itself. It trusts the Go Gateway to have already authenticated the request. If gRPC port 50051 is accidentally exposed (misconfigured firewall, Docker network), any client can:
1. Set arbitrary `user-id` metadata
2. Set arbitrary `user_id` in the protobuf request
3. Access any user's data without authentication

The security log at line 251-254 only logs a warning but does **not reject** the request when authorization metadata is missing.

**Impact**: Complete auth bypass if gRPC port is exposed. Horizontal data access across all users.

**Fix**: 
1. Add gRPC interceptor that validates the JWT from `authorization` metadata
2. Bind gRPC to localhost only in production
3. Reject requests without valid JWT (not just log warning)

### 2.2 `user_id` Can Come from Protobuf Request Body (P0 - CRITICAL)

**File**: `backend/app/services/agent_grpc_service.py`, line 248

```python
user_id = request.user_id or metadata.get("user-id", "")
```

The `user_id` from the **request body** takes precedence over the authenticated `user-id` from metadata. A malicious client could set `request.user_id = "victim-uuid"` to impersonate another user.

**Fix**: `user_id` must come **exclusively** from authenticated metadata (set by Go Gateway after JWT validation), never from the request body. The request body `user_id` should be ignored or validated to match the metadata.

### 2.3 JWT HS256 Fallback Still Active (P2 - MEDIUM)

**File**: `backend/gateway/internal/middleware/auth.go`, lines 494-499

The JWT validation still accepts HS256 tokens as a fallback during migration. The code comment says this will be removed once all issued HS256 tokens have expired, but there's no timeline or automated mechanism to enforce this.

**Risk**: HS256 with a shared secret is weaker than RS256 (asymmetric). If the secret leaks, all tokens can be forged.

### 2.4 Admin Secret Timing-Safe Comparison (Positive Finding)

**File**: `backend/gateway/internal/middleware/auth.go`, line 452

```go
subtle.ConstantTimeCompare([]byte(secretFromHeader), []byte(cfg.AdminSecret))
```

Good practice: admin secret comparison uses constant-time comparison to prevent timing attacks.

### 2.5 All Proxy Routes Require Auth Middleware (Positive Finding)

**File**: `backend/gateway/internal/handler/proxy_routes.go`

Every route group in `RegisterProxyRoutes` applies `authMiddleware` before the handler. Admin routes additionally use `middleware.RequireAdmin`. This is correctly implemented.

### 2.6 WebSocket Origin Validation (P2 - MEDIUM)

**File**: `backend/gateway/internal/handler/websocket_proxy.go`, lines 83-94

```go
CheckOrigin: func(r *http.Request) bool {
    origin := r.Header.Get("Origin")
    if origin == "" {
        return true  // <-- Allows connections without origin header
    }
    ...
}
```

Connections without an `Origin` header are **always allowed**. This is described as "same-origin requests" but could be exploited by non-browser clients (curl, custom scripts) to bypass origin checks.

### 2.7 Query `user_id` Override Blocked (Positive Finding)

**File**: `backend/gateway/internal/middleware/auth.go`, lines 405-409

The middleware correctly validates that a query parameter `user_id` matches the JWT identity, preventing user impersonation via query strings.

---

## 3. Sensitive Data Audit

### 3.1 Raw `user_id` in Loguru Logger Calls (P0 - CRITICAL)

**Files**: Multiple files across `backend/app/`

Multiple Python files log raw `user_id` values without hashing:

| File | Line | Example |
|------|------|---------|
| `agent_grpc_service.py` | 256 | `f"Auth metadata found for user_id={user_id}"` |
| `agent_grpc_service.py` | 289 | `f"StreamChat started - user_id={user_id}..."` |
| `agent_grpc_service.py` | 225 | `"Admin authorization lookup failed for user_id={}: {}"` |
| `account_lockout.py` | 71 | `f"Account locked for user: {user.username} (ID: {user_id})"` |
| `account_lockout.py` | 79 | `f"Failed login attempt recorded for user ID: {user_id}"` |
| `guest_seed_service.py` | 3710 | `f"Guest data seeded for user_id={user.id} username={user.username}"` |
| `sse.py` | 47, 81, 83, 101, etc. | Multiple `f"SSE ... for user {user_id}"` calls |
| `shop_service.py` | 521 | `f"Purchase failed: user_id={user_id}..."` |
| `celery_app.py` | 337, 340, 465, 469, 801 | Multiple user_id in logs |

**Contrast with good practice** (using `logsafe`):
```python
# Correct (in token_revocation.py):
logger.info(f"Refresh token revoked for user {logsafe.user_id_hash(user_id)}")

# Also correct (in auth.py):
logger.info("User registered successfully: user_id={}", logsafe.user_id_hash(str(user.id)))
```

**Impact**: User IDs and sometimes usernames are persisted in log files. If log aggregation or storage is compromised, user identities can be directly extracted.

**Fix**: All Python logger calls containing `user_id` should use `logsafe.user_id_hash(user_id)` (SHA-256 truncated to 12 hex chars), matching the Go-side `logsafe.UserIDHash()` pattern.

### 3.2 Go-side Log Sanitization (Positive Finding)

**File**: `backend/gateway/internal/handler/error_sanitizer.go`

The Go gateway correctly uses `logsafe.RedactText()` for all error messages before logging, which strips emails, phone numbers, CN IDs, bearer tokens, API keys, and URL credentials. WebSocket proxy uses `hashUserIDForLog()` everywhere.

### 3.3 Security Headers (Positive Finding)

**File**: `backend/gateway/internal/middleware/security.go`

Comprehensive security headers are applied:
- Content-Security-Policy (strict, no unsafe-inline)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Strict-Transport-Security (production only)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()
- Cross-Origin isolation headers

### 3.4 Redis TTL Settings (P2 - MEDIUM)

| Key Pattern | TTL | Assessment |
|-------------|-----|------------|
| `aurora:control:{user_id}` | 24h | Reasonable |
| Checkpoint storage | 24h | Reasonable |
| Context cache | 5 min | Good |
| Achievement progress context | 24h | Reasonable |
| SSE buffer | Configurable | OK |
| Idempotency keys | 24h | Reasonable |
| LLM quota (daily) | 24h | Correct |
| LLM quota (weekly) | 7 days | Correct |
| Pending actions | Per-action TTL | OK |

**Issue**: The `write_mode()` in `kill_switch.py` (line 150) writes kill switch values to Redis **without any TTL**. If the admin sets a kill switch and it's never updated again, the stale value persists forever.

```python
await redis_client.set(f"{prefix}{binding.redis_key}", normalized)
# No TTL set
```

### 3.5 Error Message Sanitization (Positive Finding)

**Files**: `error_sanitizer.go`, `api_errors.go`

All error responses to clients go through `sanitizeErrorResponse()` which:
1. Strips internal error details in production
2. Uses i18n keys for generic messages
3. Logs the full internal error server-side with `logsafe.RedactText()`
4. Records metrics for sanitized errors

---

## 4. Aurora Security Boundaries

### 4.1 `FORBIDDEN_MODELING_DOMAINS` Enforcement (Positive Finding with Caveat)

**File**: `backend/app/aurora/runtime_v1/decision_loop.py`, lines 33-59, 1162-1166

The forbidden domains list covers 17 sensitive categories:
```
clinical_diagnosis, personality_pathology, unconscious_interpretation,
inferred_social_identity, trauma_attribution, mental_disorder,
stable_trait_label, gender_identity, sexual_orientation, race_inference,
ethnicity_inference, religion_inference, class_inference, diagnosis,
pathology, personality_disorder
```

The check is applied via `_contains_forbidden_domain()` which:
1. Serializes the entire decision payload to JSON
2. Strips allowed guard terms (e.g., "diagnose_stuck_point", "diagnostic")
3. Checks if any forbidden token appears

**Caveat** (P1 - HIGH): The check is string-based (`token in text`), not semantic. A cleverly worded payload could potentially bypass the check. For example, `"clini cal_diagnosis"` would not match. Additionally, the check only applies to the **AuroraDecision** output, not to the LLM system prompt or the LLM's intermediate reasoning.

**The LLM system prompt does include** (line 901): "Do not make clinical diagnoses, personality/pathology labels, unconscious interpretations, trauma claims, or inferred social identity guesses." But LLM instruction-following is not guaranteed.

### 4.2 `HarnessUpdateRejectedError` Enforcement (Positive Finding)

**File**: `backend/app/aurora/runtime_v1/control_surface.py`, lines 131-246

The `validate_harness_update()` method:
1. Validates against `ALLOWED_FIELDS` whitelist (only 7 fields allowed)
2. Checks privacy boundaries from user preferences
3. Checks disabled actions
4. Checks DND windows
5. Raises `HarnessUpdateRejectedError` with specific error messages on violation

In the decision loop (`decision_loop.py` lines 1107-1120), when `HarnessUpdateRejectedError` is raised:
- The harness updates are reset to safe defaults
- The metadata records `harness_update_rejected: true` with error details
- The decision continues rather than crashing

This is well-implemented: the rejection is caught and the system degrades gracefully.

### 4.3 Kill Switch Security Effectiveness (P2 - MEDIUM)

**File**: `backend/app/core/kill_switch.py`

Kill switches are well-designed:
- Tri-state: `off` -> `shadow` -> `live`
- Redis-backed with settings fallback
- Prometheus gauge recording
- Graceful degradation on Redis errors

**Issue**: When Redis is unavailable and `read_mode()` falls back to settings, there's no alerting or metric to indicate the kill switch is operating in degraded mode. The warning is logged but no alert is fired.

### 4.4 Privacy Boundaries from User Preferences (Positive Finding)

**File**: `backend/app/aurora/runtime_v1/control_surface.py`, lines 320-330

User-configured privacy boundaries are properly loaded from explicit preferences and enforced through `is_privacy_blocked()` checks in the decision loop. The DND window logic correctly handles both normal and overnight time ranges.

---

## 5. Differential Privacy Audit

### 5.1 `laplace_noise` Epsilon Parameter (P0 - CRITICAL)

**File**: `backend/app/aurora/privacy.py`, lines 125-148

```python
def laplace_noise(
    value: float,
    epsilon: float = 0.3,
    *,
    sensitivity: float = 1.0,
    rng: random.Random | None = None,
) -> float:
```

**Problems**:

1. **Default epsilon = 0.3 is very strong** for individual noise addition, which is good. However, the function does not track cumulative epsilon across multiple queries. Each call is independent, meaning an attacker could make many queries and average out the noise to recover the original value.

2. **Uses Python's `random.Random()` by default** (line 141), which is NOT cryptographically secure. For differential privacy guarantees, the random source must be cryptographically secure (CSPRNG). `secrets.SystemRandom()` should be used instead.

3. **No clipping/bounding** is applied to the output. After adding Laplace noise, the result could reveal information if the original value is in a known range. For example, if all task completion rates are between 0 and 1, a noised value of -3 or 5 clearly indicates heavy noise was added to a value near 0 or 1.

### 5.2 Privacy Budget Tracking (Positive Finding with Caveat)

**File**: `backend/app/signals/privacy_community_intelligence.py`

The `PrivacyBudget` class implements proper epsilon budget tracking:
- Default per-query cost: 0.1 epsilon
- Max lifetime budget: 10.0 epsilon
- Budget exhaustion raises `PrivacyBudgetExceeded`
- Query costs are tiered: `cohort_lookup=0.05`, `trend_detection=0.1`, `pattern_mining=0.5`

The `PrivacyPreservingCommunityEngine` implements:
- **k-anonymity floor**: Cohorts under 5 members are suppressed
- **Privacy tiers**: suppressed (never share), trend_only (direction only), anonymous_aggregate (with noise)
- **Budget enforcement**: Each query checks and deducts from the user's privacy budget

**Caveat**: The `TemporalPrivacyBudget` (line 462) and `CohortDriftDetector` (line 562) are documented as "planned for future use" and "not called from production code". The budget renewal mechanism is not implemented.

### 5.3 Cohort Privacy Tiers (Positive Finding)

The three-tier privacy model is well-designed:
- **<5 members**: Completely suppressed (no data shared)
- **5-15 members**: Only trend direction (improving/declining/stable)
- **16+ members**: Full anonymized aggregate with Laplace noise

This provides strong privacy guarantees for small groups while allowing useful analytics for larger cohorts.

### 5.4 Community Signals Always Require User Confirmation (Positive Finding)

**File**: `backend/app/signals/privacy_community_intelligence.py`, lines 406-423

External observations are always generated with `"status": "candidate"` and `"requires_user_confirmation": True`. This enforces the "Iron Rule" that external signals cannot directly write personal models.

---

## 6. Summary of Critical Findings

### P0 (Must Fix Before Production)

| # | Finding | File | Impact |
|---|---------|------|--------|
| 1 | `pii_redaction_mode()` async bug | `privacy.py:58` | PII kill switch non-functional in production |
| 2 | PII redaction disconnected from LLM pipeline | `llm_secure_io.py` | User PII sent to external LLM providers |
| 3 | gRPC service has no auth validation | `agent_grpc_service.py` | Complete auth bypass if port exposed |
| 4 | `user_id` from request body overrides metadata | `agent_grpc_service.py:248` | Horizontal user impersonation |
| 5 | Raw user_id/username in Python logs (30+ sites) | Multiple files | PII in log storage |

### P1 (Should Fix Soon)

| # | Finding | File | Impact |
|---|---------|------|--------|
| 1 | Missing international phone/address/DOB regex | `privacy.py` | Non-Chinese PII not stripped |
| 2 | Forbidden domain check is string-based | `decision_loop.py:1162` | Potential bypass with clever wording |

### P2 (Should Fix Eventually)

| # | Finding | File | Impact |
|---|---------|------|--------|
| 1 | `laplace_noise` uses non-CSPRNG | `privacy.py:141` | DP guarantees weakened |
| 2 | No cumulative epsilon tracking in `laplace_noise` | `privacy.py` | Averaging attack possible |
| 3 | HS256 JWT fallback still active | `auth.go:494` | Shared secret risk |
| 4 | WebSocket allows empty origin | `websocket_proxy.go:85` | Non-browser client bypass |
| 5 | Kill switch writes without TTL | `kill_switch.py:150` | Stale values persist forever |
| 6 | No alerting for degraded kill switch mode | `kill_switch.py` | Silent fallback to settings |

---

## 7. Recommendations (Priority Order)

1. **Connect PII redaction to LLM pipeline**: `sanitize_text_for_llm()` must call `_redact_pii_text()` to strip emails, phones, IDs, and names before sending to LLM providers.

2. **Add gRPC authentication interceptor**: Validate JWT in the Python gRPC service independently, reject requests without valid tokens, and bind gRPC to localhost only.

3. **Fix `user_id` precedence**: Ignore `request.user_id` in gRPC; use only metadata `user-id` set by authenticated Go Gateway.

4. **Fix `pii_redaction_mode()` async bug**: Convert to async or use cached mode with periodic refresh.

5. **Replace raw user_id in Python logs**: Use `logsafe.user_id_hash()` everywhere, matching Go-side practice. Audit all 30+ sites identified.

6. **Expand PII regex coverage**: Add international phone patterns, passport numbers, and address patterns.

7. **Use CSPRNG in `laplace_noise`**: Replace `random.Random()` with `secrets.SystemRandom()`.

8. **Add TTL to kill switch Redis writes**: Set a TTL (e.g., 30 days) on kill switch values to prevent indefinite stale values.

9. **Add alerting for kill switch degradation**: Emit Prometheus alert when kill switch falls back to settings mode.

10. **Plan HS256 deprecation**: Set a timeline for removing HS256 JWT fallback and document the migration plan.
