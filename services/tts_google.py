from __future__ import annotations

import json
import os
from dataclasses import dataclass
from time import time

from google.api_core import exceptions as gexceptions
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.oauth2 import service_account


class TTSServiceError(Exception):
    pass


@dataclass(slots=True)
class SynthesisChunk:
    audio_content: bytes
    timepoints: list[dict[str, float]]


class GoogleTTSWrapper:
    MODE_STANDARD = "standard"
    MODE_HIGH_QUALITY = "high_quality"
    DEFAULT_FALLBACK_VOICE = "yue-HK-Standard-A"
    STANDARD_VOICES = {
        "yue-HK-Standard-A",
        "yue-HK-Standard-B",
        "yue-HK-Standard-C",
        "yue-HK-Standard-D",
    }
    _VOICE_CACHE_TTL_SECONDS = 300
    _voice_catalog_cache: dict[str, list[dict[str, str]]] | None = None
    _voice_catalog_cache_at: float = 0.0

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._client: texttospeech.TextToSpeechClient | None = None

    @classmethod
    def get_voice_catalog(cls) -> dict[str, list[dict[str, str]]]:
        now = time()
        if cls._voice_catalog_cache and (now - cls._voice_catalog_cache_at) < cls._VOICE_CACHE_TTL_SECONDS:
            return cls._voice_catalog_cache

        standard = [{"id": name, "label": name.replace("yue-HK-", "")} for name in sorted(cls.STANDARD_VOICES)]
        high_quality: list[dict[str, str]] = []

        try:
            client = cls()._get_client()
            voices = client.list_voices(language_code="yue-HK").voices
            for voice in voices:
                name = voice.name
                if not name.startswith("yue-HK-Chirp3-HD-"):
                    continue
                star = name.replace("yue-HK-Chirp3-HD-", "")
                high_quality.append({"id": name, "label": f"Chirp 3 HD - {star}"})
        except Exception:
            high_quality = []

        high_quality = sorted(high_quality, key=lambda item: item["label"])
        cls._voice_catalog_cache = {"standard": standard, "high_quality": high_quality}
        cls._voice_catalog_cache_at = now
        return cls._voice_catalog_cache

    def validate_voice(self, voice_name: str, voice_mode: str) -> bool:
        catalog = self.get_voice_catalog()
        if voice_mode == self.MODE_STANDARD:
            return voice_name in self.STANDARD_VOICES
        if voice_mode == self.MODE_HIGH_QUALITY:
            return any(voice["id"] == voice_name for voice in catalog["high_quality"])
        return False

    def synthesize_ssml(self, ssml: str, voice_name: str, speaking_rate: float) -> SynthesisChunk:
        if voice_name not in self.STANDARD_VOICES:
            raise TTSServiceError("Unsupported voice")

        input_text = texttospeech.SynthesisInput(ssml=ssml)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
        )

        def _request_for(voice: str):
            return {
                "input": input_text,
                "voice": texttospeech.VoiceSelectionParams(language_code="yue-HK", name=voice),
                "audio_config": audio_config,
                "enable_time_pointing": [texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK],
            }

        try:
            response = self._get_client().synthesize_speech(
                request=_request_for(voice_name),
                timeout=self.timeout_seconds,
            )
        except gexceptions.InvalidArgument as exc:
            # Some regions/projects do not expose every documented voice. Retry once with fallback.
            if voice_name != self.DEFAULT_FALLBACK_VOICE and "does not exist" in str(exc).lower():
                response = self._get_client().synthesize_speech(
                    request=_request_for(self.DEFAULT_FALLBACK_VOICE),
                    timeout=self.timeout_seconds,
                )
            else:
                raise TTSServiceError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - external SDK behavior
            raise TTSServiceError(str(exc)) from exc

        points = []
        for point in response.timepoints:
            points.append({"mark_name": point.mark_name, "seconds": float(point.time_seconds)})

        return SynthesisChunk(audio_content=response.audio_content, timepoints=points)

    def synthesize_text(self, text: str, voice_name: str) -> SynthesisChunk:
        if not self.validate_voice(voice_name, self.MODE_HIGH_QUALITY):
            raise TTSServiceError("Unsupported high quality voice")

        try:
            response = self._get_client().synthesize_speech(
                request={
                    "input": texttospeech.SynthesisInput(text=text),
                    "voice": texttospeech.VoiceSelectionParams(language_code="yue-HK", name=voice_name),
                    "audio_config": texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3),
                },
                timeout=self.timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - external SDK behavior
            raise TTSServiceError(str(exc)) from exc

        return SynthesisChunk(audio_content=response.audio_content, timepoints=[])

    def _get_client(self) -> texttospeech.TextToSpeechClient:
        if self._client is not None:
            return self._client

        json_value = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
        if json_value:
            info = json.loads(json_value)
            credentials = service_account.Credentials.from_service_account_info(info)
            self._client = texttospeech.TextToSpeechClient(credentials=credentials)
            return self._client

        # Falls back to GOOGLE_APPLICATION_CREDENTIALS / ADC.
        self._client = texttospeech.TextToSpeechClient()
        return self._client
