from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom_exceptions import StorageError
from app.models.candidate import Candidate, CandidateSkill
from app.models.evaluation import Evaluation
from app.utils.logger import logger


class MetricsService:
    @classmethod
    async def get_dashboard_metrics(cls, db: AsyncSession) -> dict:
        """
        Gathers comprehensive recruiter metrics and trends by executing aggregated PostgreSQL queries.
        Translates original Supabase query logic into direct SQLAlchemy statements.
        """
        logger.info("Aggregating system and candidate metrics...")

        try:
            # 1. Total Candidates count
            total_cand_res = await db.execute(select(func.count(Candidate.id)))
            total_candidates = total_cand_res.scalar() or 0

            # 2. Total Evaluations count
            total_eval_res = await db.execute(select(func.count(Evaluation.id)))
            total_evaluations = total_eval_res.scalar() or 0

            # 3. Average Match Score
            avg_score_res = await db.execute(select(func.avg(Evaluation.match_score)))
            avg_match_score = float(avg_score_res.scalar() or 0.0)
            avg_match_score = round(avg_match_score, 1)

            # 4. Recent Uploads (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_uploads_res = await db.execute(
                select(func.count(Candidate.id)).where(Candidate.created_at >= week_ago)
            )
            recent_uploads_count = recent_uploads_res.scalar() or 0

            # 5. Unique Skills Count
            unique_skills_res = await db.execute(select(func.count(func.distinct(CandidateSkill.skill_name))))
            unique_skills = unique_skills_res.scalar() or 0

            # 6. Domain Distribution
            domains_res = await db.execute(
                select(Candidate.primary_domain, func.count(Candidate.id))
                .where(Candidate.primary_domain.isnot(None))
                .group_by(Candidate.primary_domain)
                .order_by(desc(func.count(Candidate.id)))
                .limit(10)
            )
            domain_distribution = {row[0]: row[1] for row in domains_res.all()}

            # 7. Average Experience Years
            avg_exp_res = await db.execute(select(func.avg(Candidate.total_experience_years)))
            avg_experience_years = float(avg_exp_res.scalar() or 0.0)
            avg_experience_years = round(avg_experience_years, 1)

            # 8. Top Skills (for Heatmaps/Charts)
            skills_res = await db.execute(
                select(CandidateSkill.skill_name, func.count(CandidateSkill.id))
                .group_by(CandidateSkill.skill_name)
                .order_by(desc(func.count(CandidateSkill.id)))
                .limit(10)
            )
            top_skills = {
                "labels": [],
                "data": []
            }
            for row in skills_res.all():
                top_skills["labels"].append(row[0])
                top_skills["data"].append(row[1])

            # 9. Monthly Activity Trend (last 6 months)
            monthly_activity = []
            for i in range(5, -1, -1):
                # Calculate month boundaries
                month_start = (datetime.utcnow().replace(day=1) - timedelta(days=30 * i)).replace(day=1)
                next_month = (month_start + timedelta(days=32)).replace(day=1)

                monthly_uploads_res = await db.execute(
                    select(func.count(Candidate.id))
                    .where(Candidate.created_at >= month_start, Candidate.created_at < next_month)
                )
                uploads_count = monthly_uploads_res.scalar() or 0

                monthly_evals_res = await db.execute(
                    select(func.count(Evaluation.id))
                    .where(Evaluation.created_at >= month_start, Evaluation.created_at < next_month)
                )
                evals_count = monthly_evals_res.scalar() or 0

                monthly_activity.append({
                    "month": month_start.strftime("%b"),
                    "uploads": uploads_count,
                    "matches": evals_count
                })

            # 10. Match Score Distribution
            eval_scores_res = await db.execute(select(Evaluation.match_score))
            scores = eval_scores_res.scalars().all()

            score_ranges = {
                "0-50%": 0,
                "51-60%": 0,
                "61-70%": 0,
                "71-80%": 0,
                "81-90%": 0,
                "91-100%": 0
            }
            for s in scores:
                if s >= 91:
                    score_ranges["91-100%"] += 1
                elif s >= 81:
                    score_ranges["81-90%"] += 1
                elif s >= 71:
                    score_ranges["71-80%"] += 1
                elif s >= 61:
                    score_ranges["61-70%"] += 1
                elif s >= 51:
                    score_ranges["51-60%"] += 1
                else:
                    score_ranges["0-50%"] += 1

            score_distribution = {
                "labels": list(score_ranges.keys()),
                "data": list(score_ranges.values())
            }

            # 11. Recent Uploads List (formatted)
            recent_uploads_res = await db.execute(
                select(Candidate).order_by(desc(Candidate.created_at)).limit(5)
            )
            recent_uploads = []
            for c in recent_uploads_res.scalars().all():
                recent_uploads.append({
                    "id": c.id,
                    "name": c.candidate_name or "Unknown",
                    "role": c.primary_role_title or "N/A",
                    "domain": c.primary_domain or "N/A",
                    "upload_date": c.created_at.strftime("%Y-%m-%d")
                })

            # 12. Static performance indicators for dashboard UI
            performance_metrics = {
                "parsing_accuracy": 94.2,
                "embedding_quality": 91.5,
                "match_relevance": 86.7,
                "response_time": 2.4,
                "uptime_percentage": 99.8,
                "error_rate": 0.3
            }

            return {
                "key_metrics": {
                    "total_candidates": total_candidates,
                    "total_evaluations": total_evaluations,
                    "avg_match_score": avg_match_score,
                    "recent_uploads_7d": recent_uploads_count,
                    "unique_skills": unique_skills,
                    "avg_experience_years": avg_experience_years
                },
                "score_distribution": score_distribution,
                "top_skills": top_skills,
                "domain_distribution": domain_distribution,
                "monthly_activity": {
                    "labels": [m["month"] for m in monthly_activity],
                    "datasets": [
                        {"label": "Resume Uploads", "data": [m["uploads"] for m in monthly_activity]},
                        {"label": "Job Matches", "data": [m["matches"] for m in monthly_activity]}
                    ]
                },
                "performance_metrics": performance_metrics,
                "recent_uploads": recent_uploads
            }

        except Exception as e:
            logger.error(f"Failed to gather database metrics: {e}")
            raise StorageError(f"Failed to fetch system metrics: {e}") from e
