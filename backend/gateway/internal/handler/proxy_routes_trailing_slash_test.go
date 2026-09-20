/*
Core: <cognitive|execution|bridge|infra>
Phase: none
Stage: regression

Regression tests for gamification-eval P1-2 (leaderboard/inventory redirect
loop). gin's httprouter does not match "/api/v1/<group>" against
"/api/v1/<group>/*path", so wildcard-registered proxy groups 301'd the bare
collection path to "/api/v1/<group>/"; the FastAPI engine then 307'd back to
the bare path with an absolute internal Location
("http://127.0.0.1:8000/..."), giving clients an endless 301<->307 loop that
ends in 401 once the redirect fan-out drops the Authorization header.

registerREST must (1) register the bare collection path and (2) trim trailing
slashes on wildcard-matched paths before proxying.
*/
package handler

import (
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"sync"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/middleware"
)

type pathRecorder struct {
	mu   sync.Mutex
	seen []string
}

func (p *pathRecorder) handler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		p.seen = append(p.seen, r.URL.Path)
		p.mu.Unlock()
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"success":true}`))
	}
}

func (p *pathRecorder) last() string {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.seen) == 0 {
		return ""
	}
	return p.seen[len(p.seen)-1]
}

func newProxyTestSetup(t *testing.T) (*gin.Engine, *pathRecorder) {
	t.Helper()
	gin.SetMode(gin.TestMode)

	rec := &pathRecorder{}
	upstream := httptest.NewServer(rec.handler())
	t.Cleanup(upstream.Close)

	target, err := url.Parse(upstream.URL)
	if err != nil {
		t.Fatalf("parse upstream url: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(target)

	abTest := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: upstream.URL,
		Timeout:    3 * time.Second,
		Enabled:    false,
	})

	h := NewProxyRoutesHandler(proxy, abTest, zap.NewNop())

	router := gin.New()
	api := router.Group("/api/v1")
	mockAuth := func(c *gin.Context) {
		c.Set("user_id", "test-user-123")
		c.Set("auth_token", "test-token-abc")
		c.Next()
	}
	h.RegisterProxyRoutes(api, mockAuth)
	return router, rec
}

func doGET(t *testing.T, router *gin.Engine, path string) int {
	t.Helper()
	w := &closeNotifierRecorder{ResponseRecorder: httptest.NewRecorder()}
	req := httptest.NewRequest(http.MethodGet, path, nil)
	router.ServeHTTP(w, req)
	return w.Code
}

// closeNotifierRecorder satisfies gin's response_writer type assertion, which
// httputil.ReverseProxy exercises while streaming the upstream response.
type closeNotifierRecorder struct {
	*httptest.ResponseRecorder
}

func (c *closeNotifierRecorder) CloseNotify() <-chan bool {
	ch := make(chan bool, 1)
	return ch
}

func TestBareCollectionPathProxiesDirectly_NoRedirectLoop(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	for _, path := range []string{
		"/api/v1/leaderboards",
		"/api/v1/inventory",
		"/api/v1/photons",
		"/api/v1/shop",
		"/api/v1/action-proposals", // X-03：proposal 收件箱裸集合路径直连
	} {
		code := doGET(t, router, path)
		if code != http.StatusOK {
			t.Fatalf("GET %s = %d, want 200 (bare collection must proxy, not 301)", path, code)
		}
		if got := rec.last(); got != path {
			t.Fatalf("GET %s forwarded %q upstream, want %q", path, got, path)
		}
	}
}

func TestTrailingSlashWildcardPathIsTrimmedBeforeProxying(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	code := doGET(t, router, "/api/v1/leaderboards/")
	if code != http.StatusOK {
		t.Fatalf("GET /api/v1/leaderboards/ = %d, want 200", code)
	}
	if got := rec.last(); got != "/api/v1/leaderboards" {
		t.Fatalf("trailing slash forwarded %q upstream, want trimmed %q", got, "/api/v1/leaderboards")
	}
}

func TestWildcardSubpathsStillProxyUnchanged(t *testing.T) {
	router, rec := newProxyTestSetup(t)

	for _, path := range []string{
		"/api/v1/leaderboards/top-three/streak",
		"/api/v1/shop/items",
		"/api/v1/inventory/owned",
		"/api/v1/photons/balance",
		"/api/v1/action-proposals/00000000-0000-0000-0000-000000000000/receipt", // X-03：receipt 端点透传
	} {
		code := doGET(t, router, path)
		if code != http.StatusOK {
			t.Fatalf("GET %s = %d, want 200", path, code)
		}
		if got := rec.last(); got != path {
			t.Fatalf("GET %s forwarded %q upstream, want unchanged", path, got)
		}
	}
}
