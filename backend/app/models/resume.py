from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ResumeTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    raw_tex: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
