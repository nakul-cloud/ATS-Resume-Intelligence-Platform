from pydantic import BaseModel
from typing import Optional, List

class JDEvaluationRequest(BaseModel):
    jd_text: str
    domain: Optional[str] = None
    top_k: int = 5

class CandidateMatchSchema(BaseModel):
    candidate_id: int
    candidate_name: Optional[str] = None
    primary_role: Optional[str] = None
    primary_domain: Optional[str] = None
    total_experience: Optional[float] = None
    score_100: float
    strengths: List[str]
    gaps: List[str]
    interview_questions: List[str]

class JDEvaluationResponse(BaseModel):
    jd_text: str
    domain_filter: Optional[str] = None
    results: List[CandidateMatchSchema]

class JDRewriteRequest(BaseModel):
    jd_text: str

class JDRewriteResponse(BaseModel):
    role: str
    required_skills: List[str]
    responsibilities: List[str]
    tools: List[str]
    seniority_level: str
