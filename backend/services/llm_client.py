"""
Provider-agnostic LLM client using the OpenAI-compatible SDK.

Supports Google Gemini and Groq with automatic fallback.
Uses structured output (JSON schema) for reliable parsing.
"""

import json
import logging
import asyncio
from typing import TypeVar, Type

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
from pydantic import BaseModel, ValidationError

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ─── Provider Configuration ──────────────────────────────────────────────────


class ProviderConfig:
    """Configuration for a single LLM provider."""

    def __init__(self, name: str, api_key: str, base_url: str, model: str, timeout: float = 30.0):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)


def _build_providers() -> list[ProviderConfig]:
    """Build the ordered list of LLM providers based on available API keys."""
    providers = []

    if settings.has_gemini:
        providers.append(ProviderConfig(
            name="gemini",
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model=settings.gemini_model,
        ))

    if settings.has_groq:
        providers.append(ProviderConfig(
            name="groq",
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model=settings.groq_model,
        ))

    return providers


# ─── LLM Client ──────────────────────────────────────────────────────────────


class LLMClient:
    """
    Provider-agnostic LLM client with structured output and automatic fallback.
    
    Uses the OpenAI SDK which is compatible with both Gemini and Groq APIs.
    Enforces structured JSON output via Pydantic schemas.
    """

    def __init__(self):
        self.providers = _build_providers()
        if not self.providers:
            logger.warning(
                "No LLM API keys configured. Set GEMINI_API_KEY or GROQ_API_KEY."
            )

    @property
    def is_available(self) -> bool:
        return len(self.providers) > 0

    def get_provider_status(self) -> dict[str, bool]:
        """Return which providers are configured."""
        return {
            "gemini": settings.has_gemini,
            "groq": settings.has_groq,
        }

    async def structured_completion(
        self,
        messages: list[dict],
        response_schema: Type[T],
        temperature: float | None = None,
    ) -> T:
        """
        Call the LLM with structured output enforcement.
        
        Tries each provider in order. On failure, falls back to the next.
        Validates the response against the Pydantic schema.
        
        Args:
            messages: Chat messages (system + user)
            response_schema: Pydantic model class for the expected output
            temperature: Override default temperature (0.0 for deterministic)
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            LLMError: If all providers fail after retries
        """
        if not self.providers:
            raise LLMError("No LLM providers configured")

        temp = temperature if temperature is not None else settings.llm_temperature
        last_error = None

        for provider in self.providers:
            for attempt in range(settings.llm_max_retries + 1):
                try:
                    result = await self._call_provider(
                        provider, messages, response_schema, temp
                    )
                    return result
                except RateLimitError as e:
                    last_error = e
                    logger.warning(
                        f"[{provider.name}] Rate limit (429) hit, switching to next provider: {e}"
                    )
                    break
                except (APIError, APIConnectionError, APITimeoutError, TimeoutError, asyncio.TimeoutError, ValidationError) as e:
                    last_error = e
                    logger.warning(
                        f"[{provider.name}] Attempt {attempt + 1} error: {e}"
                    )
                    if attempt < settings.llm_max_retries:
                        await asyncio.sleep(1)
                    continue
                except Exception as e:
                    last_error = e
                    logger.warning(f"[{provider.name}] Unexpected error: {e}")
                    break

            logger.error(f"[{provider.name}] Provider failed, trying next provider...")

        raise LLMError(f"All LLM providers failed. Last error: {last_error}")

    async def _call_provider(
        self,
        provider: ProviderConfig,
        messages: list[dict],
        response_schema: Type[T],
        temperature: float,
    ) -> T:
        """Make a single call to a provider and validate the response."""
        schema = response_schema.model_json_schema()

        # Build completion kwargs
        kwargs = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
        }

        # Add structured output based on provider
        if provider.name == "gemini":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": schema,
                },
            }
        elif provider.name == "groq":
            kwargs["response_format"] = {
                "type": "json_object",
            }
            # For Groq, inject schema into the system message
            schema_instruction = (
                f"\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```"
            )
            messages = messages.copy()
            if messages and messages[0]["role"] == "system":
                messages[0] = {
                    **messages[0],
                    "content": messages[0]["content"] + schema_instruction,
                }
            else:
                messages.insert(0, {"role": "system", "content": schema_instruction})
            kwargs["messages"] = messages

        logger.info(f"[{provider.name}] Calling {provider.model}...")
        response = await provider.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        if not content:
            raise APIError("Empty response from LLM")

        # Parse and validate
        try:
            result = response_schema.model_validate_json(content)
        except ValidationError:
            # Try to extract JSON from markdown code blocks
            json_match = _extract_json(content)
            if json_match:
                result = response_schema.model_validate_json(json_match)
            else:
                raise

        logger.info(f"[{provider.name}] Success - validated {response_schema.__name__}")
        return result


def _extract_json(text: str) -> str | None:
    """Try to extract JSON from text that might be wrapped in markdown code blocks."""
    import re
    # Try ```json ... ``` blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


class LLMError(Exception):
    """Raised when all LLM providers fail."""
    pass


# ─── Singleton ───────────────────────────────────────────────────────────────

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
