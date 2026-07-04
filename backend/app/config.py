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

    # ── Email (SendGrid) ──────────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@example.com"

    # ── Social Media ──────────────────────────────────────────────────────────
    # Twitter / X  (OAuth 1.0a — create app at developer.twitter.com)
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    # LinkedIn  (OAuth 2.0 token from developer.linkedin.com)
    linkedin_access_token: str = ""
    linkedin_person_id: str = ""

    # Facebook / Instagram  (Meta Business App access token)
    facebook_page_id: str = ""
    facebook_access_token: str = ""
    instagram_business_account_id: str = ""

    # ── Higgsfield AI  (video + audio generation) ─────────────────────────────
    # Run `hf auth login` once, then set this to the credentials.json path.
    # Default: ~/.config/higgsfield/credentials.json (auto-detected if present)
    higgsfield_credentials_path: str = ""


settings = Settings()
