from __future__ import annotations

import json
import os
from dataclasses import dataclass

from google.cloud import texttospeech
from google.oauth2 import service_account


class TTSServiceError(Exception):
    pass


@dataclass(slots=True)
class SynthesisChunk:
    audio_content: bytes
    timepoints: list[dict[str, float]]


class GoogleTTSWrapper:
    ALLOWED_VOICES = {
        "yue-HK-Neural2-A",
        "yue-HK-Neural2-B",
        "yue-HK-Neural2-C",
        "yue-HK-Neural2-D",
    }

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._client: texttospeech.TextToSpeechClient | None = None

    def validate_voice(self, voice_name: str) -> bool:
        return voice_name in self.ALLOWED_VOICES

    def synthesize_ssml(self, ssml: str, voice_name: str, speaking_rate: float) -> SynthesisChunk:
        if not self.validate_voice(voice_name):
            raise TTSServiceError("Unsupported voice")

        input_text = texttospeech.SynthesisInput(ssml=ssml)
        voice = texttospeech.VoiceSelectionParams(language_code="yue-HK", name=voice_name)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
        )

        try:
            response = self._get_client().synthesize_speech(
                request={
                    "input": input_text,
                    "voice": voice,
                    "audio_config": audio_config,
                    "enable_time_pointing": [texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK],
                },
                timeout=self.timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - external SDK behavior
            raise TTSServiceError(str(exc)) from exc

        points = []
        for point in response.timepoints:
            points.append({"mark_name": point.mark_name, "seconds": float(point.time_seconds)})

        return SynthesisChunk(audio_content=response.audio_content, timepoints=points)

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
