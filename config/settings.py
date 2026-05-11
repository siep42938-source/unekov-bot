from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram
    bot_token: str = Field(..., env="BOT_TOKEN")
    webhook_url: str = Field("", env="WEBHOOK_URL")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # OpenAI
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")

    # Groq (бесплатно — приоритет)
    groq_api_key: str = Field("", env="GROQ_API_KEY")

    # DeepSeek
    deepseek_api_key: str = Field("", env="DEEPSEEK_API_KEY")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(1440, env="JWT_EXPIRE_MINUTES")

    # App
    app_env: str = Field("production", env="APP_ENV")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    # Admin
    admin_ids: List[int] = Field(default_factory=list, env="ADMIN_IDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            # "123456,789012" или "123456"
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    # Tokens
    free_tokens_on_register: int = Field(100, env="FREE_TOKENS_ON_REGISTER")
    daily_free_tokens: int = Field(10, env="DAILY_FREE_TOKENS")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
