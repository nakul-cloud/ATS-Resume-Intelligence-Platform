
import os

from app.config.settings import settings
from app.exceptions.custom_exceptions import AIServiceError
from app.providers.llm.factory import get_groq_client
from app.utils.json_parser import extract_json
from app.utils.logger import logger


def _build_prompt(prompt_tpl: str, candidate_profile: dict, jd_text: str) -> str:
    """Build prompt using safe string replacement.
    JD is truncated to 600 chars and summary to 300 chars to cap input tokens.
    """
    # Truncate long fields to avoid prompt bloat
    jd_short     = str(jd_text or "N/A")[:600]
    summary_short = str(candidate_profile.get('summary_text') or 'N/A')[:300]

    return (
        prompt_tpl
        .replace("{jd_text}",    jd_short)
        .replace("{role}",       str(candidate_profile.get('primary_role_title') or 'N/A'))
        .replace("{domain}",     str(candidate_profile.get('primary_domain') or 'N/A'))
        .replace("{experience}", str(candidate_profile.get('total_experience_years') or '0'))
        .replace("{education}",  str(candidate_profile.get('highest_education') or 'N/A'))
        .replace("{summary}",    summary_short)
        .replace("{skills}",     str(candidate_profile.get('skills_text') or 'N/A'))
    )

def _call_groq(prompt: str) -> dict:
    """Call Groq API and return parsed JSON result.
    max_tokens=500 hard-caps completion to prevent verbose output bloat.
    """
    groq_client = get_groq_client()
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=settings.groq_chat_model,
        temperature=0.1,
        max_tokens=1200,
        response_format={"type": "json_object"}
    )
    raw_output = response.choices[0].message.content
    return extract_json(raw_output)

def evaluate_candidate_against_jd(candidate_profile: dict, jd_text: str) -> dict:
    """
    Evaluates a candidate's profile text against a Job Description,
    calculating a match score and identifying strengths, gaps, and dynamic questions.
    """
    logger.info(f"Invoking Evaluator Agent for Candidate: {candidate_profile.get('candidate_name', 'Unknown')}")

    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "evaluator_prompt.txt")
    try:
        with open(prompt_path, encoding="utf-8") as f:
            prompt_tpl = f.read()
    except Exception as e:
        logger.error(f"Failed to read evaluator prompt from {prompt_path}: {e}")
        raise AIServiceError(f"Prompt load failed: {e}")

    try:
        prompt = _build_prompt(prompt_tpl, candidate_profile, jd_text)
        parsed_json = _call_groq(prompt)
    except Exception as e:
        err_str = str(e)
        if "json_validate_failed" in err_str or "Failed to validate JSON" in err_str:
            # Retry with a simplified, safe fallback prompt that avoids embedding raw user text
            logger.warning("Groq JSON validation failed - retrying with simplified prompt (input text may contain special characters).")
            fallback_prompt = (
                "You are a technical recruiter. Given the following candidate and job details, "
                "return ONLY a JSON object with these keys:\n"
                "- score (integer 0-100)\n"
                "- strengths (list of 6-8 strings)\n"
                "- gaps (list of 5-7 strings)\n"
                "- interview_questions (list of exactly 3 strings)\n\n"
                f"Candidate Role: {candidate_profile.get('primary_role_title', 'N/A')}\n"
                f"Domain: {candidate_profile.get('primary_domain', 'N/A')}\n"
                f"Experience: {candidate_profile.get('total_experience_years', 0)} years\n"
                f"Education: {candidate_profile.get('highest_education', 'N/A')}\n"
                f"Skills: {candidate_profile.get('skills_text', 'N/A')}\n\n"
                f"Job Description (first 800 chars): {str(jd_text or '')[:800]}\n\n"
                "Return ONLY valid JSON, no markdown, no explanation."
            )
            try:
                parsed_json = _call_groq(fallback_prompt)
            except Exception as retry_err:
                logger.error(f"Retry also failed: {retry_err}")
                raise AIServiceError(f"Candidate evaluation agent failed: {retry_err}")
        else:
            logger.error(f"Error in Evaluator Agent execution: {e}")
            raise AIServiceError(f"Candidate evaluation agent failed: {e}")

    # Verify the structure is correct
    if not isinstance(parsed_json, dict) or "score" not in parsed_json:
        raise AIServiceError("Invalid output format returned by the evaluator agent")

    return parsed_json
