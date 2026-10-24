import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "production").lower()  # fail closed: anything but 'development'/'test' behaves as production
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://clinicos:clinicos@localhost:5432/clinicos"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    access_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    refresh_days: int = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    app_url: str = os.getenv("APP_URL", "http://localhost:3001")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "ClinicOS <no-reply@clinicos.local>")
    smtp_tls: bool = os.getenv("SMTP_TLS", "1") == "1"
    twilio_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_sms_from: str = os.getenv("TWILIO_SMS_FROM", "")
    twilio_whatsapp_from: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    messaging_sync: bool = os.getenv("MESSAGING_SYNC", "0") == "1"
    run_scheduler: bool = os.getenv("RUN_SCHEDULER", "1") == "1"
    cors_origins: tuple = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    )


settings = Settings()
if len(settings.jwt_secret) < 32:
    raise RuntimeError("JWT_SECRET must be set and at least 32 characters long.")


WEAK_SECRETS = {"changeme", "secret", "password", "jwt_secret", "your-secret-key", "x" * 40, "t" * 48}


def validate(s: Settings) -> list[str]:
    """Returns problems that must stop a production start. Development only warns (see main.py)."""
    bad = []
    if len(set(s.jwt_secret)) < 10 or s.jwt_secret.lower() in WEAK_SECRETS:
        bad.append("JWT_SECRET is too predictable. Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
    if s.database_url.startswith("sqlite"):
        bad.append("DATABASE_URL must be PostgreSQL in production.")
    if "clinicos:clinicos@" in s.database_url:
        bad.append("DATABASE_URL uses the default development password.")
    if any(o == "*" for o in s.cors_origins):
        bad.append("CORS_ORIGINS must list exact origins, not '*'.")
    if any(not o.startswith("https://") and "localhost" not in o and "127.0.0.1" not in o for o in s.cors_origins):
        bad.append("CORS_ORIGINS must use https:// origins in production.")
    if any("localhost" in o or "127.0.0.1" in o for o in s.cors_origins):
        bad.append("CORS_ORIGINS still contains localhost.")
    if not s.app_url.startswith("https://"):
        bad.append("APP_URL must be https:// in production (it is used in password-reset links).")
    return bad


IS_DEV = settings.environment in ("development", "test")
if not IS_DEV:
    problems = validate(settings)
    if problems:
        raise RuntimeError("Unsafe production configuration:\n - " + "\n - ".join(problems))
