import time

import groq

from app.config.settings import settings
from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Per-model rate-limit budgets (from Groq console screenshots)
# Used only for log display; actual enforcement is by the API.
# ---------------------------------------------------------------------------
_MODEL_LIMITS: dict[str, dict] = {
    "openai/gpt-oss-120b":      {"tpm": 8_000,  "tpd": 200_000, "rpm": 30, "rpd": 1_000},
    "qwen/qwen3.6-27b":         {"tpm": 8_000,  "tpd": 200_000, "rpm": 30, "rpd": 1_000},
    "llama-3.3-70b-versatile":  {"tpm": 12_000, "tpd": 100_000, "rpm": 30, "rpd": 1_000},
}

# In-process daily/minute accumulators  (reset on restart; good enough for visibility)
_usage_counters: dict[str, dict] = {}


def _get_counter(model: str) -> dict:
    if model not in _usage_counters:
        _usage_counters[model] = {
            "total_input":  0,
            "total_output": 0,
            "total_calls":  0,
            "minute_tokens": 0,
            "minute_start":  time.time(),
        }
    return _usage_counters[model]


def _log_usage(model: str, usage, elapsed_ms: float) -> None:
    """
    Emits a structured, human-readable log line after every successful LLM call.
    Shows: model, prompt/completion tokens, session totals, and budget remaining.
    """
    if usage is None:
        return

    prompt_tokens     = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens      = getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)

    c = _get_counter(model)
    c["total_input"]  += prompt_tokens
    c["total_output"] += completion_tokens
    c["total_calls"]  += 1

    # Reset minute window if > 60 s have passed
    now = time.time()
    if now - c["minute_start"] > 60:
        c["minute_tokens"] = 0
        c["minute_start"]  = now
    c["minute_tokens"] += total_tokens

    limits = _MODEL_LIMITS.get(model, {})
    tpm    = limits.get("tpm", "?")
    tpd    = limits.get("tpd", "?")

    tpm_used_pct = f"{round(c['minute_tokens'] / tpm * 100, 1)}%" if isinstance(tpm, int) else "?"
    tpd_used_pct = f"{round((c['total_input'] + c['total_output']) / tpd * 100, 1)}%" if isinstance(tpd, int) else "?"

    tpm_remaining = (tpm - c["minute_tokens"]) if isinstance(tpm, int) else "?"
    tpd_remaining = (tpd - c["total_input"] - c["total_output"]) if isinstance(tpd, int) else "?"

    logger.info(
        f"\n"
        f"  ┌─── LLM Call ─────────────────────────────────────────────────\n"
        f"  │  Model       : {model}\n"
        f"  │  Latency     : {elapsed_ms:.0f} ms\n"
        f"  ├─── Token Usage (this call) ───────────────────────────────────\n"
        f"  │  Prompt      : {prompt_tokens:>7,} tokens  (input)\n"
        f"  │  Completion  : {completion_tokens:>7,} tokens  (output)\n"
        f"  │  Total       : {total_tokens:>7,} tokens\n"
        f"  ├─── Session Totals ────────────────────────────────────────────\n"
        f"  │  Calls       : {c['total_calls']}\n"
        f"  │  Input       : {c['total_input']:>7,} tokens\n"
        f"  │  Output      : {c['total_output']:>7,} tokens\n"
        f"  ├─── Rate Limit Budget ─────────────────────────────────────────\n"
        f"  │  TPM limit   : {tpm:>7}  |  used this min : {c['minute_tokens']:>7,}  |  remaining : {tpm_remaining}  ({tpm_used_pct})\n"
        f"  │  TPD limit   : {tpd:>7}  |  used today    : {c['total_input'] + c['total_output']:>7,}  |  remaining : {tpd_remaining}  ({tpd_used_pct})\n"
        f"  └───────────────────────────────────────────────────────────────"
    )


class RobustCompletions:
    """
    Wrapper for chat completions with built-in automatic model fallback
    and rich per-call token-usage logging.
    """

    def __init__(self, raw_client: groq.Groq):
        self.raw_client = raw_client

    def create(self, *args, **kwargs):
        # Load ordered list of models from settings
        models_to_try: list[str] = []
        if settings.llm_fallback_models:
            models_to_try = [m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()]

        # Hard-coded fallback if settings is empty
        if not models_to_try:
            models_to_try = [
                "openai/gpt-oss-120b",
                "qwen/qwen3.6-27b",
                settings.groq_chat_model or "llama-3.3-70b-versatile",
            ]

        # If the caller already pinned a model not in the list, honour it first
        user_model = kwargs.get("model")
        if user_model and user_model not in models_to_try:
            models_to_try.insert(0, user_model)

        last_error = None
        for model in models_to_try:
            kwargs["model"] = model
            logger.info(f"RobustLLM ▶  Calling model '{model}' ...")
            t0 = time.perf_counter()
            try:
                response = self.raw_client.chat.completions.create(*args, **kwargs)
                elapsed = (time.perf_counter() - t0) * 1000

                # Log rich token usage
                usage = getattr(response, "usage", None)
                _log_usage(model, usage, elapsed)

                logger.info(f"RobustLLM ✓  '{model}' succeeded in {elapsed:.0f} ms")
                return response

            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.warning(
                    f"RobustLLM ✗  '{model}' failed after {elapsed:.0f} ms → {type(e).__name__}: {e}\n"
                    f"             Falling back to next model in chain..."
                )
                last_error = e

        logger.error("RobustLLM ✗✗  ALL configured models failed. No more fallbacks available.")
        if last_error:
            raise last_error
        raise RuntimeError("RobustLLM: No models succeeded, but no error was caught.")


class RobustChat:
    def __init__(self, raw_client: groq.Groq):
        self.completions = RobustCompletions(raw_client)


class RobustLLMClient:
    """
    Drop-in wrapper for the Groq client with automatic fallback + rich logging.
    """

    def __init__(self, api_key: str | None = None):
        api_key = api_key or settings.groq_api_key
        self._raw_client = groq.Groq(
            api_key=api_key,
            base_url=settings.llm_base_url,
        )
        self.chat = RobustChat(self._raw_client)


class GroqProvider:
    """Single Responsibility: Manages robust Groq client creation."""

    _client: RobustLLMClient | None = None

    @classmethod
    def get_client(cls) -> RobustLLMClient:
        if cls._client is None:
            cls._client = RobustLLMClient()
        return cls._client
