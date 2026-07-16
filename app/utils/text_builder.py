from typing import Any


def build_embedding_text(parsed: dict[str, Any]) -> str:
    """
    Constructs a structured text block from parsed candidate dictionary
    to generate embedding representations for vector storage.
    """
    # Try skills_text first (database representation)
    skills_text = parsed.get("skills_text")
    if not skills_text:
        # Fallback to skills list (API representation)
        skills = [s.get("skill_name", "") for s in parsed.get("skills", []) if s.get("skill_name")]
        skills_text = ", ".join(skills) if skills else "N/A"

    return f"""
Role: {parsed.get('primary_role_title') or 'N/A'}
Domain: {parsed.get('primary_domain') or 'N/A'}
Experience: {parsed.get('total_experience_years') or '0'} years
Education: {parsed.get('highest_education') or 'N/A'}

Summary:
{parsed.get('summary_text') or 'N/A'}

Skills:
{skills_text}
""".strip()

def build_candidate_summary(parsed: dict[str, Any]) -> str:
    """
    Constructs a short human-readable candidate introduction text.
    """
    return f"{parsed.get('candidate_name') or 'Unknown Candidate'} - {parsed.get('primary_role_title') or 'Unknown Role'} ({parsed.get('primary_domain') or 'General Domain'})"
