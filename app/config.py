import os

class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mixlab.db")
    secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
    storage_dir = os.getenv("STORAGE_DIR", "./storage")
    trial_days = int(os.getenv("TRIAL_DAYS", "7"))
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "50"))
    max_duration_sec = int(os.getenv("MAX_DURATION_SEC", "420"))
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_id = os.getenv("STRIPE_PRICE_ID", "")
    app_url = os.getenv("APP_URL", "http://localhost:5173")
    rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
    reset_minutes = 60
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "MixLab AI <no-reply@example.com>")
    paypal_env = os.getenv("PAYPAL_ENV", "sandbox")  # sandbox | live
    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_secret = os.getenv("PAYPAL_SECRET", "")
    paypal_plan_id = os.getenv("PAYPAL_PLAN_ID", "")
    paypal_webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "")
    allowed_ext = {".wav", ".mp3", ".flac"}

settings = Settings()
