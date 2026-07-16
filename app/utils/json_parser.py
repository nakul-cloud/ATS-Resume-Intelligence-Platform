import json
import re
from typing import Any

from app.utils.logger import logger


def extract_json(raw_text: str) -> dict[str, Any] | list[Any]:
    """
    Safely extracts and parses JSON from raw LLM output,
    handling markdown blocks (```json ... ```) and minor formatting issues.
    """
    if not raw_text:
        return {}

    # Strip markdown block formatting if present
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: Try regex to extract first matching JSON block if outer text is present
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as err:
                logger.error(f"Fallback regex JSON parsing failed: {err}")

        logger.error(f"Failed to parse text as JSON: {raw_text}")
        raise ValueError("Invalid JSON format in LLM response")
