package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc/codes"
	grpcstatus "google.golang.org/grpc/status"
)

func TestWriteGRPCError_InvalidArgument(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, grpcstatus.Error(codes.InvalidArgument, "bad request"))
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.Equal(t, "bad request", resp["error"])
}

func TestWriteGRPCError_NotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, grpcstatus.Error(codes.NotFound, "not found"))
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestWriteGRPCError_Unauthenticated(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, grpcstatus.Error(codes.Unauthenticated, "no auth"))
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestWriteGRPCError_PermissionDenied(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, grpcstatus.Error(codes.PermissionDenied, "forbidden"))
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusForbidden, w.Code)
}

func TestWriteGRPCError_InternalError(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, grpcstatus.Error(codes.Internal, "boom"))
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestWriteGRPCError_NonGRPCErrors(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		writeGRPCError(c, assert.AnError)
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestInjectAuthContext_SetsBearerToken(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		c.Set("auth_token", "my-jwt-token")
		injectAuthContext(c)
		c.Status(200)
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInjectAuthContext_NoToken(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		injectAuthContext(c)
		c.Status(200)
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestErrorBookHandler_CreateError_InvalidJSON(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewErrorBookHandler(nil)
	r := gin.New()
	r.POST("/errors", func(c *gin.Context) {
		c.Set("user_id", "user-123")
		c.Next()
	}, h.CreateError)

	req := httptest.NewRequest(http.MethodPost, "/errors", strings.NewReader("not json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestComponentStatus_IsHealthy(t *testing.T) {
	assert.True(t, ComponentStatus{Status: "healthy"}.isHealthy())
	assert.True(t, ComponentStatus{Status: "degraded"}.isHealthy())
	assert.False(t, ComponentStatus{Status: "unhealthy"}.isHealthy())
}
