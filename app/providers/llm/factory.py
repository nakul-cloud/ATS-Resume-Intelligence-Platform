from app.providers.llm.groq_provider import GroqProvider, RobustLLMClient


class LLMFactory:
    """
    The Orchestrator Factory.
    Provides robust, fallback-enabled LLM clients for the application.
    """

    @staticmethod
    def get_robust_llm() -> RobustLLMClient:
        """
        Returns a client configured with automatic fallback between:
        - openai/gpt-oss-120b (Primary)
        - qwen/qwen3.6-27b (Backup)
        - settings.groq_chat_model (Safety net)
        """
        return GroqProvider.get_client()


def get_groq_client() -> RobustLLMClient:
    """
    Global convenience helper to get the fallback-enabled robust Groq client.
    """
    return LLMFactory.get_robust_llm()
