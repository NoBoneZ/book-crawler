from decouple import config
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # MongoDB Configuration
    mongodb_url: str = config("MONGODB_URL", cast=str)
    mongodb_db_name: str = config("MONGODB_DB_NAME", cast=str)

    # API Configuration
    api_host: str = config("API_HOST", cast=str)
    api_port: int = config("API_PORT", cast=str)
    api_key: str = config("API_KEY", cast=str)

    # Crawler Configuration
    crawler_concurrent_requests: int = config("CRAWLER_CONCURRENT_REQUESTS", cast=int)
    crawler_retry_attempts: int = config("CRAWLER_RETRY_ATTEMPTS", cast=int)
    crawler_retry_delay: int = config("CRAWLER_RETRY_DELAY", cast=int)
    crawler_timeout: int = config("CRAWLER_TIMEOUT", cast=int)
    crawler_user_agent: str = config("CRAWLER_USER_AGENT", cast=str)

    # Target Website
    target_url: str = config("TARGET_URL", cast=str)

    # Scheduler Configuration
    scheduler_enabled: bool = config("SCHEDULER_ENABLED", cast=bool)
    scheduler_interval_hours: float = config("SCHEDULER_INTERVAL_HOURS", cast=float)

    # Rate Limiting
    rate_limit_per_hour: int = config("RATE_LIMIT_PER_HOUR", cast=int)

    # Logging
    log_level: str = config("LOG_LEVEL", cast=str)
    log_file: str = config("LOG_FILE", cast=str)


    # Email Alert Configuration
    alert_email_enabled: str = config("ALERT_EMAIL_ENABLED", cast=str, default="")
    smtp_host: str = config("SMTP_HOST", cast=str, default="")
    smtp_port: int = config("SMTP_PORT", cast=int, default=0)
    smtp_username: str = config("SMTP_USERNAME", cast=str, default="")
    smtp_password: str = config("SMTP_PASSWORD", cast=str, default="")
    alert_recipient: str = config("ALERT_RECIPIENT", cast=str, default="")
    alert_sender_name: str = config("ALERT_SENDER_NAME", cast=str, default="")



    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()