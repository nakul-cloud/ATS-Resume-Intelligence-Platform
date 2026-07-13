from typing import Any
from groq import Groq

from app.config.settings import settings
from app.utils.logger import logger
from app.utils.json_parser import extract_json
from app.exceptions.custom_exceptions import AIServiceError

from app.providers.llm.factory import get_groq_client

def parse_and_normalize_jd(jd_text: str) -> dict[str, Any]:
    """
    Normalizes and extracts structured details from a raw job description using Groq.
    """
    logger.info("Invoking JD Rewrite Agent...")
    
    prompt = f"""
You are an expert recruiter. Analyze the job description below and extract it into a structured JSON format.

Job Description:
---
{jd_text}
---

Return ONLY a raw JSON object matching the following structure:
{{
    "role": "Standardized Job Title (e.g. Senior Frontend Developer)",
    "required_skills": ["Skill 1", "Skill 2"],
    "responsibilities": ["Responsibility 1", "Responsibility 2"],
    "tools": ["Tool/Framework 1", "Tool/Framework 2"],
    "seniority_level": "Junior" or "Mid" or "Senior" or "Lead"
}}

Guidelines:
1. Standardize the role title to be clear and match industry standards.
2. The JSON must be valid and conform EXACTLY to the structure. Do not include markdown wraps or explanations.
"""

    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_chat_model,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        parsed = extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict) or "role" not in parsed:
            raise AIServiceError("Invalid response structure from JD Rewrite Agent")
        return parsed
    except Exception as e:
        logger.error(f"Failed to normalize Job Description: {e}")
        raise AIServiceError(f"JD normalization agent failed: {e}")
