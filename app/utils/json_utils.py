import json

from app.utils.logger import logger


def parse_json_list(json_str: str | None) -> list:
    """
    Safely parses a JSON string into a list.
    Falls back to an empty list on failure or missing input.
    """
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.warning(f"Failed to parse JSON list (returning empty list): {e}")
        return []
