from fastapi import APIRouter

from app.routes.v1.endpoints.auth import router as auth_router
from app.routes.v1.endpoints.health import router as health_router
from app.routes.v1.endpoints.interview import router as interview_router
from app.routes.v1.endpoints.jd import router as jd_router
from app.routes.v1.endpoints.recruiter import router as recruiter_router
from app.routes.v1.endpoints.resume import router as resume_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(resume_router, prefix="/resumes", tags=["resumes"])
router.include_router(interview_router, prefix="/interviews", tags=["interviews"])
router.include_router(jd_router, prefix="/jds", tags=["jds"])
router.include_router(recruiter_router, prefix="/recruiter", tags=["recruiter"])
router.include_router(health_router, prefix="/health", tags=["health"])
