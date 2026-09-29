# V4-Q01 stack round-3 start provenance (2026-09-29, post second host restart)
# Tested code: worktree /Users/brsama/code/GitHub/wtQ01 @ 5cbc715f63deaeb7872a9650ce44efaef6d07f4b (branch agent/v4/q01)
# Second ENV-OUTAGE (host disk/memory chain failure -> forced restart ~13:36+0800) killed round-2 stack; same disclaimer as first outage: infra, not product failure.
# Data plane: sparkle_db/redis/minio (cosmos-own compose, FIX-557) all healthy before start (docker ps verified 15:47).
- grpc 50051: BACKEND_PYTHON=/opt/homebrew/bin/python3.11 bash scripts/run_grpc_with_env.sh (first attempt 15:57 fell to python3->3.14, ModuleNotFoundError grpc_reflection, FAIL recorded in grpc_server.log history; restarted 16:02 OK)
- fastapi 8000: uvicorn app.main:app (python3.11 homebrew site-packages)
- gateway 8080: ./bin/gateway (rebuilt by dev-stage3 first run; restarted 16:03 after gRPC was up; first instance blocked pre-listen while 50051 down - restarted, OK)
- celery worker: /opt/homebrew/bin/celery -A app.core.celery_app worker -Q high_priority,default,low_priority --concurrency=2 from wtQ01/backend (NEW in r3: needed for fixture document ingestion via process_stored_file)
