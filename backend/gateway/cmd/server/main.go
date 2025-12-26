package main

import (
	"context"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/handler"
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

	// Connect to Agent Service
	agentClient, err := agent.NewClient(cfg.AgentAddress)
	if err != nil {
		log.Fatalf("Unable to connect to agent service: %v", err)
	}
	defer agentClient.Close()

	// Initialize Handlers
	chatOrchestrator := handler.NewChatOrchestrator(agentClient, queries)

	// Setup Router
	r := gin.Default()

	// Middleware (e.g. JWT) can be added here

	// API Routes
	api := r.Group("/api/v1")
	{
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ok"})
		})
		// api.POST("/auth/login", authHandler.Login)
	}

	// WebSocket Route
	r.GET("/ws/chat", chatOrchestrator.HandleWebSocket)

	log.Printf("Gateway starting on :%s", cfg.Port)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}
