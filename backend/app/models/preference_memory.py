from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class PreferenceMemory(SQLModel, table=True):
    """The literal implementation of 'never ask the same question twice' --
    normalized_key is unique per user so a requirement the user already
    confirmed or declined is looked up deterministically, not re-derived."""

    __table_args__ = (UniqueConstraint("user_id", "normalized_key", name="uq_preference_user_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    normalized_key: str = Field(index=True)
    fact_text: str
    status: str  # "confirmed" | "declined"
    question_text: str
    answer_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
