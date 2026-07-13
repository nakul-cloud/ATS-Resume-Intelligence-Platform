from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class CandidateSkillSchema(BaseModel):
    skill_name: str

class CandidateParsedData(BaseModel):
    candidate_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    primary_role_title: Optional[str] = None
    primary_domain: Optional[str] = None
    total_experience_years: Optional[float] = None
    highest_education: Optional[str] = None
    summary_text: Optional[str] = None
    skills: list[CandidateSkillSchema] = []
    work_experience: Optional[list] = []
    projects: Optional[list] = []
    accomplishments: Optional[list] = []
    hobbies: Optional[list] = []

class CandidateResponse(BaseModel):
    id: int
    resume_id: Optional[int] = None
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    primary_role_title: Optional[str] = None
    primary_domain: Optional[str] = None
    total_experience_years: Optional[float] = None
    highest_education: Optional[str] = None
    summary_text: Optional[str] = None
    skills_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeParseResponse(BaseModel):
    status: str
    candidate_id: Optional[int] = None
    parsed_data: Optional[CandidateParsedData] = None
    message: str
