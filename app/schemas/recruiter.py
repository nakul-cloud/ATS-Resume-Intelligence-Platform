from pydantic import BaseModel
from typing import Dict, List, Any

class LiveMetricsResponse(BaseModel):
    timestamp: str
    system_mode: str
    total_candidates: int
    total_evaluations: int
    avg_match_score: float
    score_distribution: Dict[str, int]
    monthly_trend: List[Dict[str, Any]]
    top_skills: List[Dict[str, Any]]
    frequent_gaps: List[Dict[str, Any]]
    trending_weak_topics: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

class RecruiterDashboardResponse(BaseModel):
    overview: Dict[str, Any]
    candidate_pool: Dict[str, Any]
    evaluation_insights: Dict[str, Any]
    interview_analytics: Dict[str, Any]
    skill_heatmap: Dict[str, Any]
    recent_matches: List[Dict[str, Any]]
