import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.services.resume import ResumeService


async def main():
    # Setup test DB session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Simulate uploading a test resume twice
    file_name = "test_resume.pdf"
    file_bytes = b"Hello, Nakul Jadhav. email: nakul@example.com. Python developer with 3.5 years of experience."

    async with async_session() as db:
        print("--- Step 1: Uploading resume first time ---")
        cand1 = await ResumeService.parse_and_save_resume(db, file_name, file_bytes)
        print(f"Result: First Candidate ID: {cand1.id}, Name: {cand1.candidate_name}")

        print("\n--- Step 2: Uploading exact same resume bytes (Tier 1 Hash Match) ---")
        cand2 = await ResumeService.parse_and_save_resume(db, file_name, file_bytes)
        print(f"Result: Second Candidate ID: {cand2.id} (Should equal {cand1.id}: {cand1.id == cand2.id})")

        print("\n--- Step 3: Uploading slightly modified resume text (Tier 2 Similarity Match) ---")
        # Change file name and a tiny punctuation to trigger similarity
        file_bytes_modified = b"Hello, Nakul Jadhav. email: nakul@example.com. Python developer with 3.5 years of experience. Formatting details added."
        cand3 = await ResumeService.parse_and_save_resume(db, "test_resume_v2.pdf", file_bytes_modified)
        print(f"Result: Third Candidate ID: {cand3.id} (Should equal {cand1.id}: {cand1.id == cand3.id})")

if __name__ == "__main__":
    asyncio.run(main())
