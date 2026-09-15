# Secret Rotation Runbook

Created: 2026-05-01
Owner: Ops / Security
Scope: Sparkle production, staging, local deploy templates, CI secrets, and provider API keys.

## When To Run

Run this procedure immediately when:

- a `.env` file, provider key, token, webhook, DSN, database password, Redis password, MinIO credential, SMTP password, or JWT/internal key may have been committed, pasted into logs, or shared outside the approved secret store;
- a teammate leaves a privileged role;
- a vendor dashboard reports suspicious use;
- the quarterly rotation window opens.

Do not copy exposed secret values into tickets, docs, chat, or commit messages. Refer to the provider, variable name, environment, and first detection timestamp only.

## Providers To Rotate

Rotate every credential that exists in the affected environment:

| Area | Variables / credentials |
|---|---|
| App signing and internal auth | `JWT_SECRET`, `SECRET_KEY`, `INTERNAL_API_KEY`, `ADMIN_SECRET` |
| Database | `POSTGRES_PASSWORD`, `DATABASE_URL` user password |
| Redis | `REDIS_PASSWORD`, `REDIS_URL` password |
| Object storage | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` |
| LLM / AI providers | `LLM_API_KEY`, `XIAOMI_MIMO_API_KEY`, `ZHIPU_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `SILICONFLOW_API_KEY`, `HUNYUAN_API_KEY` |
| Speech | `XUNFEI_APP_ID`, `XUNFEI_API_KEY`, `XUNFEI_API_SECRET` |
| Email | `SMTP_USER`, `SMTP_PASSWORD`, provider console app passwords |
| Monitoring / incident delivery | `SENTRY_DSN`, Alertmanager webhook URLs, Grafana admin password |
| CI and automation | GitHub Actions secrets, Gemini/Google app secrets, deploy registry tokens, kubeconfigs |

## Rotation Steps

1. Freeze deploys touching the affected service until the new secret set is ready.
2. In the provider dashboard, create a replacement credential with the minimum required scope.
3. Store the new value in the approved secret manager or GitHub Actions secret store.
4. Deploy the service with the new value.
5. Run a smoke test for that provider without printing the secret:
   - Python backend: `python scripts/check_production_secrets.py --env-only`
   - tracked-file scan: `python scripts/check_production_secrets.py --tracked-only`
   - provider-specific live checks only from an environment with the key already injected.
6. Revoke the old credential after the new deploy is healthy.
7. Check provider audit logs for use after revocation. If use continues, escalate as an active incident.
8. Record evidence in the incident or rotation ticket:
   - provider and variable name,
   - environment,
   - old credential revoked time,
   - new deploy identifier,
   - smoke test command and result,
   - any follow-up action.

## Repository Rules

- Runtime files such as `.env`, `.env.local`, `.env.production`, `backend/.env`, and `backend/gateway/.env` must stay untracked.
- Only `.env.example`, `.env.local.example`, `.env.deploy.example`, and similar placeholder examples may be tracked.
- Example values must be placeholders, not provider-shaped keys.
- Generated runtime artifacts such as `celerybeat-schedule` must not be tracked.
- CI and local pre-commit must keep gitleaks enabled.

## Validation

Before approving a release, run:

```bash
git ls-files | rg '(^|/)\.env($|\.)'
python scripts/check_production_secrets.py --tracked-only
```

The first command may list only placeholder examples. The second command must pass without printing any secret values.

## Remaining Human Action

The repository can remove and guard exposed values, but only provider administrators can prove rotation. If any real credential was present in a commit, rotate the matching provider key even after the file is sanitized.
