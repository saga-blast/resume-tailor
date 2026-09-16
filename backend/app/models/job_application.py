from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class JobApplication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = "Untitled"
    company: Optional[str] = None
    tex_source: str = ""
    jd_raw_text: Optional[str] = None
    extracted_requirements_json: Optional[str] = None
    match_percentage: Optional[float] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RequirementMatch(SQLModel, table=True):
    """One row per JD requirement per job -- backs both the Q&A UI and the
    (future, M4) highlight decisions during resume generation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    job_application_id: int = Field(foreign_key="jobapplication.id", index=True)
    requirement_text: str
    requirement_category: str = "skill"
    years_required: Optional[str] = None
    priority: str = "nice_to_have"
    match_status: str = "unmatched"  # "matched" | "needs_clarification" | "declined" | "unmatched"
    matched_skill_name: Optional[str] = None
    clarifying_question: Optional[str] = None
    user_answer: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
