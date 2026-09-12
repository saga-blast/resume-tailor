from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class JobApplication(SQLModel, table=True):
    """M1 scope: just enough to back the split-pane editor (title + tex_source).

    M2/M3/M4 extend this with jd_raw_text, extracted_requirements,
    match_percentage and status once the JD-matching pipeline lands.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = "Untitled"
    tex_source: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
