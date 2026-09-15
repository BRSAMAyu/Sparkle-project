# Sparkle Disaster Recovery Runbook

> Owner: Operations / C00 integration owner  
> Last updated: 2026-05-01  
> Scope: production recovery for Sparkle Postgres, Redis, object storage, vector/index data, and uploaded files.

## 1. Recovery Targets

These are launch targets, not proof that the current single-node local compose stack already provides multi-region durability.

| Subsystem | Data role | RPO target | RTO target | Recovery source | Loss tolerance |
| --- | --- | ---: | ---: | --- | --- |
| Postgres / pgvector / AGE | System of record for users, goals, plans, cards, conversations, profiles, graph/vector rows | 15 minutes with managed PITR/WAL; 24 hours with current script-only fallback | 60 minutes | PITR snapshot first; `scripts/backup_prod_data.sh` snapshot fallback | At most 15 minutes after PITR is enabled; otherwise last successful backup |
| Redis Stack | Sessions, cache, rate limits, streams, projections, Aurora runtime state | 15 minutes for stream/projection snapshots; cache keys may be lost | 30 minutes | Redis replica/AOF/RDB; `redis.rdb` from backup fallback | Ephemeral cache can be rebuilt; unpersisted runtime/session details can be lost |
| Object storage / uploaded files | User uploaded files and derived file blobs | 24 hours until bucket versioning + cross-region replication are enabled | 2 hours | S3/MinIO versioned bucket or `minio-data.tar.gz` fallback | Files uploaded after the last backup may need user re-upload |
| Vector/index data | pgvector rows, Redis vector indexes, search projections | Same as Postgres for pgvector rows; 24 hours for Redis-only projections | 2 hours including reindex | Postgres restore, then Redis/index rebuild or `redis.rdb` fallback | Redis-only indexes can be rebuilt from Postgres where source rows exist |
| Generated reports/exports | User-visible generated files | Same as object storage | 2 hours | Object storage restore | Recreate from source data when possible |

## 2. Backup Procedure

Run from the repository root on the production maintenance host.

```bash
export BACKUP_ROOT=/var/backups/sparkle
export POSTGRES_CONTAINER=sparkle_db
export POSTGRES_DB=sparkle
export POSTGRES_USER=postgres
export REDIS_CONTAINER=sparkle_redis
export REDIS_PASSWORD="$REDIS_PASSWORD"
export MINIO_CONTAINER=sparkle_minio
bash scripts/backup_prod_data.sh
```

The backup directory contains:

- `postgres.sql.gz`
- `redis.rdb`
- `minio-data.tar.gz`
- `sha256sums.txt`
- `manifest.json`

Copy the finished directory to encrypted offsite storage before considering the backup successful.

## 3. Restore Procedure

Use this only after the incident commander declares data restore necessary.

1. Stop write traffic at the gateway or load balancer.
2. Capture the current broken state for forensics:

```bash
export BACKUP_ROOT=/var/backups/sparkle/pre-restore
bash scripts/backup_prod_data.sh
```

3. Restore the selected backup:

```bash
bash scripts/restore_prod_data.sh /var/backups/sparkle/20260501_120000
```

4. Restart application services:

```bash
docker compose restart sparkle_api sparkle_agent sparkle_gateway
```

5. Verify:

```bash
docker compose ps
cd backend && alembic current
make grpc-test
make integration-test
```

6. Reopen write traffic only after health checks, login, chat, file upload, and dashboard load all pass.

## 4. Restore Drill Checklist

Run once before production launch and then monthly.

| Step | Evidence required | Pass criteria |
| --- | --- | --- |
| Create backup from staging-like data | Backup path + `manifest.json` timestamp | Backup exits 0 and checksums exist |
| Verify checksum failure is detected | Tamper with copied artifact in a throwaway directory | Restore refuses the tampered artifact |
| Restore Postgres | `alembic current`, sample user/card/conversation query | Schema head and sample rows match source |
| Restore Redis | `redis-cli DBSIZE` and one known key/stream check | Runtime/projection keys present or rebuilt |
| Restore object storage | List bucket and download a known uploaded file | File hash matches source |
| Rebuild vector/search indexes if needed | Search smoke output | Known knowledge query returns expected item |
| Run app smoke | `make grpc-test`, `make integration-test`, manual mobile smoke | Critical flows pass |
| Record elapsed time | Start/end timestamps | Within RTO target or follow-up opened |

## 5. Regional Failure Procedure

1. Declare the incident and freeze deploys.
2. Confirm primary region status from cloud provider, database, Redis, object storage, gateway, and DNS dashboards.
3. If the primary region cannot recover inside 30 minutes, promote the warm standby region.
4. Restore or promote data in this order: Postgres, object storage, Redis, derived indexes.
5. Apply production secrets from the standby secret store; do not copy secrets through chat or tickets.
6. Run migrations only after confirming the backup schema version and application commit match.
7. Shift internal health-check traffic, then 5%, 25%, 50%, and 100% user traffic.
8. Keep the failed region read-only until data divergence is assessed.
9. Write a post-incident note with actual RTO/RPO and any data-loss window.

## 6. Follow-Ups

| ID | Priority | Gap | Required owner action |
| --- | --- | --- | --- |
| DR-C09-1 | P0 | Offsite encrypted backups are documented but not automated in this repo | Add scheduled encrypted upload to cloud object storage and alert on failure |
| DR-C09-2 | P0 | First full restore drill is not yet evidenced | Execute the checklist against staging and attach logs to the tracker |
| DR-C09-3 | P1 | Redis HA/AOF/replication posture is not encoded in compose or IaC | Choose managed Redis or define Sentinel/Cluster + AOF settings |
| DR-C09-4 | P1 | Object storage versioning and cross-region replication are not yet enforced | Enable bucket versioning, lifecycle rules, and replication in production IaC |
| DR-C09-5 | P1 | Reindex command for Redis/search projections is not a single operator command | Add a scripted rebuild path from Postgres source data |
