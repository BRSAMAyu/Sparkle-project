# R12 / R1A3 — Goals_Plans 二次深度审查
**Date**: 2024-05-24
**Scope**: Goals + Plans
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The frontend provides a rich multi-sensory plan tracking and goal breakdown UI, aligned with the vision. However, critical integration gaps between the Gateway and Backend prevent core phase and sprint functionalities from working.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 2 |
| P1 (important gap, ship with plan) | 0 |
| P2 (nice to have, post-launch) | 0 |
| Verified working | 3 |

---

## R11 P0 验证
N/A - Initial secondary audit for Goals/Plans in R12.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Exam Sprint Endpoints Not Proxied in Go Gateway
**File**: `backend/gateway/internal/handler/proxy_routes.go`
**Lines**: 569-577
**Problem**: The Go Gateway only explicitly proxies `POST /intake` for the `/exam-sprint` route group. However, the Flutter client depends on multiple other endpoints like `/exam-sprint/completion`, `/exam-sprint/post-exam-review`, and `/exam-sprint/portfolio` defined in `mobile/lib/core/network/api_endpoints.dart` and implemented in the Python backend. Because Go Gateway uses explicit routing without an `Any("/*path")` wildcard for `/exam-sprint`, these essential plan features will return 404 Not Found.
**Evidence**:
```go
	examSprint := api.Group("/exam-sprint")
	examSprint.Use(authMiddleware)
	{
		// route-tier: authed
		examSprint.POST("/intake", h.proxyWithHeaders)
	}
```
**Expected**: Go Gateway should proxy all endpoints under `/exam-sprint`.
**Fix recommendation**: Replace explicit `POST "/intake"` with `examSprint.Any("/*path", h.proxyWithHeaders)` and `examSprint.Any("", h.proxyWithHeaders)` in `proxy_routes.go`.

### P0-2: Plan Phases Endpoints Not Proxied in Go Gateway
**File**: `backend/gateway/internal/handler/proxy_routes.go`
**Lines**: 322-333 (approx, under `plans` group)
**Problem**: The Flutter app makes requests to `/plans/:id/phases` and `/plans/phases/:phaseCardId/activate` (and `complete`, `feedback`, etc.) as defined in `api_endpoints.dart`. The Go Gateway explicitly defines routes for `/plans/:id`, `/plans/:id/progress`, etc., but completely omits any routes for phases. As a result, any operations related to Plan Phases will fail with a 404.
**Evidence**:
```go
	plans := api.Group("/plans")
	plans.Use(authMiddleware)
	{
		// ... explicit routes like plans.GET("/:id") ...
		// MISSING: plans.GET("/:id/phases")
		// MISSING: plans.POST("/phases/:phaseCardId/activate")
	}
```
**Expected**: Go Gateway must proxy requests for `/plans/:id/phases`, `/plans/:id/phases/reorder` and `/plans/phases/*`.
**Fix recommendation**: Add explicit routes for `plans.GET("/:id/phases", h.proxyWithHeaders)`, `plans.POST("/:id/phases/reorder", h.proxyWithHeaders)`, and a wildcard for `plans.Any("/phases/*path", h.proxyWithHeaders)` in `proxy_routes.go`.

---

## P1 Findings (Important, Ship With Plan)
None found in this trace sequence.

---

## P2 Findings (Post-Launch)
None found in this trace sequence.

---

## Verified Working (Strengths)
### V-1: Goal Creation & Detail Navigation
- **Verification**: Flutter `GoalRoutes` correctly map `/goals/new` and `/goals/:goalId`. The UI successfully retrieves `GoalDetailData` via `GET /experience/goal-detail/{goalId}` and allows tasks to be completed, triggering `POST /tasks/{taskId}/complete`. Go Gateway handles `/goals` and `/experience` routing properly.
- **Verdict**: Working and properly integrated.

### V-2: Minimum Acceptance Criteria Confirmation
- **Verification**: User can confirm minimum acceptance criteria which fires a `PUT` to `/experience/goal-detail/{goalId}/criteria-status`. The Python backend in `api/v1/experience/goal_router.py` correctly implements this and updates the database.
- **Verdict**: Working and properly integrated.

### V-3: Plan Overview & Generation
- **Verification**: Flutter correctly fetches plans via `/plans` and generates tasks via `POST /plans/{id}/generate-tasks`. The Go Gateway accurately proxies these routes, and the UI handles loading, error states, and empty states robustly with graceful retries.
- **Verdict**: Working and properly integrated.

---

## Cross-Route Integration Issues
None beyond the aforementioned proxy 404s. The API contract schemas match exactly between Dart models and Python pydantic schemas.

---

## Code Quality Observations
- **Flutter**: State management via Riverpod `AsyncValue` is handled elegantly with robust error catching and user-facing snackbars.
- **Go**: The explicit routing pattern in `proxy_routes.go` is safer than a global catch-all but requires rigid maintenance, which directly led to the P0-1 and P0-2 bugs where newly added backend routes were forgotten in the gateway layer.