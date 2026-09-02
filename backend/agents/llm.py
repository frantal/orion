"""Minimal, provider-agnostic LLM client (OpenAI-compatible chat completions).

The LLM is optional. When it is not configured, callers must fall back to the
deterministic layer. The client only ever returns validated JSON; any transport
error raises :class:`LLMUnavailableError` and any schema mismatch raises
:class:`LLMOutputValidationError`. Only structured, ORION-generated numeric data
is ever sent — never raw third-party text — which limits prompt-injection risk.
"""

from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from backend.core.config import Settings, get_settings
from backend.core.exceptions import LLMOutputValidationError, LLMUnavailableError
from backend.core.logging import get_logger

logger = get_logger("agents.llm")

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Thin async wrapper over an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def available(self) -> bool:
        return self._settings.llm_configured

    async def complete_json(self, system_prompt: str, user_payload: dict, schema: type[T]) -> T:
        """Request a JSON completion and validate it against ``schema``."""
        if not self.available:
            raise LLMUnavailableError("LLM is not configured.")

        body = {
            "model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"LLM request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMUnavailableError(f"LLM error {resp.status_code}: {resp.text[:200]}")

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailableError("Malformed LLM response envelope") from exc

        return self.validate(content, schema)

    @staticmethod
    def validate(content: str, schema: type[T]) -> T:
        """Parse ``content`` as JSON and validate against ``schema``. Rejects on failure."""
        try:
            data = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise LLMOutputValidationError("LLM output is not valid JSON") from exc
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            logger.warning("LLM output rejected", extra={"errors": exc.error_count()})
            raise LLMOutputValidationError(f"LLM output failed validation: {exc}") from exc
