package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

// rateLimitRoutePathViaRouter runs a request through a real gin router so
// normalizeRateLimitRoutePath sees the same FullPath()/NoRoute conditions as
// production. An empty registerPath exercises the NoRoute branch.
func rateLimitRoutePathViaRouter(t *testing.T, registerPath, requestPath string) string {
	t.Helper()
	var captured string
	router := gin.New()
	if registerPath != "" {
		router.Any(registerPath, func(c *gin.Context) {
			captured = normalizeRateLimitRoutePath(c)
		})
	} else {
		router.NoRoute(func(c *gin.Context) {
			captured = normalizeRateLimitRoutePath(c)
		})
	}
	req := httptest.NewRequest(http.MethodGet, requestPath, nil)
	req.RemoteAddr = "127.0.0.1:12345"
	router.ServeHTTP(httptest.NewRecorder(), req)
	require.NotEmpty(t, captured, "middleware must have captured a bucket path")
	return captured
}

// TestNormalizeRateLimitRoutePath_BoundedBuckets pins the GW-P3-1 fix: the
// rate-limit bucket namespace must stay bounded for wildcard templates and
// unmatched (NoRoute) paths, so anonymous clients cannot mint arbitrary
// buckets by appending suffix junk to proxy prefixes.
func TestNormalizeRateLimitRoutePath_BoundedBuckets(t *testing.T) {
	// Wildcard template: same-depth concrete suffixes share one bucket even
	// when their content differs (arbitrary suffixes must not multiply
	// buckets)...
	suffixA := rateLimitRoutePathViaRouter(t, "/api/v1/user/*path", "/api/v1/user/settings/AAAAAAAAAA")
	suffixB := rateLimitRoutePathViaRouter(t, "/api/v1/user/*path", "/api/v1/user/settings/BBBBBBBBBB")
	require.Equal(t, suffixA, suffixB,
		"wildcard routes must bucket by template + depth, not by concrete path content")

	// ...while different depths remain distinct so /settings and
	// /settings/ai-usage do not throttle each other (original intent).
	deeper := rateLimitRoutePathViaRouter(t, "/api/v1/user/*path", "/api/v1/user/settings/AAAAAAAAAA/deeper")
	require.NotEqual(t, suffixA, deeper)

	// Extremely deep paths must not extend the namespace either.
	floor := rateLimitRoutePathViaRouter(t, "/api/v1/user/*path", "/api/v1/user/a/b/c/d/e/f/g/h/i/j/k/l")
	capped := rateLimitRoutePathViaRouter(t, "/api/v1/user/*path", "/api/v1/user/a/b/c/d/e/f/x/y/z")
	require.Equal(t, floor, capped, "segment count must be capped")

	// NoRoute: suffix junk on a proxied auth prefix must not mint buckets.
	nrA := rateLimitRoutePathViaRouter(t, "", "/api/v1/auth/login/AAAAAAAAAA")
	nrB := rateLimitRoutePathViaRouter(t, "", "/api/v1/auth/login/BBBBBBBBBB")
	require.Equal(t, nrA, nrB, "NoRoute buckets must ignore untrusted path content")

	// Explicit (non-wildcard) routes keep the plain template as bucket.
	exact := rateLimitRoutePathViaRouter(t, "/api/v1/tasks", "/api/v1/tasks")
	require.Equal(t, "/api/v1/tasks", exact)
}
