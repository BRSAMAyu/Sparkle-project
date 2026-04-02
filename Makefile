.PHONY: dev-up sync-db sync-equipment proto-gen proto-lint proto-breaking proto-check-generated proto-deprecation-check proto-tools-build db-migrate db-dump db-sqlc db-validate env-check smoke openclaw-ready openclaw-smoke quality-baseline quality-baseline-full quality-budget-check openapi-contract-check flutter-analyze-gate mobile-design-lint fixture-init local-config-check local-ai-check local-backend-smoke local-mobile-smoke local-acceptance local-signoff-preflight local-final-signoff auth-test community-test file-pipeline-test worker-test china-mirrors-setup mobile-setup-china pip-install-china uv-install-china mobile-build-china mobile-build-intl mobile-build-china-ios mobile-build-intl-ios init-minio-buckets

# Load environment variables from .env
include .env

DB_CONTAINER=sparkle_db
DB_USER?=$(if $(POSTGRES_USER),$(POSTGRES_USER),postgres)
DB_NAME?=$(if $(POSTGRES_DB),$(POSTGRES_DB),sparkle)
PROTO_TOOLCHAIN_IMAGE?=sparkle/proto-toolchain:latest
BACKEND_VENV?=backend/.venv/bin
BACKEND_PYTHON?=$(BACKEND_VENV)/python
ALEMBIC?=$(BACKEND_VENV)/alembic
BACKEND_PYTHON_ABS?=$(abspath $(BACKEND_PYTHON))

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
	@python3 backend/scripts/check_shadowing.py

# 核心同步流：Python 迁移 -> 导出结构 -> 生成 Go 代码
sync-db: db-migrate db-dump db-sqlc
	@echo "✅ Database Schema & Go Code Synced Successfully!"

sync-equipment:
	@echo "🔄 Backfilling user equipment state..."
	cd backend && ../$(BACKEND_PYTHON) -m app.data.migrate_equipment_state
	@echo "✅ Equipment state synced."

db-migrate:
	@echo "🔄 Running Python Alembic Migrations..."
	cd backend && ( \
		set -e; \
		heads_output="$$(../$(ALEMBIC) heads 2>&1)" || { echo "❌ Failed to read Alembic heads."; echo "$$heads_output"; exit 1; }; \
		heads_count="$$(printf "%s\n" "$$heads_output" | rg -c "^[0-9a-f]" || true)"; \
		if [ "$$heads_count" -ne 1 ]; then \
			echo "❌ Alembic head mismatch detected (expected 1 head, got $$heads_count)."; \
			echo "alembic heads:"; printf "%s\n" "$$heads_output"; \
			echo "alembic current:"; ../$(ALEMBIC) current || true; \
			echo "alembic history (last 20 lines):"; ../$(ALEMBIC) history | tail -n 20 || true; \
			if [ "$$FORCE_STAMP" = "1" ]; then \
				echo "⚠️ FORCE_STAMP=1 set. Stamping heads (no purge) to reconcile state."; \
				if [ -t 0 ]; then \
					read -p "⚠️  This will skip consistency checks. Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1; \
				fi; \
				../$(ALEMBIC) stamp heads; \
			else \
				echo "Set FORCE_STAMP=1 to stamp heads after you confirm the desired revision."; \
				exit 1; \
			fi; \
		fi; \
		if ! ../$(ALEMBIC) upgrade head; then \
			echo "❌ Alembic upgrade failed. Diagnostic output:"; \
			echo "alembic heads:"; ../$(ALEMBIC) heads || true; \
			echo "alembic current:"; ../$(ALEMBIC) current || true; \
			echo "alembic history (last 20 lines):"; ../$(ALEMBIC) history | tail -n 20 || true; \
			if [ "$$FORCE_STAMP" = "1" ]; then \
				echo "⚠️ FORCE_STAMP=1 set. Stamping heads (no purge) to reconcile state."; \
				if [ -t 0 ]; then \
					read -p "⚠️  This will skip consistency checks. Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1; \
				fi; \
				../$(ALEMBIC) stamp heads; \
				../$(ALEMBIC) upgrade head; \
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
	$(BACKEND_PYTHON) backend/scripts/init_redis_index.py

sync-rag:
	@echo "🔄 Syncing PG KnowledgeNodes to Redis..."
	$(BACKEND_PYTHON) backend/scripts/sync_pg_to_redis.py

init-minio-buckets:
	@echo "🪣 Ensuring MinIO buckets exist..."
	$(BACKEND_PYTHON) backend/scripts/init_minio_buckets.py

smoke:
	@set -e; \
	echo "🔎 Running config self-check..."; \
	$(BACKEND_PYTHON) backend/scripts/check_config_effective.py; \
	echo "🔎 Checking backend health..."; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS http://localhost:8000/health > /dev/null; then \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "❌ Backend /health failed"; \
			exit 1; \
		fi; \
		sleep 2; \
	done; \
	echo "🔎 Checking gateway health..."; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS http://localhost:8080/api/v1/health > /dev/null; then \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "❌ Gateway /api/v1/health failed"; \
			exit 1; \
		fi; \
		sleep 2; \
	done; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS http://localhost:8080/api/v1/health/cqrs > /dev/null; then \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "❌ Gateway /api/v1/health/cqrs failed"; \
			exit 1; \
		fi; \
		sleep 2; \
	done; \
	echo "✅ Smoke checks passed."

openclaw-ready:
	@python3 scripts/openclaw_ready.py

openclaw-smoke:
	@python3 scripts/openclaw_ready.py --smoke-only

quality-baseline:
	@echo "📊 Collecting quality baseline metrics..."
	python3 scripts/collect_quality_baseline.py --output quality/baseline_snapshot.json

quality-baseline-full:
	@echo "📊 Collecting full quality baseline (includes runtime checks)..."
	python3 scripts/collect_quality_baseline.py --run-checks --output quality/baseline_snapshot_full.json

quality-budget-check:
	@echo "🧱 Enforcing technical debt budget..."
	python3 scripts/check_tech_debt_budget.py

openapi-contract-check:
	@echo "🧾 Checking OpenAPI contract snapshot..."
	python3 scripts/check_openapi_contract.py

flutter-analyze-gate:
	@echo "📱 Running Flutter analyze gate..."
	python3 scripts/check_flutter_analyze_gate.py --project-dir mobile --budget-file quality/flutter_analyze_allowlist.json --write-report quality/flutter_analyze_report.json

mobile-design-lint:
	@echo "🎨 Running mobile design system lint..."
	cd mobile && dart lib/core/design/validation/design_system_linter.dart lib

# Build proto toolchain container image (single source of truth for local + CI)
proto-tools-build:
	@echo "🐳 Building proto toolchain image $(PROTO_TOOLCHAIN_IMAGE)..."
	docker build -f docker/proto-toolchain.Dockerfile -t $(PROTO_TOOLCHAIN_IMAGE) .

# 生成 Protobuf 代码 (默认使用容器化工具链)
proto-gen:
	@echo "🚀 Generating Protobuf Code via unified toolchain..."
	@PROTO_TOOLCHAIN_IMAGE=$(PROTO_TOOLCHAIN_IMAGE) scripts/proto_toolchain.sh gen
	@echo "✅ Protobuf code generated successfully."

# Buf linting and breaking change detection
proto-lint:
	@echo "🔍 Linting Protobuf files via unified toolchain..."
	@PROTO_TOOLCHAIN_IMAGE=$(PROTO_TOOLCHAIN_IMAGE) scripts/proto_toolchain.sh lint

proto-breaking:
	@echo "🔍 Checking for breaking changes via unified toolchain..."
	@PROTO_TOOLCHAIN_IMAGE=$(PROTO_TOOLCHAIN_IMAGE) scripts/proto_toolchain.sh breaking '.git#branch=main'

proto-check-generated:
	@echo "🔍 Verifying generated code is up-to-date..."
	@PROTO_TOOLCHAIN_IMAGE=$(PROTO_TOOLCHAIN_IMAGE) scripts/proto_toolchain.sh check-generated

proto-deprecation-check:
	@echo "🔍 Validating proto deprecation windows..."
	python3 scripts/check_proto_deprecated_windows.py

# Legacy proto generation (fallback if buf not installed)
proto-gen-legacy:
	@echo "🚀 Generating Protobuf Code (Legacy)..."
	@echo "  → Go..."
	mkdir -p backend/gateway/gen/agent/v1
	mkdir -p backend/gateway/gen/galaxy/v1
	mkdir -p backend/gateway/gen/stt/v1
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/agent/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/agent/v1 --go-grpc_opt=paths=source_relative \
	       proto/agent_service.proto
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/galaxy/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/galaxy/v1 --go-grpc_opt=paths=source_relative \
	       proto/galaxy_service.proto
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/stt/v1 --go_opt=paths=source_relative \
	       --go-grpc_out=backend/gateway/gen/stt/v1 --go-grpc_opt=paths=source_relative \
	       proto/stt_service.proto
	@echo "  → WebSocket..."
	mkdir -p backend/gateway/gen/ws
	protoc --proto_path=proto \
	       --go_out=backend/gateway/gen/ws --go_opt=paths=source_relative \
	       proto/websocket.proto
	@echo "  → Python..."
	mkdir -p backend/app/gen/agent/v1
	mkdir -p backend/app/gen/galaxy/v1
	mkdir -p backend/app/gen/stt/v1
	python3 -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/agent/v1 \
	       --grpc_python_out=backend/app/gen/agent/v1 \
	       --pyi_out=backend/app/gen/agent/v1 \
	       proto/agent_service.proto
	python3 -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/galaxy/v1 \
	       --grpc_python_out=backend/app/gen/galaxy/v1 \
	       --pyi_out=backend/app/gen/galaxy/v1 \
	       proto/galaxy_service.proto
	python3 -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen/stt/v1 \
	       --grpc_python_out=backend/app/gen/stt/v1 \
	       --pyi_out=backend/app/gen/stt/v1 \
	       proto/stt_service.proto
	python3 -m grpc_tools.protoc \
	       --proto_path=proto \
	       --python_out=backend/app/gen \
	       --pyi_out=backend/app/gen \
	       proto/websocket.proto
	@echo "  → Dart..."
	@if [ -x "$$HOME/.pub-cache/bin/protoc-gen-dart" ]; then \
		if PATH="$$HOME/.pub-cache/bin:$$PATH" protoc --proto_path=proto \
			--dart_out=grpc:mobile/lib/gen \
			proto/agent_service.proto proto/websocket.proto proto/galaxy_service.proto proto/stt_service.proto; then \
			echo "✅ Dart protobuf generated"; \
		else \
			echo "⚠️  Dart protobuf generation failed in current environment"; \
		fi; \
	else \
		echo "⚠️  protoc-gen-dart not found; skipped Dart generation"; \
	fi
	@echo "✅ Protobuf code generated successfully!"

# Python gRPC 服务相关命令
grpc-server:
	@echo "🚀 Starting Python gRPC Server..."
	@BACKEND_PYTHON=$(BACKEND_PYTHON_ABS) /bin/bash backend/scripts/run_grpc_with_env.sh

# Python FastAPI 服务
api-server:
	@echo "🚀 Starting Python FastAPI Server..."
	cd backend && $(BACKEND_PYTHON_ABS) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env

grpc-test:
	@echo "🧪 Testing gRPC Server..."
	cd backend && ../$(BACKEND_PYTHON) test_grpc_simple.py

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
	cd backend/gateway && go run ./cmd/server

# 集成测试
integration-test:
	@echo "🧪 Running WebSocket Integration Test..."
	@echo "⚠️  Make sure Python gRPC server and Go Gateway are running!"
	cd backend && ../$(BACKEND_PYTHON) test_websocket_client.py

# Celery 任务队列相关命令
celery-up:
	@echo "🚀 Starting Celery Task Queue System..."
	@echo "   Checking prerequisites..."
	@if ! docker image ls | grep -q "sparkle_backend"; then \
		echo "❌ Backend image not found. Building..."; \
		cd backend && docker build -t sparkle_backend .; \
	fi
	@echo "   Starting services..."
	@docker run -d --name sparkle_celery_worker --network sparkle-project_default \
		-e DATABASE_URL=postgresql://$(DB_USER):$(DB_PASSWORD)@sparkle_db:5432/$(DB_NAME) \
		-e REDIS_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_RESULT_BACKEND=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/2 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app worker -l info -Q high_priority,default,low_priority --concurrency=4 2>/dev/null || echo "Worker may already be running"
	@docker run -d --name sparkle_celery_glm_batch_worker --network sparkle-project_default \
		-e DATABASE_URL=postgresql://$(DB_USER):$(DB_PASSWORD)@sparkle_db:5432/$(DB_NAME) \
		-e REDIS_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_RESULT_BACKEND=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/2 \
		-e GLM_BATCH_MAX_CONCURRENCY=2 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app worker -l info -Q glm_batch --concurrency=2 --hostname=glm-batch@%h 2>/dev/null || echo "GLM batch worker may already be running"
	@docker run -d --name sparkle_celery_beat --network sparkle-project_default \
		-e DATABASE_URL=postgresql://$(DB_USER):$(DB_PASSWORD)@sparkle_db:5432/$(DB_NAME) \
		-e REDIS_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-e CELERY_BROKER_URL=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 \
		-v $$(pwd)/backend:/app \
		sparkle_backend celery -A app.core.celery_app beat -l info 2>/dev/null || echo "Beat may already be running"
	@if [ "$(FLOWER_ENABLE)" = "1" ]; then \
		docker run -d --name sparkle_flower --network sparkle-project_default -p 5555:5555 \
			$(FLOWER_IMAGE) celery --broker=redis://:$(REDIS_PASSWORD)@sparkle_redis:6379/1 flower --port=5555 2>/dev/null || echo "Flower may already be running"; \
	else \
		echo "ℹ️  Flower disabled. Set FLOWER_ENABLE=1 to start it."; \
	fi
	@echo "✅ Celery services started!"
	@echo "   Worker: docker logs -f sparkle_celery_worker"
	@echo "   GLM Batch Worker: docker logs -f sparkle_celery_glm_batch_worker"
	@echo "   Beat: docker logs -f sparkle_celery_beat"
	@echo "   Flower: http://localhost:5555"

celery-logs-worker:
	@echo "📊 Celery Worker Logs..."
	@docker logs -f sparkle_celery_worker 2>/dev/null || echo "Worker not running"

celery-logs-glm:
	@echo "📊 Celery GLM Batch Worker Logs..."
	@docker logs -f sparkle_celery_glm_batch_worker 2>/dev/null || echo "GLM batch worker not running"

celery-logs-beat:
	@echo "📊 Celery Beat Logs..."
	@docker logs -f sparkle_celery_beat 2>/dev/null || echo "Beat not running"

celery-flower:
	@echo "🌐 Opening Flower Dashboard..."
	@open http://localhost:5555 2>/dev/null || echo "Open http://localhost:5555 in your browser"

celery-restart:
	@echo "🔄 Restarting Celery services..."
	@docker stop sparkle_celery_worker sparkle_celery_glm_batch_worker sparkle_celery_beat 2>/dev/null || true
	@docker rm sparkle_celery_worker sparkle_celery_glm_batch_worker sparkle_celery_beat 2>/dev/null || true
	@make celery-up

celery-flush:
	@echo "🗑️  Flushing Celery queues..."
	@docker exec sparkle_redis redis-cli -n 1 FLUSHDB 2>/dev/null || echo "Redis not running"

celery-status:
	@echo "📊 Celery Services Status..."
	@docker ps --filter "name=celery_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No Celery services running"

celery-stop:
	@echo "🛑 Stopping Celery services..."
	@docker stop sparkle_celery_worker sparkle_celery_glm_batch_worker sparkle_celery_beat sparkle_flower 2>/dev/null || true
	@docker rm sparkle_celery_worker sparkle_celery_glm_batch_worker sparkle_celery_beat sparkle_flower 2>/dev/null || true
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
	@echo "  2️⃣  make api-server     # Start Python FastAPI server"
	@echo "  3️⃣  make celery-up      # Start Celery task queue"
	@echo "  4️⃣  make grpc-server    # Start Python gRPC server"
	@echo "  5️⃣  make gateway-run    # Start Go Gateway"
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

# Build variants for different markets
mobile-build-china:
	@echo "🇨🇳 Building for China market (Google services disabled)..."
	cd mobile && flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=false --dart-define=FCM_ENABLED=false

mobile-build-intl:
	@echo "🌍 Building for International market..."
	cd mobile && flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=true

mobile-build-china-ios:
	@echo "🇨🇳 Building iOS for China market..."
	cd mobile && flutter build ios --dart-define=ENABLE_GOOGLE_SERVICES=false --dart-define=FCM_ENABLED=false

mobile-build-intl-ios:
	@echo "🌍 Building iOS for International market..."
	cd mobile && flutter build ios --dart-define=ENABLE_GOOGLE_SERVICES=true
# 配置自检
env-check:
	@echo "🔍 Checking effective config + connectivity..."
	cd backend && ../$(BACKEND_PYTHON) scripts/check_config_effective.py

fixture-init:
	@echo "🧪 Initializing deterministic local fixtures..."
	cd backend && ../$(BACKEND_PYTHON) scripts/init_local_fixture.py

local-config-check:
	@echo "🔐 Auditing required local configuration..."
	cd backend && ../$(BACKEND_PYTHON) scripts/check_required_local_config.py

local-ai-check:
	@echo "🤖 Probing all configured AI providers..."
	cd backend && ../$(BACKEND_PYTHON) scripts/check_ai_providers.py

auth-test:
	@echo "🔑 Running auth + user settings smoke..."
	cd backend && ../$(BACKEND_PYTHON) scripts/auth_smoke.py

community-test:
	@echo "👥 Running community + gateway CQRS smoke..."
	cd backend && ../$(BACKEND_PYTHON) scripts/community_smoke.py

file-pipeline-test:
	@echo "📎 Running file upload + vectorization smoke..."
	@TOKEN=$$(cd backend && ../$(BACKEND_PYTHON) scripts/print_local_smoke_token.py); \
	DATABASE_URL=$$(cd backend && ../$(BACKEND_PYTHON) -c "import os, sys; sys.path.append(os.getcwd()); from app.config import settings; print(settings.DATABASE_URL)"); \
	TOKEN="$$TOKEN" DATABASE_URL="$$DATABASE_URL" $(BACKEND_PYTHON) scripts/smoke_file_pipeline.py --file backend/test_weekly_report.pdf --token "$$TOKEN" --database-url "$$DATABASE_URL"

worker-test:
	@echo "⚙️ Running worker queue smoke..."
	cd backend && ../$(BACKEND_PYTHON) scripts/worker_smoke.py

local-backend-smoke: local-config-check fixture-init smoke auth-test community-test worker-test file-pipeline-test grpc-test integration-test
	@echo "✅ Local backend acceptance passed."

local-mobile-smoke:
	@echo "📱 Running local mobile smoke suite..."
	cd mobile && flutter test test/app/router_smoke_test.dart test/app/main_pages_load_smoke_test.dart test/app/main_actions_smoke_test.dart test/integration/full_stack_e2e_test.dart -r compact

local-acceptance: local-backend-smoke local-ai-check local-mobile-smoke
	@echo "✅ Local full-stack acceptance passed."

local-signoff-preflight:
	@echo "🧭 Running local final sign-off preflight..."
	cd backend && ../$(BACKEND_PYTHON) scripts/local_signoff_preflight.py

local-final-signoff: local-signoff-preflight
	@echo "🔎 Running final runtime smoke..."
	@$(MAKE) smoke
	@echo "🧪 Running final gateway sign-off suite..."
	cd backend/gateway && go test ./internal/handler ./internal/middleware
	@echo "🧪 Running final backend sign-off suite..."
	cd backend && ../$(BACKEND_PYTHON) scripts/ai_chat_multiturn_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/accountability_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/galaxy_plan_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/achievement_visual_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/seed_library_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/insights_acceptance.py
	cd backend && ../$(BACKEND_PYTHON) scripts/cognitive_capsule_acceptance.py
	@echo "📱 Running final mobile sign-off suite..."
	cd mobile && flutter test test/widget/visual_elements_layout_regression_test.dart test/widget/chat_history_sheet_regression_test.dart test/widget/learning_path_task_path_navigation_test.dart test/widget/simulator_chain_regression_test.dart test/widget/chat_action_card_navigation_test.dart test/widget/accountability_invite_closure_test.dart test/unit/accountability_invite_flow_test.dart test/unit/chat_provider_test.dart test/app/main_pages_load_smoke_test.dart -r compact
	@echo "✅ Local final sign-off suite passed."

# ═══════════════════════════════════════════════════════════════════
# China Network Mirror Configuration
# ═══════════════════════════════════════════════════════════════════

china-mirrors-setup:
	@echo "🇨🇳 Setting up China network mirrors..."
	@bash scripts/setup_china_mirrors.sh

mobile-setup-china:
	@echo "📱 Setting up Flutter/Dart mirrors for China..."
	@bash scripts/setup_flutter_mirrors.sh
	@echo ""
	@echo "⚠️  Please restart your terminal or run: source ~/.zshrc"
	@echo "Then run: cd mobile && flutter pub get"

pip-install-china:
	@echo "🐍 Installing Python dependencies with China mirror..."
	pip install -r backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

uv-install-china:
	@echo "🐍 Installing Python dependencies with uv (China mirror)..."
	uv pip install -r backend/requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/
