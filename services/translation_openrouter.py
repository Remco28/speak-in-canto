from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from urllib import error, request


class TranslationServiceError(Exception):
    pass


class TranslationTimeoutError(TranslationServiceError):
    pass


@dataclass(slots=True)
class TranslationResult:
    translation: str
    provider: str
    model: str


class OpenRouterTranslationService:
    RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})

    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/free",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

    def translate_to_english(self, text: str) -> TranslationResult:
        if not self.api_key:
            raise TranslationServiceError("OPENROUTER_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Translate the user's text to natural English. Return only the translation.",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        }

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "canto-reader/1.0",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        # Bounded retry for transient failures only (timeouts, connection
        # errors, 429/5xx). Total added time is capped at
        # retry_backoff_seconds * (2 ** max_retries) plus the per-attempt
        # timeouts, so request time cannot grow unbounded.
        last_error: Exception | None = None
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = resp.read().decode("utf-8")
                    parsed = json.loads(body)
            except error.HTTPError as exc:
                detail = ""
                try:
                    detail_body = exc.read().decode("utf-8")
                    detail = detail_body[:300]
                except Exception:
                    detail = str(exc)
                if exc.code == 403 and "1010" in detail:
                    raise TranslationServiceError(
                        "Forbidden by upstream edge (403/1010). Check API key permissions/team access and network egress."
                    ) from exc
                if exc.code in self.RETRYABLE_HTTP_STATUS and attempt < self.max_retries:
                    last_error = TranslationServiceError(f"Upstream error {exc.code}: {detail}")
                    try:
                        exc.close()
                    except Exception:
                        pass
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                raise TranslationServiceError(f"Upstream error {exc.code}: {detail}") from exc
            except (socket.timeout, TimeoutError) as exc:
                if attempt < self.max_retries:
                    last_error = TranslationTimeoutError("Translation request timed out.")
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                raise TranslationTimeoutError("Translation request timed out.") from exc
            except error.URLError as exc:
                if isinstance(getattr(exc, "reason", None), socket.timeout):
                    if attempt < self.max_retries:
                        last_error = TranslationTimeoutError("Translation request timed out.")
                        time.sleep(self.retry_backoff_seconds * (2**attempt))
                        continue
                    raise TranslationTimeoutError("Translation request timed out.") from exc
                if attempt < self.max_retries:
                    last_error = TranslationServiceError(str(exc))
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                raise TranslationServiceError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - runtime/network edge behavior
                raise TranslationServiceError(str(exc)) from exc
            break
        else:  # pragma: no cover - defensive; loop always breaks or raises
            raise TranslationServiceError(str(last_error) if last_error else "Translation failed.")

        translation = _extract_translation(parsed)
        if not translation:
            raise TranslationServiceError("Translation response was empty.")

        return TranslationResult(translation=translation, provider="openrouter", model=self.model)


def _extract_translation(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first = choices[0] or {}
    message = first.get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()

    return ""
