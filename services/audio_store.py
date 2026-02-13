from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass(slots=True)
class StoredAudio:
    filename: str
    url: str
    bytes_size: int


class AudioStore:
    def __init__(self, root_dir: str = "static/temp_audio") -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_audio(self, content: bytes) -> StoredAudio:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        filename = f"tts_{timestamp}_{uuid.uuid4().hex[:12]}.mp3"
        path = self.root / filename
        path.write_bytes(content)
        return StoredAudio(
            filename=filename,
            url=f"/static/temp_audio/{filename}",
            bytes_size=len(content),
        )

    def cleanup(
        self,
        ttl_hours: int = 4,
        max_files: int = 120,
        max_bytes: int = 300 * 1024 * 1024,
    ) -> dict[str, int]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=ttl_hours)

        deleted = 0
        files = self._list_audio_files()

        # TTL pass first
        for path in files:
            if datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1

        files = self._list_audio_files()

        # High-watermark pass by oldest-first eviction
        while files and (len(files) > max_files or self._total_bytes(files) > max_bytes):
            oldest = files[0]
            oldest.unlink(missing_ok=True)
            deleted += 1
            files = self._list_audio_files()

        return {
            "remaining_files": len(files),
            "remaining_bytes": self._total_bytes(files),
            "deleted_files": deleted,
        }

    def _list_audio_files(self) -> list[Path]:
        return sorted(
            [p for p in self.root.glob("*.mp3") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
        )

    def _total_bytes(self, files: list[Path]) -> int:
        total = 0
        for path in files:
            total += path.stat().st_size
        return total
