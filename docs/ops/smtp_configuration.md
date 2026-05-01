# Sparkle SMTP Configuration

Sparkle uses SMTP for password reset and email verification messages.

## Environment Variables

| Variable | Required in production | Notes |
| --- | --- | --- |
| `EMAIL_ENABLED` | No | Defaults to `false` in development and `true` in production when omitted. Set `false` only when email flows are intentionally disabled. |
| `SMTP_HOST` | Yes, when email is enabled | SMTP server host, for example `smtp.example.com`. |
| `SMTP_PORT` | Yes, when email is enabled | Use `587` for STARTTLS or `465` for implicit TLS. |
| `SMTP_USER` | Yes, when email is enabled | SMTP account username. |
| `SMTP_PASSWORD` | Yes, when email is enabled | SMTP account password or provider app password. |
| `EMAIL_FROM` | Yes, when email is enabled | Sender address, for example `no-reply@example.com`. |
| `EMAIL_FROM_NAME` | No | Defaults to `Sparkle`. |

## Production Example

```env
ENVIRONMENT=production
EMAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=sparkle-smtp-user
SMTP_PASSWORD=replace_with_real_smtp_password
EMAIL_FROM=no-reply@example.com
EMAIL_FROM_NAME=Sparkle
```

## Runtime Behavior

- `SMTP_PORT=587` uses STARTTLS.
- `SMTP_PORT=465` uses implicit TLS.
- When `EMAIL_ENABLED=false`, email sending returns `false` and logs a skip message.
- In production, startup fails if email is enabled but SMTP settings are missing or placeholders.
