from typing import Any

from pydantic import BaseModel


class AgentSelfEvalRequest(BaseModel):
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    jd_text: str

class ProjectsRecommendationRequest(BaseModel):
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    evaluation_id: int | None = None
    score: float | None = None
    domain: str | None = None
    gaps: list[str] | None = None

class ResumeRewriteRequest(BaseModel):
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    jd_text: str | None = None
    focus_areas: list[str] | None = None

class InterviewEvaluateRequest(BaseModel):
    session_id: str
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    question: str
    user_answer: str
    role: str | None = ""
    domain: str | None = ""

class CandidatePersistRequest(BaseModel):
    name: str
    email: str | None = None
    phone_number: str | None = None
    role: str | None = None
    domain: str | None = None
    experience: float | None = 0.0
    highest_education: str | None = None
    summary_text: str | None = None
    skills: list[str] = []
    projects: list[dict[str, Any]] | None = []
    accomplishments: list[str] | None = []
    hobbies: list[str] | None = []
    work_experience: list[dict[str, Any]] | None = []

class StatelessInterviewStartRequest(BaseModel):
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    jd_text: str
    gaps: list[str] | None = []
    evaluation_score: float | None = None  # Overall fit score from self-evaluation
    score_tier: str | None = None  # FUNDAMENTALS | BASIC | GAP_ANALYSIS | ADVANCED

class StatelessInterviewSubmitRequest(BaseModel):
    session_id: str | None = None
    candidate_id: int | None = None
    candidate_data: dict[str, Any] | None = None
    jd_text: str
    gaps: list[str] | None = []
    question_text: str
    answer_text: str
    difficulty_level: str
    history: list[dict[str, Any]] = []
    is_advanced: bool | None = False
    score_tier: str | None = None  # Passed through from the frontend for tier-aware logic

