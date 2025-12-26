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
	@echo "  → Go..."
	mkdir -p backend/gateway/gen/agent/v1
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/agent/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/agent/v1 --go-grpc_opt=paths=source_relative \
	       proto/agent_service.proto
	@echo "  → Python..."
	mkdir -p backend/app/gen/agent/v1
	python -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/agent/v1 \
	       --grpc_python_out=backend/app/gen/agent/v1 \
	       --pyi_out=backend/app/gen/agent/v1 \
	       proto/agent_service.proto
	@echo "✅ Protobuf code generated successfully!"

# Python gRPC 服务相关命令
grpc-server:
	@echo "🚀 Starting Python gRPC Server..."
	cd backend && python grpc_server.py

grpc-test:
	@echo "🧪 Testing gRPC Server..."
	cd backend && python test_grpc_simple.py

# Go Gateway 相关命令
gateway-build:
	@echo "🔨 Building Go Gateway..."
	cd backend/gateway && go mod tidy && go build -o bin/gateway ./cmd/server
	@echo "✅ Go Gateway built successfully!"

gateway-run:
	@echo "🚀 Starting Go Gateway..."
	cd backend/gateway && ./bin/gateway

gateway-dev:
	@echo "🚀 Starting Go Gateway (dev mode with rebuild)..."
	cd backend/gateway && go run cmd/server/main.go

# 集成测试
integration-test:
	@echo "🧪 Running WebSocket Integration Test..."
	@echo "⚠️  Make sure Python gRPC server and Go Gateway are running!"
	cd backend && python test_websocket_client.py

# 启动完整开发环境
dev-all:
	@echo "🚀 Starting Full Development Environment..."
	@echo "1️⃣  Starting Database..."
	make dev-up
	@echo ""
	@echo "2️⃣  Starting Python gRPC Server..."
	@echo "   Run in a separate terminal: make grpc-server"
	@echo ""
	@echo "3️⃣  Starting Go Gateway..."
	@echo "   Run in a separate terminal: make gateway-run"
	@echo ""
	@echo "✅ Development infrastructure ready!"
	@echo "   - Database: localhost:5432"
	@echo "   - Python gRPC: localhost:50051"
	@echo "   - Go Gateway: localhost:8080"
	@echo "   - WebSocket: ws://localhost:8080/ws/chat"
