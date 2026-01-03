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

	log.Printf("正在连接数据库: %s", cfg.DatabaseURL)

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("❌ 数据库连接失败: %v", err)
	}
	defer conn.Close(ctx)

	log.Println("✅ 数据库连接成功！")

	// 测试查询
	var count int64
	err = conn.QueryRow(ctx, "SELECT COUNT(*) FROM users").Scan(&count)
	if err != nil {
		log.Fatalf("❌ 查询失败: %v", err)
	}

	log.Printf("✅ 成功查询 users 表，当前记录数: %d", count)

	// 测试其他关键表
	tables := []string{"chat_messages", "tasks", "knowledge_nodes", "plans"}
	for _, table := range tables {
		var tableCount int64
		err = conn.QueryRow(ctx, fmt.Sprintf("SELECT COUNT(*) FROM %s", table)).Scan(&tableCount)
		if err != nil {
			log.Printf("⚠️  查询 %s 表失败: %v", table, err)
		} else {
			log.Printf("✅ %s 表: %d 条记录", table, tableCount)
		}
	}

	log.Println("\n🎉 数据库访问链路测试完成！Go 网关可以正常访问 PostgreSQL 数据库。")
}
