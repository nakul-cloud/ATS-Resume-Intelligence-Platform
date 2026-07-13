import hashlib
import re
from decimal import Decimal
from typing import Any, List, Set, Dict

def compute_file_hash(file_bytes: bytes) -> str:
    """
    Computes the SHA-256 hash of raw file bytes.
    """
    if not file_bytes:
        return ""
    return hashlib.sha256(file_bytes).hexdigest()

def compute_text_similarity(text_a: str, text_b: str) -> float:
    """
    Computes Jaccard word-level similarity between two raw text strings.
    Returns a score between 0.0 and 1.0.
    """
    if not text_a or not text_b:
        return 0.0
        
    # Lowercase and split into alphanumeric word tokens
    words_a = set(re.findall(r"\w+", text_a.lower()))
    words_b = set(re.findall(r"\w+", text_b.lower()))
    
    if not words_a or not words_b:
        return 0.0
        
    intersection = len(words_a.intersection(words_b))
    union = len(words_a.union(words_b))
    return float(intersection / union)

def compute_field_diff(old_candidate: Any, new_parsed: dict) -> dict:
    """
    Compares every candidate data column between old candidate model and new parsed dictionary.
    Returns a dictionary of changes in format {field: {"old": val, "new": val}}.
    """
    diff = {}
    
    # Text/Scalar columns comparison
    fields = [
        ("candidate_name", "candidate_name"),
        ("email", "email"),
        ("phone_number", "phone_number"),
        ("primary_role_title", "primary_role_title"),
        ("primary_domain", "primary_domain"),
        ("highest_education", "highest_education"),
        ("summary_text", "summary_text")
    ]
    
    for col, key in fields:
        old_val = getattr(old_candidate, col) or ""
        new_val = new_parsed.get(key) or ""
        if str(old_val).strip() != str(new_val).strip():
            diff[col] = {
                "old": old_val if old_val else None,
                "new": new_val if new_val else None
            }
            
    # Total experience years comparison (handle Decimal type safely)
    old_exp = old_candidate.total_experience_years or Decimal("0.0")
    new_exp_val = new_parsed.get("total_experience_years")
    new_exp = Decimal(str(new_exp_val)) if new_exp_val is not None else Decimal("0.0")
    if old_exp != new_exp:
        diff["total_experience_years"] = {
            "old": float(old_exp),
            "new": float(new_exp)
        }
        
    return diff

def compute_skills_diff(old_skills: List[str], new_skills: List[str]) -> dict:
    """
    Compares lists of skill strings and finds added and removed skills.
    """
    old_set = {s.strip().lower() for s in old_skills if s.strip()}
    new_set = {s.strip().lower() for s in new_skills if s.strip()}
    
    old_map = {s.strip().lower(): s.strip() for s in old_skills if s.strip()}
    new_map = {s.strip().lower(): s.strip() for s in new_skills if s.strip()}
    
    added = [new_map[s] for s in (new_set - old_set)]
    removed = [old_map[s] for s in (old_set - new_set)]
    
    return {
        "added": added,
        "removed": removed,
        "changed": len(added) > 0 or len(removed) > 0
    }
