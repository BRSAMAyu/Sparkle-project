package main

import (
	"context"
	"fmt"
	"log"

	"github.com/jackc/pgx/v5"
	"github.com/sparkle/gateway/internal/config"
)

func main() {
	cfg := config.Load()

	log.Printf("Connecting to database: %s", cfg.DatabaseURL)

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("❌ Database connection failed: %v", err)
	}
	defer conn.Close(ctx)

	log.Println("✅ Database connection successful!")

	// 测试查询
	var count int64
	err = conn.QueryRow(ctx, "SELECT COUNT(*) FROM users").Scan(&count)
	if err != nil {
		log.Fatalf("❌ Query failed: %v", err)
	}

	log.Printf("✅ Successfully queried users table, current record count: %d", count)

	// 测试其他关键表
	tables := []string{"chat_messages", "tasks", "knowledge_nodes", "plans"}
	for _, table := range tables {
		var tableCount int64
		err = conn.QueryRow(ctx, fmt.Sprintf("SELECT COUNT(*) FROM %s", table)).Scan(&tableCount)
		if err != nil {
			log.Printf("⚠️  Query %s table failed: %v", table, err)
		} else {
			log.Printf("✅ %s table: %d records", table, tableCount)
		}
	}

	log.Println("\n🎉 Database access chain test complete! Go gateway can access PostgreSQL database normally.")
}
