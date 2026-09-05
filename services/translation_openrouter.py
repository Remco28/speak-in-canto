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


class OpenRouterTranslationService:
    def __init__(
        self,
        api_key: str,
        model: str = "minimax/minimax-m3:free",
        base_url: str = "https://openrouter.ai/api/v1",
        site_url: str = "",
        app_name: str = "Speak in Canto",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url.strip()
        self.app_name = app_name.strip()
        self.timeout_seconds = timeout_seconds

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

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "speak-in-canto/1.0",
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-OpenRouter-Title"] = self.app_name

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
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
            raise TranslationServiceError(f"OpenRouter error {exc.code}: {detail}") from exc
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
