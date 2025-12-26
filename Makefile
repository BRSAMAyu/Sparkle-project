.PHONY: dev-up sync-db proto-gen

DB_CONTAINER=sparkle_db
DB_USER=postgres
DB_NAME=sparkle

# 启动基础设施
dev-up:
	docker compose up -d

# 核心同步流：Python 迁移 -> 导出结构 -> 生成 Go 代码
sync-db:
	@echo "🔄 1. Running Python Alembic Migrations..."
	cd backend && alembic upgrade head
	@echo "🔍 Checking if $(DB_CONTAINER) is running..."
	@docker ps -q -f name=$(DB_CONTAINER) > /dev/null || (echo "❌ Error: Container $(DB_CONTAINER) is not running. Run 'make dev-up' first." && exit 1)
	@echo " 2. Dumping Schema (Structure Only)..."
	mkdir -p backend/gateway/internal/db
	docker exec $(DB_CONTAINER) pg_dump -U $(DB_USER) -d $(DB_NAME) --schema-only | grep -v '^\\' > backend/gateway/internal/db/schema.sql
	@echo "⚡ 3. Generating Go Code via SQLC..."
	cd backend/gateway && sqlc generate
	@echo "✅ Database Schema & Go Code Synced Successfully!"

# 生成 Protobuf 代码
proto-gen:
	@echo "🚀 Generating Protobuf Code..."
	mkdir -p backend/gateway/gen/agent/v1
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/agent/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/agent/v1 --go-grpc_opt=paths=source_relative \
	       proto/agent_service.proto
