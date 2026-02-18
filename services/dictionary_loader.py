from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_LINE_RE = re.compile(
    r"^(?P<trad>\S+)\s+(?P<simp>\S+)\s+\[(?P<pinyin>[^\]]*)\](?:\s+\{(?P<jyutping>[^}]*)\})?\s*/(?P<defs>.+)/$"
)


@dataclass(slots=True)
class DictionaryEntry:
    term: str
    definitions: tuple[str, ...]
    source: str
    jyutping: str = ""


class DictionaryLoader:
    def load_file(self, path: str | Path, source: str) -> dict[str, list[DictionaryEntry]]:
        raw_path = Path(path)
        if not raw_path.exists():
            raise FileNotFoundError(f"Dictionary file not found: {raw_path}")

        by_term: dict[str, list[DictionaryEntry]] = {}
        with raw_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = self._parse_line(line, source)
                if entry is None:
                    continue
                by_term.setdefault(entry.term, []).append(entry)

        return by_term

    def merge(self, *dictionaries: dict[str, list[DictionaryEntry]]) -> dict[str, list[DictionaryEntry]]:
        merged: dict[str, list[DictionaryEntry]] = {}
        for source_map in dictionaries:
            for term, entries in source_map.items():
                merged.setdefault(term, []).extend(entries)
        return merged

    def _parse_line(self, line: str, source: str) -> DictionaryEntry | None:
        clean = line.strip()
        if not clean or clean.startswith("#"):
            return None

        match = _LINE_RE.match(clean)
        if not match:
            return None

        term = match.group("trad")
        defs_part = match.group("defs")
        definitions = tuple(part.strip() for part in defs_part.split("/") if part.strip())
        if not definitions:
            return None

        return DictionaryEntry(
            term=term,
            definitions=definitions,
            source=source,
            jyutping=(match.group("jyutping") or "").strip(),
        )
