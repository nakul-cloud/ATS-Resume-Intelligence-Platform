from app.graphs.state import InterviewEvalState
from app.agents.interview_eval_agent import evaluate_interview_answer
from app.utils.logger import logger

async def ie_evaluate_answer_node(state: InterviewEvalState) -> dict:
    """Node: Grades candidate answer and generates follow-up."""
    logger.info("LangGraph Interview Node: Evaluating answer...")
    try:
        evaluation = evaluate_interview_answer(
            question_text=state["question"],
            candidate_answer=state["user_answer"],
            role=state["role"],
            domain=state["domain"],
            current_difficulty=state["current_difficulty"]
        )
        return {
            "answer_score": evaluation.get("score", 0.0),
            "feedback": evaluation.get("feedback", ""),
            "strengths": evaluation.get("strengths", []),
            "weaknesses": evaluation.get("weaknesses", []),
            "follow_up_question": evaluation.get("follow_up_question", ""),
            "next_difficulty": evaluation.get("next_difficulty", "MEDIUM"),
            "error": ""
        }
    except Exception as e:
        logger.error(f"Interview evaluation failed: {e}")
        # Return fallback values for structural keys to prevent downstream KeyErrors
        return {
            "error": f"Evaluation failed: {str(e)}",
            "answer_score": 0.0,
            "next_difficulty": state.get("current_difficulty", "MEDIUM"), # Keep same difficulty on error
            "follow_up_question": "Could you please try rephrasing your last response?" # Graceful fallback question
        }
