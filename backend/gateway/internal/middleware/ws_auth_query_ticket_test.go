package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// WSQ-2（WS-TICKET-DESIGN §2.3）测试基建：miniredis 里预置一张可核销的票。
const wsQueryTicketTestTicket = "0f0e0d0c-1111-2222-3333-444455556666"
const wsQueryTicketTestPayload = `{"user_id":"ws-ticket-user","token":"ticket-bearer-token"}`

func newWsTicketRedisForTest(t *testing.T) (*miniredis.Miniredis, *redis.Client) {
	t.Helper()
	mr := miniredis.RunT(t)
	require.NoError(t, mr.Set(wsTicketKeyPrefix+wsQueryTicketTestTicket, wsQueryTicketTestPayload))
	return mr, redis.NewClient(&redis.Options{Addr: mr.Addr()})
}

// 闸门两态（§6.1-2 前置）：ALLOW_WS_QUERY_TICKET=false 时 ?ticket= 不放行且票
// 不被消耗；翻 true 后同一张票核销成功，且单次有效（第二发 401）。
// 全程 ALLOW_WS_QUERY_TOKEN=false —— ticket 通道不再被生产禁令连坐。
func TestWsAuthMiddleware_QueryTicketGateTwoStates(t *testing.T) {
	cfg := testAuthConfig()
	cfg.AllowWsQueryToken = false
	mr, rdb := newWsTicketRedisForTest(t)

	// 关门：401 missing_credentials，票原封不动。
	cfg.AllowWsQueryTicket = false
	closedRouter := newWsAuthTestRouter(cfg, rdb)
	closed := performWsAuthRequest(closedRouter, "/ws?ticket="+wsQueryTicketTestTicket, "")
	require.Equal(t, http.StatusUnauthorized, closed.Code)
	assert.Contains(t, closed.Body.String(), "authorization_token_required")
	assert.True(t, mr.Exists(wsTicketKeyPrefix+wsQueryTicketTestTicket),
		"closed gate must not consume the ticket")

	// 开门（默认/生产放行）：同一张票核销成功。
	cfg.AllowWsQueryTicket = true
	openRouter := newWsAuthTestRouter(cfg, rdb)
	open := performWsAuthRequest(openRouter, "/ws?ticket="+wsQueryTicketTestTicket, "")
	require.Equal(t, http.StatusOK, open.Code)
	assert.Contains(t, open.Body.String(), `"user_id":"ws-ticket-user"`)
	assert.Contains(t, open.Body.String(), `"auth_token":"ticket-bearer-token"`)
	assert.Contains(t, open.Body.String(), `"ws_auth_method":"ticket"`)
	assert.False(t, mr.Exists(wsTicketKeyPrefix+wsQueryTicketTestTicket),
		"ticket must be consumed (GETDEL single-use)")

	// 单次核销：重放同一张票 401。
	replay := performWsAuthRequest(openRouter, "/ws?ticket="+wsQueryTicketTestTicket, "")
	assert.Equal(t, http.StatusUnauthorized, replay.Code)
}

// 生产口径（§6.1-2）：ALLOW_WS_QUERY_TOKEN=false + ALLOW_WS_QUERY_TICKET=true 下
// ?token= 401、?ticket=（有效票）核销成功。
func TestWsAuthMiddleware_ProductionPostureTicketOpenTokenShut(t *testing.T) {
	cfg := testAuthConfig()
	cfg.AllowWsQueryToken = false
	cfg.AllowWsQueryTicket = true
	_, rdb := newWsTicketRedisForTest(t)

	token := makeTestJWT(cfg, nil)
	router := newWsAuthTestRouter(cfg, rdb)

	byToken := performWsAuthRequest(router, "/ws?token="+token, "")
	require.Equal(t, http.StatusUnauthorized, byToken.Code)
	assert.Contains(t, byToken.Body.String(), "authorization_token_required")

	byTicket := performWsAuthRequest(router, "/ws?ticket="+wsQueryTicketTestTicket, "")
	require.Equal(t, http.StatusOK, byTicket.Code)
	assert.Contains(t, byTicket.Body.String(), `"ws_auth_method":"ticket"`)
}

// 闸门只覆盖 query 通道（§3.2）：subprotocol 携带的票不受
// ALLOW_WS_QUERY_TICKET 影响，关门状态下照常核销。
func TestWsAuthMiddleware_SubprotocolTicketIgnoresQueryGate(t *testing.T) {
	cfg := testAuthConfig()
	cfg.AllowWsQueryToken = false
	cfg.AllowWsQueryTicket = false
	_, rdb := newWsTicketRedisForTest(t)

	router := newWsAuthTestRouter(cfg, rdb)
	req := httptest.NewRequest(http.MethodGet, "/ws", nil)
	req.Header.Set("Sec-WebSocket-Protocol", "ticket="+wsQueryTicketTestTicket)
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, req)

	require.Equal(t, http.StatusOK, recorder.Code)
	assert.Contains(t, recorder.Body.String(), `"ws_auth_method":"ticket"`)
}
