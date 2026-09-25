/*
Core: bridge
Phase: clarify
Stage: regression

O10 regression tests (J-01 first3, evidence v3/09_evidence/j01_first3): the
engine serves POST /api/v1/goals/analyze-intent (goal_intent.py, mounted at
the /goals prefix) but the gateway Goals group never registered the route, so
every wizard intent analysis fell through to NoRoute and answered
{"error":"route not found"} (curl: gateway 404 vs engine 401 unauthenticated).
The FME entry — the flagship "tell us your goal in your own words" surface —
was silently dead for 5/5 measured personas (116-141ms catch-all fallback to
the legacy form).

The goals group must register the POST face (the engine has no GET/PUT/DELETE
face for this path) on the same authed group as its /goals/ siblings, and the
route must proxy to the engine instead of 404ing at the gateway.
*/
package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func doPOSTWithBody(t *testing.T, router *gin.Engine, path, body string) int {
	t.Helper()
	w := &closeNotifierRecorder{ResponseRecorder: httptest.NewRecorder()}
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	return w.Code
}

// TestGoalsAnalyzeIntentProxiesToEngine pins O10: the analyze-intent route
// must forward to the engine (200 from the upstream in this harness, 401/4xx
// from the real engine in production) — never a gateway-side 404.
func TestGoalsAnalyzeIntentProxiesToEngine(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	code := doPOSTWithBody(t, router, "/api/v1/goals/analyze-intent", `{"text":"通过高数考试"}`)
	if code != http.StatusOK {
		t.Fatalf("POST /api/v1/goals/analyze-intent = %d, want 200 (must proxy to engine, not 404)", code)
	}
	if got := rec.last(); got != "/api/v1/goals/analyze-intent" {
		t.Fatalf("analyze-intent forwarded %q upstream, want path unchanged", got)
	}
}

// TestGoalsAnalyzeIntentRouteRegistration pins the method face: POST exists on
// the authed goals group; no other method face is registered (the engine only
// serves POST — extra faces would proxy straight to engine 405).
func TestGoalsAnalyzeIntentRouteRegistration(t *testing.T) {
	router := r208TestRouter(t)

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	require.True(t, registered["POST /api/v1/goals/analyze-intent"],
		"POST /api/v1/goals/analyze-intent must be registered on the authed goals group")
	require.False(t, registered["GET /api/v1/goals/analyze-intent"],
		"engine serves POST only; GET face must stay absent")
}
