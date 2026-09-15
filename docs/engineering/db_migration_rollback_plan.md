# DB Migration Rollback Plan — T6.2.3

> Applies to: PostgreSQL 16 + Alembic (52 migrations), Go sqlc schema

## Rollback Strategy

### Principle: Every migration MUST be reversible

- All Alembic migrations include `downgrade()` functions
- Schema changes use ADD-first, DROP-later pattern
- No destructive columns dropped in same release as schema change

### Pre-Migration Checklist

```bash
# 1. Backup database
pg_dump -h $PGHOST -U postgres sparkle > backup_$(date +%Y%m%d_%H%M).sql

# 2. Record current migration head
cd backend && alembic heads

# 3. Test downgrade on staging
alembic downgrade -1   # rollback one step
alembic upgrade head    # re-apply
```

### Rollback Procedures

#### Level 1: Single migration rollback (safe, fast)

```bash
cd backend
alembic downgrade -1
# Verify: alembic current
```

#### Level 2: Multi-migration rollback (to known good state)

```bash
cd backend
# Find the target revision
alembic history --verbose
# Downgrade to specific revision
alembic downgrade <revision_id>
```

#### Level 3: Full database restore from backup

```bash
# Stop application services
docker compose stop sparkle_api sparkle_agent sparkle_gateway

# Restore from backup
psql -h $PGHOST -U postgres -c "DROP DATABASE sparkle;"
psql -h $PGHOST -U postgres -c "CREATE DATABASE sparkle;"
psql -h $PGHOST -U postgres sparkle < backup_YYYYMMDD_HHMM.sql

# Restart services
docker compose start sparkle_db redis
sleep 5
docker compose start sparkle_api sparkle_agent sparkle_gateway
```

### Column Addition Pattern (Non-Breaking)

```python
# upgrade()
op.add_column('users', sa.Column('new_field', sa.String(), nullable=True))

# downgrade()
op.drop_column('users', 'new_field')
```

### Column Removal Pattern (Two-Phase)

```python
# Phase 1: Mark deprecated (current release)
# upgrade() — no action, code already ignores column

# Phase 2: Remove column (next release, after code deployed)
# upgrade()
op.drop_column('users', 'deprecated_field')
# downgrade()
op.add_column('users', sa.Column('deprecated_field', sa.String(), nullable=True))
```

### Go Schema Sync

After any rollback that changes schema:
```bash
make sync-db    # Re-dump schema.sql + regenerate sqlc models
cd gateway && go build ./...  # Verify Go code compiles
```

### Emergency Contacts

| Role | Contact |
|------|---------|
| DBA | On-call rotation |
| Backend Lead | GitHub @BRSAMA |
| SRE | Alertmanager → PagerDuty |
