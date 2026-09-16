from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ProfileSkill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    category: str = "skill"
    source: str = "resume"  # "resume" | "confirmed" | "declined" (confirmed/declined used from M3 onward)
    evidence_text: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Profile(SQLModel, table=True):
    """Fuller parsed resume content (beyond skills) used as LLM generation context.

    One row per user. Stored as JSON blobs rather than normalized tables since
    nothing needs to query into their internals yet -- only ProfileSkill does.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    experience_json: str = "[]"
    projects_json: str = "[]"
    education_json: str = "[]"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
