from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = "sqlite:///./ca_engine.db"

    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None

    DOCUSIGN_INTEGRATION_KEY: Optional[str] = None
    DOCUSIGN_ACCOUNT_ID: Optional[str] = None
    DROPBOX_SIGN_API_KEY: Optional[str] = None

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None

    COMPANY_NAME: str = "Cruel & Associates"
    COMPANY_PHONE: str = "(864) 990-1301"
    COMPANY_EMAIL: str = "yueseyuan.cruel@cruelandassociates.site"
    COMPANY_WEBSITE: str = "www.cruelandassociates.site"
    COMPANY_ADDRESS: str = "South Carolina"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
