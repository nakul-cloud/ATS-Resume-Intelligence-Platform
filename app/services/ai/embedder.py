from __future__ import annotations

import asyncio

from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.utils.logger import logger
from app.utils.text_builder import build_embedding_text


class EmbeddingService:
    """
    Centralized embedding service following the Single Responsibility Principle.

    Responsibilities:
    - Lazily loading and caching the SentenceTransformer model (singleton).
    - Encoding raw text strings into dense float vectors.
    - Building normalized embedding text from structured candidate dictionaries.

    This service is intentionally stateless beyond the cached model instance,
    making it safe to use as a shared dependency across all services that
    require vector generation (ResumeService, EvaluationService, etc.).
    """

    _model: SentenceTransformer | None = None

    # ---------------------------------------------------------------------------
    # Model Management
    # ---------------------------------------------------------------------------

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """
        Lazily initializes and returns the global singleton SentenceTransformer model.
        The model is loaded only once on first use and re-used across all calls.
        """
        if cls._model is None:
            logger.info(
                f"[EmbeddingService] Loading SentenceTransformer model "
                f"({settings.embedding_model_name})..."
            )
            cls._model = SentenceTransformer(settings.embedding_model_name)
            logger.info("[EmbeddingService] Model loaded and cached successfully.")
        return cls._model

    # ---------------------------------------------------------------------------
    # Encoding
    # ---------------------------------------------------------------------------

    @classmethod
    def encode_text(cls, text: str) -> list[float]:
        """
        Encodes a plain text string into a dense float vector synchronously.

        Args:
            text: The raw text string to encode.

        Returns:
            A list of floats representing the semantic embedding vector.
        """
        model = cls.get_model()
        return model.encode(text).tolist()

    @classmethod
    async def encode_text_async(cls, text: str) -> list[float]:
        """
        Asynchronous wrapper around encode_text() to avoid blocking the event loop.
        Uses asyncio.to_thread() to run the CPU-bound encode in a thread pool executor.

        Args:
            text: The raw text string to encode.

        Returns:
            A list of floats representing the semantic embedding vector.
        """
        return await asyncio.to_thread(cls.encode_text, text)

    @classmethod
    def encode_candidate(cls, candidate_dict: dict) -> tuple[list[float], str]:
        """
        Builds a normalized candidate profile text from a structured dictionary
        and encodes it into a dense float vector.

        Args:
            candidate_dict: A dictionary with standard candidate profile keys
                            (primary_role_title, primary_domain, total_experience_years,
                             highest_education, summary_text, skills_text).

        Returns:
            A tuple of (vector, profile_text) where:
            - vector: Dense float embedding vector for Qdrant indexing.
            - profile_text: The normalized string used for embedding (useful for logging).
        """
        profile_text = build_embedding_text(candidate_dict)
        vector = cls.encode_text(profile_text)
        return vector, profile_text

    @classmethod
    async def encode_candidate_async(
        cls, candidate_dict: dict
    ) -> tuple[list[float], str]:
        """
        Async wrapper around encode_candidate() to avoid blocking the event loop.
        """
        profile_text = build_embedding_text(candidate_dict)
        vector = await cls.encode_text_async(profile_text)
        return vector, profile_text
