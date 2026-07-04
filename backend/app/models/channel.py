from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Channel(Base, TimestampMixin):
    """A configured communication channel (Telegram bot, Discord webhook, etc.)."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "telegram" | "discord_webhook" | "slack_webhook" | "generic_webhook"
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Type-specific JSON config (tokens, URLs, allowed IDs, etc.)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
