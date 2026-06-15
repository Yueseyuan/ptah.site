from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Aegis Credit Investigator"
    DEV_NO_AUTH: bool = True
    DATABASE_URL: str = "sqlite:///./aegis.db"
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "generated_reports"

    class Config:
        env_file = ".env"


settings = Settings()
