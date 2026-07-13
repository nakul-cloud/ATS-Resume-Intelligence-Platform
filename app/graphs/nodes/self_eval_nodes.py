from app.graphs.state import SelfEvalState
from app.agents.resume_parser_agent import parse_resume_text
from app.agents.evaluator import evaluate_candidate_against_jd
from app.utils.pdf_extractor import extract_pdf_text
from app.utils.text_builder import build_embedding_text
from app.utils.logger import logger

async def se_evaluate_node(state: SelfEvalState) -> dict:
    """Node: Extracts, parses, and evaluates candidate against JD."""
    logger.info("LangGraph Self-Eval Node: Running evaluation...")
    try:
        if state.get("pdf_bytes"):
            text = extract_pdf_text(state["pdf_bytes"])
            parsed_resume = parse_resume_text(text)
            c_dict = {
                "primary_role_title": parsed_resume.get("primary_role_title"),
                "primary_domain": parsed_resume.get("primary_domain"),
                "total_experience_years": parsed_resume.get("total_experience_years"),
                "highest_education": parsed_resume.get("highest_education"),
                "summary_text": parsed_resume.get("summary_text"),
                "skills_text": ", ".join([s["skill_name"] for s in parsed_resume.get("skills", []) if s.get("skill_name")]),
            }
        else:
            # Bypass PDF parsing, use already populated candidate metadata from the database
            logger.info("Empty pdf_bytes: Bypassing PDF extraction and using database candidate metadata directly.")
            c_dict = {
                "primary_role_title": state.get("role", "N/A"),
                "primary_domain": state.get("domain", "N/A"),
                "total_experience_years": state.get("experience_years", 0.0),
                "highest_education": state.get("education", "N/A"),
                "summary_text": state.get("resume_text", "N/A"),
                "skills_text": state.get("skills_text", "N/A"),
            }
            parsed_resume = {
                "candidate_name": "",
                "email": "",
                "phone_number": "",
                "primary_role_title": state.get("role", "N/A"),
                "primary_domain": state.get("domain", "N/A"),
                "total_experience_years": state.get("experience_years", 0.0),
                "highest_education": state.get("education", "N/A"),
                "summary_text": state.get("resume_text", "N/A"),
                "skills": [{"skill_name": s.strip()} for s in state.get("skills_text", "").split(",") if s.strip()]
            }
            text = state.get("resume_text", "")

        evaluation = evaluate_candidate_against_jd(c_dict, state["jd_text"])
        
        # Only return the modified or new keys. Do NOT use **state.
        return {
            "resume_text": text,
            "parsed_resume": parsed_resume,
            "candidate_text": build_embedding_text(c_dict),
            "score_100": evaluation["score"],
            "strengths": evaluation["strengths"],
            "gaps": evaluation["gaps"],
            "interview_questions": evaluation["interview_questions"],
            "role": parsed_resume.get("primary_role_title", "N/A"),
            "domain": parsed_resume.get("primary_domain", "N/A"),
            "error": "",
            "current_step": "evaluation_complete"
        }
    except Exception as e:
        logger.error(f"Self-eval failed: {e}")
        return {"error": f"Evaluation failed: {str(e)}", "current_step": "evaluation_failed"}

async def se_decide_node(state: SelfEvalState) -> dict:
    """Node: Decision Agent that decides routing based on match score."""
    score = state.get("score_100", 0.0)
    logger.info(f"LangGraph Self-Eval Node: Decision Agent checking score ({score})...")
    
    if score < 60:
        next_action = "confidence_feedback"
        reasoning = "Score < 60. Routing to Confidence Feedback."
    elif score < 80:
        next_action = "gap_analysis"
        reasoning = "Score 60-79. Routing to Gap Analysis."
    else:
        next_action = "interview_prep"
        reasoning = "Score >= 80. Routing to Advanced Interview Prep."
        
    return {
        "next_action": next_action,
        "decision_reasoning": reasoning,
        "current_step": "decision_made"
    }

async def se_confidence_feedback_node(state: SelfEvalState) -> dict:
    """Node: Generates basics-focused learning roadmap and confidence feedback."""
    logger.info("LangGraph Self-Eval Node: Executing Confidence Feedback Agent...")
    score = state.get("score_100", 0.0)
    
    feedback = f"Based on your score of {score}, here is a plan to build confidence."
    roadmap = [
        "Weeks 1-2: Master core languages & algorithms fundamentals",
        "Weeks 3-4: Build a small project demonstrating core concepts"
    ]
    return {
        "confidence_feedback": feedback,
        "learning_roadmap": roadmap,
        "interview_questions": ["Introduce yourself and walk me through your best project."],
        "current_step": "confidence_feedback_complete"
    }

async def se_gap_analysis_node(state: SelfEvalState) -> dict:
    """Node: Generates targeted mock questions on gaps and a medium roadmap."""
    logger.info("LangGraph Self-Eval Node: Executing Gap Analysis Agent...")
    gaps = state.get("gaps", [])
    
    feedback = "You are almost ready! Focus on bridging your specific technology gaps."
    roadmap = [
        "Week 1: Research and study the identified skill gaps",
        "Week 2: Build a mini-project targeting these missing libraries"
    ]
    
    gap_questions = [f"How do you handle tasks requiring {g}?" for g in gaps[:3]]
    
    return {
        "confidence_feedback": feedback,
        "learning_roadmap": roadmap,
        "interview_questions": gap_questions, 
        "current_step": "gap_analysis_complete"
    }

async def se_interview_prep_node(state: SelfEvalState) -> dict:
    """Node: Generates advanced system design mock questions and roadmap."""
    logger.info("LangGraph Self-Eval Node: Executing Advanced Prep Agent...")
    
    feedback = "Excellent match! Focus on advanced system architecture."
    roadmap = [
        "Week 1: Practice complex architectural design patterns",
        "Week 2: Dive deep into performance scaling & databases"
    ]
    return {
        "confidence_feedback": feedback,
        "learning_roadmap": roadmap,
        "current_step": "interview_prep_complete"
    }

async def se_error_handler_node(state: SelfEvalState) -> dict:
    """Node: Graceful error handler."""
    return {
        "confidence_feedback": f"System error: {state.get('error', 'Unknown')}",
        "learning_roadmap": ["Review job description requirements."],
        "current_step": "error_handled"
    }
