import os
from typing import Any

from app.config.settings import settings
from app.exceptions.custom_exceptions import AIServiceError
from app.providers.llm.factory import get_groq_client
from app.utils.json_parser import extract_json
from app.utils.logger import logger


def recommend_projects(
    role: str,
    experience_years: float,
    skills: list[str],
    gaps: list[str]
) -> list[dict[str, Any]]:
    """
    Calls Groq to recommend 3 personalized hands-on projects to bridge the candidate's skill gaps
    based on their target role, experience level, and existing skill set.
    """
    logger.info(f"Generating personalized project recommendations for Role: {role} ({experience_years} Yrs Exp)...")

    gaps_str = ", ".join(gaps) if gaps else "General advancement gaps"
    skills_str = ", ".join(skills) if skills else "General technical skills"

    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "project_rec_prompt.txt")
    try:
        with open(prompt_path, encoding="utf-8") as f:
            prompt_tpl = f.read()
    except Exception as e:
        logger.error(f"Failed to read projects prompt from {prompt_path}: {e}")
        raise AIServiceError(f"Prompt load failed: {e}")

    prompt = prompt_tpl.format(
        role=role,
        experience_years=experience_years,
        skills_str=skills_str,
        gaps_str=gaps_str
    )

    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=settings.groq_chat_model,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        parsed = extract_json(raw_output)

        # Groq with json_object might wrap the array under a key or return the raw array.
        # Let's extract the list dynamically.
        if isinstance(parsed, dict):
            # If the LLM returned e.g. {"projects": [...]}, extract it
            for _key, val in parsed.items():
                if isinstance(val, list):
                    return val
            # Fallback if it is a dict but not nested
            return [parsed]
        if isinstance(parsed, list):
            return parsed

        raise AIServiceError("Invalid response format returned by the projects recommendation agent")
    except Exception as e:
        logger.error(f"Error in Projects Recommendation Agent execution: {e}")
        raise AIServiceError(f"Projects recommendation agent failed: {e}")
