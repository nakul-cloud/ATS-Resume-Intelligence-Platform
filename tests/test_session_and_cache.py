import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.config.settings import settings
from app.services.resume import ResumeService
from app.services.jd import JDService
from app.controllers.recruiter_controller import RecruiterController
from app.controllers.candidate_controller import CandidateController
from app.models.candidate import Candidate

async def main():
    # Setup database engine and session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("--- Step 1: Testing PostgreSQL Job Description Normalization Caching ---")
        jd_text = "Wanted: Senior Python Developer with FastAPI and Postgres skills. 5+ years of experience."
        
        print("First normalization request (Cache MISS expected):")
        jd1 = await JDService.normalize_job_description(db, jd_text)
        print(f"Result: {jd1.get('role', 'N/A')}")
        
        print("\nSecond normalization request (Cache HIT expected):")
        jd2 = await JDService.normalize_job_description(db, jd_text)
        print(f"Result: {jd2.get('role', 'N/A')}")
        
        print("\n--- Step 2: Testing Session-wise (In-Memory) Resume Parsing ---")
        file_bytes = b"Hello, Rahul Verma. email: rahul@example.com. Python developer with 4 years of experience."
        parsed_data = await ResumeService.parse_resume_session("rahul_resume.pdf", file_bytes)
        
        # Check that parsed data contains correct info
        print(f"Parsed Name: {parsed_data.get('candidate_name')}")
        print(f"Parsed Email: {parsed_data.get('email')}")
        
        # Verify that candidate is NOT saved in PostgreSQL
        stmt = select(Candidate).where(Candidate.email == "rahul@example.com")
        res = await db.execute(stmt)
        c_db = res.scalars().all()
        print(f"Verification: Found {len(c_db)} candidates matching email in DB. (Should be 0: {len(c_db) == 0})")
        
        print("\n--- Step 3: Explicitly Persisting Parsed Candidate to PostgreSQL/Qdrant ---")
        # Format candidate data matching CandidatePersistRequest
        persist_data = {
            "name": parsed_data.get("candidate_name") or "Rahul Verma",
            "email": parsed_data.get("email"),
            "phone_number": parsed_data.get("phone_number"),
            "role": parsed_data.get("primary_role_title"),
            "domain": parsed_data.get("primary_domain"),
            "experience": float(parsed_data.get("total_experience_years")) if parsed_data.get("total_experience_years") else 4.0,
            "highest_education": parsed_data.get("highest_education"),
            "summary_text": parsed_data.get("summary_text") or "Summary text here",
            "skills": [s.get("skill_name") for s in parsed_data.get("skills", []) if s.get("skill_name")]
        }
        
        cand = await ResumeService.persist_parsed_candidate(db, persist_data)
        print(f"Result: Persisted Candidate ID: {cand.id}, Name: {cand.candidate_name}")
        
        # Verify candidate is now present in PostgreSQL
        res_verify = await db.execute(select(Candidate).where(Candidate.id == cand.id))
        c_verify = res_verify.scalar_one_or_none()
        print(f"Verification: Candidate exists in DB: {c_verify is not None}")

        print("\n--- Step 4: Testing Self Evaluation with In-Memory Candidate Data ---")
        eval_res = await CandidateController.agent_self_evaluate(
            db=db,
            candidate_id=0,
            candidate_data=persist_data,
            jd_text="Senior Python Developer role with FastAPI experience."
        )
        print(f"Result: Self Eval Score: {eval_res.get('score_100')}%")
        print(f"Result Status: {eval_res.get('status')}")

if __name__ == "__main__":
    asyncio.run(main())
