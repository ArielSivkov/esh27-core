# backend/models/vertex_llm.py
"""
Async Vertex AI wrapper for the esh27-core microservice.

Features:
- Uses Vertex AI (google-cloud-aiplatform and vertexai SDK) to call Gemini 2.5 Flash (gemini-2.5-flash).
- Exposes an async generate_async(...) coroutine that maps a GenerateRequest directly to Vertex generate calls
  using asyncio.run_in_executor (to run the blocking Vertex SDK calls in a threadpool).
- In-memory TTL context cache (cachetools.TTLCache) to maintain conversation continuity and reduce token cost.
- Regex output sanitizer to strip "Agent:", "System:", and "Assistant:" prefixes.
- Tenacity retries for transient errors.
- Pydantic request/response models included for convenience.
"""

from __future__ import annotations

import os
import re
import uuid
import logging
import asyncio
import threading
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from cachetools import TTLCache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Vertex AI SDKs
# google-cloud-aiplatform is required for credentialing and aiplatform init.
# vertexai contains the TextGenerationModel convenience wrapper.
try:
    from google.cloud import aiplatform
    import vertexai
    from vertexai.preview.language_models import TextGenerationModel
except Exception:
    # Import errors will surface at runtime if dependencies are not installed.
    aiplatform = None
    vertexai = None
    TextGenerationModel = None  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# --------------------
# Pydantic models
# --------------------
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="User prompt / message text")
    mode: Optional[str] = Field("chat", description="Mode of generation, e.g., 'chat' or 'completion'")
    language: Optional[str] = Field("en", description="Language code (ISO), e.g., 'en', 'fr')
    length: Optional[int] = Field(256, ge=1, le=65536, description="Approx maximum output tokens to generate")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context continuity")
    model: Optional[str] = Field("gemini-2.5-flash", description="Model identifier to use (defaults to Gemini 2.5 Flash)")


class GenerateUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class GenerateResponse(BaseModel):
    id: str
    model: str
    text: str
    sanitized_text: str
    usage: Optional[GenerateUsage] = None
    meta: Optional[Dict[str, Any]] = None


# --------------------
# VertexLLM implementation
# --------------------
class VertexLLM:
    """
    Async wrapper around Vertex AI text generation (Gemini family).

    Usage:
        llm = VertexLLM(project=os.getenv("GCP_PROJECT"), region="us-central1")
        response = await llm.generate_async(GenerateRequest(prompt="Hello"))
    """

    # default TTL: 15 minutes for conversation context, size limit for memory
    DEFAULT_CONTEXT_TTL_SECONDS = int(os.getenv("CONTEXT_TTL_SECONDS", "900"))
    DEFAULT_CONTEXT_MAX_ITEMS = int(os.getenv("CONTEXT_MAX_ITEMS", "1024"))

    SANITIZE_RE = re.compile(r"(?mi)^(?:Agent:|System:|Assistant:)\s*", flags=re.MULTILINE)

    def __init__(self, project: Optional[str] = None, region: Optional[str] = None, cache: TTLCache | None = None):
        self.project = project or os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region or os.getenv("GCP_REGION", "us-central1")
        self.model_name_default = "gemini-2.5-flash"

        # Initialize vertex / aiplatform if available
        if aiplatform is not None:
            try:
                # aiplatform.init is idempotent, safe to call multiple times
                aiplatform.init(project=self.project, location=self.region)
                # also initialize the vertexai helper package
                if vertexai is not None:
                    vertexai.init(project=self.project, location=self.region)
            except Exception as e:
                logger.warning("Failed to initialize Vertex AI SDK: %s", e)

        # TTL cache for conversation context (protect with lock for thread-safety)
        self._cache = cache or TTLCache(maxsize=self.DEFAULT_CONTEXT_MAX_ITEMS, ttl=self.DEFAULT_CONTEXT_TTL_SECONDS)
        self._cache_lock = threading.RLock()

        # Thread pool executor will be used implicitly by asyncio.run_in_executor (default executor)
        # We can optionally create our own executor in future to limit concurrency.

    # --------------------
    # Sanitizer
    # --------------------
    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """
        Remove agent-like prefixes from the output to ensure we return user-facing content.
        Strips leading "Agent:", "System:", and "Assistant:" on any line.
        """
        if not text:
            return text
        sanitized = cls.SANITIZE_RE.sub("", text)
        # Clean up excessive whitespace/newlines resulting from removals
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized).strip()
        return sanitized

    # --------------------
    # Context cache helpers
    # --------------------
    def _get_context(self, conversation_id: str) -> str:
        with self._cache_lock:
            return self._cache.get(conversation_id, "")

    def _update_context(self, conversation_id: str, new_messages: str) -> None:
        with self._cache_lock:
            prev = self._cache.get(conversation_id, "")
            # Simple concatenation. Real systems may want structured turns and token trimming.
            combined = (prev + "\n" + new_messages).strip() if prev else new_messages
            self._cache[conversation_id] = combined

    # --------------------
    # Token / cost helpers (heuristic)
    # --------------------
    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Very rough heuristic: 1 token ≈ 4 characters for typical English text
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    @staticmethod
    def estimate_cost_usd(model: str, tokens: int) -> float:
        # Placeholder: estimate cost using a tiny assumed price-per-1k-tokens for Gemini family.
        # In production replace with accurate pricing lookup.
        price_per_1k = 0.03  # USD per 1k tokens -- conservative placeholder
        return (tokens / 1000.0) * price_per_1k

    # --------------------
    # Internal blocking generate (wrapped with tenacity retry)
    # --------------------
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(Exception),
    )
    def _generate_sync(self, prompt: str, model_name: str, max_output_tokens: int, language: str, mode: str) -> Dict[str, Any]:
        """
        Blocking call to Vertex AI text generation. Wrapped with retries.
        Executed in a thread via asyncio.run_in_executor from async wrapper.
        Returns a dict with keys: 'text' and 'meta' (the raw SDK response if available).
        """
        logger.debug("Starting blocking Vertex generate call (model=%s, tokens=%d)", model_name, max_output_tokens)
        if TextGenerationModel is None:
            raise RuntimeError("Vertex SDK not available: ensure 'vertexai' package is installed.")

        # Build a prompt envelope depending on mode; this helps keep chat vs completion behavior explicit.
        if mode and mode.lower().startswith("chat"):
            # For chat mode, we may prepend a short system instruction about language
            system_prefix = f"[System language={language}]\n" if language else ""
            effective_prompt = f"{system_prefix}{prompt}"
        else:
            effective_prompt = prompt

        # Load the model (the SDK caches model clients, so this is lightweight after first call)
        try:
            model = TextGenerationModel.from_pretrained(model_name)
        except Exception as e:
            # Log and re-raise so retry can occur
            logger.exception("Failed to load model %s: %s", model_name, e)
            raise

        # Vertex TextGenerationModel.generate parameters:
        #   - prompt or input: we will provide prompt
        #   - max_output_tokens: controls output length
        #   - temperature, top_p, etc. could be parameterized
        try:
            # This call is blocking (network + IO). We run in executor from async wrapper.
            generation = model.generate(
                prompt=effective_prompt,
                max_output_tokens=max_output_tokens,
                temperature=0.2,
                top_p=0.95,
                # Other generation params can be added here
            )
        except Exception as e:
            logger.exception("Vertex generate failed: %s", e)
            raise

        # generation.text contains the text string in the current SDK; the object may vary by SDK version.
        text = getattr(generation, "text", None)
        # Fallback: convert to str
        if text is None:
            text = str(generation)

        return {"text": text, "meta": {"sdk_response": generation}}

    # --------------------
    # Public async API
    # --------------------
    async def generate_async(self, request: GenerateRequest) -> GenerateResponse:
        """
        Asynchronous entry point. Accepts GenerateRequest and returns GenerateResponse.
        The blocking Vertex SDK call runs via asyncio.get_running_loop().run_in_executor.
        """
        # Validate and set defaults
        model_name = request.model or self.model_name_default
        max_output_tokens = int(request.length or 256)
        mode = (request.mode or "chat").lower()
        language = request.language or "en"
        prompt = request.prompt or ""

        # Build prompt with conversation context if provided
        conversation_id = request.conversation_id
        if conversation_id:
            # Append cached context to the prompt; for cost reasons, ensure we don't overgrow tokens in production
            context = self._get_context(conversation_id)
            if context:
                # We append context as a prefix to the current prompt to provide continuity.
                # In production you'd format this better (timestamps, turn separators, token trimming).
                prompt_with_context = f"{context}\n\nUser: {prompt}"
            else:
                prompt_with_context = f"User: {prompt}"
        else:
            prompt_with_context = prompt

        # Run blocking generate in executor
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._generate_sync(prompt_with_context, model_name, max_output_tokens, language, mode)
            )
        except Exception as exc:
            logger.exception("Generation failed for model %s: %s", model_name, exc)
            raise

        raw_text = result.get("text", "")
        sanitized = self.sanitize_output(raw_text)

        # Update conversation context if requested
        if conversation_id:
            # For simplicity add the prompt + sanitized reply to the context
            context_append = f"User: {prompt}\nAssistant: {sanitized}"
            try:
                self._update_context(conversation_id, context_append)
            except Exception:
                logger.exception("Failed to update conversation cache for %s", conversation_id)

        # Heuristic usage estimation
        prompt_tokens = self.estimate_tokens(prompt_with_context)
        completion_tokens = self.estimate_tokens(raw_text)
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.estimate_cost_usd(model_name, total_tokens)

        usage = GenerateUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
        )

        response = GenerateResponse(
            id=str(uuid.uuid4()),
            model=model_name,
            text=raw_text,
            sanitized_text=sanitized,
            usage=usage,
            meta={"raw_meta": "<SDK response object available in server logs>", **({"sdk_meta": None} if result.get("meta") is None else {})},
        )

        return response


# Create a module-level default instance for quick imports
_default_llm: Optional[VertexLLM] = None


def get_default_llm() -> VertexLLM:
    global _default_llm
    if _default_llm is None:
        _default_llm = VertexLLM()
    return _default_llm
