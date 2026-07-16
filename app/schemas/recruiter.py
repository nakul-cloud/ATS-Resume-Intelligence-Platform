from typing import Any

from pydantic import BaseModel


class LiveMetricsResponse(BaseModel):
    timestamp: str
    system_mode: str
    total_candidates: int
    total_evaluations: int
    avg_match_score: float
    score_distribution: dict[str, int]
    monthly_trend: list[dict[str, Any]]
    top_skills: list[dict[str, Any]]
    frequent_gaps: list[dict[str, Any]]
    trending_weak_topics: list[dict[str, Any]]
    recent_activity: list[dict[str, Any]]

class RecruiterDashboardResponse(BaseModel):
    overview: dict[str, Any]
    candidate_pool: dict[str, Any]
    evaluation_insights: dict[str, Any]
    interview_analytics: dict[str, Any]
    skill_heatmap: dict[str, Any]
    recent_matches: list[dict[str, Any]]
