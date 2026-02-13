from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable

try:
    import pycantonese as pc
except Exception:  # pragma: no cover - handled at runtime
    pc = None


SENTENCE_BREAKS = {"。", "！", "？", "!", "?"}
CLAUSE_BREAKS = {"，", ",", "；", ";", "：", ":"}


@dataclass(slots=True)
class Token:
    token_id: int
    char: str
    raw_index: int
    jyutping: str


@dataclass(slots=True)
class ChunkBuildResult:
    ssml: str
    mark_to_token: dict[str, int]
    mark_count: int


class SSMLBuilder:
    def normalize_text(self, text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    def build_tokens(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        for idx, char in enumerate(text):
            tokens.append(Token(token_id=idx, char=char, raw_index=idx, jyutping=""))
        self._attach_jyutping(tokens)
        return tokens

    def build_token_chunks(
        self,
        tokens: list[Token],
        mode: str,
        target_max_bytes: int = 4200,
        hard_max_bytes: int = 5000,
    ) -> list[list[Token]]:
        if not tokens:
            return []

        segments = self._split_segments(tokens)
        chunks: list[list[Token]] = []
        current: list[Token] = []

        for segment in segments:
            if not segment:
                continue

            candidate = current + segment
            if self._chunk_size(candidate, mode) <= target_max_bytes:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = []

            if self._chunk_size(segment, mode) <= target_max_bytes:
                current = segment
                continue

            for token in segment:
                candidate = current + [token]
                size = self._chunk_size(candidate, mode)
                if size <= target_max_bytes:
                    current = candidate
                    continue

                if not current:
                    # A single token should never hit this, but enforce hard safety.
                    if size > hard_max_bytes:
                        raise ValueError("Token cannot fit into hard SSML byte limit")
                    current = [token]
                    continue

                chunks.append(current)
                current = [token]

                if self._chunk_size(current, mode) > hard_max_bytes:
                    raise ValueError("Chunk cannot fit into hard SSML byte limit")

        if current:
            chunks.append(current)

        for chunk in chunks:
            if self._chunk_size(chunk, mode) > hard_max_bytes:
                raise ValueError("Chunk cannot fit into hard SSML byte limit")

        return chunks

    def build_ssml_for_chunk(self, tokens: Iterable[Token], mode: str) -> ChunkBuildResult:
        mark_to_token: dict[str, int] = {}
        parts: list[str] = ["<speak>"]

        for token in tokens:
            if self._should_mark(token, mode):
                mark_name = f"c_{token.token_id}"
                parts.append(f'<mark name="{mark_name}"/>')
                mark_to_token[mark_name] = token.token_id
            parts.append(escape(token.char))

        parts.append("</speak>")
        ssml = "".join(parts)
        return ChunkBuildResult(ssml=ssml, mark_to_token=mark_to_token, mark_count=len(mark_to_token))

    def _split_segments(self, tokens: list[Token]) -> list[list[Token]]:
        segments: list[list[Token]] = []
        current: list[Token] = []

        for token in tokens:
            current.append(token)
            if token.char in SENTENCE_BREAKS or token.char in CLAUSE_BREAKS:
                segments.append(current)
                current = []

        if current:
            segments.append(current)

        return segments

    def _chunk_size(self, tokens: list[Token], mode: str) -> int:
        chunk = self.build_ssml_for_chunk(tokens, mode)
        return len(chunk.ssml.encode("utf-8"))

    def _should_mark(self, token: Token, mode: str) -> bool:
        if token.char.isspace():
            return False

        if mode == "full":
            return True

        if mode == "reduced":
            return self._is_cjk(token.char) or token.char in SENTENCE_BREAKS

        raise ValueError(f"Unknown sync mode: {mode}")

    def _attach_jyutping(self, tokens: list[Token]) -> None:
        if pc is None:
            return

        for token in tokens:
            if not self._is_cjk(token.char):
                continue

            try:
                value = pc.characters_to_jyutping(token.char)
                if isinstance(value, list) and value:
                    first = value[0]
                    if isinstance(first, tuple) and len(first) >= 2:
                        token.jyutping = str(first[1] or "")
                    else:
                        token.jyutping = str(first or "")
                else:
                    token.jyutping = ""
            except Exception:
                token.jyutping = ""

    def _is_cjk(self, char: str) -> bool:
        code = ord(char)
        return (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x2CEAF
        )
