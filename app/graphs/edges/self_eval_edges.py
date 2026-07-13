from app.graphs.state import SelfEvalState

def route_self_eval(state: SelfEvalState) -> str:
    """Decider: Routes to specialized agents based on next_action."""
    if state.get("error"):
        return "error_handler"
    
    action = state.get("next_action")
    if action == "confidence_feedback":
        return "confidence_agent"
    elif action == "gap_analysis":
        return "gap_agent"
    elif action == "interview_prep":
        return "interview_agent"
    return "error_handler"
