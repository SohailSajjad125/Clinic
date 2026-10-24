# Deployment checklist

1. **Secrets:** create them on the server (never in git). `JWT_SECRET`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Keep `ENVIRONMENT=production` (the default): the API refuses to start with weak or localhost settings.
2. **Database:** managed PostgreSQL 14+ with TLS (`?sslmode=require`), encryption at rest and automated backups. Run `scripts/create_db_roles.sql`, run migrations as `clinicos_owner`, and run the API as `clinicos_app`. Do not expose the database port to the internet.
3. **Backend:** `pip install -r backend/requirements.txt`; `alembic upgrade head`; run `uvicorn app.main:app --host 127.0.0.1 --port 8000` (add `--proxy-headers --forwarded-allow-ips <proxy-ip>` behind a proxy) behind nginx/Caddy that terminates HTTPS. One instance until real-time and rate limits move to Redis. `STORAGE_DIR` on a private persistent disk (or S3/R2 by replacing `app/core/storage.py`).
4. **Frontends:** `npm ci && npm run build && npm start` in `website/` and `webapp/` (or a host such as Vercel). Set `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_SITE_URL` at build time. Serve everything over HTTPS only.
5. **CORS / links:** `CORS_ORIGINS` = the exact website and app origins (https). `APP_URL` = the web app URL.
6. **First platform admin:** `python -m app.cli create-superadmin you@example.com "Your Name"`.
7. **Before launch:** schedule `scripts/backup.sh` and test a restore; add a WAF/rate limit at the proxy; set up log monitoring; get legal review of the privacy policy and terms; consider an independent penetration test.
