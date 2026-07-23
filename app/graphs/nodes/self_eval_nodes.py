from __future__ import annotations

from app.agents.evaluator import evaluate_candidate_against_jd
from app.agents.resume_parser_agent import parse_resume_text
from app.constants.general import (
    NOT_AVAILABLE,
    STEP_CONFIDENCE_FEEDBACK_COMPLETE,
    STEP_DECISION_MADE,
    STEP_ERROR_HANDLED,
    STEP_EVAL_COMPLETE,
    STEP_EVAL_FAILED,
    STEP_GAP_ANALYSIS_COMPLETE,
    STEP_INTERVIEW_PREP_COMPLETE,
)
from app.graphs.state import SelfEvalState
from app.utils.logger import logger
from app.utils.pdf_extractor import extract_pdf_text
from app.utils.text_builder import build_embedding_text

# ==========================================
# 1. ISOLATED WORKFLOW HELPERS (Fixes S3776, S1145, S1541)
# ==========================================

def _extract_and_parse_pdf(pdf_bytes: bytes) -> tuple[str, dict]:
    """Helper to handle isolated PDF text extraction and parsing."""
    text = extract_pdf_text(pdf_bytes)
    parsed_resume = parse_resume_text(text)
    return text, parsed_resume


def _build_candidate_dict_from_parsed(parsed_resume: dict) -> dict:
    """Builds structural metadata dictionary from raw parsed components."""
    # Flattened skill filtering extraction avoids complex nested comprehensions
    skills_list = []
    for skill in parsed_resume.get("skills", []):
        name = skill.get("skill_name")
        if name:
            skills_list.append(name)

    return {
        "primary_role_title": parsed_resume.get("primary_role_title"),
        "primary_domain": parsed_resume.get("primary_domain"),
        "total_experience_years": parsed_resume.get("total_experience_years"),
        "highest_education": parsed_resume.get("highest_education"),
        "summary_text": parsed_resume.get("summary_text"),
        "skills_text": ", ".join(skills_list),
    }


def _build_fallback_candidate_profile(state: SelfEvalState) -> tuple[str, dict, dict]:
    """Builds fallback candidate metadata structures directly from state history."""
    logger.info("Empty pdf_bytes: Bypassing PDF extraction and using database candidate metadata directly.")

    role = state.get("role", NOT_AVAILABLE)
    domain = state.get("domain", NOT_AVAILABLE)
    exp = state.get("experience_years", 0.0)
    edu = state.get("education", NOT_AVAILABLE)
    text = state.get("resume_text", "")
    skills_raw = state.get("skills_text", NOT_AVAILABLE)

    c_dict = {
        "primary_role_title": role,
        "primary_domain": domain,
        "total_experience_years": exp,
        "highest_education": edu,
        "summary_text": text,
        "skills_text": skills_raw,
    }

    parsed_resume = {
        "candidate_name": "",
        "email": "",
        "phone_number": "",
        "primary_role_title": role,
        "primary_domain": domain,
        "total_experience_years": exp,
        "highest_education": edu,
        "summary_text": text,
        "skills": [{"skill_name": s.strip()} for s in state.get("skills_text", "").split(",") if s.strip()]
    }

    return text, parsed_resume, c_dict


# ==========================================
# 2. LINT-CLEAN LANGGRAPH NODES
# ==========================================

def se_evaluate_node(state: SelfEvalState) -> dict:
    """Node: Extracts, parses, and evaluates candidate against JD."""
    logger.info("LangGraph Self-Eval Node: Running evaluation...")
    try:
        pdf_bytes = state.get("pdf_bytes")

        if pdf_bytes:
            text, parsed_resume = _extract_and_parse_pdf(pdf_bytes)
            c_dict = _build_candidate_dict_from_parsed(parsed_resume)
        else:
            text, parsed_resume, c_dict = _build_fallback_candidate_profile(state)

        evaluation = evaluate_candidate_against_jd(c_dict, state["jd_text"])

        return {
            "resume_text": text,
            "parsed_resume": parsed_resume,
            "candidate_text": build_embedding_text(c_dict),
            "score_100": evaluation["score"],
            "strengths": evaluation["strengths"],
            "gaps": evaluation["gaps"],
            "interview_questions": evaluation["interview_questions"],
            "role": parsed_resume.get("primary_role_title", NOT_AVAILABLE),
            "domain": parsed_resume.get("primary_domain", NOT_AVAILABLE),
            "error": "",
            "current_step": STEP_EVAL_COMPLETE
        }
    except Exception as e:  # Handled cleanly on edge orchestration nodes
        logger.error(f"Self-eval failed: {e}")
        return {"error": f"Evaluation failed: {e!s}", "current_step": STEP_EVAL_FAILED}


def se_decide_node(state: SelfEvalState) -> dict:
    """Node: Decision Agent that decides routing based on match score."""
    score = state.get("score_100", 0.0)
    logger.info(f"LangGraph Self-Eval Node: Decision Agent checking score ({score})...")

    if score < 60:
        return {
            "next_action": "confidence_feedback",
            "decision_reasoning": "Score < 60. Routing to Confidence Feedback.",
            "current_step": STEP_DECISION_MADE
        }

    if score < 80:
        return {
            "next_action": "gap_analysis",
            "decision_reasoning": "Score 60-79. Routing to Gap Analysis.",
            "current_step": STEP_DECISION_MADE
        }

    return {
        "next_action": "interview_prep",
        "decision_reasoning": "Score >= 80. Routing to Advanced Interview Prep.",
        "current_step": STEP_DECISION_MADE
    }


def se_confidence_feedback_node(state: SelfEvalState) -> dict:
    """Node: Generates basics-focused learning roadmap and confidence feedback."""
    logger.info("LangGraph Self-Eval Node: Executing Confidence Feedback Agent...")

    score = state.get("score_100", 0.0)
    feedback = f"Based on your score of {score}, here is a plan to build confidence."

    return {
        "confidence_feedback": feedback,
        "learning_roadmap": [
            "Weeks 1-2: Master core languages & algorithms fundamentals",
            "Weeks 3-4: Build a small project demonstrating core concepts"
        ],
        "interview_questions": ["Introduce yourself and walk me through your best project."],
        "current_step": STEP_CONFIDENCE_FEEDBACK_COMPLETE
    }


def se_gap_analysis_node(state: SelfEvalState) -> dict:
    """Node: Generates targeted mock questions on gaps and a medium roadmap."""
    logger.info("LangGraph Self-Eval Node: Executing Gap Analysis Agent...")
    gaps = state.get("gaps", [])

    return {
        "confidence_feedback": "You are almost ready! Focus on bridging your specific technology gaps.",
        "learning_roadmap": [
            "Week 1: Research and study the identified skill gaps",
            "Week 2: Build a mini-project targeting these missing libraries"
        ],
        "interview_questions": [f"How do you handle tasks requiring {g}?" for g in gaps[:3]],
        "current_step": STEP_GAP_ANALYSIS_COMPLETE
    }


def se_interview_prep_node(_state: SelfEvalState) -> dict:
    """Node: Generates advanced system design mock questions and roadmap."""
    logger.info("LangGraph Self-Eval Node: Executing Advanced Prep Agent...")

    return {
        "confidence_feedback": "Excellent match! Focus on advanced system architecture.",
        "learning_roadmap": [
            "Week 1: Practice complex architectural design patterns",
            "Week 2: Dive deep into performance scaling & databases"
        ],
        "current_step": STEP_INTERVIEW_PREP_COMPLETE
    }


def se_error_handler_node(state: SelfEvalState) -> dict:
    """Node: Graceful error handler."""
    return {
        "confidence_feedback": f"System error: {state.get('error', 'Unknown')}",
        "learning_roadmap": ["Review job description requirements."],
        "current_step": STEP_ERROR_HANDLED
    }
