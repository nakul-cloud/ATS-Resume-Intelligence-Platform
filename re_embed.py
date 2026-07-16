"""
Reads candidates from Postgres, builds their search profile texts,
generates embeddings using SentenceTransformer, and upserts them
into Qdrant.
"""

import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.models import Candidate
from app.services.ai.vector_store import VectorStore
from app.utils.text_builder import build_embedding_text


async def main():
    print("Initializing clients and models...")
    # 1. Initialize Postgres
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # 2. Initialize Qdrant
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)

    # 3. Ensure the resumes collection exists
    print("Ensuring Qdrant collection exists...")
    VectorStore.init_collection()

    # 4. Load SentenceTransformer model from Hugging Face
    # BAAI/bge-large-en-v1.5 yields 1024-dimensional vectors matching Settings.qdrant_vector_size
    print("Loading SentenceTransformer model (BAAI/bge-large-en-v1.5)...")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")

    # 5. Load candidates from DB
    print("Fetching candidates from database...")
    async with async_session() as session:
        result = await session.execute(select(Candidate))
        candidates = result.scalars().all()

    print(f"Found {len(candidates)} candidates in database.")

    if not candidates:
        print("No candidates found to embed.")
        await qdrant_client.close()
        return

    # 6. Generate embeddings and upload to Qdrant
    points = []
    print("Generating embeddings...")
    for idx, c in enumerate(candidates, start=1):
        # Convert candidate row to dictionary
        c_dict = {
            "primary_role_title": c.primary_role_title,
            "primary_domain": c.primary_domain,
            "total_experience_years": c.total_experience_years,
            "highest_education": c.highest_education,
            "summary_text": c.summary_text,
            "skills_text": c.skills_text,
        }

        # Build structured profile text (does NOT contain the candidate's name)
        profile_text = build_embedding_text(c_dict)

        # Generate embedding vector of the profile text
        vector = model.encode(profile_text).tolist()

        # Prepare Qdrant Point (Payload acts as metadata)
        point = PointStruct(
            id=c.id,
            vector=vector,
            payload={
                "metadata": { # Kept in metadata only
                "candidate_id": c.id,
                "candidate_name": c.candidate_name,
                "primary_role_title": c.primary_role_title,
                "primary_domain": c.primary_domain,
                "total_experience_years": float(c.total_experience_years) if c.total_experience_years else 0.0,
                "skills_text": c.skills_text,
                "summary_text": c.summary_text,
                },
                "content": profile_text,                 # Embedded profile text block (no name)
            }
        )
        points.append(point)

        if idx % 20 == 0 or idx == len(candidates):
            print(f"Generated embeddings for {idx}/{len(candidates)} candidates...")

    # Upsert points into Qdrant in batches
    batch_size = 50
    print(f"Upserting points into Qdrant in batches of {batch_size}...")
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        await qdrant_client.upsert(
            collection_name=VectorStore.COLLECTION_NAME,
            points=batch
        )
        print(f"Upserted points {i+1} to {min(i+batch_size, len(points))}")

    await qdrant_client.close()
    print("Re-embedding process completed successfully! All candidates uploaded to Qdrant.")

if __name__ == "__main__":
    asyncio.run(main())
