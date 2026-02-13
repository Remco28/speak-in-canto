from __future__ import annotations

import json
import socket
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


class GrokTranslationService:
    def __init__(
        self,
        api_key: str,
        model: str = "grok-4-1-fast-non-reasoning",
        base_url: str = "https://api.x.ai/v1",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def translate_to_english(self, text: str) -> TranslationResult:
        if not self.api_key:
            raise TranslationServiceError("GROK_API_KEY is not configured.")

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
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

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
            raise TranslationServiceError(f"Upstream error {exc.code}: {detail}") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise TranslationTimeoutError("Translation request timed out.") from exc
        except error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), socket.timeout):
                raise TranslationTimeoutError("Translation request timed out.") from exc
            raise TranslationServiceError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - runtime/network edge behavior
            raise TranslationServiceError(str(exc)) from exc

        translation = _extract_translation(parsed)
        if not translation:
            raise TranslationServiceError("Translation response was empty.")

        return TranslationResult(translation=translation, provider="grok", model=self.model)


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
