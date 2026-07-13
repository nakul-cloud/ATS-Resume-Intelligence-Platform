from app.graphs.state import ResumeParserState

def route_parsing(state: ResumeParserState) -> str:
    """Decider: Routes back to parser on fail, otherwise proceeds to store."""
    if state.get("parsed_data"):
        return "store"
    
    # Simple bounds check to manage retry loop safely
    if state.get("error_message") and state.get("retry_count", 0) < state.get("max_retries", 3):
        return "parse"
    else:
        # Return the string literal matching the key in the conditional edge dictionary mapping
        return "failed"
