# Sparkle S2-0 Runnable Golden Path Bring-Up

> Date: 2026-04-06  
> Status: Verified local golden path  
> Purpose: Turn Stage 2 Workstream 1 into one concrete, repeatable bring-up path for future Codex runs
> Companion audit:
> - `docs/product/implementation/SPARKLE_S2_0A_ENVIRONMENT_AND_STARTUP_AUDIT_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_S2_0B_GOLDEN_PATH_BRING_UP_CHECKLIST_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_S2_0C_IOS_SIMULATOR_SMOKE_VALIDATION_2026-04-06.md`

---

## 0. What This Document Is

This is the first runnable Stage 2 execution note.

It is not a broad environment manual.

It is the shortest path we currently trust for:

1. booting the real local stack
2. validating backend and gateway readiness
3. launching a real mobile simulator path
4. proving guest entry into the core shell on the full stack

---

## 1. Verified Golden Path

### Chosen path

For S2-0, the validated golden path is:

> **local backend + local gateway + local Redis/Postgres/MinIO + iOS simulator + Flutter integration test**

Why this path:

- the machine already has a working iOS simulator
- the app defaults to `localhost` correctly on iOS simulator
- the repository already contains a real UI integration test for guest entry and core shell navigation

### Verified on 2026-04-06

The following path was run successfully on this machine:

1. `./scripts/dev_local_stack.sh up`
2. `make smoke`
3. `make local-signoff-preflight`
4. `cd mobile && flutter test integration_test/app_test.dart -d 79461B43-C730-47C4-9994-10CA7C5546BD -r compact`

Result:

- backend health passed
- gateway health passed
- gateway CQRS health passed
- PostgreSQL connectivity passed
- Redis connectivity passed
- Redis search index `idx:knowledge` present
- Alembic current revision at head
- iOS simulator build passed
- guest user entered the app and the integration test navigated across the core shell

---

## 2. Exact Startup Checklist

### Step 1. Confirm device availability

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter devices
```

Expected:

- one booted iOS simulator appears

### Step 2. Bring up the local stack

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
./scripts/dev_local_stack.sh up
```

This path currently does the useful setup work that broad docs often skip:

- starts PostgreSQL, Redis, and MinIO
- initializes Apache AGE schema
- creates Redis index `idx:knowledge`
- starts local gRPC, API, gateway, and workers

### Step 3. Validate health before touching mobile

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
make smoke
make local-signoff-preflight
```

Do not continue to mobile if either command fails.

### Step 4. Run the real simulator proof

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter test integration_test/app_test.dart -d <IOS_SIMULATOR_ID> -r compact
```

What this proves:

- app boots on the simulator
- guest login works against the real backend
- dashboard shell loads
- navigation to galaxy, chat, community, profile, and back home works

### Step 5. Optional manual app launch

If you want an interactive app after the automated proof:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter run -d <IOS_SIMULATOR_ID>
```

---

## 3. Current Known Issues

### Non-blocking for the golden path

1. `./scripts/dev_local_stack.sh up` has repo side effects.
   - It recreates the Redis search index `idx:knowledge`.
   - It rebuilds the tracked gateway binary at `backend/gateway/bin/gateway`.

### Blocking issue fixed during this run

1. The iOS app initially failed to compile because `dashboard_screen.dart` referenced `context.sparkleTypography.bodySmall`, while `SparkleTypography` no longer exposed that getter.
   - A compatibility getter was restored in `mobile/lib/core/design/tokens_v2/theme_manager.dart`.

2. The gateway initially returned `404` for `GET /api/v1/growth/dashboard` even though FastAPI exposed the route.
   - The live issue was a missing `/growth` proxy group in `backend/gateway/internal/handler/proxy_routes.go`.
   - The gateway route table was updated and the simulator smoke no longer logs the growth-dashboard warning.

---

## 4. Recommended Default Command Set For Future Codex Runs

If the next Codex needs the fastest truthful Stage 2 bring-up, use this sequence:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
./scripts/dev_local_stack.sh up
make smoke
make local-signoff-preflight
cd mobile
flutter devices
flutter test integration_test/app_test.dart -d <IOS_SIMULATOR_ID> -r compact
```

---

## 5. Stage 2 Exit Signal For S2-0

S2-0 should be considered complete enough to move forward when:

1. a future Codex can run the checklist above without guesswork
2. the local stack reaches green health before mobile launch
3. the simulator proof reaches the dashboard shell through guest entry
4. failures are recorded as concrete blockers instead of vague startup uncertainty

As of 2026-04-06, this condition is met for the iOS simulator path.
