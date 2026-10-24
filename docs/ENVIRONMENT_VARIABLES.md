# Environment variables (backend)
| Variable | Purpose |
|---|---|
| ENVIRONMENT | `production` (default, strict) or `development`/`test` (relaxed, API docs on). Never use development on a public server |
| GLOBAL_RATE_LIMIT | Requests per minute per IP (default 600) |
| DATABASE_URL | `postgresql+psycopg://user:pass@host:5432/db` |
| JWT_SECRET | Required, 32+ random characters |
| ACCESS_TOKEN_MINUTES / REFRESH_TOKEN_DAYS | Token lifetimes (15 / 14) |
| CORS_ORIGINS | Comma-separated allowed origins |
| APP_URL | Web app URL used in emailed links |
| STORAGE_DIR | Where uploaded documents are stored |
| SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_TLS | Email delivery |
| TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SMS_FROM, TWILIO_WHATSAPP_FROM | SMS and WhatsApp |
| GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL | Groq assistant (model default `openai/gpt-oss-120b`) |
| RUN_SCHEDULER | `1` to run reminders in-process, `0` to disable |

Frontends: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL` (website), `NEXT_PUBLIC_SITE_URL`.

**Admin panel overrides.** Platform admins can change the Groq key/model, SMTP, Twilio and the sign-up switches at runtime (Admin > Settings). Saved values win over these environment variables; the variables are the fallback. Saved secrets are encrypted with `SETTINGS_ENCRYPTION_KEY` (or `JWT_SECRET` if that is unset). Set a separate `SETTINGS_ENCRYPTION_KEY` in production and never change it without re-entering the keys.
