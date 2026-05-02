# Sparkle Production RBAC Runbook

Date: 2026-05-02

## Scope

FV-06 introduces opt-in production isolation for PostgreSQL, Redis, and MinIO. Local development remains on the legacy single-account path unless `SPARKLE_RBAC_ENABLED=true`.

## PostgreSQL Roles

The Alembic migration `c17_20260502_create_service_roles.py` creates four login roles:

- `sparkle_gateway`: chat, auth, session, file metadata, and CQRS tables only.
- `sparkle_engine`: signals, Aurora, Galaxy, source/document, memory, plan, task, and user-state tables.
- `sparkle_celery`: engine permissions plus outbox/projection/DLQ tables.
- `sparkle_readonly`: read-only access for Grafana/admin inspection.

Role passwords are not hardcoded. Before running the migration in production, set:

```bash
export SPARKLE_GATEWAY_DB_PASSWORD=...
export SPARKLE_ENGINE_DB_PASSWORD=...
export SPARKLE_CELERY_DB_PASSWORD=...
export SPARKLE_READONLY_DB_PASSWORD=...
```

The migration is intentionally safe to run before enabling RBAC. Services continue to use `DATABASE_URL` until `SPARKLE_RBAC_ENABLED=true`.

## Service DSNs

Set the service URLs in `.env`:

```bash
SPARKLE_RBAC_ENABLED=true
SPARKLE_GATEWAY_DATABASE_URL=postgresql://sparkle_gateway:...@sparkle_db:5432/sparkle?sslmode=require
SPARKLE_ENGINE_DATABASE_URL=postgresql+asyncpg://sparkle_engine:...@sparkle_db:5432/sparkle?sslmode=require
SPARKLE_CELERY_DATABASE_URL=postgresql+asyncpg://sparkle_celery:...@sparkle_db:5432/sparkle?sslmode=require
```

Gateway selects `SPARKLE_GATEWAY_DATABASE_URL`; Python API/gRPC selects `SPARKLE_ENGINE_DATABASE_URL`; Celery workers and beat select `SPARKLE_CELERY_DATABASE_URL`.

## Redis ACL

`docker-compose.prod.yml` generates an ACL file at container start; `redis.conf` points Redis at `/tmp/users.acl`.

- `default`: legacy admin path for health checks and emergency rollback.
- `gateway`: chat/session/auth/rate-limit/CQRS key prefixes.
- `engine`: Aurora/Galaxy/signals/context/user/cache/memory key prefixes.
- `celery`: broker/result and worker key prefixes.

Set these URLs:

```bash
SPARKLE_GATEWAY_REDIS_URL=redis://gateway:...@sparkle_redis:6379/0
SPARKLE_ENGINE_REDIS_URL=redis://engine:...@sparkle_redis:6379/0
SPARKLE_CELERY_BROKER_URL=redis://celery:...@sparkle_redis:6379/1
SPARKLE_CELERY_RESULT_BACKEND=redis://celery:...@sparkle_redis:6379/2
```

## MinIO Buckets

`minio_rbac_init` creates three buckets and service users:

- `sparkle-uploads`: gateway/backend upload path.
- `sparkle-exports`: export jobs.
- `sparkle-backups`: backup jobs.

Each account receives a bucket-scoped policy only for its bucket.

## Rollout

1. Deploy with `SPARKLE_RBAC_ENABLED=false`.
2. Run `alembic upgrade c17_20260502` with the four role password env vars set.
3. Start production Compose and confirm Redis ACL and MinIO init jobs succeed.
4. Run smoke checks with legacy DSNs.
5. Flip `SPARKLE_RBAC_ENABLED=true` for one canary instance.
6. Verify gateway chat/session paths, Python health, Celery worker ping, and MinIO upload.
7. Roll across the remaining instances.

## Rollback

Fast rollback:

```bash
SPARKLE_RBAC_ENABLED=false
docker compose -f docker-compose.prod.yml up -d gateway_blue gateway_green backend agent celery_worker celery_beat
```

Full rollback after traffic is stable:

```bash
cd backend
alembic downgrade c12_20260502
```

The downgrade revokes default privileges, revokes existing table/sequence/schema grants, and drops all four service roles.

## Credential Rotation

1. Generate the new service password.
2. As the DB admin, run `ALTER ROLE <role> PASSWORD '<new password>';`.
3. Update the matching `SPARKLE_*_DATABASE_URL`.
4. Restart only the affected service class.
5. Repeat for Redis with `ACL SETUSER <user> >new-password` and update its URL.
6. Rotate MinIO with `mc admin user disable`, add/enable the replacement user, and attach the same bucket policy.
