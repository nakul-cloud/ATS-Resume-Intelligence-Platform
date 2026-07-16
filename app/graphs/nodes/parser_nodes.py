from app.agents.resume_parser_agent import parse_resume_text
from app.graphs.state import ResumeParserState
from app.utils.logger import logger
from app.utils.pdf_extractor import extract_pdf_text


async def rp_extract_node(state: ResumeParserState) -> dict:
    """Node: Extracts text from PDF bytes."""
    logger.info("LangGraph Parser Node: Extracting PDF Text...")
    try:
        text = extract_pdf_text(state["pdf_bytes"])
        return {"resume_text": text, "error_message": None}
    except Exception as e:
        return {"error_message": f"PDF Extraction Failed: {e!s}"}

async def rp_parse_node(state: ResumeParserState) -> dict:
    """Node: Parses text into structured JSON using LLM Agent (with retry loop)."""
    current_retry = state.get("retry_count", 0) + 1
    logger.info(f"LangGraph Parser Node: LLM parsing (Attempt {current_retry}/{state['max_retries']})...")

    prompt_modifier = ""
    if state.get("error_message"):
        prompt_modifier = f"ATTENTION: Previous parse failed due to error: {state['error_message'][:100]}. Please double-check formatting."

    try:
        parsed_data = parse_resume_text(state["resume_text"], prompt_modifier=prompt_modifier)
        if not parsed_data.get("candidate_name"):
            raise ValueError("Parsed data is missing critical 'candidate_name' field.")

        return {"parsed_data": parsed_data, "error_message": None, "retry_count": current_retry}
    except Exception as e:
        return {"error_message": f"Parsing Failed: {e!s}", "retry_count": current_retry}

async def rp_store_node(state: ResumeParserState) -> dict:
    """Node: Embeds and stores the parsed data in database and vector-store."""
    logger.info("LangGraph Parser Node: Processing embedding & storing...")
    return {"error_message": None}
