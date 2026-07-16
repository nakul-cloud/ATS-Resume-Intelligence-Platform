import uuid
from datetime import datetime

from pydantic import BaseModel


class InterviewSessionCreateRequest(BaseModel):
    candidate_id: int
    evaluation_id: int | None = None

class InterviewSessionResponse(BaseModel):
    id: uuid.UUID
    candidate_id: int
    evaluation_id: int | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class InterviewQuestionResponse(BaseModel):
    id: int
    session_id: uuid.UUID
    question_text: str
    difficulty_level: str
    question_order: int

    class Config:
        from_attributes = True

class InterviewAnswerSubmitRequest(BaseModel):
    question_id: int
    answer_text: str
    # Context hints (optional, fallback if not cached in session)
    role: str | None = None
    domain: str | None = None

class InterviewAnswerEvaluationResponse(BaseModel):
    answer_score: float
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    follow_up_question: str | None = None
    next_difficulty: str
    status: str
