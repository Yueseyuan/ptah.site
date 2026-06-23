from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "APEX AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./apex_data/database/apex.db"

    # Security
    secret_key: str = "change-me-generate-with-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Paths
    apex_data_dir: Path = Path("apex_data")

    # Model backends
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    huggingface_api_token: str = ""
    # Set to http://localhost:8003 to route via free-claude-code proxy
    anthropic_base_url: str = "https://api.anthropic.com"
    ollama_base_url: str = "http://localhost:11434"
    llamacpp_base_url: str = "http://localhost:8080"
    lmstudio_base_url: str = "http://localhost:1234"
    localai_base_url: str = "http://localhost:8080"
    vllm_base_url: str = "http://localhost:8000"


settings = Settings()
