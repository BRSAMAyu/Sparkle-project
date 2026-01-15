.PHONY: dev-up dev-up-all dev-preflight dev-reset db-reset sync-db proto-gen db-migrate db-dump db-sqlc db-validate

DB_CONTAINER=sparkle_db
DB_USER=postgres
DB_NAME=sparkle
DB_PASSWORD ?= change-me
REDIS_PASSWORD ?= change-me
FLOWER_IMAGE ?= mher/flower:1.2.0
FLOWER_ENABLE ?= 0

# macOS-specific check: Unset CC/CXX if they interfere with Flutter
_check_macos_env:
	@if [[ "$$OSTYPE" == "darwin"* ]] && [[ -n "$$CC" ]] || [[ -n "$$CXX" ]]; then \
		echo "⚠️  macOS detected with CC/CXX set. Unsetting for Flutter compatibility..."; \
		unset CC CXX; \
	fi

# 启动基础设施
dev-up:
	@make _check_macos_env
	@make dev-preflight
	docker compose up -d sparkle_db redis minio

# 启动完整容器栈（包含后端/网关/可观测性）
dev-up-all:
	@make _check_macos_env
	@make dev-preflight
	docker compose up -d

dev-preflight:
	@if [ ! -f .env ]; then \
		echo "⚠️  Missing .env in repo root. Copy .env.example to .env for compose defaults."; \
	fi
	@if [ -d postgres_data ]; then \
		echo "ℹ️  Detected existing postgres_data. If auth fails, run 'make db-reset'."; \
	fi

# 核心同步流：Python 迁移 -> 导出结构 -> 生成 Go 代码
sync-db: db-migrate db-dump db-sqlc
	@echo "✅ Database Schema & Go Code Synced Successfully!"

db-migrate:
	@echo "🔄 Running Python Alembic Migrations..."
	cd backend && alembic upgrade head

db-validate:
	@echo "🔍 Checking if $(DB_CONTAINER) is running..."
	@docker ps -q -f name=$(DB_CONTAINER) > /dev/null || (echo "❌ Error: Container $(DB_CONTAINER) is not running. Run 'make dev-up' first." && exit 1)

db-dump: db-validate
	@echo "🧾 Dumping Schema (Structure Only)..."
	mkdir -p backend/gateway/internal/db
	docker exec $(DB_CONTAINER) pg_dump -U $(DB_USER) -d $(DB_NAME) --schema-only | \
		grep -v '^\\' > backend/gateway/internal/db/schema.sql

db-sqlc:
	@echo "⚡ Generating Go Code via SQLC..."
	cd backend/gateway && sqlc generate

# RAG 相关命令 (v2.0)
init-rag:
	@echo "🏗️ Initializing Redis Index..."
	python backend/scripts/init_redis_index.py

sync-rag:
	@echo "🔄 Syncing PG KnowledgeNodes to Redis..."
	python backend/scripts/sync_pg_to_redis.py

# 生成 Protobuf 代码 (使用 Buf 工具链)
# P1: Modernized protocol management with buf.build
proto-gen:
	@echo "🚀 Generating Protobuf Code with Buf..."
	@if command -v buf >/dev/null 2>&1; then \
		buf generate; \
		echo "✅ Protobuf code generated successfully via Buf!"; \
	else \
		echo "⚠️  Buf not installed, falling back to protoc..."; \
		make proto-gen-legacy; \
	fi

# Buf linting and breaking change detection
proto-lint:
	@echo "🔍 Linting Protobuf files..."
	buf lint

proto-breaking:
	@echo "🔍 Checking for breaking changes..."
	buf breaking --against '.git#branch=main'

# Legacy proto generation (fallback if buf not installed)
proto-gen-legacy:
	@echo "🚀 Generating Protobuf Code (Legacy)..."
	@echo "  → Go..."
	mkdir -p backend/gateway/gen/agent/v1
	mkdir -p backend/gateway/gen/galaxy/v1
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/agent/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/agent/v1 --go-grpc_opt=paths=source_relative \
	       proto/agent_service.proto
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/galaxy/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/galaxy/v1 --go-grpc_opt=paths=source_relative \
	       proto/galaxy_service.proto
	@echo "  → WebSocket..."
	mkdir -p backend/gateway/gen/ws
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/ws --go_opt=paths=source_relative \
	       proto/websocket.proto
	@echo "  → Python..."
	mkdir -p backend/app/gen/agent/v1
	mkdir -p backend/app/gen/galaxy/v1
	python -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/agent/v1 \
	       --grpc_python_out=backend/app/gen/agent/v1 \
	       --pyi_out=backend/app/gen/agent/v1 \
	       proto/agent_service.proto
	python -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/galaxy/v1 \
	       --grpc_python_out=backend/app/gen/galaxy/v1 \
	       --pyi_out=backend/app/gen/galaxy/v1 \
	       proto/galaxy_service.proto
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

# Celery 任务队列相关命令
celery-up:
	@echo "🚀 Starting Celery Task Queue System..."
	@echo "   Checking prerequisites..."
	@if ! docker image ls | grep -q "sparkle_backend"; then \
		echo "❌ Backend image not found. Building..."; \
		cd backend && docker build -t sparkle_backend .; \
	fi
	@echo "   Starting services..."
	@docker run -d --name sparkle_celery_worker --network sparkle-flutter_default \
		-e DATABASE_URL=postgresql://$(DB_USER):$(DB_PASSWORD)@sparkle_db:5432/$(DB_NAME) \
		-e REDIS_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_RESULT_BACKEND=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/2 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app worker -l info -Q high_priority,default,low_priority --concurrency=2 2>/dev/null || echo "Worker may already be running"
	@docker run -d --name sparkle_celery_beat --network sparkle-flutter_default \
		-e DATABASE_URL=postgresql://$(DB_USER):$(DB_PASSWORD)@sparkle_db:5432/$(DB_NAME) \
		-e REDIS_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app beat -l info 2>/dev/null || echo "Beat may already be running"
	@if [ "$(FLOWER_ENABLE)" = "1" ]; then \
		docker run -d --name sparkle_flower --network sparkle-flutter_default -p 5555:5555 \
			$(FLOWER_IMAGE) celery --broker=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 flower --port=5555 2>/dev/null || echo "Flower may already be running"; \
	else \
		echo "ℹ️  Flower disabled. Set FLOWER_ENABLE=1 to start it."; \
	fi
	@echo "✅ Celery services started!"
	@echo "   Worker: docker logs -f sparkle_celery_worker"
	@echo "   Beat: docker logs -f sparkle_celery_beat"
	@echo "   Flower: http://localhost:5555"

celery-logs-worker:
	@echo "📊 Celery Worker Logs..."
	@docker logs -f sparkle_celery_worker 2>/dev/null || echo "Worker not running"

celery-logs-beat:
	@echo "📊 Celery Beat Logs..."
	@docker logs -f sparkle_celery_beat 2>/dev/null || echo "Beat not running"

celery-flower:
	@echo "🌐 Opening Flower Dashboard..."
	@open http://localhost:5555 2>/dev/null || echo "Open http://localhost:5555 in your browser"

celery-restart:
	@echo "🔄 Restarting Celery services..."
	@docker stop sparkle_celery_worker sparkle_celery_beat 2>/dev/null || true
	@docker rm sparkle_celery_worker sparkle_celery_beat 2>/dev/null || true
	@make celery-up

celery-flush:
	@echo "🗑️  Flushing Celery queues..."
	@docker exec sparkle_redis redis-cli -n 1 FLUSHDB 2>/dev/null || echo "Redis not running"

celery-status:
	@echo "📊 Celery Services Status..."
	@docker ps --filter "name=sparkle_celery" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No Celery services running"

celery-stop:
	@echo "🛑 Stopping Celery services..."
	@docker stop sparkle_celery_worker sparkle_celery_beat sparkle_flower 2>/dev/null || true
	@docker rm sparkle_celery_worker sparkle_celery_beat sparkle_flower 2>/dev/null || true
	@echo "✅ Celery services stopped"

# 启动完整开发环境 (包含 Celery)
dev-all:
	@make _check_macos_env
	@echo "🚀 Starting Full Development Environment..."
	@echo "1️⃣  Starting Database & Redis..."
	@make dev-up
	@echo ""
	@echo "✅ Step 1 Complete! Infrastructure is ready."
	@echo ""
	@echo "Next steps (run in separate terminals):"
	@echo "  2️⃣  make celery-up      # Start Celery task queue"
	@echo "  3️⃣  make grpc-server    # Start Python gRPC server"
	@echo "  4️⃣  make gateway-run    # Start Go Gateway"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "   - Flower: http://localhost:5555"
	@echo "   - Redis CLI: docker exec -it sparkle_redis redis-cli"
	@echo ""
	@echo "🔧 Quick Commands:"
	@echo "   make celery-status     # Check Celery services"
	@echo "   make celery-logs-worker # View worker logs"

db-reset:
	@echo "🧹 Resetting local Postgres data (destructive)..."
	@docker compose stop sparkle_db >/dev/null 2>&1 || true
	@rm -rf postgres_data
	@echo "✅ Postgres data cleared. Run 'make dev-up' to recreate."

dev-reset:
	@echo "🧹 Resetting local dev data (destructive)..."
	@docker compose down >/dev/null 2>&1 || true
	@rm -rf postgres_data redis_data minio_data flower_data
	@echo "✅ Local dev data cleared. Run 'make dev-up' to recreate."
