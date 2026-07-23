import os
from typing import Any

from app.config.settings import settings
from app.exceptions.custom_exceptions import AIServiceError
from app.providers.llm.factory import get_groq_client
from app.utils.json_parser import extract_json
from app.utils.logger import logger


def optimize_resume_bullets(
    candidate_name: str,
    experience_years: float,
    skills: list[str],
    projects: list[dict],
    jd_text: str,
    focus_areas: list[str]
) -> dict[str, Any]:
    """
    Sends candidate's details and the target Job Description to Groq to generate
    highly customized, high-impact STAR optimized resume bullet point rewrites.
    """
    logger.info(f"Invoking Resume Rewrite Agent for candidate: {candidate_name}...")

    skills_str = ", ".join(skills) if skills else "General technical skills"
    focus_str = ", ".join(focus_areas) if focus_areas else "Action Verbs, Metrics & Impact"

    # Extract original highlights or summaries from experience/projects
    original_bullets = []
    if projects:
        for p in projects[:3]:
            title = p.get("title") or p.get("project_title") or "Project"
            desc = p.get("description") or p.get("project_description") or ""
            if desc:
                original_bullets.append(f"Worked on {title}: {desc}")

    if not original_bullets:
        original_bullets = [
            "Responsible for full-stack engineering and API routes.",
            "Helped improve application load speeds and refactored code.",
            "Collaborated with product teams to roll out features."
        ]

    bullets_formatted = "\n".join([f"- {b}" for b in original_bullets])

    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "rewriter_prompt.txt")
    try:
        with open(prompt_path, encoding="utf-8") as f:
            prompt_tpl = f.read()
    except Exception as e:
        logger.error(f"Failed to read rewriter prompt from {prompt_path}: {e}")
        raise AIServiceError(f"Prompt load failed: {e}")

    prompt = prompt_tpl.format(
        candidate_name=candidate_name,
        experience_years=experience_years,
        skills_str=skills_str,
        focus_str=focus_str,
        bullets_formatted=bullets_formatted,
        jd_text=jd_text
    )

    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        parsed = extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict) or "optimized_bullets" not in parsed:
            raise AIServiceError("Invalid response structure from Resume Rewrite Agent")
        return parsed
    except Exception as e:
        logger.error(f"Failed to optimize resume bullets: {e}")
        raise AIServiceError(f"Resume rewrite agent failed: {e}")
