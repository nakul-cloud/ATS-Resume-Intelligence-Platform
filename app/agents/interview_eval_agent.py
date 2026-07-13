import os
from typing import Any

from app.config.settings import settings
from app.utils.logger import logger
from app.utils.json_parser import extract_json
from app.exceptions.custom_exceptions import AIServiceError

from app.providers.llm.factory import get_groq_client


# ---------------------------------------------------------------------------
# Prompt loader — reads all named sections from interview_prompt.txt
# ---------------------------------------------------------------------------

_PROMPT_CACHE: dict[str, str] | None = None

def _load_prompts() -> dict[str, str]:
    """
    Loads interview_prompt.txt and splits it into named sections keyed by
    their [SECTION_NAME] headers. Result is cached in-process.
    """
    global _PROMPT_CACHE
    if _PROMPT_CACHE is not None:
        return _PROMPT_CACHE

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "interview_prompt.txt"
    )
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read interview prompts from {prompt_path}: {e}")
        raise AIServiceError(f"Prompt load failed: {e}")

    sections: dict[str, str] = {}
    current_key = None
    current_lines: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = stripped[1:-1]  # e.g. "INITIAL_QUESTION_PROMPT"
            current_lines = []
        else:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    _PROMPT_CACHE = sections
    return sections


def _get_tier_context(tier: str) -> str:
    """Returns the tier-specific instruction block from the prompt file."""
    prompts = _load_prompts()
    tier_key = f"TIER_{tier}"
    return prompts.get(tier_key, prompts.get("TIER_GAP_ANALYSIS", ""))


def _get_advanced_round_message() -> str:
    """Returns the advanced round instruction from the prompt file."""
    prompts = _load_prompts()
    return prompts.get("TIER_ADVANCED_ROUND", "Generate a highly difficult advanced question.")


# ---------------------------------------------------------------------------
# Public agent functions
# ---------------------------------------------------------------------------

def generate_initial_question(
    role: str,
    domain: str,
    skills: str,
    gaps: list[str],
    tier: str = "GAP_ANALYSIS",
) -> dict[str, Any]:
    """
    Generates the first interview question.
    Question style is determined by the score tier read from interview_prompt.txt:
      BASIC        (30-59) : Easy confidence-building questions on known skills
      GAP_ANALYSIS (60-79) : Medium difficulty targeting identified gaps
      ADVANCED     (>= 80) : Expert-level system-design questions
    """
    logger.info(f"Generating initial interview question | Role: {role} | Tier: {tier}")

    prompts = _load_prompts()
    template = prompts.get("INITIAL_QUESTION_PROMPT", "")
    tier_context = _get_tier_context(tier)

    prompt = (
        template
        .replace("{role}", str(role))
        .replace("{domain}", str(domain))
        .replace("{skills}", str(skills))
        .replace("{gaps}", ", ".join(gaps) if gaps else "None specified")
        .replace("{tier_context}", tier_context)
    )

    try:
        response = get_groq_client().chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        parsed = extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict) or "question_text" not in parsed:
            raise AIServiceError("Invalid response structure from initial question agent")
        # Ensure topic field is present for diversity tracking
        if "topic" not in parsed:
            parsed["topic"] = parsed["question_text"][:60]
        return parsed
    except Exception as e:
        logger.error(f"Failed to generate initial question: {e}")
        raise AIServiceError(f"Interview agent initial question failed: {e}")


def generate_next_stateless_question(
    candidate_profile: dict[str, Any],
    jd_text: str,
    gaps: list[str],
    history: list[dict[str, Any]],
    is_advanced: bool = False,
    tier: str = "GAP_ANALYSIS",
) -> dict[str, Any]:
    """
    Generates the next dynamic question based on candidate profile, JD, gaps, history,
    and score tier. Tier instructions are read from interview_prompt.txt.
    """
    logger.info(f"Generating next question | tier={tier} | is_advanced={is_advanced}")

    role = candidate_profile.get("primary_role_title") or "Software Developer"
    domain = candidate_profile.get("primary_domain") or "General Tech"
    skills = candidate_profile.get("skills_text") or ""

    # Build history string AND extract already-covered topics for diversity enforcement
    history_str = ""
    covered_topics: list[str] = []
    for idx, item in enumerate(history):
        history_str += (
            f"Question {idx+1}: {item.get('question_text')}\n"
            f"Answer {idx+1}: {item.get('answer_text')}\n"
            f"Score: {item.get('answer_score')}/100\n"
            f"Feedback: {item.get('feedback')}\n\n"
        )
        # Collect topic if available, otherwise fall back to question snippet
        topic = item.get("topic") or item.get("question_text", "")[:60]
        if topic:
            covered_topics.append(topic)

    covered_topics_str = ", ".join(covered_topics) if covered_topics else "None yet"

    # Pick the round-specific instruction from the prompt file
    if is_advanced:
        is_advanced_message = _get_advanced_round_message()
    else:
        is_advanced_message = _get_tier_context(tier)

    prompts = _load_prompts()
    template = prompts.get("NEXT_QUESTION_PROMPT", "")

    prompt = (
        template
        .replace("{role}", str(role))
        .replace("{domain}", str(domain))
        .replace("{jd_text}", str(jd_text or "N/A"))
        .replace("{skills}", str(skills))
        .replace("{gaps}", ", ".join(gaps) if gaps else "None specified")
        .replace("{history_str}", history_str)
        .replace("{is_advanced_message}", is_advanced_message)
        .replace("{covered_topics}", covered_topics_str)
    )

    logger.info(
        f"Next question context | tier={tier} | is_advanced={is_advanced} | "
        f"questions_so_far={len(history)} | covered_topics=[{covered_topics_str}]"
    )

    try:
        response = get_groq_client().chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        parsed = extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict) or "question_text" not in parsed:
            raise AIServiceError("Invalid response structure from next question agent")
        # Ensure topic field present
        if "topic" not in parsed:
            parsed["topic"] = parsed["question_text"][:60]
        return parsed
    except Exception as e:
        logger.error(f"Failed to generate next question: {e}")
        raise AIServiceError(f"Interview agent next question failed: {e}")


def evaluate_interview_answer(
    question_text: str,
    candidate_answer: str,
    role: str,
    domain: str,
    current_difficulty: str,
) -> dict[str, Any]:
    """
    Evaluates the candidate's answer and returns scoring, feedback, strengths, and weaknesses.
    """
    logger.info("Evaluating candidate interview answer...")

    prompts = _load_prompts()
    template = prompts.get("EVALUATION_PROMPT", "")
    prompt = (
        template
        .replace("{role}", str(role))
        .replace("{domain}", str(domain))
        .replace("{question_text}", str(question_text))
        .replace("{candidate_answer}", str(candidate_answer))
        .replace("{current_difficulty}", str(current_difficulty))
    )

    try:
        response = get_groq_client().chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        parsed = extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict) or "score" not in parsed:
            raise AIServiceError("Invalid response structure from evaluation agent")
        return parsed
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {e}")
        raise AIServiceError(f"Interview evaluation agent failed: {e}")


def generate_final_report(
    role: str,
    domain: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generates a unified final report summarising all answers, strengths, gaps, and feedback.
    """
    logger.info("Generating final unified interview report...")

    history_str = ""
    for idx, item in enumerate(history):
        history_str += (
            f"Question {idx+1} ({item.get('difficulty_level', 'MEDIUM')}): {item.get('question_text')}\n"
            f"Answer {idx+1}: {item.get('answer_text')}\n"
            f"Score: {item.get('answer_score')}/100\n"
            f"Feedback: {item.get('feedback')}\n"
            f"Strengths: {', '.join(item.get('strengths', []))}\n"
            f"Weaknesses/Gaps: {', '.join(item.get('weaknesses', []))}\n\n"
        )

    prompt = f"""You are an expert technical interviewer. Review the candidate's complete mock interview history for the role of {role} in {domain}.
Generate a comprehensive, professional summary report.

Interview History:
---
{history_str}
---

Your response MUST be a JSON object with this exact schema:
{{
    "average_score": 0.0,
    "confidence_feedback": "A summary of their overall profile match, technical readiness, and how well they communicated.",
    "strengths": [
        "Detailed, specific technical strength 1 based on their answers",
        "Detailed, specific technical strength 2 based on their answers"
    ],
    "suggestions": [
        "A specific, actionable improvement suggestion addressing gap 1",
        "A specific, actionable improvement suggestion addressing gap 2",
        "A specific, actionable improvement suggestion addressing gap 3"
    ]
}}

Provide specific, constructive technical details. Do not use generic placeholders. Return ONLY raw JSON.
"""
    try:
        response = get_groq_client().chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return extract_json(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to generate final report: {e}")
        # Aggregated fallback
        all_strengths, all_weaknesses = [], []
        for h in history:
            all_strengths.extend(h.get("strengths", []))
            all_weaknesses.extend(h.get("weaknesses", []))
        scores = [h.get("answer_score", 0.0) for h in history]
        avg = sum(scores) / len(scores) if scores else 0.0
        return {
            "average_score": round(avg, 1),
            "confidence_feedback": "Completed mock interview session.",
            "strengths": list(set(all_strengths))[:5],
            "suggestions": list(set(all_weaknesses))[:5],
        }
