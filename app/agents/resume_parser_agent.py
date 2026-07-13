from typing import Any
from groq import Groq

from app.config.settings import settings
from app.utils.logger import logger
from app.utils.json_parser import extract_json
from app.exceptions.custom_exceptions import AIServiceError

from app.providers.llm.factory import get_groq_client

import os

def parse_resume_text(resume_text: str, prompt_modifier: str = "") -> dict[str, Any]:
    """
    Sends raw resume text to Groq and extracts structured candidate data in JSON format.
    """
    logger.info("Invoking Resume Parser Agent...")
    
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "parser_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_tpl = f.read()
    except Exception as e:
        logger.error(f"Failed to read parser prompt from {prompt_path}: {e}")
        raise AIServiceError(f"Prompt load failed: {e}")
        
    correction_instruction = f"\n{prompt_modifier}\n" if prompt_modifier else ""
    prompt = prompt_tpl.format(
        correction_instruction=correction_instruction,
        resume_text=resume_text
    )

    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional resume parsing assistant. You MUST extract candidate information from the provided resume text and return it as a valid JSON object matching the requested schema. Do not output any preamble, markdown wraps (like ```json), explanations, or text outside the JSON structure. The response must start with '{' and end with '}'."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=settings.groq_chat_model,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        parsed_json = extract_json(raw_output)
        
        # Verify the structure is correct
        if not isinstance(parsed_json, dict):
            raise AIServiceError("Invalid output format returned by the parser agent")
            
        return parsed_json
    except Exception as e:
        logger.error(f"Error in Resume Parser Agent execution: {e}")
        raise AIServiceError(f"Resume parsing agent failed: {e}")
