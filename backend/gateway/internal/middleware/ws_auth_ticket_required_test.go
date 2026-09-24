package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// WSQ-7（WS-TICKET-DESIGN §2.5 P5 / §6.1）：WS_TICKET_REQUIRED 收紧开关两态测试。
// 关（默认观察期）：三顺位认证链保持原状（回归）。
// 开：WsAuth 只走 ticket——即使 JWT 完全有效，旧凭证直连也一律
// 401 + `ws_ticket_required`（且不花验签/Redis 认证成本），ticket 双通道
// （query + subprotocol）不受影响。

func TestWsAuthMiddleware_TicketRequiredOffKeepsDowngradePaths(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = false // default posture
	_, rdb := newWsTicketRedisForTest(t)
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "ws-user-tighten-off",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"jti":  "ws-jti-tighten-off",
		"sid":  "ws-session-tighten-off",
		"iss":  cfg.JWTIssuer,
		"aud":  cfg.JWTAudience,
	})
	router := newWsAuthTestRouter(cfg, rdb)

	byHeader := performWsAuthRequest(router, "/ws", token)
	require.Equal(t, http.StatusOK, byHeader.Code)
	assert.Contains(t, byHeader.Body.String(), `"ws_auth_method":"jwt_header"`)
}

func TestWsAuthMiddleware_TicketRequiredRejectsValidJWTHeader(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = true
	_, rdb := newWsTicketRedisForTest(t)
	// Key: a fully VALID JWT — proves the rejection is policy, not signature.
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "ws-user-tighten",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"jti":  "ws-jti-tighten",
		"sid":  "ws-session-tighten",
		"iss":  cfg.JWTIssuer,
		"aud":  cfg.JWTAudience,
	})
	router := newWsAuthTestRouter(cfg, rdb)

	recorder := performWsAuthRequest(router, "/ws", token)

	require.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "ws_ticket_required")
	assert.NotContains(t, recorder.Body.String(), "invalid_or_expired_token",
		"old credentials must be rejected by policy before any validation")
}

func TestWsAuthMiddleware_TicketRequiredRejectsQueryToken(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = true
	cfg.AllowWsQueryToken = true // even the dev-only query channel is a downgrade path
	_, rdb := newWsTicketRedisForTest(t)
	token := makeTestJWT(cfg, nil)
	router := newWsAuthTestRouter(cfg, rdb)

	recorder := performWsAuthRequest(router, "/ws?token="+token, "")

	require.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "ws_ticket_required")
}

func TestWsAuthMiddleware_TicketRequiredRejectsMissingCredentials(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = true
	_, rdb := newWsTicketRedisForTest(t)
	router := newWsAuthTestRouter(cfg, rdb)

	recorder := performWsAuthRequest(router, "/ws", "")

	require.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "ws_ticket_required")
}

func TestWsAuthMiddleware_TicketRequiredStillAcceptsQueryTicket(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = true
	cfg.AllowWsQueryTicket = true // query channel keeps its own gate
	mr, rdb := newWsTicketRedisForTest(t)
	router := newWsAuthTestRouter(cfg, rdb)

	recorder := performWsAuthRequest(router, "/ws?ticket="+wsQueryTicketTestTicket, "")

	require.Equal(t, http.StatusOK, recorder.Code)
	assert.Contains(t, recorder.Body.String(), `"ws_auth_method":"ticket"`)
	assert.False(t, mr.Exists(wsTicketKeyPrefix+wsQueryTicketTestTicket),
		"ticket must be consumed (GETDEL single-use)")
}

func TestWsAuthMiddleware_TicketRequiredStillAcceptsSubprotocolTicket(t *testing.T) {
	cfg := testAuthConfig()
	cfg.WsTicketRequired = true
	cfg.AllowWsQueryTicket = false // subprotocol channel is independent of the query gate
	_, rdb := newWsTicketRedisForTest(t)
	router := newWsAuthTestRouter(cfg, rdb)

	req := httptest.NewRequest(http.MethodGet, "/ws", nil)
	req.Header.Set("Sec-WebSocket-Protocol", "ticket="+wsQueryTicketTestTicket)
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, req)

	require.Equal(t, http.StatusOK, recorder.Code)
	assert.Contains(t, recorder.Body.String(), `"ws_auth_method":"ticket"`)
}
