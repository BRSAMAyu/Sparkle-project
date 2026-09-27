/*
Core: bridge
Phase: clarify
Stage: regression

V3-FIX-337 regression tests: the engine has served
POST /api/v1/push/interaction since api/v1/push_interaction.py was mounted
via api_router.include_router (route-tier: authed), but the gateway never
registered a /push group and NoRoute only whitelists /api/v1/auth/* — so the
mobile push-interaction receipt (notification_service._reportPushInteraction,
the endpoint's sole writer) answered a permanent gateway-side 404, and the
mobile catch swallowed it. Push open/dismiss feedback was structurally lost.

The push group must register the POST face (the engine has no GET/PUT/PATCH/
DELETE face for this path) and proxy to the engine unchanged instead of 404ing
at the gateway. Same failure shape as O10 (goals/analyze-intent) and
V3-FIX-145 (copy-to-library): engine-mounted, gateway-unmounted.
*/
package handler

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestPushInteractionProxiesToEngine pins V3-FIX-337: the push interaction
// receipt must forward to the engine (200 from the upstream in this harness,
// 401/4xx from the real engine in production) — never a gateway-side 404.
func TestPushInteractionProxiesToEngine(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	path := "/api/v1/push/interaction"
	code := doPOSTWithBody(t, router, path, `{"push_id":"00000000-0000-0000-0000-000000000003","action":"opened"}`)
	if code != http.StatusOK {
		t.Fatalf("POST %s = %d, want 200 (must proxy to engine, not 404)", path, code)
	}
	if got := rec.last(); got != path {
		t.Fatalf("push interaction forwarded %q upstream, want path unchanged", got)
	}
}

// TestPushInteractionRouteRegistration pins the method face: POST exists on
// the authed push group; no other method face is registered (the engine only
// serves POST — extra faces would proxy straight to engine 405), and no
// wildcard sibling under /push/* exists for paths the engine cannot serve.
func TestPushInteractionRouteRegistration(t *testing.T) {
	router := r208TestRouter(t)

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	const want = "POST /api/v1/push/interaction"
	require.True(t, registered[want],
		"POST /push/interaction must be registered on the authed push group (V3-FIX-337)")
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodPatch, http.MethodDelete} {
		require.False(t, registered[method+" "+want[len("POST "):]],
			"engine serves POST only; %s face must stay absent", method)
	}
	require.False(t, registered["GET /api/v1/push/*path"],
		"engine has no /push/* wildcard face; wildcard group must stay absent")
}
