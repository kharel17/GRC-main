from typing import List, Union, Optional
from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "GRC Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:3000"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 24
    ENVIRONMENT: str = "development"  # development | staging | production
    
    # DATABASE
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    SQLALCHEMY_DATABASE_URI: Union[str, None] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None], info: dict) -> any:
        if isinstance(v, str):
            return v
        uri = str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            port=info.data.get("POSTGRES_PORT"),
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        ))
        # Add SSL for cloud databases (non-localhost)
        server = info.data.get("POSTGRES_SERVER", "localhost")
        if server and server != "localhost" and "127.0.0.1" not in server:
            uri += "?ssl=require"
        return uri

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            origins = [i.strip() for i in v.split(",")]
            # Filter out empty strings and return as-is (including wildcards)
            return [o for o in origins if o]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        return []

    # FILE STORAGE
    FILE_STORAGE_BACKEND: str = "local"  # "local" or "s3"
    UPLOAD_DIR: str = "/app/uploads"
    
    # S3 (only needed when FILE_STORAGE_BACKEND=s3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # seconds

    # LOGGING
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # ALLOWED HOSTS
    ALLOWED_HOSTS: List[str] = ["*"]

    # AI (Gemini)
    GEMINI_API_KEY: Optional[str] = None


    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
