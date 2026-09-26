/*
Core: bridge
Phase: clarify
Stage: regression

V3-FIX-145 regression tests: the engine has served
POST /api/v1/community/groups/{group_id}/files/{file_id}/copy-to-library
since the initial commit (api/v1/community.py, route-tier: authed), but the
gateway community group is purely explicit routes and never registered this
face, and NoRoute only proxies /api/v1/auth/* — so "save group file to my
library" answered a gateway-side 404 route-not-found while the mobile entry
points (file_message_bubble / group_knowledge_base_view) were live. This is
the same failure shape as O10 (goals/analyze-intent): engine-mounted,
gateway-unmounted.

The community group must register the POST face (the engine has no
GET/PUT/DELETE face for this path) on the same authed group as its sibling
Group Files routes, and the route must proxy to the engine unchanged instead
of 404ing at the gateway.
*/
package handler

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestCommunityCopyToLibraryProxiesToEngine pins V3-FIX-145: the
// copy-to-library route must forward to the engine (200 from the upstream in
// this harness, 401/4xx from the real engine in production) — never a
// gateway-side 404.
func TestCommunityCopyToLibraryProxiesToEngine(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	path := "/api/v1/community/groups/00000000-0000-0000-0000-000000000001/files/00000000-0000-0000-0000-000000000002/copy-to-library"
	code := doPOSTWithBody(t, router, path, "")
	if code != http.StatusOK {
		t.Fatalf("POST %s = %d, want 200 (must proxy to engine, not 404)", path, code)
	}
	if got := rec.last(); got != path {
		t.Fatalf("copy-to-library forwarded %q upstream, want path unchanged", got)
	}
}

// TestCommunityCopyToLibraryRouteRegistration pins the method face: POST
// exists on the authed community group; no other method face is registered
// (the engine only serves POST — extra faces would proxy straight to engine
// 405).
func TestCommunityCopyToLibraryRouteRegistration(t *testing.T) {
	router := r208TestRouter(t)

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	const want = "POST /api/v1/community/groups/:group_id/files/:file_id/copy-to-library"
	require.True(t, registered[want],
		"POST copy-to-library must be registered on the authed community group")
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodPatch, http.MethodDelete} {
		require.False(t, registered[method+" "+want[len("POST "):]],
			"engine serves POST only; %s face must stay absent", method)
	}
}
