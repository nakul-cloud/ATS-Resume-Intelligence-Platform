import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config.settings import settings


class VectorStore:
    _client = None
    COLLECTION_NAME = "resumes"

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._client is None:
            cls._client = QdrantClient(url=settings.qdrant_url)
        return cls._client

    @classmethod
    def init_collection(cls):
        """Creates collection if not exists"""
        client = cls.get_client()
        if not client.collection_exists(cls.COLLECTION_NAME):
            # Using settings.embedding_dimensions
            client.create_collection(
                collection_name=cls.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.embedding_dimensions, distance=Distance.COSINE
                ),
            )

    @classmethod
    async def upsert_chunks(
        cls, ids: list[str] | list[int], vectors: list[list[float]], payloads: list[dict]
    ):
        """Upsert points into collection (non-blocking via thread executor)"""
        cls.init_collection()
        client = cls.get_client()
        points = [
            PointStruct(id=idx, vector=vec, payload=pay)
            for idx, vec, pay in zip(ids, vectors, payloads, strict=True)
        ]
        await asyncio.to_thread(
            client.upsert, collection_name=cls.COLLECTION_NAME, points=points
        )
        # Create payload index for metadata.candidate_id
        client.create_payload_index(
            collection_name=cls.COLLECTION_NAME,
            field_name="metadata.candidate_id",
            field_schema="integer"
        )
        # Create text index on metadata.primary_domain to enable dynamic full-text MatchText filtering
        client.create_payload_index(
            collection_name=cls.COLLECTION_NAME,
            field_name="metadata.primary_domain",
            field_schema="text"
        )

    @classmethod
    async def delete_by_document_id(cls, document_id: str):
        """Delete old vectors for update/overwrite (non-blocking)"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = cls.get_client()
        points_selector = Filter(
            must=[
                FieldCondition(
                    key="metadata.document_id", match=MatchValue(value=document_id)
                )
            ]
        )
        await asyncio.to_thread(
            client.delete,
            collection_name=cls.COLLECTION_NAME,
            points_selector=points_selector,
        )

    @classmethod
    async def search_candidates(
        cls,
        query_vector: list[float],
        limit: int = 5,
        domain: str | None = None,
        filters: dict | None = None
    ) -> list:
        """
        Executes a semantic vector search on Qdrant, optionally applying a dynamic domain filter
        and other metadata filters (e.g. skills, experience_min, candidate_id).
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText, Range
        
        client = cls.get_client()
        must_conditions = []
        
        # 1. Main domain filter argument (backward compatibility)
        if domain:
            must_conditions.append(
                FieldCondition(
                    key="metadata.primary_domain",
                    match=MatchText(text=domain)
                )
            )
            
        # 2. General dynamic filters dict
        if filters:
            # Domain key in dict
            d = filters.get("domain")
            if d:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.primary_domain",
                        match=MatchText(text=d)
                    )
                )
                
            # Skills key in dict (can be single skill string or list of skills)
            skills = filters.get("skills")
            if skills:
                if isinstance(skills, str):
                    skills = [skills]
                for skill in skills:
                    must_conditions.append(
                        FieldCondition(
                            key="metadata.skills_text",
                            match=MatchText(text=skill)
                        )
                    )
                    
            # Minimum experience years key
            exp_min = filters.get("experience_min")
            if exp_min is not None:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.total_experience_years",
                        range=Range(gte=float(exp_min))
                    )
                )
                
            # Candidate ID check
            c_id = filters.get("candidate_id")
            if c_id is not None:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.candidate_id",
                        match=MatchValue(value=int(c_id))
                    )
                )
                
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        results = await asyncio.to_thread(
            client.query_points,
            collection_name=cls.COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        return results.points
