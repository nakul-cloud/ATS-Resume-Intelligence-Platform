from typing_extensions import TypedDict


class ResumeParserState(TypedDict):
    """State for the resilient resume parsing retry workflow."""
    pdf_bytes: bytes
    resume_text: str
    parsed_data: dict | None
    embedding: list[float] | None
    file_name: str
    error_message: str | None
    max_retries: int
    retry_count: int
    storage_result: dict | None

class SelfEvalState(TypedDict):
    """State for the multi-agentic candidate self-evaluation workflow."""
    # Input
    pdf_bytes: bytes
    jd_text: str
    resume_text: str

    # Core Evaluation Results
    score_100: float
    strengths: list[str]
    gaps: list[str]
    interview_questions: list[str]
    role: str
    domain: str
    skills_text: str
    experience_years: float
    education: str

    # Agentic Decisions & Outputs
    learning_roadmap: list[str]
    confidence_feedback: str
    next_action: str
    decision_reasoning: str
    error: str
    current_step: str

    # Internal variables
    parsed_resume: dict
    candidate_text: str

class InterviewEvalState(TypedDict):
    """State for the adaptive mock interview answering and evaluation loop."""
    # Input
    question: str
    user_answer: str
    role: str
    domain: str
    current_difficulty: str

    # Output
    answer_score: float
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    follow_up_question: str
    next_difficulty: str
    error: str
