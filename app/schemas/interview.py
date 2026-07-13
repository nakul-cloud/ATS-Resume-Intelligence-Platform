import uuid
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class InterviewSessionCreateRequest(BaseModel):
    candidate_id: int
    evaluation_id: Optional[int] = None

class InterviewSessionResponse(BaseModel):
    id: uuid.UUID
    candidate_id: int
    evaluation_id: Optional[int] = None
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
    role: Optional[str] = None
    domain: Optional[str] = None

class InterviewAnswerEvaluationResponse(BaseModel):
    answer_score: float
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    follow_up_question: Optional[str] = None
    next_difficulty: str
    status: str
