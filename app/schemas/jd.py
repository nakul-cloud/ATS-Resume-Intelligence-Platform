
from pydantic import BaseModel


class JDEvaluationRequest(BaseModel):
    jd_text: str
    domain: str | None = None
    top_k: int = 5

class CandidateMatchSchema(BaseModel):
    candidate_id: int
    candidate_name: str | None = None
    primary_role: str | None = None
    primary_domain: str | None = None
    total_experience: float | None = None
    score_100: float
    strengths: list[str]
    gaps: list[str]
    interview_questions: list[str]

class JDEvaluationResponse(BaseModel):
    jd_text: str
    domain_filter: str | None = None
    results: list[CandidateMatchSchema]

class JDRewriteRequest(BaseModel):
    jd_text: str

class JDRewriteResponse(BaseModel):
    role: str
    required_skills: list[str]
    responsibilities: list[str]
    tools: list[str]
    seniority_level: str
