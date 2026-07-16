from datetime import datetime

from pydantic import BaseModel, EmailStr


class CandidateSkillSchema(BaseModel):
    skill_name: str

class CandidateParsedData(BaseModel):
    candidate_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    primary_role_title: str | None = None
    primary_domain: str | None = None
    total_experience_years: float | None = None
    highest_education: str | None = None
    summary_text: str | None = None
    skills: list[CandidateSkillSchema] = []
    work_experience: list | None = []
    projects: list | None = []
    accomplishments: list | None = []
    hobbies: list | None = []

class CandidateResponse(BaseModel):
    id: int
    resume_id: int | None = None
    candidate_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    primary_role_title: str | None = None
    primary_domain: str | None = None
    total_experience_years: float | None = None
    highest_education: str | None = None
    summary_text: str | None = None
    skills_text: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeParseResponse(BaseModel):
    status: str
    candidate_id: int | None = None
    parsed_data: CandidateParsedData | None = None
    message: str
