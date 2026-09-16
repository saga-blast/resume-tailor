from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class LLMProviderConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str = "anthropic"
    model: str = "claude-sonnet-5"
    encrypted_api_key: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
