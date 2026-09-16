from pydantic import BaseModel


class ProfileSkillItem(BaseModel):
    name: str
    category: str


class ProfileExperienceItem(BaseModel):
    title: str
    company: str
    dates: str
    bullets: list[str]


class ProfileProjectItem(BaseModel):
    name: str
    description: str


class ProfileEducationItem(BaseModel):
    school: str
    degree: str
    dates: str


class ParsedProfile(BaseModel):
    skills: list[ProfileSkillItem]
    experience: list[ProfileExperienceItem]
    projects: list[ProfileProjectItem]
    education: list[ProfileEducationItem]


class ExtractedRequirement(BaseModel):
    text: str
    category: str  # "skill" | "tool" | "experience" | "responsibility"
    years_required: str | None = None
    priority: str  # "must_have" | "nice_to_have"


class ExtractedRequirements(BaseModel):
    requirements: list[ExtractedRequirement]
