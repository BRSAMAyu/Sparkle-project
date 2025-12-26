package main

import (
	"context"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/handler"
	"github.com/sparkle/gateway/internal/infra/redis"
	"github.com/sparkle/gateway/internal/middleware"
	"github.com/sparkle/gateway/internal/service"
)

func main() {
	cfg := config.Load()

	// Connect to DB
	ctx := context.Background()
	conn, err := pgx.Connect(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer conn.Close(ctx)
	queries := db.New(conn)

	// Connect to Redis
	rdb, err := redis.NewClient(cfg)
	if err != nil {
		log.Fatalf("Unable to connect to Redis: %v", err)
	}
	defer rdb.Close()

	// Initialize Services
	quotaService := service.NewQuotaService(rdb)
	chatHistoryService := service.NewChatHistoryService(rdb)
	semanticCacheService := service.NewSemanticCacheService(rdb)

	// Connect to Agent Service
	agentClient, err := agent.NewClient(cfg.AgentAddress)
	if err != nil {
		log.Fatalf("Unable to connect to agent service: %v", err)
	}
	defer agentClient.Close()

	// Initialize Handlers
	chatOrchestrator := handler.NewChatOrchestrator(
		agentClient,
		queries,
		chatHistoryService,
		quotaService,
		semanticCacheService,
	)
	groupChatHandler := handler.NewGroupChatHandler(queries)

	// Setup Router
	r := gin.Default()

	// Middleware (e.g. JWT) can be added here

	// WebSocket Route (Go Native)
	r.GET("/ws/chat", middleware.AuthMiddleware(cfg), chatOrchestrator.HandleWebSocket)

	// Middleware
	authMiddleware := middleware.AuthMiddleware(cfg)

	// API Routes
	api := r.Group("/api/v1")
	{
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ok"})
		})

		// Go Optimized Endpoints
		api.GET("/groups/:group_id/messages", authMiddleware, groupChatHandler.GetMessages)
	}

	// Reverse Proxy for Python Backend (REST API)
	targetURL, err := url.Parse("http://localhost:8000")
	if err != nil {
		log.Fatalf("Failed to parse Python backend URL: %v", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
		req.Host = targetURL.Host
	}

	// Forward all other requests to Python Backend
	// This covers /api/v1/groups, /api/v1/users, etc.
	// We wrap the proxy with Auth checks for protected routes
	r.NoRoute(func(c *gin.Context) {
		path := c.Request.URL.Path

		// Public routes that don't need Go-side validation (let Python handle or open)
		// /api/v1/auth/* -> Login/Register
		// /api/v1/health -> Health check (though we handled one explicitly above)
		// /docs, /redoc, /openapi.json -> Swagger UI
		if strings.HasPrefix(path, "/api/v1/auth") ||
			path == "/api/v1/health" ||
			strings.HasPrefix(path, "/docs") ||
			strings.HasPrefix(path, "/redoc") ||
			strings.HasPrefix(path, "/openapi.json") {
			proxy.ServeHTTP(c.Writer, c.Request)
			return
		}

		// Verify Token
		authMiddleware(c)
		if c.IsAborted() {
			return
		}

		// Token is valid. Pass user_id to backend via header for trust (optional)
		userID := c.GetString("user_id")
		if userID != "" {
			c.Request.Header.Set("X-User-ID", userID)
		}

		proxy.ServeHTTP(c.Writer, c.Request)
	})

	log.Printf("Gateway starting on :%s", cfg.Port)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}
