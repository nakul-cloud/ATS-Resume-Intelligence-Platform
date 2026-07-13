from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AgentSelfEvalRequest(BaseModel):
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    jd_text: str

class ProjectsRecommendationRequest(BaseModel):
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    evaluation_id: Optional[int] = None
    score: Optional[float] = None
    domain: Optional[str] = None
    gaps: Optional[List[str]] = None

class ResumeRewriteRequest(BaseModel):
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    jd_text: Optional[str] = None
    focus_areas: Optional[List[str]] = None

class InterviewEvaluateRequest(BaseModel):
    session_id: str
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    question: str
    user_answer: str
    role: Optional[str] = ""
    domain: Optional[str] = ""

class CandidatePersistRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    domain: Optional[str] = None
    experience: Optional[float] = 0.0
    highest_education: Optional[str] = None
    summary_text: Optional[str] = None
    skills: List[str] = []
    projects: Optional[List[Dict[str, Any]]] = []
    accomplishments: Optional[List[str]] = []
    hobbies: Optional[List[str]] = []
    work_experience: Optional[List[Dict[str, Any]]] = []

class StatelessInterviewStartRequest(BaseModel):
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    jd_text: str
    gaps: Optional[List[str]] = []
    evaluation_score: Optional[float] = None  # Overall fit score from self-evaluation
    score_tier: Optional[str] = None  # FUNDAMENTALS | BASIC | GAP_ANALYSIS | ADVANCED

class StatelessInterviewSubmitRequest(BaseModel):
    session_id: Optional[str] = None
    candidate_id: Optional[int] = None
    candidate_data: Optional[Dict[str, Any]] = None
    jd_text: str
    gaps: Optional[List[str]] = []
    question_text: str
    answer_text: str
    difficulty_level: str
    history: List[Dict[str, Any]] = []
    is_advanced: Optional[bool] = False
    score_tier: Optional[str] = None  # Passed through from the frontend for tier-aware logic

