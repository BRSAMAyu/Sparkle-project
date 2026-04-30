package middleware

import (
	"net"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestInternalIPWhitelist_DevelopmentBypass(t *testing.T) {
	cfg := &config.Config{
		Environment:        "development",
		InternalIPWhitelist: []string{"10.0.0.0/8"},
	}
	r := gin.New()
	r.Use(InternalIPWhitelistMiddleware(cfg))
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInternalIPWhitelist_EmptyWhitelist(t *testing.T) {
	cfg := &config.Config{
		Environment:         "production",
		InternalIPWhitelist: []string{},
	}
	r := gin.New()
	r.Use(InternalIPWhitelistMiddleware(cfg))
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestParseInternalWhitelist_CIDR(t *testing.T) {
	nets := parseInternalWhitelist([]string{"10.0.0.0/8", "172.16.0.0/12"})
	assert.Len(t, nets, 2)
	assert.True(t, nets[0].Contains(net.ParseIP("10.1.2.3")))
	assert.True(t, nets[1].Contains(net.ParseIP("172.16.5.5")))
	assert.False(t, nets[0].Contains(net.ParseIP("192.168.1.1")))
}

func TestParseInternalWhitelist_SingleIP(t *testing.T) {
	nets := parseInternalWhitelist([]string{"192.168.1.100"})
	assert.Len(t, nets, 1)
	assert.True(t, nets[0].Contains(net.ParseIP("192.168.1.100")))
	assert.False(t, nets[0].Contains(net.ParseIP("192.168.1.101")))
}

func TestParseInternalWhitelist_Empty(t *testing.T) {
	nets := parseInternalWhitelist([]string{})
	assert.Len(t, nets, 0)

	nets = parseInternalWhitelist(nil)
	assert.Len(t, nets, 0)
}

func TestParseInternalWhitelist_InvalidEntries(t *testing.T) {
	nets := parseInternalWhitelist([]string{"not-an-ip", "", "10.0.0.0/8"})
	assert.Len(t, nets, 1)
	assert.True(t, nets[0].Contains(net.ParseIP("10.1.2.3")))
}

func TestParseInternalWhitelist_IPv6(t *testing.T) {
	nets := parseInternalWhitelist([]string{"::1"})
	assert.Len(t, nets, 1)
	assert.True(t, nets[0].Contains(net.ParseIP("::1")))
	assert.False(t, nets[0].Contains(net.ParseIP("::2")))
}

func TestParseInternalWhitelist_TrimsSpaces(t *testing.T) {
	nets := parseInternalWhitelist([]string{"  10.0.0.0/8  "})
	assert.Len(t, nets, 1)
}
