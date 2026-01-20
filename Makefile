.PHONY: dev-up sync-db proto-gen db-migrate db-dump db-sqlc db-validate env-check smoke

DB_CONTAINER=sparkle_db
DB_USER?=$(if $(POSTGRES_USER),$(POSTGRES_USER),postgres)
DB_NAME?=$(if $(POSTGRES_DB),$(POSTGRES_DB),sparkle)

# macOS-specific check: Unset CC/CXX if they interfere with Flutter
_check_macos_env:
	@if [[ "$$OSTYPE" == "darwin"* ]] && [[ -n "$$CC" ]] || [[ -n "$$CXX" ]]; then \
		echo "⚠️  macOS detected with CC/CXX set. Unsetting for Flutter compatibility..."; \
		unset CC CXX; \
	fi

# 启动基础设施
dev-up:
	@make _check_macos_env
	docker compose up -d

# 核心同步流：Python 迁移 -> 导出结构 -> 生成 Go 代码
sync-db: db-migrate db-dump db-sqlc
	@echo "✅ Database Schema & Go Code Synced Successfully!"

db-migrate:
	@echo "🔄 Running Python Alembic Migrations..."
	cd backend && ( \
		set -e; \
		heads_output="$$(alembic heads 2>&1)" || { echo "❌ Failed to read Alembic heads."; echo "$$heads_output"; exit 1; }; \
		heads_count="$$(printf "%s\n" "$$heads_output" | rg -c "^[0-9a-f]" || true)"; \
		if [ "$$heads_count" -ne 1 ]; then \
			echo "❌ Alembic head mismatch detected (expected 1 head, got $$heads_count)."; \
			echo "alembic heads:"; printf "%s\n" "$$heads_output"; \
			echo "alembic current:"; alembic current || true; \
			echo "alembic history (last 20 lines):"; alembic history | tail -n 20 || true; \
			if [ "$$FORCE_STAMP" = "1" ]; then \
				echo "⚠️ FORCE_STAMP=1 set. Stamping heads (no purge) to reconcile state."; \
				alembic stamp heads; \
			else \
				echo "Set FORCE_STAMP=1 to stamp heads after you confirm the desired revision."; \
				exit 1; \
			fi; \
		fi; \
		if ! alembic upgrade head; then \
			echo "❌ Alembic upgrade failed. Diagnostic output:"; \
			echo "alembic heads:"; alembic heads || true; \
			echo "alembic current:"; alembic current || true; \
			echo "alembic history (last 20 lines):"; alembic history | tail -n 20 || true; \
			if [ "$$FORCE_STAMP" = "1" ]; then \
				echo "⚠️ FORCE_STAMP=1 set. Stamping heads (no purge) to reconcile state."; \
				alembic stamp heads; \
				alembic upgrade head; \
			else \
				echo "Set FORCE_STAMP=1 to stamp heads after you confirm the desired revision."; \
				exit 1; \
			fi; \
		fi; \
	)

db-validate:
	@echo "🔍 Checking if $(DB_CONTAINER) is running..."
	@docker ps -q -f name=$(DB_CONTAINER) > /dev/null || (echo "❌ Error: Container $(DB_CONTAINER) is not running. Run 'make dev-up' first." && exit 1)

db-dump: db-validate
	@echo "🧾 Dumping Schema (Structure Only)..."
	mkdir -p backend/gateway/internal/db
	docker exec $(DB_CONTAINER) pg_dump -U $(DB_USER) -d $(DB_NAME) --schema-only | \
		grep -v '^\\' | \
		sed "s/SELECT pg_catalog.set_config('search_path', '', false);/SELECT pg_catalog.set_config('search_path', 'public', false);/g" | \
		sed "s/public\.//g" > backend/gateway/internal/db/schema.sql

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

smoke:
	@set -e; \
	echo "🔎 Running config self-check..."; \
	python backend/scripts/check_config_effective.py; \
	echo "🔎 Checking backend health..."; \
	curl -fsS http://localhost:8000/health > /dev/null || (echo "❌ Backend /health failed" && exit 1); \
	echo "🔎 Checking gateway health..."; \
	curl -fsS http://localhost:8080/api/v1/health > /dev/null || (echo "❌ Gateway /api/v1/health failed" && exit 1); \
	curl -fsS http://localhost:8080/api/v1/health/cqrs > /dev/null || (echo "❌ Gateway /api/v1/health/cqrs failed" && exit 1); \
	echo "✅ Smoke checks passed."

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
		-e DATABASE_URL=postgresql://postgres:change-me@sparkle_db:5432/sparkle \
		-e REDIS_URL=redis://:change-me@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:change-me@sparkle_redis:6379/1 \
		-e CELERY_RESULT_BACKEND=redis://:change-me@sparkle_redis:6379/2 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app worker -l info -Q high_priority,default,low_priority --concurrency=2 2>/dev/null || echo "Worker may already be running"
	@docker run -d --name sparkle_celery_beat --network sparkle-flutter_default \
		-e DATABASE_URL=postgresql://postgres:change-me@sparkle_db:5432/sparkle \
		-e REDIS_URL=redis://:change-me@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:change-me@sparkle_redis:6379/1 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app beat -l info 2>/dev/null || echo "Beat may already be running"
	@docker run -d --name sparkle_flower --network sparkle-flutter_default -p 5555:5555 \
		mher/flower:1.2.0 celery --broker=redis://:change-me@sparkle_redis:6379/1 flower --port=5555 2>/dev/null || echo "Flower may already be running"
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

# Mobile Development
mobile-proto:
	@echo "🚀 Generating Dart Protobufs..."
	@mkdir -p mobile/lib/gen
	@export PATH="$$PATH":"$$HOME/.pub-cache/bin" && buf generate --template buf.gen.dart.yaml

mobile-gen: mobile-proto
	@echo "🏗️ Running Build Runner..."
	cd mobile && flutter pub get && dart run build_runner build --delete-conflicting-outputs

mobile-run:
	@echo "🚀 Starting Mobile App..."
	@if [[ "$$OSTYPE" == "darwin"* ]]; then \
		echo "🍎 macOS detected. Unsetting CC/CXX..."; \
		unset CC CXX; \
	fi; \
	cd mobile && flutter run
# 配置自检
env-check:
	@echo "🔍 Checking effective config + connectivity..."
	cd backend && python scripts/check_config_effective.py
